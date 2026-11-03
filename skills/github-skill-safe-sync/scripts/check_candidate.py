#!/usr/bin/env python3
"""Read-only protection gate. Exit 3 means hold; exit 2 means invalid input."""
import argparse
import hashlib
import json
from pathlib import Path


def inventory(root):
    if not root.is_dir() or not (root / 'SKILL.md').is_file():
        raise ValueError('Missing skill directory or SKILL.md')
    result = {}
    for path in sorted(root.rglob('*')):
        key = str(path.relative_to(root))
        if path.is_symlink():
            result[key] = ('symlink', str(path.readlink()))
        elif path.is_file():
            result[key] = ('file', hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mode & 0o777)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill', required=True)
    parser.add_argument('--installed', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    args = parser.parse_args()
    try:
        policy = json.loads((Path(__file__).parent / 'protected-skills.json').read_text())
        protected = policy['protected_skills']
        if policy['version'] != 1 or not isinstance(protected, dict):
            raise ValueError('Invalid protection policy')
        required = {'walmart-out-of-stock-copy', 'github-skill-safe-sync'}
        if not required.issubset(protected):
            raise ValueError('Required protections missing')
        if args.skill not in protected:
            print('UNPROTECTED: baseline and local-edit checks still required')
            return 0
        if protected[args.skill]['mode'] != 'hold-local':
            raise ValueError('Invalid protection mode')
        if inventory(args.installed) == inventory(args.candidate):
            print('UNCHANGED: no replacement needed')
            return 0
        print('HOLD_LOCAL: protected skill differs; replacement forbidden')
        return 3
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'BLOCKED: {exc}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
