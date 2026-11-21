#!/usr/bin/env python3
"""Regenerate the reviewed site without replacing independently managed page sections."""
import subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
for args in [
 [sys.executable,'-X','utf8','scripts/generate_pages.py','--updated-only','--refresh-existing'],
 [sys.executable,'-X','utf8','scripts/sync_readability.py'],
 [sys.executable,'-X','utf8','scripts/build_enrichment.py'],
 [sys.executable,'-X','utf8','scripts/inject_parts.py'],
 ['node','scripts/build-search-index.mjs'],
 [sys.executable,'-X','utf8','scripts/build_sitemap.py'],
]:
 subprocess.run(args,cwd=ROOT,check=True)
