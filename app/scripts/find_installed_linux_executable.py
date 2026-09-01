from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Locate the main executable installed by a deb package.')
    parser.add_argument('--package', required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    entries = subprocess.check_output(['dpkg', '-L', args.package], text=True).splitlines()
    executable_names = {
        'media-experiment-ledger-studio',
        'Media Experiment Ledger Studio',
    }
    candidates: list[Path] = []
    for raw in entries:
        path = Path(raw)
        if not path.is_file() or not os.access(path, os.X_OK):
            continue
        if path.name in executable_names:
            print(path)
            return 0
        if '/opt/' in path.as_posix() and path.suffix == '' and path.name not in {
            'chrome-sandbox',
            'chrome_crashpad_handler',
            'mel-engine',
        }:
            candidates.append(path)
    if len(candidates) == 1:
        print(candidates[0])
        return 0
    listing = '\n'.join(entries)
    raise SystemExit(f'Unable to identify one installed application executable for {args.package}. dpkg -L output:\n{listing}')


if __name__ == '__main__':
    raise SystemExit(main())
