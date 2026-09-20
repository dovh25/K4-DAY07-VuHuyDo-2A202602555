import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.chunking import ChunkingStrategyComparator

def strip_frontmatter(text: str) -> str:
    """Strip YAML frontmatter from markdown file content."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text.strip()

def run_baseline():
    comparator = ChunkingStrategyComparator()
    docs = [
        Path("data/ecommerce/return-window.md"),
        Path("data/ecommerce/return-shipping-and-packaging.md"),
        Path("data/ecommerce/seller-return-refund-obligations.md"),
    ]
    
    print("=== BASELINE ANALYSIS ON 3 E-COMMERCE DOCUMENTS ===")
    for doc_path in docs:
        if not doc_path.exists():
            print(f"File not found: {doc_path}")
            continue
        raw_text = doc_path.read_text(encoding="utf-8")
        clean_text = strip_frontmatter(raw_text)
        print(f"\nDocument: {doc_path.name} ({len(clean_text)} chars)")
        res = comparator.compare(clean_text, chunk_size=300)
        for strat, stats in res.items():
            print(f"  - Strategy: {strat:15} | Count: {stats['count']:2} | Avg Len: {stats['avg_length']:.1f}")

if __name__ == "__main__":
    run_baseline()
