"""Gemini API health-check script (connectivity + structured-output format).

Standalone verification of the Google GenAI SDK setup before building the
harness on top of it:

1. Loads GEMINI_API_KEY from the environment (or .env in the project root).
2. Reports the installed google-genai SDK version.
3. Lists the current flash-lite models via the SDK and picks a free-tier target
   (falls back to a documented default if the list call fails).
4. One trivial plain-text call, timed, proving connectivity + round-trip latency.
5. One strict-JSON call to prove the model reliably returns parseable JSON
   (this decides whether the real harness needs fence/extra-text stripping).
6. Classified error handling: bad key / rate-limit(429) / network-timeout /
   everything else gets its own distinct message.

No classification or translation logic lives here - format + connectivity only.

Run from the project root:
    python scripts/gemini_health_check.py
"""
import io
import json
import os
import re
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT, ".env")

PLACEHOLDER_KEYS = {
    "your-api-key-here",
    "your_key_here",
    "changeme",
    "replace-with-your-key",
    "your-key",
}
PREFERRED_MODELS = [
    "gemini-3.5-flash-lite",  # current stable flash-lite (GA 2026-07-21), free tier
    "gemini-3.1-flash-lite",  # stable, free tier
    "gemini-2.5-flash-lite",  # older stable fallback
    "gemini-2.0-flash-lite",
]
FALLBACK_MODEL = "gemini-3.5-flash-lite"
REQUEST_TIMEOUT_MS = 30_000

PLAIN_PROMPT = "Reply with exactly the word OK and nothing else."
JSON_PROMPT = (
    'Respond with only this JSON, no other text: '
    '{"status": "ok", "model": "<model name you are>"}'
)


