import sys, io, os, csv, ast, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EN = os.path.join(ROOT, "scripts", "wordnet_hinglish_filter.py")
ADJ = os.path.join(ROOT, "reports", "pilot_pool_adjudicated.tsv")
VOC = os.path.join(ROOT, "reports", "vocab_phinc_freq_fixed.tsv")
OUT = os.path.join(ROOT, "reports", "candidate_hinglish_pool.tsv")
OUT_FAIL = os.path.join(ROOT, "reports", "task4_transliteration_failures.tsv")


def read_tsv(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        rows = list(r)
    return rows[0], rows[1:]


def parse_override_set(path, name):
    src = open(path, "r", encoding="utf-8").read()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for t in targets:
            if isinstance(t, ast.Name) and t.id == name:
                return set(ast.literal_eval(node.value))
    raise ValueError(f"{name} not found in {path}")


def main():
    ovr = parse_override_set(EN, "HINGLISH_OVERRIDE")
    print(f"HINGLISH_OVERRIDE count (live code): {len(ovr)}")

    voc_fields, voc_rows = read_tsv(VOC)
    tok_i = voc_fields.index("token")
    freq_i = voc_fields.index("rows_containing_token")
    freq = {r[tok_i]: int(r[freq_i]) for r in voc_rows}

    adj_fields, adj_rows = read_tsv(ADJ)
    t_i = adj_fields.index("token")
    f_i = adj_fields.index("frequency")
    l_i = adj_fields.index("label")
    pool = {}
    for r in adj_rows:
        if r[l_i] == "HINGLISH":
            pool[r[t_i]] = (int(r[f_i]), "pilot_pool")
    overlap = 0
    for t in ovr:
        if t in pool:
            pool[t] = (max(pool[t][0], freq.get(t, pool[t][0])), "both")
            overlap += 1
        else:
            pool[t] = (freq.get(t, 0), "override_list")
    print(f"merged pool size: {len(pool)} (pilot HINGLISH: {len(pool)-len(ovr)+overlap}, override: {len(ovr)}, overlap both: {overlap})")

    from ai4bharat.transliteration import XlitEngine
    engine = XlitEngine(lang2use="hi", beam_width=4, rescore=True)

    tokens = sorted(pool, key=lambda t: -pool[t][0])
    failures = []
    t0 = time.perf_counter()
    with open(OUT, "w", encoding="utf-8", newline="") as fh, \
         open(OUT_FAIL, "w", encoding="utf-8", newline="") as ff:
        fh.write("token\tfrequency\tsource\tdevanagari_candidate_1\tdevanagari_candidate_2\tdevanagari_candidate_3\tdevanagari_candidate_4\n")
        ff.write("token\tfrequency\terror\n")
        for t in tokens:
            freq_v, src = pool[t]
            try:
                cands = engine.translit_word(t, lang_code="hi", topk=4) or []
                cands = [c for c in cands if c]
            except Exception as exc:
                cands = []
                failures.append((t, freq_v, type(exc).__name__))
                ff.write(f"{t}\t{freq_v}\t{type(exc).__name__}\n")
            row = [t, str(freq_v), src] + cands[:4] + [""] * (4 - min(len(cands[:4]), 4))
            fh.write("\t".join(row) + "\n")
    print(f"wrote {len(tokens)} rows in {time.perf_counter()-t0:.1f}s; transliteration failures: {len(failures)}")
    print("done ->", OUT)
    print("BATCHING: sequential translit_word calls used (BATCHING_TRUSTED=false from Task 2)")


if __name__ == "__main__":
    main()