import sys, io, os, csv, json, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.task4_candidate_pool import parse_override_set

EN  = os.path.join(ROOT, "scripts", "wordnet_hinglish_filter.py")
POOL = os.path.join(ROOT, "reports", "candidate_hinglish_pool.tsv")
OUT = os.path.join(ROOT, "canonical_map.json")


def main():
    ambiguous = parse_override_set(EN, "AMBIGUOUS_OVERRIDE")
    print(f"AMBIGUOUS_OVERRIDE (live code): {sorted(ambiguous)}")

    with open(POOL, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
    header = rows[0]
    t_i = header.index("token")
    c_i = header.index("devanagari_candidate_1")
    data = rows[1:]

    canonical_map = {}
    leaked = []
    for r in data:
        tok, final = r[t_i], r[c_i]
        if tok in ambiguous:
            leaked.append(tok)
            continue
        if not final:
            print(f"WARN: empty candidate_1 for {tok!r} -> skipped")
            continue
        canonical_map[tok] = final

    if leaked:
        print("STOP: ambiguous tokens leaked into pool:", leaked)
        sys.exit(1)
    assert not set(ambiguous) & set(canonical_map), "ambiguous token in map"

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(canonical_map, fh, ensure_ascii=False, indent=2)

    print(f"canonical_map.json written: {len(canonical_map)} entries")
    sample = random.sample(sorted(canonical_map), min(10, len(canonical_map)))
    for k in sample:
        print(f"  {k!r:20} -> {canonical_map[k]!r}")
    print("exclusion checks passed: no AMBIGUOUS token in map")


if __name__ == "__main__":
    main()