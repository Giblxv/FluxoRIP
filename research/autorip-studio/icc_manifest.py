"""Inventário determinístico ICC/ICM, sem seguir diretórios ou arquivos symlink.

Não interpreta CMYKW e não carrega bibliotecas de transformação de cores.
"""
import argparse
import json
import os
from pathlib import Path

from icc_inspect import ICCError, inspect_icc

PROFILE_SUFFIXES = {'.icc', '.icm'}
MAX_PROFILE_COUNT = 10_000


def inventory(root, *, max_files=MAX_PROFILE_COUNT):
    """Percorre apenas diretórios físicos a partir da raiz fornecida.

    Inclui symlinks com extensão ICC/ICM no inventário como ignorados,
    sem os abrir. Diretórios symlink não entram no percurso, mesmo que
    apontem para dentro da árvore ou formem ciclos.
    """
    root = Path(root)
    if not isinstance(max_files, int) or isinstance(max_files, bool) or not 1 <= max_files <= MAX_PROFILE_COUNT:
        raise ValueError('max_files must be between 1 and 10000')
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Directory not found or symbolic-link root rejected')

    paths = []
    skipped_directories = []
    for current, dirs, names in os.walk(root, topdown=True, followlinks=False):
        here = Path(current)
        # Do not ever descend into a directory symlink. All subsequent names
        # are inspected without following a directory link.
        safe_dirs = []
        for name in sorted(dirs, key=lambda n: (n.casefold(), n)):
            candidate = here / name
            if candidate.is_symlink():
                skipped_directories.append(candidate.relative_to(root).as_posix())
            else:
                safe_dirs.append(name)
        dirs[:] = safe_dirs
        for name in names:
            p = here / name
            if p.suffix.lower() not in PROFILE_SUFFIXES:
                continue
            paths.append(p)
            if len(paths) > max_files:
                raise ValueError('Profile count exceeds limit')

    paths.sort(key=lambda p: (p.relative_to(root).as_posix().casefold(), p.relative_to(root).as_posix()))
    entries, hashes = [], {}
    for p in paths:
        relative = p.relative_to(root).as_posix()
        if p.is_symlink():
            entries.append({'path': relative, 'status': 'skipped_symlink'})
            continue
        try:
            details = inspect_icc(p)
            digest = details['sha256']
            entries.append({'path': relative, 'status': 'valid_header', **details})
            hashes.setdefault(digest, []).append(relative)
        except (ICCError, OSError, ValueError) as exc:
            entries.append({'path': relative, 'status': 'invalid', 'error': str(exc)})
    return {'root': str(root), 'total': len(paths),
            'valid_headers': sum(e['status'] == 'valid_header' for e in entries),
            'entries': entries,
            'skipped_symlink_directories': sorted(skipped_directories, key=lambda n: (n.casefold(), n)),
            'duplicate_sha256': {h: v for h, v in hashes.items() if len(v) > 1},
            'warning': 'ICC header inspection does not prove print suitability, white ink or CMYKW channel order.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Safe read-only ICC/ICM metadata inventory')
    parser.add_argument('directory')
    parser.add_argument('--max-files', type=int, default=MAX_PROFILE_COUNT)
    args = parser.parse_args()
    print(json.dumps(inventory(args.directory, max_files=args.max_files), indent=2, ensure_ascii=False))