def load_api_key():
    """Load GEMINI_API_KEY from .env if present, then from the environment."""
    try:
        from dotenv import load_dotenv
        loaded_dotenv = True
    except ImportError:
        loaded_dotenv = False

    if os.path.exists(ENV_PATH):
        if loaded_dotenv:
            # Default behaviour: does NOT override vars already in process env.
            load_dotenv(ENV_PATH)
            print(f"[env] loaded {ENV_PATH} via python-dotenv")
        else:
            try:
                with open(ENV_PATH, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            os.environ.setdefault(k.strip(), v.strip())
                print(f"[env] loaded {ENV_PATH} (manual fallback, python-dotenv missing)")
            except OSError as exc:
                print(f"[env] warning: could not read {ENV_PATH}: {exc}")
    else:
        print(f"[env] no .env file at {ENV_PATH}; relying on process environment")

    return os.environ.get("GEMINI_API_KEY", "").strip()


def check_api_key(key):
    """Explicitly reject missing/blank/placeholder keys."""
    if not key:
        print("ERROR: GEMINI_API_KEY is not set and no usable value was found in .env.")
        print("       Add GEMINI_API_KEY to:")
        print("         - the project root .env file, or")
        print("         - your shell/process environment,")
        print("       then re-run. Do not proceed with a blank or placeholder key.")
        return False
    if key in PLACEHOLDER_KEYS or key.lower().startswith("your") or len(key) < 10:
        print("ERROR: GEMINI_API_KEY looks like a placeholder, not a real key.")
        print("       Get a key from https://aistudio.google.com/apikey and update .env.")
        return False
    return True


def import_sdk():
    """Import google-genai; print the installed version. Graceful if missing."""
    try:
        import httpx
        import requests
        import google.genai
        from google import genai
        from google.genai import errors
    except ImportError as exc:
        print("ERROR: google-genai SDK not installed for this interpreter.")
        print('       Install it with:  python -m pip install "google-genai>=2.0,<3.0"')
        print(f"       (import failed at: {exc})")
        return None, None, None, None
    version = getattr(google.genai, "__version__", "unknown (attr not exposed)")
    return httpx, requests, genai, errors


def classify_error(err, httpx, requests, errors):
    """Map an exception to (category, human-readable detail)."""
    code = getattr(err, "code", None)
    message = getattr(err, "message", None)
    status = getattr(err, "status", None)
    response = getattr(err, "response", None)

    if errors is not None and isinstance(err, errors.APIError):
        detail = f"HTTP {code} {status or ''} - {message or err}".strip()
        if code == 429:
            retry_after = None
            try:
                if response is not None and hasattr(response, "headers"):
                    retry_after = response.headers.get("retry-after")
            except Exception:
                retry_after = None
            if retry_after:
                return "rate-limit", f"HTTP 429 rate-limit. Retry-After: {retry_after!r}"
            return "rate-limit", "HTTP 429 rate-limit (no Retry-After header in response)"
        blob = f"{message} {status}".lower().replace("_", " ")
        if code in (400, 401, 403) and (
            "api key" in blob
            or "key not valid" in blob
            or "unauthenticated" in blob
            or "permission denied" in blob
        ):
            return "bad-key", f"API key rejected: HTTP {code} {status} - {message}"
        if 500 <= (code or 0) < 600:
            return "server-error", detail
        return "client-error", detail

    if isinstance(err, httpx.HTTPError):
        return "network-or-timeout", f"{type(err).__name__}: {err}"
    if isinstance(err, requests.RequestException):
        return "network-or-timeout", f"{type(err).__name__}: {err}"
    if isinstance(err, TimeoutError):
        return "network-or-timeout", f"{type(err).__name__}: {err}"

    return "other", f"{type(err).__name__}: {err}"


def try_parse_json(text):
    """Try to parse text as JSON: raw -> markdown-fenced -> first {...} block."""
    t = (text or "").strip()
    if not t:
        return False, None
    try:
        return True, json.loads(t)
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*(.*?)```", t, re.DOTALL)
    if fence:
        try:
            return True, json.loads(fence.group(1).strip())
        except json.JSONDecodeError:
            pass
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end > start:
        try:
            return True, json.loads(t[start:end + 1])
        except json.JSONDecodeError:
            pass
    return False, None


def listing_models(client):
    """Return (available_flash_lite_names, total_models) from models.list()."""
    names = []
    try:
        for m in client.models.list():
            names.append(m.name)
    except Exception as exc:
        print(f"[models] WARNING: models.list() failed, using documented default. Reason: {exc}")
        return None, None
    total = len(names)
    flash = sorted(
        n.removeprefix("models/") for n in names if "flash-lite" in n
    )
    return flash, total


def pick_model(client):
    """Pick the best free/cheap flash-lite model, preferring the current stable one."""
    flash, total = listing_models(client)
    if flash:
        print(f"[models] {total} models visible; flash-lite candidates ({len(flash)}):")
        for name in flash:
            print(f"           - {name}")
        for pref in PREFERRED_MODELS:
            if pref in flash:
                chosen = pref
                break
        else:
            stable = [n for n in flash if not n.endswith("-preview")]
            chosen = (stable or flash)[0]
        print(f"[models] target model: {chosen}")
        return chosen
    print(f"[models] model list unavailable -> using documented free-tier default: {FALLBACK_MODEL}")
    return FALLBACK_MODEL


def timed_generate(client, model, prompt):
    """Run a generate_content call, timed; return (elapsed_ms, error_tag, detail, text)."""
    t0 = time.perf_counter()
    try:
        resp = client.models.generate_content(model=model, contents=prompt)
        elapsed = (time.perf_counter() - t0) * 1000.0
        text = resp.text.strip() if getattr(resp, "text", None) else ""
        if not text:
            return elapsed, "empty", "model returned no text", ""
        return elapsed, None, None, text
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000.0
        hx, rq, _, errmod = import_sdk()
        category, detail = classify_error(exc, hx, rq, errmod)
        return elapsed, category, detail, ""


def main():
    print("=" * 60)
    print("GEMINI API HEALTH CHECK")
    print("=" * 60)

    key = load_api_key()
    if not check_api_key(key):
        sys.exit(1)

    httpx_mod, requests_mod, genai, errors = import_sdk()
    if httpx_mod is None:
        sys.exit(1)

    import google.genai as _gg
    sdk_version = getattr(_gg, "__version__", "unknown")
    print(f"\n[sdk] package: google-genai   version: {sdk_version}")

    client = genai.Client(api_key=key, http_options={"timeout": REQUEST_TIMEOUT_MS})
    model = pick_model(client)

    print("\n--- TEST 1: plain-text call (connectivity + latency) ---")
    elapsed, tag, detail, text = timed_generate(client, model, PLAIN_PROMPT)
    if tag is None:
        print(f"OK  latency: {elapsed:.1f} ms")
        print(f"    raw response text: {text!r}")
    else:
        print(f"FAILED ({tag}): {detail}   [{elapsed:.1f} ms]")

    print("\n--- TEST 2: strict-JSON call (structured-output reliability) ---")
    elapsed, tag, detail, text = timed_generate(client, model, JSON_PROMPT)
    if tag is None:
        ok, parsed = try_parse_json(text)
        if ok:
            print(f"OK  parsed JSON (json.loads succeeded): {parsed}")
            got_model = parsed.get("model") if isinstance(parsed, dict) else None
            print(f"    model field reported by model: {got_model!r} (target: {model})")
        else:
            print("PARSE FAILED - model did not return raw parseable JSON.")
            print(f"    Raw text was:\n{text}")
            print("    (This means the harness will need fence/extra-text stripping.)")
        print(f"    latency: {elapsed:.1f} ms")
    else:
        print(f"FAILED ({tag}): {detail}   [{elapsed:.1f} ms]")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  SDK version       : {sdk_version}")
    print(f"  Model used        : {model}")
    print(f"  API key loaded    : {'yes' if key else 'no'} (never printed)")


if __name__ == "__main__":
    main()