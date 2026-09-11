"""wordnet_hinglish_filter.py

Rules-based, zero-API-cost pre-filter for the P1 router-collision problem
(see PROBLEMS.md). This runs BEFORE any LLM call. Its only job is to shrink
the pool of tokens that genuinely need LLM adjudication down to the smallest
possible remainder.

Pipeline (each token gets exactly one label, first matching rule wins):

    raw token
      -> [regex pre-filter]            -> NON_LINGUISTIC   (numbers, units,
                                                              URLs, @mentions,
                                                              #hashtags,
                                                              mojibake / P2)
      -> [ambiguous override table]    -> AMBIGUOUS         (main, to, maine..)
      -> [hinglish override table]     -> HINGLISH          (thi, jab, kr, ...)
      -> [WordNet exact match]         -> ENGLISH
      -> [WordNet fuzzy, guarded]      -> ENGLISH   (len >= 7 AND the matched
                                                     lemma is a common English
                                                     word -- see report)
      -> (nothing resolved it)         -> UNCERTAIN_NEEDS_LLM

Only UNCERTAIN_NEEDS_LLM tokens should ever be sent to the LLM adjudicator.
Everything else is resolved for free and deterministically. This is the P1
rules layer that feeds the FINALIZED Tier 0 classification in
reports/hinglish_normalization_architecture.md (gate G1).

This script does NOT touch the network itself -- it only reads the locally
downloaded WordNet corpus via nltk.

Requirements (install once):
    pip install nltk
    python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"

Run (step 1 -- self-test always first):
    python scripts/wordnet_hinglish_filter.py
Run (step 2 -- real vocabulary, token per line or "token<TAB>freq"):
    python scripts/wordnet_hinglish_filter.py --vocab reports/vocab_phinc_freq.tsv
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Set

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from nltk.corpus import wordnet as wn
except ImportError:  # pragma: no cover
    print(
        "ERROR: nltk is not installed. Run: pip install nltk\n"
        'Then: python -c "import nltk; nltk.download(\'wordnet\'); '
        "nltk.download('omw-1.4')\"",
        file=sys.stderr,
    )
    raise

# Common-English gate for the fuzzy layer. A fuzzy match is only trusted when
# the matched lemma is itself a HIGH-FREQUENCY English word (wordfreq top-N),
# which blocks single-edit collisions like bahut->baht (baht is not common)
# while still catching real English typos. See reports/wordnet_layer_report.md.
# wordfreq is a declared project dependency (requirements.txt).
_EN_COMMON_TOP_N = 20000
try:
    from wordfreq import top_n_list as _top_n_list
    _EN_COMMON = frozenset(_top_n_list("en", _EN_COMMON_TOP_N))
    _HAS_WORDFREQ = True
except Exception:  # pragma: no cover - degraded to exact-match only
    _EN_COMMON = frozenset()
    _HAS_WORDFREQ = False


# ---------------------------------------------------------------------------
# Override tables (curated from PROBLEMS.md P1 diagnostic; extend as new
# high-frequency collisions surface -- see collision_len4_en_freq_sorted.tsv)
# ---------------------------------------------------------------------------

# Category 1 from P1: unambiguous, always-Hinglish in this corpus regardless
# of context. Safe to hard-override to HINGLISH unconditionally.
HINGLISH_OVERRIDE: Set[str] = {
    "hai", "to", "ke", "ki", "se", "ka", "ho", "ko", "aur", "bhai",
    "kar", "kya", "ek", "toh", "ab", "koi", "na", "aap", "ne", "tha",
    "tu", "thi", "jab", "hue", "band", "ni", "ham", "bt", "kr", "bal", "rh",
    # Surfaces from the first full-vocab run: guarded fuzzy-English audit
    # (2026-09-11). Unambiguous Hinglish loanwords that WordNet's common-
    # English gate would otherwise mislabel ENGLISH. All freq <= 5.
    "milenge", "andhere", "banwana", "karwate", "sanskriti", "sadharan",
    "sahaara", "sultani", "madrasi", "congressi", "bastiyon", "wicketo",
    "stadiumi", "hospitalo", "pakistaniyo", "pakistanio", "pakistano",
    "karaoge",
}

# Category 2 from P1: context-dependent. A token-in-isolation router cannot
# resolve these correctly (main = "\u092e\u0948\u0902" or English "main"; to =
# "\u0924\u094b" or English "to"). These get NO static canonical mapping --
# documented as a real limitation, not silently guessed.
AMBIGUOUS_OVERRIDE: Set[str] = {
    "main", "maine", "me", "the",
}

# ---------------------------------------------------------------------------
# Regex pre-filter (P2-adjacent): things that are not linguistic tokens at
# all and should never reach WordNet or the LLM.
# ---------------------------------------------------------------------------

_RE_URL = re.compile(r"^(https?://|www\.)\S+$", re.IGNORECASE)
_RE_MENTION = re.compile(r"^@\w+$")
_RE_HASHTAG = re.compile(r"^#\w+$")
_RE_NUMBER_WITH_UNIT = re.compile(
    r"^\d+(\.\d+)?(kg|g|mg|km|m|cm|mm|hr|hrs|min|mins|sec|secs|am|pm|x|k|rs|inr|usd|\$|%)?$",
    re.IGNORECASE,
)
_RE_PURE_PUNCT_OR_DIGIT = re.compile(r"^[\W\d_]+$", re.UNICODE)
# Devanagari block: U+0900-U+097F. Latin letters: a-zA-Z. Anything else
# (mojibake, stray control chars, emoji-decode garbage per P2) is suspect.
_RE_SANE_CHARSET = re.compile(r"^[a-zA-Z\u0900-\u097F]+$")


def is_non_linguistic(token: str) -> bool:
    """True for numbers/units, URLs, mentions, hashtags, punctuation-only,
    or mojibake/garbage tokens that should never reach a lexical check."""
    if not token:
        return True
    if _RE_URL.match(token) or _RE_MENTION.match(token) or _RE_HASHTAG.match(token):
        return True
    if _RE_NUMBER_WITH_UNIT.match(token):
        return True
    if _RE_PURE_PUNCT_OR_DIGIT.match(token):
        return True
    if not _RE_SANE_CHARSET.match(token):
        # Contains characters outside latin/devanagari -> almost certainly
        # mojibake (P2) or emoji-decode garbage, not a real word.
        return True
    return False


# ---------------------------------------------------------------------------
# WordNet exact match
# ---------------------------------------------------------------------------

def wordnet_exact_match(token_lower: str) -> bool:
    """True if token_lower is a real WordNet dictionary entry."""
    return len(wn.synsets(token_lower)) > 0


# ---------------------------------------------------------------------------
# WordNet fuzzy match (guarded). Length-gated AND common-English-gated.
#
# The unguarded version (WordNet lemma edit-distance, len >= 5) was validated
# against the real vocabulary and produced silent WRONG labels on the most
# common Hinglish content words (bahut->baht, karna->karma, saath, accha,
# chahiye, kaise, kahan, bahot...). Per the "worse than deferring" rule this
# was unacceptable, so a fuzzy hit now additionally requires:
#   - token len >= 7 (short tokens are exactly where EN/HI collide);
#   - the matched lemma is a COMMON English word (wordfreq top-20k);
#   - distance <= 1 (len <= 9) or <= 2 (len > 9).
# Tokens that fail these checks fall through to UNCERTAIN_NEEDS_LLM instead of
# being confidently mislabeled. See reports/wordnet_layer_report.md.
# ---------------------------------------------------------------------------

MIN_LEN_FOR_FUZZY = 7

_lemma_index: Dict[tuple, Set[str]] = {}
_lemma_index_built = False


def _build_lemma_index() -> None:
    """Bucket every WordNet lemma by (first_letter, length) so fuzzy lookup
    doesn't have to scan the full ~147k lemma list per token."""
    global _lemma_index_built
    if _lemma_index_built:
        return
    for lemma in wn.all_lemma_names():
        lemma = lemma.lower().replace("_", "")
        if not lemma.isalpha():
            continue
        key = (lemma[0], len(lemma))
        _lemma_index.setdefault(key, set()).add(lemma)
    _lemma_index_built = True


