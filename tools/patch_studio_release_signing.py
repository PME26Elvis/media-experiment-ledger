from __future__ import annotations

from pathlib import Path

path = Path('.github/workflows/app-release-core.yml')
text = path.read_text(encoding='utf-8')
old = '''      - name: Build Windows packages
        if: matrix.family == 'windows'
        shell: pwsh
        env:
          CSC_LINK: ${{ secrets.WIN_CSC_LINK }}
          CSC_KEY_PASSWORD: ${{ secrets.WIN_CSC_KEY_PASSWORD }}
          CSC_IDENTITY_AUTO_DISCOVERY: ${{ needs.preflight.outputs.channel == 'stable' && 'true' || 'false' }}
        run: npx electron-builder --win nsis portable ${{ matrix.arch_flag }} --publish never
      - name: Build Linux packages
        if: matrix.family == 'linux'
        shell: bash
        run: npx electron-builder --linux AppImage deb ${{ matrix.arch_flag }} --publish never
      - name: Build macOS packages
        if: matrix.family == 'macos'
        shell: bash
        env:
          CSC_LINK: ${{ secrets.MAC_CSC_LINK }}
          CSC_KEY_PASSWORD: ${{ secrets.MAC_CSC_KEY_PASSWORD }}
          CSC_IDENTITY_AUTO_DISCOVERY: ${{ needs.preflight.outputs.channel == 'stable' && 'true' || 'false' }}
          APPLE_ID: ${{ secrets.APPLE_ID }}
          APPLE_APP_SPECIFIC_PASSWORD: ${{ secrets.APPLE_APP_SPECIFIC_PASSWORD }}
          APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
        run: npx electron-builder --mac dmg zip ${{ matrix.arch_flag }} --publish never
'''
new = '''      - name: Build unsigned Windows prerelease packages
        if: matrix.family == 'windows' && needs.preflight.outputs.channel != 'stable'
        shell: pwsh
        env:
          CSC_IDENTITY_AUTO_DISCOVERY: 'false'
        run: npx electron-builder --win nsis portable ${{ matrix.arch_flag }} --publish never
      - name: Build signed Windows stable packages
        if: matrix.family == 'windows' && needs.preflight.outputs.channel == 'stable'
        shell: pwsh
        env:
          CSC_LINK: ${{ secrets.WIN_CSC_LINK }}
          CSC_KEY_PASSWORD: ${{ secrets.WIN_CSC_KEY_PASSWORD }}
          CSC_IDENTITY_AUTO_DISCOVERY: 'true'
        run: npx electron-builder --win nsis portable ${{ matrix.arch_flag }} --publish never
      - name: Build Linux packages
        if: matrix.family == 'linux'
        shell: bash
        run: npx electron-builder --linux AppImage deb ${{ matrix.arch_flag }} --publish never
      - name: Build unsigned macOS prerelease packages
        if: matrix.family == 'macos' && needs.preflight.outputs.channel != 'stable'
        shell: bash
        env:
          CSC_IDENTITY_AUTO_DISCOVERY: 'false'
        run: npx electron-builder --mac dmg zip ${{ matrix.arch_flag }} --publish never
      - name: Build signed and notarized macOS stable packages
        if: matrix.family == 'macos' && needs.preflight.outputs.channel == 'stable'
        shell: bash
        env:
          CSC_LINK: ${{ secrets.MAC_CSC_LINK }}
          CSC_KEY_PASSWORD: ${{ secrets.MAC_CSC_KEY_PASSWORD }}
          CSC_IDENTITY_AUTO_DISCOVERY: 'true'
          APPLE_ID: ${{ secrets.APPLE_ID }}
          APPLE_APP_SPECIFIC_PASSWORD: ${{ secrets.APPLE_APP_SPECIFIC_PASSWORD }}
          APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
        run: npx electron-builder --mac dmg zip ${{ matrix.arch_flag }} --publish never
'''
if text.count(old) != 1:
    raise RuntimeError(f'Expected exactly one packaging block, found {text.count(old)}')
updated = text.replace(old, new)
if '${{ secrets.MAC_CSC_LINK }}' not in updated or 'Build unsigned macOS prerelease packages' not in updated:
    raise RuntimeError('Patched release core is incomplete.')
path.write_text(updated, encoding='utf-8')
print('Patched prerelease/stable packaging environment separation.')
