#!/usr/bin/env python3
"""Extract every routed action from Jellyfin.Api/Controllers/*.cs.

Emits JSON: one record per (HTTP method, route template) pair.
"""
import json
import os
import re
import sys

CTRL_DIR = "Jellyfin.Api/Controllers"

HTTP_ATTR = re.compile(r'^\[Http(Get|Post|Put|Delete|Head|Patch|Options)(?:\(\s*(?:"([^"]*)")?[^)]*\))?\]')
ROUTE_ATTR = re.compile(r'^\[Route\("([^"]*)"\)\]')
CLASS_DECL = re.compile(r'^public\s+(?:sealed\s+)?class\s+(\w+)\s*:')
METHOD_DECL = re.compile(r'^\s*(?:public|internal|private|protected)\s+.*\(')

def strip_attr(line):
    """Return attribute body if line (any indent) is a single-line attribute."""
    s = line.strip()
    if s.startswith('[') and s.endswith(']'):
        return s
    return None

def parse(path):
    src = open(path, encoding='utf-8').read()
    lines = src.split('\n')
    fname = os.path.basename(path)

    # --- class level ---
    class_name = None
    class_line = None
    for i, ln in enumerate(lines):
        m = CLASS_DECL.match(ln)
        if m:
            class_name = m.group(1)
            class_line = i
            break
    if class_name is None:
        return []

    # walk backwards from class decl collecting column-0 attributes
    class_attrs = []
    j = class_line - 1
    while j >= 0:
        s = lines[j].strip()
        if s.startswith('[') and s.endswith(']') and not lines[j].startswith(' '):
            class_attrs.append(s)
            j -= 1
        elif s.startswith('///') or s == '':
            j -= 1
        else:
            break

    base_route = None
    for a in class_attrs:
        m = ROUTE_ATTR.match(a)
        if m:
            base_route = m.group(1)
    if base_route is None:
        base_route = '[controller]'
    base_route = base_route.replace('[controller]', class_name[:-len('Controller')])

    class_hidden = any('ApiExplorerSettings' in a and 'IgnoreApi = true' in a for a in class_attrs)
    class_obsolete = any(a.startswith('[Obsolete') for a in class_attrs)

    # --- method level ---
    records = []
    buf = []          # (attr_text, lineno)
    buf_start = None
    in_body_depth = 0

    for i in range(class_line + 1, len(lines)):
        raw = lines[i]
        s = raw.strip()
        if not s or s.startswith('///') or s.startswith('//'):
            continue
        a = strip_attr(raw)
        if a is not None and raw.startswith('    [') and not raw.startswith('        '):
            if not buf:
                buf_start = i + 1
            buf.append(a)
            continue
        # multi-line attribute continuation (e.g. [Authorize(\n  Policy = ...)])
        if buf and raw.startswith('    ') and not raw.startswith('        ') and s.endswith(')]'):
            buf[-1] = buf[-1] + ' ' + s
            continue
        if buf:
            # this line should be the member declaration
            httpattrs = []
            hidden = class_hidden
            obsolete = class_obsolete
            authorize = None
            for k, at in enumerate(buf):
                m = HTTP_ATTR.match(at)
                if m:
                    httpattrs.append((m.group(1).upper(), m.group(2) or '', buf_start + k))
                if 'ApiExplorerSettings' in at and 'IgnoreApi = true' in at:
                    hidden = True
                if at.startswith('[Obsolete'):
                    obsolete = True
                if at.startswith('[Authorize'):
                    pm = re.search(r'Policy\s*=\s*Policies\.(\w+)', at)
                    authorize = pm.group(1) if pm else 'Default'
            if httpattrs:
                mm = re.search(r'\b(\w+)\s*\(', s)
                action = mm.group(1) if mm else '?'
                for (verb, tmpl, ln) in httpattrs:
                    if tmpl:
                        route = (base_route + '/' + tmpl) if base_route else tmpl
                    else:
                        route = base_route
                    route = '/' + route.strip('/')
                    records.append({
                        'route': route,
                        'method': verb,
                        'controller': class_name,
                        'file': f'{CTRL_DIR}/{fname}',
                        'attr_line': ln,
                        'action': action,
                        'hidden': hidden,
                        'hidden_scope': 'class' if class_hidden else ('method' if hidden else ''),
                        'obsolete': obsolete,
                        'authorize': authorize,
                    })
            buf = []
            buf_start = None
    return records

all_records = []
for f in sorted(os.listdir(CTRL_DIR)):
    if f.endswith('.cs'):
        all_records.extend(parse(os.path.join(CTRL_DIR, f)))

json.dump(all_records, sys.stdout, indent=1)
