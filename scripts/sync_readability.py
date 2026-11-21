#!/usr/bin/env python3
"""Refresh fact labels only; preserve each page's independently maintained content."""
import json,re
from pathlib import Path
from generate_pages import facts_html
ROOT=Path(__file__).resolve().parent.parent
def main():
 count=0
 for t in json.loads((ROOT/'data/topics_master.json').read_text(encoding='utf8')):
  p=ROOT/t['href'].strip('/')/'index.html'
  if not p.exists():continue
  s=p.read_text(encoding='utf8')
  pattern=r'(<h2 class="sec">公式窓口・確認先</h2><div class="official">)(.*?)(?=<a class="official-link")'
  # Existing facts are the prefix of the official source block. Preserve every source link.
  n,k=re.subn(pattern,lambda m:m[1]+facts_html(t.get('facts')),s,count=1,flags=re.S)
  if not k:raise ValueError('Facts boundary missing: '+str(p))
  if n!=s:p.write_text(n,encoding='utf8',newline='\n');count+=1
 print(f'Fact label pages updated: {count}')
if __name__=='__main__':main()
