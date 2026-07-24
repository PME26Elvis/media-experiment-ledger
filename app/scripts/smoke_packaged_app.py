from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = APP_ROOT / 'release'
PRODUCT_NAME = 'Media Experiment Ledger Studio'
DEFAULT_OUTPUT_PATH = APP_ROOT / 'packaged-smoke-evidence.json'
MINIMUM_ROUTE_AUDIT_CHECKS = 130


def candidates() -> list[Path]:
    if sys.platform == 'win32':
        return sorted(
            path
            for path in RELEASE_ROOT.glob('**/*.exe')
            if 'unpacked' in path.as_posix().lower()
            and path.name == f'{PRODUCT_NAME}.exe'
        )
    if sys.platform == 'darwin':
        return sorted(RELEASE_ROOT.glob(f'**/{PRODUCT_NAME}.app/Contents/MacOS/{PRODUCT_NAME}'))
    exact = sorted(RELEASE_ROOT.glob('**/linux-unpacked/media-experiment-ledger-studio'))
    if exact:
        return exact
    return sorted(
        path
        for path in RELEASE_ROOT.glob('**/linux-unpacked/*')
        if path.is_file() and os.access(path, os.X_OK)
    )


def executable_label(executable: Path | None) -> str | None:
    if executable is None:
        return None
    try:
        return str(executable.relative_to(APP_ROOT))
    except ValueError:
        return str(executable)


def persist_evidence(
    *,
    output_path: Path,
    executable: Path | None,
    completed: subprocess.CompletedProcess[str] | None,
    app_evidence: dict[str, object] | None,
    failure: str | None,
) -> dict[str, object]:
    evidence: dict[str, object] = {
        **(app_evidence or {}),
        'runnerSchemaVersion': 4,
        'executable': executable_label(executable),
        'exitCode': completed.returncode if completed else None,
        'stdoutTail': (completed.stdout or '')[-12000:] if completed else '',
        'stderrTail': (completed.stderr or '')[-12000:] if completed else '',
        'runnerFailure': failure,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    return evidence


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Launch and qualify a packaged or installed MEL Studio executable.')
    parser.add_argument('--executable', type=Path, help='Explicit installed executable. Defaults to an unpacked package below app/release.')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT_PATH, help='Evidence JSON output path.')
    parser.add_argument('--user-data', type=Path, help='Persistent user-data directory. Defaults to an isolated temporary directory.')
    parser.add_argument('--timeout', type=int, default=180, help='Maximum launch duration in seconds.')
    parser.add_argument('--minimum-route-checks', type=int, default=MINIMUM_ROUTE_AUDIT_CHECKS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = args.output.resolve()
    if args.executable:
        available = [args.executable.expanduser().resolve()]
    else:
        available = candidates()
    if not available:
        evidence = persist_evidence(
            output_path=output_path,
            executable=None,
            completed=None,
            app_evidence=None,
            failure=f'No packaged executable found below {RELEASE_ROOT}',
        )
        raise RuntimeError(str(evidence['runnerFailure']))
    executable = available[0]
    if not executable.is_file():
        evidence = persist_evidence(
            output_path=output_path,
            executable=executable,
            completed=None,
            app_evidence=None,
            failure=f'Executable does not exist: {executable}',
        )
        raise RuntimeError(str(evidence['runnerFailure']))

    with tempfile.TemporaryDirectory(prefix='mel-packaged-smoke-') as directory:
        root = Path(directory)
        result_path = root / 'smoke-result.json'
        user_data = args.user_data.expanduser().resolve() if args.user_data else root / 'user-data'
        user_data.mkdir(parents=True, exist_ok=True)
        environment = {
            **os.environ,
            'MEL_SMOKE_TEST': '1',
            'MEL_SMOKE_RESULT_PATH': str(result_path),
            'XDG_CONFIG_HOME': str(user_data),
            'HOME': str(user_data),
            'APPDATA': str(user_data),
            'LOCALAPPDATA': str(user_data),
        }
        command = [str(executable), f'--user-data-dir={user_data}']
        if sys.platform.startswith('linux'):
            xvfb = shutil.which('xvfb-run')
            if not xvfb:
                evidence = persist_evidence(
                    output_path=output_path,
                    executable=executable,
                    completed=None,
                    app_evidence=None,
                    failure='xvfb-run is required for the packaged Linux smoke test.',
                )
                raise RuntimeError(str(evidence['runnerFailure']))
            command = [xvfb, '-a', *command, '--no-sandbox']
        print('+', subprocess.list2cmdline(command), flush=True)
        completed: subprocess.CompletedProcess[str] | None = None
        try:
            completed = subprocess.run(
                command,
                cwd=executable.parent,
                env=environment,
                text=True,
                capture_output=True,
                timeout=args.timeout,
            )
        except subprocess.TimeoutExpired as error:
            completed = subprocess.CompletedProcess(
                command,
                124,
                stdout=error.stdout or '',
                stderr=error.stderr or '',
            )
            evidence = persist_evidence(
                output_path=output_path,
                executable=executable,
                completed=completed,
                app_evidence=None,
                failure='Packaged app smoke timed out.',
            )
            raise RuntimeError(f'Packaged smoke timed out; evidence={evidence}') from error

        app_evidence: dict[str, object] | None = None
        failure: str | None = None
        if result_path.is_file():
            try:
                app_evidence = json.loads(result_path.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, OSError) as error:
                failure = f'Invalid app smoke result: {type(error).__name__}: {error}'
        else:
            failure = 'Packaged app did not write smoke evidence.'

        evidence = persist_evidence(
            output_path=output_path,
            executable=executable,
            completed=completed,
            app_evidence=app_evidence,
            failure=failure,
        )
        expected = {
            'packaged': True,
            'rendererLoaded': True,
            'preloadBridge': True,
            'routeAuditPassed': True,
            'engineReady': True,
        }
        failures = [key for key, value in expected.items() if evidence.get(key) is not value]
        if not (evidence.get('database') or {}).get('ok') if isinstance(evidence.get('database'), dict) else True:
            failures.append('database.ok')
        route_checks = evidence.get('routeAuditChecks')
        if not isinstance(route_checks, int) or route_checks < args.minimum_route_checks:
            failures.append(f'routeAuditChecks<{args.minimum_route_checks}')
        if completed.returncode != 0:
            failures.append(f'exit={completed.returncode}')
        if failure:
            failures.append(failure)
        if failures:
            raise RuntimeError(f'Packaged smoke failed: {", ".join(failures)}; evidence={evidence}')
        print(json.dumps(evidence, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
