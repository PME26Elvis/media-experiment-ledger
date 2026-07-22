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


def main() -> int:
    available = candidates()
    if not available:
        raise RuntimeError(f'No packaged executable found below {RELEASE_ROOT}')
    executable = available[0]
    with tempfile.TemporaryDirectory(prefix='mel-packaged-smoke-') as directory:
        result_path = Path(directory) / 'smoke-result.json'
        user_data = Path(directory) / 'user-data'
        environment = {
            **os.environ,
            'MEL_SMOKE_TEST': '1',
            'MEL_SMOKE_RESULT_PATH': str(result_path),
            'XDG_CONFIG_HOME': str(user_data),
            'HOME': str(user_data),
            'APPDATA': str(user_data),
            'LOCALAPPDATA': str(user_data),
        }
        command = [str(executable)]
        if sys.platform.startswith('linux'):
            xvfb = shutil.which('xvfb-run')
            if not xvfb:
                raise RuntimeError('xvfb-run is required for the packaged Linux smoke test.')
            command = [xvfb, '-a', *command]
        print('+', subprocess.list2cmdline(command), flush=True)
        completed = subprocess.run(
            command,
            cwd=executable.parent,
            env=environment,
            text=True,
            capture_output=True,
            timeout=120,
        )
        if not result_path.is_file():
            raise RuntimeError(
                f'Packaged app did not write smoke evidence. code={completed.returncode}\n'
                f'stdout={completed.stdout}\nstderr={completed.stderr}'
            )
        evidence = json.loads(result_path.read_text(encoding='utf-8'))
        expected = {
            'packaged': True,
            'rendererLoaded': True,
            'preloadBridge': True,
            'engineReady': True,
        }
        failures = [key for key, value in expected.items() if evidence.get(key) is not value]
        if not (evidence.get('database') or {}).get('ok'):
            failures.append('database.ok')
        if completed.returncode != 0:
            failures.append(f'exit={completed.returncode}')
        output_path = APP_ROOT / 'packaged-smoke-evidence.json'
        output_path.write_text(json.dumps({
            **evidence,
            'executable': str(executable.relative_to(APP_ROOT)),
            'exitCode': completed.returncode,
            'stdoutTail': completed.stdout[-4000:],
            'stderrTail': completed.stderr[-4000:],
        }, indent=2), encoding='utf-8')
        if failures:
            raise RuntimeError(f'Packaged smoke failed: {", ".join(failures)}; evidence={evidence}')
        print(json.dumps(evidence, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
