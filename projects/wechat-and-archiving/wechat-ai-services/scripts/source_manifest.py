#!/usr/bin/env python3
"""Explicitly refresh publication hashes after source review; no service access."""
import argparse
import hashlib
import json
from public_check import ROOT, candidates

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--write', action='store_true', help='Write reviewed source hashes; otherwise print them.')
args = parser.parse_args()
manifest = ROOT / 'source-files.json'
value = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in candidates() if p != manifest}
text = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
if args.write:
    manifest.write_text(text)
else:
    print(text, end='')
