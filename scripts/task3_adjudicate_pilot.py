import sys, io, os, csv, json, time, re
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.gemini_health_check import (
    load_api_key, check_api_key, import_sdk, classify_error, try_parse_json,
    pick_model, REQUEST_TIMEOUT_MS,
)

READ = dict(sep="\t", quoting=csv.QUOTE_NONE, keep_default_na=False, encoding="utf-8")
PILOT = os.path.join(ROOT, "reports/pilot_pool_uncertain.tsv")
SENT  = os.path.join(ROOT, "Datasets/phinc_cleaned_step1to4.csv")
OUT   = os.path.join(ROOT, "reports/pilot_pool_adjudicated.tsv")
OUT_REVIEW = os.path.join(ROOT, "reports/task3_needs_manual_review.tsv")
OUT_NOCTX  = os.path.join(ROOT, "reports/task3_no_context_found.tsv")
OUT_FAIL   = os.path.join(ROOT, "reports/task3_llm_call_failures.tsv")
LABEL_RE   = re.compile(r"\b(ENGLISH|HINGLISH|AMBIGUOUS)\b", re.IGNORECASE)


def make_prompt(token, examples):
    lines = [
        'You are a language classifier for Romanized Hindi/English code-mixed text.',
        f'Token: "{token}"',
        'Example sentences containing it:',
    ]
    for i, s in enumerate(examples, 1):
        lines.append(f"{i}. {s}")
    lines += [
        'Classify the token as exactly one of: ENGLISH, HINGLISH, AMBIGUOUS.',
        '- ENGLISH: standard English word in this context.',
        '- HINGLISH: Romanized Hindi/Hinglish word.',
        '- AMBIGUOUS: meaning/language genuinely depends on context and shifts between examples.',
        'Respond with only JSON: {"label": "...", "reason": "one line"}',
    ]
    return "\n".join(lines)


def ensure_header(path, header):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "a", encoding="utf-8", newline="") as f:
            f.write(header)


def main():
    pilot = pd.read_csv(PILOT, **READ)
    rows = list(zip(pilot["token"], pilot["freq"]))
    print(f"pilot tokens: {len(rows)}")

    clean = pd.read_csv(SENT)["Sentence_clean"].astype(str).str.strip()
    examples_map = {}
    for s in clean:
        for w in set(s.split()):
            lst = examples_map.setdefault(w, [])
            if len(lst) < 3:
                lst.append(s)
    print(f"sentence words indexed: {len(examples_map)}")

    key = load_api_key()
    if not check_api_key(key):
        sys.exit(1)
    _, _, genai, _ = import_sdk()
    client = genai.Client(api_key=key, http_options={"timeout": REQUEST_TIMEOUT_MS})
    model = pick_model(client)
    print(f"model: {model}")

    done_tokens = set()
    if os.path.exists(OUT):
        done = pd.read_csv(OUT, **READ)
        done_tokens = set(
            t for t, r in zip(done["token"], done["llm_reason"])
            if not r.startswith("llm_call_failed_default")
        )
        print(f"resume: {len(done_tokens)} already adjudicated (retries llm-failed)")

    no_ctx   = []
    manual   = []
    failures = []

    ensure_header(OUT,          "token\tfrequency\tlabel\tllm_reason\texample_sentence_used\n")
    ensure_header(OUT_REVIEW,   "token\tfrequency\tllm_reason\texample_sentences\n")
    ensure_header(OUT_NOCTX,    "token\tfrequency\n")
    ensure_header(OUT_FAIL,     "token\tfrequency\terror\n")

    t0 = time.perf_counter()
    n  = 0

    with open(OUT, "a", encoding="utf-8", newline="") as fh_out, \
         open(OUT_REVIEW, "a", encoding="utf-8", newline="") as fh_rev, \
         open(OUT_NOCTX, "a", encoding="utf-8", newline="") as fh_nc, \
         open(OUT_FAIL, "a", encoding="utf-8", newline="") as fh_fail:

        for token, freq in rows:
            if token in done_tokens:
                continue

            examples = examples_map.get(token, [])[:3]

            if not examples:
                no_ctx.append((token, freq))
                fh_nc.write(f"{token}\t{freq}\n")
                fh_out.write(f"{token}\t{freq}\tHINGLISH\tno_context_default\t\n")
                n += 1
                continue

            prompt = make_prompt(token, examples)
            label = None
            reason = ""
            last_err = ""
            rl_streak = 0

            def _backoff(exc):
                nonlocal rl_streak
                sleep = 3
                res = getattr(exc, "response", None)
                if res is not None and hasattr(res, "headers"):
                    ra = res.headers.get("retry-after")
                    if ra:
                        try:
                            sleep = int(ra) + 1
                        except ValueError:
                            pass
                _, _, _, errmod = import_sdk()
                cat, detail = classify_error(exc, None, None, errmod)
                last_err_text = f"{cat}: {detail}"
                if cat == "rate-limit":
                    rl_streak += 1
                    sleep = max(sleep * rl_streak, 10)
                else:
                    rl_streak = 0
                return min(sleep, 300), last_err_text

            for attempt in (1, 2):
                try:
                    resp = client.models.generate_content(model=model, contents=prompt)
                    text = resp.text.strip() if getattr(resp, "text", None) else ""
                    ok, parsed = try_parse_json(text)
                    if ok and isinstance(parsed, dict):
                        raw = str(parsed.get("label", ""))
                        m = LABEL_RE.search(raw) or LABEL_RE.search(json.dumps(parsed))
                        label = m.group(1).upper() if m else None
                        reason = str(parsed.get("reason", "")).strip()
                        break
                    last_err = f"unparseable response: {text[:120]!r}"
                except Exception as exc:
                    wait, last_err = _backoff(exc)
                    time.sleep(wait)

            if label is None:
                failures.append((token, freq, last_err))
                fh_fail.write(f"{token}\t{freq}\t{last_err.replace(chr(9),' ').replace(chr(10),' ')}\n")
                final_label, final_reason = "HINGLISH", "llm_call_failed_default:" + last_err
            elif label == "ENGLISH":
                final_label, final_reason = "ENGLISH", reason
            elif label == "AMBIGUOUS":
                final_label, final_reason = "PENDING_MANUAL_REVIEW", reason
                manual.append((token, freq, reason, examples))
                joined = " | ".join(e.replace(chr(9),' ').replace(chr(10),' ') for e in examples)
                fh_rev.write(f"{token}\t{freq}\t{reason.replace(chr(9),' ').replace(chr(10),' ')}\t{joined}\n")
            else:
                final_label, final_reason = "HINGLISH", reason or "ambiguous-unsure-default"

            ex = examples[0] if examples else ""
            fh_out.write(f"{token}\t{freq}\t{final_label}\t"
                         + final_reason.replace(chr(9),' ').replace(chr(10),' ') + "\t"
                         + ex.replace(chr(9),' ').replace(chr(10),' ') + "\n")
            fh_out.flush(); fh_rev.flush(); fh_nc.flush(); fh_fail.flush()
            n += 1
            if n % 25 == 0:
                el = time.perf_counter() - t0
                rate = el / n
                print(f"  {n} done | {rate*1000:.0f} ms/tok | ETA {rate*(len(rows)-n)/60:.1f} min", flush=True)

    print(f"adjudicated: {n} (new this run); manual-review: {len(manual)}; no-context: {len(no_ctx)}; failures: {len(failures)}")
    print("done ->", OUT)


if __name__ == "__main__":
    main()