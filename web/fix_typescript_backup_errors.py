#!/usr/bin/env python3
"""Fight Royale: stop TypeScript from compiling Python installer's source backups.

From the Fight Royale `web` directory:
    python fix_typescript_backup_errors.py --dry-run
    python fix_typescript_backup_errors.py
    npx tsc --noEmit -p .

Changes ONLY web/tsconfig.json. It does not delete, rename or rewrite backups,
or touch active game code. No third-party Python packages required.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
import tempfile


class ConfigError(RuntimeError):
    pass


def without_comments(s: str) -> str:
    """Replace JSONC comments with whitespace (preserving character offsets)."""
    out = list(s)
    i = 0
    quoted = False
    escaped = False
    while i < len(s):
        c = s[i]
        if quoted:
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == '"':
                quoted = False
            i += 1
            continue
        if c == '"':
            quoted = True
            i += 1
            continue
        if c == '/' and i + 1 < len(s) and s[i + 1] == '/':
            j = i
            while j < len(s) and s[j] not in '\r\n':
                out[j] = ' '
                j += 1
            i = j
            continue
        if c == '/' and i + 1 < len(s) and s[i + 1] == '*':
            j = i
            end = s.find('*/', i + 2)
            if end == -1:
                raise ConfigError('Unterminated /* comment in tsconfig.json')
            while j < end + 2:
                if s[j] not in '\r\n':
                    out[j] = ' '
                j += 1
            i = j
            continue
        i += 1
    return ''.join(out)


def jsonc_parse(raw: str) -> dict:
    s = without_comments(raw)
    # Eliminate trailing commas in JSONC without modifying quoted strings.
    chars = list(s)
    quoted = escaped = False
    for i, c in enumerate(s):
        if quoted:
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == '"':
                quoted = False
            continue
        if c == '"':
            quoted = True
        elif c == ',':
            j = i + 1
            while j < len(s) and s[j].isspace():
                j += 1
            if j < len(s) and s[j] in ']}':
                chars[i] = ' '
    try:
        cfg = json.loads(''.join(chars))
    except json.JSONDecodeError as e:
        raise ConfigError('Cannot safely read tsconfig.json: ' + str(e)) from e
    if not isinstance(cfg, dict):
        raise ConfigError('tsconfig.json root must be an object')
    return cfg


def find_root_key_array(s: str, wanted: str):
    """Find a root-level JSON string property with an array value."""
    clean = without_comments(s)
    depth = 0
    i = 0
    while i < len(clean):
        c = clean[i]
        if c == '"':
            end = i + 1
            escaped = False
            while end < len(clean):
                if escaped:
                    escaped = False
                elif clean[end] == '\\':
                    escaped = True
                elif clean[end] == '"':
                    break
                end += 1
            if end >= len(clean):
                raise ConfigError('Unterminated string in tsconfig.json')
            if depth == 1:
                try:
                    key = json.loads(clean[i:end + 1])
                except json.JSONDecodeError:
                    key = None
                j = end + 1
                while j < len(clean) and clean[j].isspace():
                    j += 1
                if key == wanted and j < len(clean) and clean[j] == ':':
                    j += 1
                    while j < len(clean) and clean[j].isspace():
                        j += 1
                    if j >= len(clean) or clean[j] != '[':
                        raise ConfigError('Existing "exclude" is not an array; refusing to overwrite it')
                    k, bracket, in_string, esc = j, 0, False, False
                    while k < len(clean):
                        ch = clean[k]
                        if in_string:
                            if esc:
                                esc = False
                            elif ch == '\\':
                                esc = True
                            elif ch == '"':
                                in_string = False
                        else:
                            if ch == '"':
                                in_string = True
                            elif ch == '[':
                                bracket += 1
                            elif ch == ']':
                                bracket -= 1
                                if bracket == 0:
                                    return (j, k)
                        k += 1
                    raise ConfigError('Unclosed exclude array')
            i = end + 1
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        i += 1
    return None


def patch_tsconfig(src: str) -> tuple[str, bool]:
    cfg = jsonc_parse(src)
    nl = '\r\n' if '\r\n' in src else '\n'
    target = 'scripts/backups'
    if 'exclude' in cfg:
        exclude = cfg['exclude']
        if not isinstance(exclude, list) or not all(isinstance(x, str) for x in exclude):
            raise ConfigError('Existing exclude must be an array of strings')
        if any(x.replace('\\', '/').rstrip('/') in ('scripts/backups', 'scripts/backups/**') for x in exclude):
            return src, False
        span = find_root_key_array(src, 'exclude')
        if span is None:
            raise ConfigError('Could not locate the root exclude array')
        a, b = span
        # Only the exclude list is normalized; all other tsconfig text is preserved.
        newlist = json.dumps([*exclude, target], ensure_ascii=False)
        revised = src[:a] + newlist + src[b + 1:]
    else:
        clean = without_comments(src)
        start = clean.find('{')
        if start < 0:
            raise ConfigError('No root object found in tsconfig.json')
        j = start + 1
        while j < len(clean) and clean[j].isspace():
            j += 1
        empty = j < len(clean) and clean[j] == '}'
        injection = nl + '  "exclude": ["node_modules", "scripts/backups"]' + ('' if empty else ',')
        revised = src[:start + 1] + injection + src[start + 1:]
    revised_cfg = jsonc_parse(revised)
    if target not in revised_cfg.get('exclude', []):
        raise ConfigError('Post-edit validation did not retain scripts/backups exclusion')
    return revised, True


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dry-run', action='store_true', help='Preview without modifying files')
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parent,
                   help='Fight Royale web folder (default: directory containing script)')
    a = p.parse_args()
    path = a.root.resolve() / 'tsconfig.json'
    if not path.is_file():
        print('ERROR: tsconfig.json not found at ' + str(path), file=sys.stderr)
        print('Place the script in the web directory, or pass --root <web-directory>.', file=sys.stderr)
        return 1
    original_bytes = path.read_bytes()
    bom = original_bytes.startswith(b'\xef\xbb\xbf')
    try:
        original = original_bytes.decode('utf-8-sig')
        updated, changed = patch_tsconfig(original)
    except (UnicodeError, ConfigError) as e:
        print('ERROR: ' + str(e), file=sys.stderr)
        return 1
    if not changed:
        print('Already fixed: TypeScript is configured to exclude scripts/backups.')
        return 0
    print('Will update: ' + str(path))
    print('Adding: scripts/backups to tsconfig.json exclude (no game TS files changed).')
    if a.dry_run:
        print('DRY RUN PASSED: nothing written.')
        return 0
    backup = path.with_name('tsconfig.json.before_exclude_backups_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.bak')
    staged = None
    try:
        backup.write_bytes(original_bytes)
        payload = (b'\xef\xbb\xbf' if bom else b'') + updated.encode('utf-8')
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.tsconfig_patch_', suffix='.tmp', delete=False) as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
            staged = Path(f.name)
        staged.replace(path)
    except OSError as e:
        if backup.is_file():
            try:
                path.write_bytes(original_bytes)
            except OSError as rollback_error:
                print('ROLLBACK FAILED: ' + str(rollback_error), file=sys.stderr)
        print('ERROR: ' + str(e), file=sys.stderr)
        return 1
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)
    print('Fixed. tsconfig backup saved: ' + str(backup))
    print('Next: npx tsc --noEmit -p .')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