def _levenshtein(a: str, b: str, max_dist: int) -> int:
    """Standard iterative Levenshtein distance with early-exit once the
    running minimum in a row exceeds max_dist (cheap pruning)."""
    if abs(len(a) - len(b)) > max_dist:
        return max_dist + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        row_min = i
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            row_min = min(row_min, cur[j])
        if row_min > max_dist:
            return max_dist + 1
        prev = cur
    return prev[-1]


def _fuzzy_threshold(length: int) -> int:
    """Distance allowed scales gently with length; stays conservative."""
    if length <= 9:
        return 1
    return 2


def wordnet_fuzzy_match(token_lower: str) -> bool:
    """True if token_lower is within a length-scaled edit distance of some
    real WordNet lemma of similar length, AND that lemma is a common English
    word (wordfreq top-20k). Only called for len >= MIN_LEN_FOR_FUZZY."""
    _build_lemma_index()
    threshold = _fuzzy_threshold(len(token_lower))
    first = token_lower[0]
    candidates: Set[str] = set()
    for dl in range(-threshold, threshold + 1):
        key = (first, len(token_lower) + dl)
        if key in _lemma_index:
            candidates |= _lemma_index[key]
    for cand in candidates:
        if cand == token_lower:
            return True
        if _levenshtein(token_lower, cand, threshold) <= threshold:
            if _HAS_WORDFREQ and cand not in _EN_COMMON:
                # lemma exists but is not a common English word (e.g. 'baht')
                # -- this is a collision, not a resolved English typo.
                continue
            return True
    return False


