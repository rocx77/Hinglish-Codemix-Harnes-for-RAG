"""Export the full PHINC vocabulary with corpus row-frequencies (TSV).

Reads Datasets/phinc_cleaned_step1to4.csv (Sentence_clean), lowercases,
splits on whitespace, counts per-token row-occurrences (a sentence counts a
token once, matching the collision diagnostics), and writes
reports/vocab_phinc_freq.tsv sorted by frequency desc.

This is build-pipeline Step 1 of the canonical-map pipeline (see
reports/hinglish_normalization_architecture.md) and the vocabulary file that
scripts/wordnet_hinglish_filter.py consumes with --vocab.

Run:  python scripts/export_phinc_vocab.py
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from collections import Counter

import pandas as pd

DATA = os.path.join(ROOT, "Datasets", "phinc_cleaned_step1to4.csv")
OUT = os.path.join(ROOT, "reports", "vocab_phinc_freq.tsv")

df = pd.read_csv(DATA, usecols=["Sentence_clean"])
df = df.dropna()

tok_freq = Counter()
vocab = set()
for s in df["Sentence_clean"].astype(str):
    toks = [t.lower() for t in s.split()]
    if not toks:
        continue
    seen = set(toks)
    vocab.update(seen)
    for t in seen:
        tok_freq[t] += 1

rows = sorted(tok_freq.items(), key=lambda kv: (-kv[1], kv[0]))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("token\trows_containing_token\n")
    for t, f in rows:
        fh.write(f"{t}\t{f}\n")

total_rows = len(df)
print(f"rows read: {total_rows}")
print(f"unique tokens (case-insensitive): {len(vocab)}")
print(f"total token row-occurrence mass: {sum(tok_freq.values())}")
print(f"frequency-sorted vocab written to: {OUT} ({len(rows)} data rows)")