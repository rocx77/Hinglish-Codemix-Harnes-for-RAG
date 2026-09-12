import sys, io, os, csv
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READ = dict(sep="\t", quoting=csv.QUOTE_NONE, keep_default_na=False, encoding="utf-8")

def load(rel):
    return pd.read_csv(os.path.join(ROOT, rel), **READ)

vocab = load("reports/vocab_phinc_freq_fixed.tsv")
labels = load("reports/wordnet_layer_output_fixed.tsv")

print("vocab cols:", list(vocab.columns), "| rows:", len(vocab))
print("labels cols:", list(labels.columns), "| rows:", len(labels))

vocab = vocab.rename(columns={vocab.columns[0]: "token", vocab.columns[1]: "freq"})
labels = labels.rename(columns={labels.columns[0]: "token", labels.columns[1]: "label"})

merged = pd.merge(vocab, labels[["token", "label", "method"]], on="token", how="inner")
print("joined rows:", len(merged))

unmatched = pd.concat([
    vocab[~vocab["token"].isin(labels["token"])],
    labels[~labels["token"].isin(vocab["token"])],
])
unmatched = unmatched[["token"]].drop_duplicates()
if len(unmatched):
    out = os.path.join(ROOT, "reports/task1_unmatched_tokens.tsv")
    unmatched.to_csv(out, sep="\t", index=False, quoting=csv.QUOTE_NONE, encoding="utf-8")
    print("unmatched tokens logged:", len(unmatched), "->", out)
else:
    print("unmatched tokens: 0")

uncertain = merged[merged["label"] == "UNCERTAIN_NEEDS_LLM"]
print("UNCERTAIN_NEEDS_LLM count:", len(uncertain))
total = int(uncertain["freq"].sum())
print("total occurrence mass:", total)
if len(uncertain) != 14778 or total != 58555:
    print("NOTE: numbers differ from documented baseline (14778 / 58555) — review before trusting downstream")

uncertain = uncertain.sort_values("freq", ascending=False).reset_index(drop=True)
uncertain["cum_occ"] = uncertain["freq"].cumsum()
uncertain["cum_pct"] = (uncertain["cum_occ"] / total * 100).round(3)

rows = []
for target in (70, 80, 90):
    hit = uncertain[uncertain["cum_pct"] >= target].iloc[0]
    rows.append((target, int(hit["cum_occ"]), float(hit["cum_pct"])))

counts = {}
for target, cum, pct in rows:
    n = int((uncertain["cum_pct"] < float(target)).sum()) + 1
    counts[target] = n
    print(f"coverage {target}% | n_tokens {n} | cum_occurrences {cum} | cum_pct {pct}")

n80 = counts[80]
tier = 80 if n80 <= 2500 else 70
print(f"decision rule: 80% needs {n80} tokens (<=2500 ?) -> using {tier}% tier")

n_sel = counts[tier]
pilot = uncertain.iloc[:n_sel][["token", "freq", "cum_pct"]].rename(columns={"cum_pct": "cumulative_pct_at_this_point"})
out = os.path.join(ROOT, "reports/pilot_pool_uncertain.tsv")
pilot.to_csv(out, sep="\t", index=False, quoting=csv.QUOTE_NONE, encoding="utf-8")
print("wrote", out, "| rows:", len(pilot), "| cumulative pct at last row:", pilot["cumulative_pct_at_this_point"].iloc[-1])