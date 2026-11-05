"""Check that both release archives contain all package code and assets."""
from pathlib import Path
import sys
import tarfile
import zipfile


def main():
    root = Path(__file__).resolve().parents[1]
    dist = Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'dist'
    expected = {
        path.relative_to(root).as_posix()
        for path in (root / 'django_stripe').rglob('*')
        if path.is_file() and '__pycache__' not in path.parts
        and (path.suffix == '.py' or 'static' in path.parts or 'templates' in path.parts)
    }
    wheels = list(dist.glob('*.whl'))
    sdists = list(dist.glob('*.tar.gz'))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit('Expected exactly one wheel and one source distribution')
    with zipfile.ZipFile(wheels[0]) as archive:
        wheel_files = set(archive.namelist())
    with tarfile.open(sdists[0]) as archive:
        source_files = {name.partition('/')[2] for name in archive.getnames()}
    for kind, contents in [('wheel', wheel_files), ('sdist', source_files)]:
        missing = expected - contents
        if missing:
            raise SystemExit(f'{kind} is missing: {sorted(missing)}')
        print(f'{kind}: all {len(expected)} package files present')
    if any(name.startswith(('tests/', 'scripts/')) for name in wheel_files):
        raise SystemExit('Development files must not be installed as wheel packages')


if __name__ == '__main__':
    main()
