"""Pre-Tier-1 token router for the Hinglish normalization pipeline.

Classifies a single, already-tokenized, punctuation-stripped token into
exactly one of:

    ENGLISH              - a recognized English word (case-insensitive lookup
                           against a real English wordlist)
    NUMERIC_OR_ALPHANUMERIC
                         - purely numeric tokens, or alphanumeric codes/units
                           that are not enumerable by dictionary
    CANDIDATE_HINGLISH   - anything else; this is what gets passed on to
                           Tier 1/2/3 normalization

Wordlist: the `wordfreq` package, `top_n_list("en", N)`. Pure-Python with
bundled data (no build or model inference), built for the .venv310 env.

This module is intentionally fast: a single dict lookup + regex check, with
sentence-piece / vocabulary pre-computation cached at import time. It performs
NO model inference and is safe to run on every token of every query.

NOTE: This router is deliberately naive. Because "English" is a frequency top-N
list, genuine Hinglish words that collide with short/common English words (e.g.
`main`, `to`, `maine`) get classified as ENGLISH. Callers should treat the
category as a first-pass filter, not ground truth.
"""
from __future__ import annotations

import re

__all__ = ["classify_token", "classify_batch", "Category"]

# ---------------------------------------------------------------------------
# Wordlist (English)
# ---------------------------------------------------------------------------
# Number of most-frequent English words used for the ENGLISH lookup. Chosen to
# cover common function + content words while keeping the set small enough that
# accidental Hinglish collisions are limited. Increase for higher recall of
# rare English words (at the cost of more collisions).
_EN_WORDLIST_SIZE = 50000

try:
    from wordfreq import top_n_list as _top_n_list
    _EN_WORDS = frozenset(w for w in _top_n_list("en", _EN_WORDLIST_SIZE))
    _WORDLIST_SOURCE = f"wordfreq top_n_list('en', {_EN_WORDLIST_SIZE})"
except Exception as _e:  # pragma: no cover - fallback for odd environments
    _EN_WORDS = frozenset()
    _WORDLIST_SOURCE = f"UNAVAILABLE ({_e!r})"

# ---------------------------------------------------------------------------
# Enum-like category constants
# ---------------------------------------------------------------------------
class Category:
    ENGLISH = "ENGLISH"
    NUMERIC_OR_ALPHANUMERIC = "NUMERIC_OR_ALPHANUMERIC"
    CANDIDATE_HINGLISH = "CANDIDATE_HINGLISH"


# ---------------------------------------------------------------------------
# Numeric / alphanumeric regex checks
# ---------------------------------------------------------------------------
# Purely numeric (4050) or containing a digit mixed with letters in a
# unit/code-like pattern (5g, 1kg, 24x7, 10w30).
_RE_NUMERIC = re.compile(r"^\d+$")
_RE_NUM_LEAD = re.compile(r"^\d+[a-z]+$", re.IGNORECASE)
_RE_NUM_MIXED = re.compile(r"^\d+[a-z]+\d*$", re.IGNORECASE)


def _is_numeric_or_alnum(token: str) -> bool:
    # purely numeric: 4050
    if _RE_NUMERIC.fullmatch(token):
        return True
    # digit-led unit/code patterns: 5g, 1kg, 10w30, 24x7
    if _RE_NUM_LEAD.fullmatch(token) or _RE_NUM_MIXED.fullmatch(token):
        return True
    # general digit+letter mixture (unit/code-like): 24x7, a1b2c3
    if re.search(r"\d", token) and re.search(r"[a-z]", token, re.IGNORECASE):
        return True
    return False


def classify_token(token: str) -> str:
    """Classify a single token into one of the three category strings."""
    if not isinstance(token, str) or not token:
        # Empty/non-strings are not routable content; treat as Hinglish-candidate
        # (an empty token is a tokenizer concern, not ours).
        return Category.CANDIDATE_HINGLISH

    if _is_numeric_or_alnum(token):
        return Category.NUMERIC_OR_ALPHANUMERIC

    if token.lower() in _EN_WORDS:
        return Category.ENGLISH

    return Category.CANDIDATE_HINGLISH


def classify_batch(tokens) -> dict:
    """Classify a list of tokens, returning {token: category}."""
    return {t: classify_token(t) for t in tokens}


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    TEST_TOKENS = [
        "laptop", "mobile", "phone", "wifi", "server",
        "5g", "1kg", "4050", "24x7",
        "bahut", "bht", "kaha", "uske", "padega",
        "mra", "kr", "rh", "acct", "bal", "ktn",
    ]

    results = classify_batch(TEST_TOKENS)
    ambi = {"main": "='main' - valid Hinglish 'I' AND English 'main'",
            "to": "='to' - Hinglish 'that' AND English 'to'",
            "maine": "maine - Hinglish 'I did' AND English 'Maine'=US state",
            "apna": "apna - Hinglish 'own/our' (not in English list)"}

    print(f"Wordlist source: {_WORDLIST_SOURCE}")
    print(f"English wordlist size: {len(_EN_WORDS)}")
    print()
    print(f"{'TOKEN':<12}{'CATEGORY':<26}NOTE")
    print("-" * 60)
    for t in TEST_TOKENS:
        note = ambi.get(t, "")
        print(f"{t:<12}{results[t]:<26}{note}")

    print()
    print("Ambiguity / collision check (not in the 20, but illustrative):")
    for t in ["main", "to", "maine", "apna"]:
        print(f"  {t:<8}-> {classify_token(t)}")
    print()
    print("Note: ambiguous Hinglish/English tokens are flagged here, not silently "
          "resolved. The router picks ENGLISH first; the downstream Tier1/2/3 "
          "pipeline is responsible for resolving true ambiguity.")