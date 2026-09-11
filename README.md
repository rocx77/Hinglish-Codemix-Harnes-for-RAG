# HinglishCodeMix Harness for RAG

Experimenting with Retrieval-Augmented Generation (RAG) on Hinglish/English
code-mixed data using the PHINC parallel corpus.

## Project Structure

```
Datasets/                          Raw + cleaned data
  English-Hindi ... corpus.csv     Raw PHINC (read-only)
  phinc_cleaned_step1to4.csv       Cleaned output

scripts/                           Pipeline scripts (run in order)
  clean_phinc.py                   Step 1-4: load, clean, dedup
  export_phinc_vocab.py            Full vocab + row-frequency export
  wordnet_hinglish_filter.py       P1 zero-cost rules pre-filter (5 labels)
  gemini_health_check.py           Gemini API connectivity/structured-output check
  (02-06 planned)

src/                               Reusable library modules
  token_router.py                  Pre-Tier-1 router (ENGLISH / numeric / Hinglish)

reports/                           Reports & verification write-ups
  hinglish_normalization_architecture.md   FINALIZED Tier 1/2/3 spec (read first)
  wordnet_layer_report.md                 P1 rules-layer validation

AGENTS.md                          Agent instructions & conventions
PROBLEMS.md                        Problems-encountered & solutions log
CHANGELOG.md                       Change log (append-only)
```

## Setup

```bash
pip install -r requirements.txt
python scripts/clean_phinc.py
python scripts/export_phinc_vocab.py
python scripts/wordnet_hinglish_filter.py
```

## Pipeline

| Step | Script           | Description                       | Status |
|------|------------------|-----------------------------------|--------|
| 0    | `wordnet_hinglish_filter.py` | P1 token pre-filter for normalization (5 labels) | Done   |
| 1    | `clean_phinc.py` | Clean PHINC corpus (Steps 1-4)    | Done   |
| 2    | Build benchmark  | Generate query/passage pairs       | TODO   |
| 3    | Run retrieval    | BM25 + dense retrieval             | TODO   |
| 4    | Rerank           | Cross-encoder / LLM reranking      | TODO   |
| 5    | Evaluate         | MRR, MAP, NDCG metrics             | TODO   |
| 6    | Failure analysis | Error pattern analysis             | TODO   |

See `AGENTS.md` for conventions and `CHANGELOG.md` for progress.