# ---------------------------------------------------------------------------
# Main classifier
# ---------------------------------------------------------------------------

LABELS = ("NON_LINGUISTIC", "AMBIGUOUS", "HINGLISH", "ENGLISH", "UNCERTAIN_NEEDS_LLM")


@dataclass
class Classification:
    token: str
    label: str
    method: str


def classify_token_rules(token: str) -> Classification:
    if is_non_linguistic(token):
        return Classification(token, "NON_LINGUISTIC", "regex_prefilter")

    lower = token.lower()

    if lower in AMBIGUOUS_OVERRIDE:
        return Classification(token, "AMBIGUOUS", "override_ambiguous")

    if lower in HINGLISH_OVERRIDE:
        return Classification(token, "HINGLISH", "override_hinglish")

    if wordnet_exact_match(lower):
        return Classification(token, "ENGLISH", "wordnet_exact")

    if len(lower) >= MIN_LEN_FOR_FUZZY and wordnet_fuzzy_match(lower):
        return Classification(
            token, "ENGLISH", f"wordnet_fuzzy_edit{_fuzzy_threshold(len(lower))}"
        )

    return Classification(token, "UNCERTAIN_NEEDS_LLM", "unresolved")


# ---------------------------------------------------------------------------
# Built-in self-test against the known-labeled diagnostic sample.
# Run this FIRST, before pointing the script at the real vocabulary.
# ---------------------------------------------------------------------------

_KNOWN_HINGLISH = ["thi", "jab", "hue", "band", "ni", "kr", "bal", "rh", "bt"]
_KNOWN_ENGLISH = ["kiwi", "dah", "wong", "salt", "mps", "oral", "crib", "flu"]


