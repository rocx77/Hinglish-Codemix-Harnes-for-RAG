# Low-Latency 3-Tier Normalization Middleware for Hinglish-to-Devanagari RAG

## 1. System Architecture & Technical Stack
The system acts as a low-latency query normalization middleware within a Retrieval-Augmented Generation (RAG) pipeline, designed to mitigate subword tokenization drift in dense retrievers (like BGE-M3) when processing code-mixed Hinglish text.

**Middleware Pipeline:**
*   **Tier 1:** Canonical Hashmap (O(1) lookup).
*   **Tier 2:** Phonetic Weighted Edit Distance (custom penalty costs for vowel/consonant variations).
*   **Tier 3:** Neural Fallback (`IndicXlit` via `ai4bharat-transliteration`).

**Environment & Hardware Integration:**
*   **Local Python Environment:** Native Windows Python 3.10 virtual environment (`venv`) to completely bypass modern Python 3.11+ `dataclass` bugs in `fairseq`.
*   **Hardware Acceleration:** PyTorch compiled with CUDA 12.1 to fully utilize RTX 4050 Ada Lovelace tensor cores for batched `translit_sentence` inference, keeping the neural fallback step latency well under target constraints.

---

## 2. Literature Review: Foundations and Modern Tooling
*(Organized thematically to establish the trajectory of mixed-script retrieval challenges)*

### The Mixed-Script Retrieval Problem
The fundamental failure mode of information retrieval systems when faced with Romanized or mixed-script Indic text has been well-documented. Early foundational work formally defined how spelling variations and transliteration noise break standard term-matching and tokenization. 

### Prior Normalization Approaches
Historically, handling transliteration variability relied on classical algorithms rather than neural encodings. Approaches like the Hindex algorithm customized phonetic matching specifically for mixed-script transliterated Hindi queries. These approaches built upon classical weighted edit-distance foundations (Oommen & Loke, 1997), which form the algorithmic basis for this system's Tier 2 normalization layer.

### Modern Retrieval Tooling
The architecture of this project leverages several distinct advances in modern natural language processing. BGE-M3 (Chen et al., 2024) serves as the downstream multilingual semantic retriever. The Tier 3 fallback relies on `IndicXlit`, a neural transliteration model trained on the extensive Aksharantar parallel datasets. Additionally, system retrieval metrics are aligned with the standard evaluation frameworks established by Lewis et al. (2020) for RAG and dense benchmarks like Hindi-BEIR.

### Dataset Limitations
While robust corpora like PHINC (Srivastava & Singh, 2020) and Hinglish-TOP (Agarwal et al., 2023) exist for translation and parsing tasks, neither serves as a dedicated retrieval benchmark with document-level relevance judgments.

---

## 3. Research Gap & System Novelty
The challenge of Hinglish retrieval is not entirely unstudied; the Forum for Information Retrieval Evaluation (FIRE) hosted "Mixed Script Information Retrieval" and "Transliterated Search" shared tasks between 2013 and 2015. Teams successfully utilized edit-distance query expansion to retrieve Hindi documents. However, this prior work leaves a significant measurement gap in the modern AI landscape, which this project addresses:

1.  **The Dense Encoder Gap:** The FIRE shared tasks predated dense embeddings, relying instead on query expansion feeding into classical language models. No studies have evaluated whether cheap deterministic normalization still improves retrieval—or interacts differently—when the downstream system is a modern dense encoder (like BGE-M3) that already possesses some multilingual pretraining robustness.
2.  **Lack of Noisy Input Benchmarks:** Current state-of-the-art benchmarks for Hindi, such as Hindi-BEIR, evaluate clean Devanagari and translated text. There is currently no modern benchmark that combines dense retrieval evaluation metrics with noisy, Romanized Hinglish query inputs.
3.  **Missing 3-Way Controlled Comparisons:** There is no existing quantification comparing raw dense retrieval, heavy Machine Translation (MT) normalization, and cheap deterministic normalization. This comparison is necessary to determine exactly how much of MT's semantic benefit can be recovered by a computationally cheaper method.
4.  **Novel Tiered Architecture:** Exact dictionaries, phonetic edit-distance matching, and neural transliteration exist as isolated tools. Assembling them into a strict 3-tier fallback pipeline to optimize latency specifically for a RAG architecture has not been previously evaluated as a cohesive system.