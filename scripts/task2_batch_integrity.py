import sys, io, os, csv, json
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

READ = dict(sep="\t", quoting=csv.QUOTE_NONE, keep_default_na=False, encoding="utf-8")

pilot = pd.read_csv(os.path.join(ROOT, "reports/pilot_pool_uncertain.tsv"), **READ)
sample = pilot.head(100)["token"].tolist()
N = len(sample)
print("tokens tested:", N)

from ai4bharat.transliteration import XlitEngine
engine = XlitEngine(lang2use="hi", beam_width=4, rescore=True)

def normalize_batch(res):
    if isinstance(res, list) and len(res) == 1 and isinstance(res[0], list):
        flat = res[0]
        per = [flat[i*4:(i+1)*4] for i in range(len(flat) // 4)]
        if len(per) == N:
            return per
    if isinstance(res, list) and len(res) == N and isinstance(res[0], list):
        return res
    return None

batch1 = normalize_batch(engine.batch_transliterate_words(sample, "en", "hi", topk=4))
batch2 = normalize_batch(engine.batch_transliterate_words(sample, "en", "hi", topk=4))
sequential = [engine.translit_word(t, lang_code="hi", topk=1)[0] for t in sample]

lines = []
def log(s):
    print(s)
    lines.append(s)

log(f"## Batch integrity check (top {N} pilot-pool tokens)")
log("")
log(f"### 1. Length check")
log(f"- batch_input length: {N}")
log(f"- batch_result_1 structure: nrows={len(batch1) if batch1 is not None else 'PARSE-FAIL'}, "
    f"nper_row={[len(r) for r in batch1][:3] if batch1 else []} (expected {N} rows x {4} candidates, or flat {N*4})")
log("")

length_ok = batch1 is not None and batch2 is not None and len(batch1) == N and len(batch2) == N
log(f"- RESULT: {'PASS' if length_ok else 'FAIL — reproduces the collapse anomaly'}\n")

log("### 2. Determinism check (batch1 vs batch2, same input/order)")
det_mismatch = []
if length_ok:
    for i in range(N):
        if batch1[i] != batch2[i]:
            det_mismatch.append(i)
log(f"- mismatched indices: {det_mismatch if det_mismatch else 'none'}")
det_ok = length_ok and not det_mismatch
log(f"- RESULT: {'PASS' if det_ok else 'FAIL'}\n")

log("### 3. Batch vs sequential top-candidate check")
seq_mismatch = []
if length_ok:
    for i in range(N):
        if batch1[i][0] != sequential[i]:
            seq_mismatch.append(i)
log(f"- mismatched indices: {len(seq_mismatch)}")
for i in seq_mismatch[:20]:
    log(f"  [{i}] token={sample[i]!r}  batch_top={batch1[i][0]}  seq_top={sequential[i]}")
    log(f"       batch_cands={json.dumps(batch1[i], ensure_ascii=False)}")
seq_ok = length_ok and not seq_mismatch
log(f"- RESULT: {'PASS' if seq_ok else 'FAIL'}\n")

trusted = length_ok and det_ok and seq_ok
log(f"BATCHING_TRUSTED: {str(trusted).lower()}")

out = os.path.join(ROOT, "reports/batch_integrity_check.md")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\\nwrote", out)