from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    command = [
        sys.executable,
        '-m',
        'unittest',
        'discover',
        '-s',
        'engine/tests',
        '-p',
        'test_*.py',
        '-v',
    ]
    environment = dict(os.environ)
    environment['PYTHONPATH'] = 'engine'
    completed = subprocess.run(
        command,
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = completed.stdout or ''
    Path('python-test.log').write_text(output, encoding='utf-8')
    print(output, end='')
    return completed.returncode


if __name__ == '__main__':
    raise SystemExit(main())
