"""Diagnose the short-token English/Hinglish collision problem on the real PHINC vocabulary.

Read-only on src/token_router.py. Reads phinc_cleaned_step1to4.csv
(Sentence_clean), extracts the unique lowercase vocabulary, classifies every
token with classify_token(), buckets by length, and samples the "danger zone"
(length <= 4 and length 5 tokens classified ENGLISH) for manual review.

Run:  .venv310\\Scripts\\python.exe scripts\\token_collision_diagnostic.py
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import random
from collections import Counter, defaultdict

import pandas as pd

from src.token_router import classify_token, Category

DATA = os.path.join(ROOT, "Datasets", "phinc_cleaned_step1to4.csv")
SEED = 42

df = pd.read_csv(DATA, usecols=["Sentence_clean"])
df = df.dropna()

tok_freq = Counter()
first_example = {}
vocab = set()

for s in df["Sentence_clean"].astype(str):
    toks = [t.lower() for t in s.split()]
    if not toks:
        continue
    seen = set(toks)
    vocab.update(seen)
    for t in seen:
        tok_freq[t] += 1
        if t not in first_example:
            first_example[t] = s

print("=== STEP 1: VOCABULARY ===")
print(f"rows read: {len(df)}")
print(f"unique tokens (case-insensitive): {len(vocab)}")

classify = {t: classify_token(t) for t in vocab}

print("\n=== STEP 2: LENGTH BUCKETS ===")
buckets = defaultdict(Counter)
for t, cat in classify.items():
    key = len(t) if len(t) <= 7 else 8
    buckets[key][cat] += 1

hdr = f"{'Len':<6}{'Total':<10}{'ENGLISH':<12}{'NUM/ALNUM':<14}{'CAND_HIN':<10}"
print(hdr)
print("-" * len(hdr))
for L in range(1, 9):
    label = f"{L}" if L < 8 else "8+"
    c = buckets[L]
    print(f"{label:<6}{c.total():<10}{c[Category.ENGLISH]:<12}{c[Category.NUMERIC_OR_ALPHANUMERIC]:<14}{c[Category.CANDIDATE_HINGLISH]:<10}")

def sample_and_print(pool, n, headline):
    print(f"\n=== {headline} (seed={SEED}, n={n}) ===")
    random.seed(SEED)
    chosen = random.sample(pool, n)
    chosen.sort(key=lambda t: tok_freq[t], reverse=True)
    print(f"{'TOKEN':<20}{'FREQ':<8}EXAMPLE SENTENCE (Sentence_clean)")
    print("-" * 90)
    for t in chosen:
        ex = first_example.get(t, "")
        print(f"{t:<20}{tok_freq[t]:<8}{ex}")

short_en = sorted(
    t for t, cat in classify.items() if len(t) <= 4 and cat == Category.ENGLISH
)
len5_en = sorted(
    t for t, cat in classify.items() if len(t) == 5 and cat == Category.ENGLISH
)

print(f"\npool size len<=4 ENGLISH: {len(short_en)}")
print(f"pool size len==5 ENGLISH: {len(len5_en)}")

sample_and_print(short_en, 60, "STEP 3: SAMPLE len<=4 ENGLISH")
sample_and_print(len5_en, 30, "STEP 4: SAMPLE len==5 ENGLISH")

print("\n=== EXTRA: ENGLISH SHARE BY LENGTH (numeric) ===")
for L in range(1, 9):
    c = buckets[L]
    pct = 100.0 * c[Category.ENGLISH] / c.total() if c.total() else 0.0
    print(f"len {L if L < 8 else '8+'}: {c[Category.ENGLISH]}/{c.total()} = {pct:.1f}% ENGLISH")