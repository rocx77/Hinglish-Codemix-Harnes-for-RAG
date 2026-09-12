## Batch integrity check (top 100 pilot-pool tokens)

### 1. Length check
- batch_input length: 100
- batch_result_1 structure: nrows=100, nper_row=[4, 4, 4] (expected 100 rows x 4 candidates, or flat 400)

- RESULT: PASS

### 2. Determinism check (batch1 vs batch2, same input/order)
- mismatched indices: none
- RESULT: PASS

### 3. Batch vs sequential top-candidate check
- mismatched indices: 8
  [8] token='liye'  batch_top=लिए  seq_top=लिये
       batch_cands=["लिए", "लिये", "लीये", "लीए"]
  [25] token='abhi'  batch_top=अभी  seq_top=अभि
       batch_cands=["अभी", "अभि", "आभी", "आभि"]
  [47] token='my'  batch_top=माई  seq_top=माय
       batch_cands=["माई", "माय", "मी", "माइ"]
  [55] token='pata'  batch_top=पता  seq_top=पाटा
       batch_cands=["पता", "पाटा", "पटा", "पाता"]
  [60] token='nhi'  batch_top=नही  seq_top=न्ही
       batch_cands=["नही", "न्ही", "न्हि", "न्हीं"]
  [76] token='sahi'  batch_top=सही  seq_top=साही
       batch_cands=["सही", "साही", "सहि", "साहि"]
  [89] token='zyada'  batch_top=ज्यादा  seq_top=ज़्यादा
       batch_cands=["ज्यादा", "ज़्यादा", "ज्याडा", "ज़्याडा"]
  [98] token='chal'  batch_top=चल  seq_top=चाल
       batch_cands=["चल", "चाल", "छल", "छाल"]
- RESULT: FAIL

BATCHING_TRUSTED: false
