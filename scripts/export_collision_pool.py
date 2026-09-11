"""Exhaustive (not sampled) frequency-sorted export of the length<=4 ENGLISH pool.

Read-only on src/token_router.py. Reads phinc_cleaned_step1to4.csv
(Sentence_clean). Rebuilds the vocabulary + classifications exactly like
scripts/token_collision_diagnostic.py, then exports EVERY length<=4 ENGLISH
token with its corpus frequency (rows containing the token), sorted desc,
plus cumulative-coverage ranks for 80% and 95% of the pool's frequency mass.

Also writes reports/collision_len4_en_freq_sorted.tsv for downstream override
building.

Run:  .venv310\\Scripts\\python.exe scripts\\export_collision_pool.py
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from collections import Counter

import pandas as pd

from src.token_router import classify_token, Category

DATA = os.path.join(ROOT, "Datasets", "phinc_cleaned_step1to4.csv")
OUT = os.path.join(ROOT, "reports", "collision_len4_en_freq_sorted.tsv")

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

classify = {t: classify_token(t) for t in vocab}
pool = sorted(
    t for t, c in classify.items()
    if len(t) <= 4 and c == Category.ENGLISH
)
print(f"unique tokens: {len(vocab)}")
print(f"len<=4 ENGLISH pool: {len(pool)}  (expected 2383)")

pool.sort(key=lambda t: tok_freq[t], reverse=True)

total_mass = sum(tok_freq[t] for t in pool)
cum = 0
rank_80 = rank_95 = None
rows = []
for i, t in enumerate(pool, start=1):
    f = tok_freq[t]
    rows.append((t, len(t), f))
    cum += f
    if rank_80 is None and cum >= 0.80 * total_mass:
        rank_80 = i
    if rank_95 is None and cum >= 0.95 * total_mass:
        rank_95 = i

def cum_pct(n):
    return 100.0 * sum(r[2] for r in rows[:n]) / total_mass

print(f"pool total row-occurrences (frequency mass): {total_mass}")
print(f"80% coverage reached at rank: {rank_80}  (cum {cum_pct(rank_80):.1f}%)")
print(f"95% coverage reached at rank: {rank_95}  (cum {cum_pct(rank_95):.1f}%)")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("token\tlength\trows_containing_token\n")
    for t, L, f in rows:
        fh.write(f"{t}\t{L}\t{f}\n")
print(f"\nfull table written to: {OUT} ({len(rows)} data rows)")
print("\n=== FULL TABLE (token | length | frequency) ===")
for t, L, f in rows:
    print(f"{t}\t{L}\t{f}")