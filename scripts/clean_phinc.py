"""Clean the PHINC Hinglish-English parallel corpus (Steps 1-4 only).

Run from the project root:  python scripts/clean_phinc.py
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import re
import pandas as pd
import ftfy
from rapidfuzz import fuzz
from collections import defaultdict

RE_MENTION  = re.compile(r"@(\w+)")
RE_HASHTAG  = re.compile(r"#(\w+)")
RE_URL      = re.compile(
    r"(https?://\S+)"                          # standard http(s) URLs
    r"|(www\.\S+)"                             # www-prefixed
    r"|((?:pic\.)?twitter\.com/\S+)"           # twitter.com and pic.twitter.com
    r"|(t\.co/\S+)"                            # t.co short links
    r"|(bit\.ly/\S+)",                         # bit.ly short links
    flags=re.IGNORECASE
)
RE_MULTI_WS = re.compile(r"\s+")


def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = RE_MENTION.sub(r"\1", text)
    text = RE_HASHTAG.sub(r"\1", text)
    text = RE_URL.sub("", text)
    text = ftfy.fix_text(text)
    text = RE_MULTI_WS.sub(" ", text).strip()
    return text


INPUT  = os.path.join(ROOT, r"Datasets\English-Hindi code-mixed parallel corpus.csv")
OUTPUT = os.path.join(ROOT, r"Datasets\phinc_cleaned_step1to4.csv")

df = pd.read_csv(INPUT)
total = len(df)
print(f"[Step 1] Loaded {total:,} rows")

mask = (
    df["Sentence"].isna()
    | df["English_Translation"].isna()
    | df["Sentence"].astype(str).str.strip().eq("")
    | df["English_Translation"].astype(str).str.strip().eq("")
)
dropped_null = int(mask.sum())
df = df[~mask].reset_index(drop=True)
print(f"[Step 1] Dropped {dropped_null:,} null/empty rows -> {len(df):,} remaining")

df["Sentence_clean"] = df["Sentence"].apply(clean_text)
print("[Step 2] Sentence_clean column created")

df["English_Translation_clean"] = df["English_Translation"].apply(clean_text)
df["translation_too_short"] = df["English_Translation_clean"].apply(lambda t: len(t.split()) < 4)
short_count = int(df["translation_too_short"].sum())
print(f"[Step 3] English_Translation_clean created, {short_count:,} flagged translation_too_short")

before_exact = len(df)
df = df.drop_duplicates(subset="English_Translation_clean", keep="first").reset_index(drop=True)
exact_dropped = before_exact - len(df)
print(f"[Step 4a] Dropped {exact_dropped:,} exact-duplicate rows -> {len(df):,} remaining")

print("[Step 4b] Computing near-duplicate pairs ...")

n = len(df)
translations = df["English_Translation_clean"].tolist()

parent = list(range(n))
rank   = [0] * n

def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

def union(a, b):
    ra, rb = find(a), find(b)
    if ra == rb:
        return
    if rank[ra] < rank[rb]:
        ra, rb = rb, ra
    parent[rb] = ra
    if rank[ra] == rank[rb]:
        rank[ra] += 1

first_token_idx = defaultdict(list)
for i, t in enumerate(translations):
    ft = t.split()[0] if t else ""
    first_token_idx[ft].append(i)

for ft, indices in first_token_idx.items():
    if len(indices) < 2:
        continue
    for a in range(len(indices)):
        for b in range(a + 1, len(indices)):
            ia, ib = indices[a], indices[b]
            score = fuzz.token_sort_ratio(translations[ia], translations[ib])
            if score >= 90:
                union(ia, ib)

comp_id = {}
next_id = 0
for i in range(n):
    root = find(i)
    if root not in comp_id:
        comp_id[root] = next_id
        next_id += 1
    df.at[i, "near_dup_group_id"] = comp_id[root]

df["near_dup_group_id"] = df["near_dup_group_id"].astype(int)

group_sizes = df["near_dup_group_id"].value_counts()
multi_groups = (group_sizes > 1)
n_multi = int(multi_groups.sum())
multi_sizes = group_sizes[multi_groups]

print(f"[Step 4b] {n_multi:,} near-duplicate groups found (size > 1)")
if n_multi > 0:
    print(f"           Top sizes: {sorted(multi_sizes.values, reverse=True)[:20]}")

out_cols = [
    "Sentence", "Sentence_clean",
    "English_Translation", "English_Translation_clean",
    "translation_too_short", "near_dup_group_id",
]
df[out_cols].to_csv(OUTPUT, index=False)
print(f"\nSaved cleaned CSV -> {OUTPUT}")

print("\n" + "=" * 60)
print("  CLEANING SUMMARY")
print("=" * 60)
print(f"  Total rows (raw)                    : {total:>8,}")
print(f"  Dropped (null/empty)                : {dropped_null:>8,}")
print(f"  Remaining after Step 1              : {total - dropped_null:>8,}")
print(f"  Dropped (exact-dup)                 : {exact_dropped:>8,}")
print(f"  Remaining after Step 4 exact-dedup  : {len(df):>8,}")
print(f"  translation_too_short = True        : {short_count:>8,}")
print(f"  Near-dup groups (size > 1)          : {n_multi:>8,}")
print("=" * 60)
