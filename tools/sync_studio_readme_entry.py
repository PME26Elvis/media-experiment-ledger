from __future__ import annotations

from pathlib import Path

START = '<!-- STUDIO_ENTRY:START -->'
END = '<!-- STUDIO_ENTRY:END -->'

ENTRIES = {
    'README.md': f'''{START}
> [!TIP]
> **桌面版：Media Experiment Ledger Studio**  
> 跨平台、本機優先的 Atlas、物件偵測與媒體自動化桌面產品維護於 [`app-main`](https://github.com/PME26Elvis/media-experiment-ledger/tree/app-main)。  
> [下載 Studio Releases](https://github.com/PME26Elvis/media-experiment-ledger/releases?q=studio-v) · [桌面 App 說明](https://github.com/PME26Elvis/media-experiment-ledger/blob/app-main/app/README.md) · [完整規格](https://github.com/PME26Elvis/media-experiment-ledger/blob/app-main/docs/app/README.md)
{END}''',
    'README.en.md': f'''{START}
> [!TIP]
> **Desktop app: Media Experiment Ledger Studio**  
> The cross-platform, local-first Atlas, object-detection, and media-automation desktop product is maintained on [`app-main`](https://github.com/PME26Elvis/media-experiment-ledger/tree/app-main).  
> [Download Studio Releases](https://github.com/PME26Elvis/media-experiment-ledger/releases?q=studio-v) · [Desktop app guide](https://github.com/PME26Elvis/media-experiment-ledger/blob/app-main/app/README.md) · [Complete specification](https://github.com/PME26Elvis/media-experiment-ledger/blob/app-main/docs/app/README.md)
{END}''',
}


def replace_or_insert(path: Path, entry: str) -> bool:
    text = path.read_text(encoding='utf-8')
    if START in text or END in text:
        if text.count(START) != 1 or text.count(END) != 1:
            raise RuntimeError(f'Invalid Studio entry markers in {path}')
        before, remainder = text.split(START, 1)
        _, after = remainder.split(END, 1)
        updated = f'{before}{entry}{after}'
    else:
        paragraphs = text.split('\n\n', 3)
        if len(paragraphs) < 4:
            raise RuntimeError(f'Unable to locate introductory paragraph in {path}')
        updated = '\n\n'.join([paragraphs[0], paragraphs[1], paragraphs[2], entry, paragraphs[3]])
    if updated == text:
        return False
    path.write_text(updated, encoding='utf-8')
    return True


def main() -> int:
    changed = []
    for name, entry in ENTRIES.items():
        if replace_or_insert(Path(name), entry):
            changed.append(name)
    print(f'Updated: {", ".join(changed) if changed else "none"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