def run_self_test(verbose: bool = True) -> float:
    """Classifies the known-labeled tokens and reports rules-layer accuracy.

    Note: this measures the RULES LAYER alone, not the LLM. A token landing
    in UNCERTAIN_NEEDS_LLM is not a rules-layer error per se (it's honestly
    deferring), but a token landing in the WRONG hard label (e.g. a known
    Hinglish word coming back ENGLISH) is a real bug worth investigating
    before scaling up.
    """
    correct = 0
    wrong = 0
    deferred = 0
    total = len(_KNOWN_HINGLISH) + len(_KNOWN_ENGLISH)

    if verbose:
        print("=" * 88)
        print("SELF-TEST: known-labeled tokens from the P1 diagnostic")
        print("=" * 88)

    for tok in _KNOWN_HINGLISH:
        c = classify_token_rules(tok)
        if c.label == "HINGLISH":
            correct += 1
            verdict = "OK"
        elif c.label == "UNCERTAIN_NEEDS_LLM":
            deferred += 1
            verdict = "DEFERRED (would go to LLM, acceptable)"
        else:
            wrong += 1
            verdict = f"WRONG -- expected HINGLISH, got {c.label}"
        if verbose:
            print(
                f"  {tok:8s} expected=HINGLISH  got={c.label:22s} "
                f"via={c.method:20s} {verdict}"
            )

    for tok in _KNOWN_ENGLISH:
        c = classify_token_rules(tok)
        if c.label == "ENGLISH":
            correct += 1
            verdict = "OK"
        elif c.label == "UNCERTAIN_NEEDS_LLM":
            deferred += 1
            verdict = "DEFERRED (would go to LLM, acceptable)"
        else:
            wrong += 1
            verdict = f"WRONG -- expected ENGLISH, got {c.label}"
        if verbose:
            print(
                f"  {tok:8s} expected=ENGLISH   got={c.label:22s} "
                f"via={c.method:20s} {verdict}"
            )

    if verbose:
        print("-" * 88)
        print(f"Correct (rules resolved it right): {correct}/{total}")
        print(f"Deferred to LLM (honest, not wrong): {deferred}/{total}")
        print(f"WRONG (rules resolved it, incorrectly): {wrong}/{total}")
        print("=" * 88)
        if wrong > 0:
            print(
                "!! At least one hard-label error. Do NOT proceed to the full "
                "vocabulary run until this is understood -- a WRONG here means "
                "the rules layer is confidently mislabeling, which is worse "
                "than deferring."
            )

    return correct / total


# ---------------------------------------------------------------------------
# CLI: run against a real vocabulary file (one token per line, optionally
# "token\tfrequency") and emit a labeled TSV.
# ---------------------------------------------------------------------------

def run_on_vocab_file(path: str, out_path: str) -> None:
    counts: Dict[str, int] = defaultdict(int)
    with open(path, "r", encoding="utf-8") as f_in, \
         open(out_path, "w", encoding="utf-8") as f_out:
        f_out.write("token\tlabel\tmethod\n")
        for line in f_in:
            line = line.rstrip("\n")
            if not line:
                continue
            token = line.split("\t")[0].strip()
            if not token:
                continue
            c = classify_token_rules(token)
            counts[c.label] += 1
            f_out.write(f"{c.token}\t{c.label}\t{c.method}\n")

    total = sum(counts.values())
    print(f"Wrote {out_path} ({total} tokens)")
    for label in LABELS:
        n = counts.get(label, 0)
        pct = (100.0 * n / total) if total else 0.0
        print(f"  {label:22s} {n:7d}  ({pct:5.1f}%)")
    n_uncertain = counts.get("UNCERTAIN_NEEDS_LLM", 0)
    print(
        f"\n-> {n_uncertain} tokens ({100.0 * n_uncertain / total:.1f}% of vocab) "
        f"need the LLM adjudicator pass. Everything else is resolved for free."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="P1 rules-based English/Hinglish/non-linguistic pre-filter."
    )
    parser.add_argument(
        "--vocab", type=str, default=None,
        help="Path to a vocabulary file, one token per line (or 'token<TAB>freq'). "
             "If omitted, only the self-test runs.",
    )
    parser.add_argument(
        "--out", type=str,
        default=os.path.join(ROOT, "reports", "wordnet_layer_output.tsv"),
        help="Output TSV path (only used with --vocab).",
    )
    parser.add_argument(
        "--skip-self-test", action="store_true",
        help="Skip the built-in self-test (not recommended).",
    )
    args = parser.parse_args()

    if not args.skip_self_test:
        run_self_test(verbose=True)
        if args.vocab is None:
            sys.exit(0)
        print()

    if args.vocab:
        run_on_vocab_file(args.vocab, args.out)


if __name__ == "__main__":
    main()