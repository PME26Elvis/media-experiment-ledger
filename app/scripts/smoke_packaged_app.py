from __future__ import annotations

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
OUTPUT_PATH = APP_ROOT / 'packaged-smoke-evidence.json'
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


def persist_evidence(
    *,
    executable: Path | None,
    completed: subprocess.CompletedProcess[str] | None,
    app_evidence: dict[str, object] | None,
    failure: str | None,
) -> dict[str, object]:
    evidence: dict[str, object] = {
        **(app_evidence or {}),
        'runnerSchemaVersion': 3,
        'executable': str(executable.relative_to(APP_ROOT)) if executable else None,
        'exitCode': completed.returncode if completed else None,
        'stdoutTail': (completed.stdout or '')[-12000:] if completed else '',
        'stderrTail': (completed.stderr or '')[-12000:] if completed else '',
        'runnerFailure': failure,
    }
    OUTPUT_PATH.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    return evidence


def main() -> int:
    available = candidates()
    if not available:
        evidence = persist_evidence(
            executable=None,
            completed=None,
            app_evidence=None,
            failure=f'No packaged executable found below {RELEASE_ROOT}',
        )
        raise RuntimeError(str(evidence['runnerFailure']))
    executable = available[0]
    with tempfile.TemporaryDirectory(prefix='mel-packaged-smoke-') as directory:
        root = Path(directory)
        result_path = root / 'smoke-result.json'
        user_data = root / 'user-data'
        user_data.mkdir(parents=True)
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
                timeout=180,
            )
        except subprocess.TimeoutExpired as error:
            completed = subprocess.CompletedProcess(
                command,
                124,
                stdout=error.stdout or '',
                stderr=error.stderr or '',
            )
            evidence = persist_evidence(
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
        if not isinstance(route_checks, int) or route_checks < MINIMUM_ROUTE_AUDIT_CHECKS:
            failures.append(f'routeAuditChecks<{MINIMUM_ROUTE_AUDIT_CHECKS}')
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
