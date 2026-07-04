#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report_status.py — data/topics_master.json のstatus集計をカテゴリ別・全体別に表示する。

実行: python3 scripts/report_status.py
"""
import json
from collections import Counter
from pathlib import Path

LEDGER = Path(__file__).resolve().parent.parent / "data" / "topics_master.json"

STATUS_ORDER = ["draft", "ai-checked", "machine-verified", "human-verified", "published"]


def main():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    print(f"全項目数: {len(ledger)}")
    print()

    overall = Counter(i.get("status", "draft") for i in ledger)
    print("=== 全体 ===")
    for s in STATUS_ORDER:
        if overall.get(s):
            print(f"  {s}: {overall[s]}")
    print()

    by_cat = {}
    for i in ledger:
        by_cat.setdefault(i["category"], Counter())[i.get("status", "draft")] += 1

    print("=== カテゴリ別 ===")
    for cat, counts in by_cat.items():
        total = sum(counts.values())
        parts = ", ".join(f"{s}:{counts[s]}" for s in STATUS_ORDER if counts.get(s))
        print(f"  {cat} ({total}件): {parts}")


if __name__ == "__main__":
    main()
