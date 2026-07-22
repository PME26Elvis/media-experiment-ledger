from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent
ENGINE_ROOT = APP_ROOT / 'engine'
DIST_ROOT = APP_ROOT / 'engine-bin'
BUILD_ROOT = APP_ROOT / '.engine-build'
EXECUTABLE_NAME = 'mel-engine.exe' if os.name == 'nt' else 'mel-engine'


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    print('+', subprocess.list2cmdline(command), flush=True)
    return subprocess.run(command, check=True, text=True, **kwargs)


def build() -> Path:
    shutil.rmtree(DIST_ROOT, ignore_errors=True)
    shutil.rmtree(BUILD_ROOT, ignore_errors=True)
    DIST_ROOT.mkdir(parents=True, exist_ok=True)
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)

    data_separator = ';' if os.name == 'nt' else ':'
    command = [
        sys.executable,
        '-m',
        'PyInstaller',
        '--noconfirm',
        '--clean',
        '--onedir',
        '--name',
        'mel-engine',
        '--distpath',
        str(DIST_ROOT),
        '--workpath',
        str(BUILD_ROOT / 'work'),
        '--specpath',
        str(BUILD_ROOT / 'spec'),
        '--paths',
        str(ENGINE_ROOT),
        '--paths',
        str(REPO_ROOT / 'tools'),
        '--hidden-import',
        'yolo_core',
        '--hidden-import',
        'nanodet_core',
        '--collect-all',
        'onnxruntime',
        '--copy-metadata',
        'onnxruntime',
        '--add-data',
        f"{REPO_ROOT / 'object-detection' / 'coco-80.json'}{data_separator}mel_engine/data",
        str(ENGINE_ROOT / 'mel_engine_entry.py'),
    ]
    run(command, cwd=APP_ROOT)
    executable = DIST_ROOT / 'mel-engine' / EXECUTABLE_NAME
    if not executable.is_file():
        raise RuntimeError(f'PyInstaller did not create {executable}')
    return executable


def smoke(executable: Path) -> None:
    with tempfile.TemporaryDirectory() as directory:
        request = json.dumps({
            'operation': 'scan',
            'job_id': 'engine-build-smoke',
            'image_path': directory,
            'video_path': '',
        }) + '\n'
        completed = run(
            [str(executable)],
            cwd=executable.parent,
            input=request,
            capture_output=True,
            timeout=120,
        )
        events = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
        results = [event for event in events if event.get('type') == 'result']
        errors = [event for event in events if event.get('type') == 'error']
        if errors or not results or results[-1].get('data', {}).get('count') != 0:
            raise RuntimeError(
                f'Engine smoke failed. stdout={completed.stdout!r} stderr={completed.stderr!r}',
            )


def write_manifest(executable: Path) -> None:
    files = []
    for path in sorted(executable.parent.rglob('*')):
        if path.is_file():
            files.append({
                'path': path.relative_to(executable.parent).as_posix(),
                'size_bytes': path.stat().st_size,
                'sha256': sha256(path),
            })
    manifest = {
        'schema_version': 1,
        'engine_version': '0.1.0',
        'python_version': platform.python_version(),
        'platform': platform.system().lower(),
        'machine': platform.machine().lower(),
        'entrypoint': executable.relative_to(APP_ROOT).as_posix(),
        'entrypoint_sha256': sha256(executable),
        'file_count': len(files),
        'total_bytes': sum(item['size_bytes'] for item in files),
        'files': files,
    }
    manifest_path = executable.parent / 'engine-build-manifest.json'
    temporary = manifest_path.with_suffix('.tmp')
    temporary.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    temporary.replace(manifest_path)
    print(json.dumps({
        'engine': str(executable),
        'files': manifest['file_count'],
        'bytes': manifest['total_bytes'],
        'sha256': manifest['entrypoint_sha256'],
    }, indent=2))


def main() -> int:
    executable = build()
    smoke(executable)
    write_manifest(executable)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
