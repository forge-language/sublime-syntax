#!/usr/bin/env python3
"""Build Forge.sublime-package from a fixed, reproducible syntax-only allowlist."""
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    'LICENSE', 'README.md', 'Forge.sublime-syntax', 'Forge.sublime-settings',
    'Forge.sublime-build', 'Comments.tmPreferences', 'Main.sublime-menu',
    'Default.sublime-commands', 'snippets/for.sublime-snippet',
    'snippets/function.sublime-snippet', 'snippets/import.sublime-snippet',
    'snippets/native-main.sublime-snippet',
)


def build():
    target = ROOT / 'dist/Forge.sublime-package'
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp')
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in sorted(FILES):
                source = ROOT / name
                if source.is_symlink() or not source.is_file():
                    raise ValueError('Missing or unsafe package resource: ' + name)
                entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, source.read_bytes())
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_name(target.name + '.sha256').write_text(digest + '  ' + target.name + '\n')
    print(target)
    print(digest)
    return target


if __name__ == '__main__':
    build()
