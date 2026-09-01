import difflib
import matplotlib.pyplot as plt
import nltk
from nltk.metrics.distance import edit_distance
import pandas as pd
import seaborn as sns

# # Ensure NLTK environment is ready
# try:
#     _ = edit_distance("test", "text")
# except Exception:
#     nltk.download("punkt")

# from ai4bharat.transliteration import XlitEngine

# # ------------------------------------------------------------------
# # 1. Load Sample Benchmark Dataset
# # ------------------------------------------------------------------
# sample_data = {
#     "hinglish_input": [
#         "mujhko",
#         "saza",
#         "di",
#         "pyar",
#         "ki",
#         "bht",
#         "bohot",
#         "bahut",
#         "dhanyabad",
#         "dhanywad",
#         "dhanyavaad",
#         "sapnon",
#         "rani",
#         "aayegi",
#         "tu",
#         "khabar",
#         "zindagi",
#         "mra",
#         "kya",
#         "hai",
#     ],
#     "ground_truth_devanagari": [
#         "मुझको",
#         "सज़ा",
#         "दी",
#         "प्यार",
#         "की",
#         "बहुत",
#         "बहुत",
#         "बहुत",
#         "धन्यवाद",
#         "धन्यवाद",
#         "धन्यवाद",
#         "सपनों",
#         "रानी",
#         "आएगी",
#         "तू",
#         "खबर",
#         "जिंदगी",
#         "मेरा",
#         "क्या",
#         "है",
#     ],
# }

# df = pd.DataFrame(sample_data)

# # ------------------------------------------------------------------
# # 2. Run IndicXlit Model
# # ------------------------------------------------------------------
# print("Initializing IndicXlit engine for Hindi ('hi')...")
# engine = XlitEngine("hi", beam_width=4, rescore=True)


# def transliterate_text(text):
#     try:
#         res = engine.translit_word(text, topk=1)
#         return res["hi"][0] if ("hi" in res and res["hi"]) else ""
#     except Exception:
#         return ""


# print("Running IndicXlit on Hinglish inputs...")
# df["indicxlit_output"] = df["hinglish_input"].apply(transliterate_text)

# # ------------------------------------------------------------------
# # 3. Calculate Metrics using NLTK & Standard Library
# # ------------------------------------------------------------------
# # Metric A: Exact Match Accuracy
# df["exact_match"] = df["indicxlit_output"] == df["ground_truth_devanagari"]

# # Metric B: Character Edit Distance (NLTK Levenshtein)
# df["edit_distance"] = df.apply(
#     lambda row: edit_distance(
#         row["indicxlit_output"], row["ground_truth_devanagari"]
#     ),
#     axis=1,
# )

# # Metric C: Character Error Rate (CER)
# df["cer"] = df.apply(
#     lambda row: (
#         row["edit_distance"] / max(len(row["ground_truth_devanagari"]), 1)
#     ),
#     axis=1,
# )

# # Metric D: Phonetic Similarity Ratio (built-in difflib)
# df["similarity_score"] = df.apply(
#     lambda row: difflib.SequenceMatcher(
#         None, row["indicxlit_output"], row["ground_truth_devanagari"]
#     ).ratio()
#     * 100,
#     axis=1,
# )

# # Aggregate Summary Metrics
# total_samples = len(df)
# accuracy = df["exact_match"].mean() * 100
# avg_cer = df["cer"].mean() * 100
# avg_similarity = df["similarity_score"].mean()

# # ------------------------------------------------------------------
# # 4. Print Results & Summary
# # ------------------------------------------------------------------
# print("\n" + "=" * 80)
# print("              SIDE-BY-SIDE TRANSLITERATION RESULTS")
# print("=" * 80)
# print(
#     df[
#         [
#             "hinglish_input",
#             "ground_truth_devanagari",
#             "indicxlit_output",
#             "exact_match",
#             "edit_distance",
#             "similarity_score",
#         ]
#     ].to_string(index=False)
# )

# print("\n" + "=" * 40)
# print("       AGGREGATE METRICS")
# print("=" * 40)
# print(f"Total Words Tested            : {total_samples}")
# print(f"Exact Match Accuracy         : {accuracy:.2f}%")
# print(f"Character Error Rate (CER)   : {avg_cer:.2f}%")
# print(f"Average Similarity Score     : {avg_similarity:.2f}%")
# print("=" * 40)

# # ------------------------------------------------------------------
# # 5. Plot Performance Chart
# # ------------------------------------------------------------------
# sns.set_theme(style="whitegrid")
# fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# metrics_df = pd.DataFrame(
#     {
#         "Metric": [
#             "Exact Match Accuracy",
#             "Avg Similarity Score",
#             "100 - CER",
#         ],
#         "Percentage (%)": [accuracy, avg_similarity, 100 - avg_cer],
#     }
# )

# sns.barplot(
#     data=metrics_df,
#     x="Metric",
#     y="Percentage (%)",
#     palette="viridis",
#     ax=axes[0],
# )
# axes[0].set_ylim(0, 105)
# axes[0].set_title("IndicXlit Performance Summary", fontsize=14, fontweight="bold")
# for p in axes[0].patches:
#     axes[0].annotate(
#         f"{p.get_height():.1f}%",
#         (p.get_x() + p.get_width() / 2.0, p.get_height() - 8),
#         ha="center",
#         va="center",
#         color="white",
#         fontweight="bold",
#     )

# sns.countplot(data=df, x="edit_distance", palette="mako", ax=axes[1])
# axes[1].set_title(
#     "NLTK Edit Distance Distribution (0 = Perfect Match)",
#     fontsize=14,
#     fontweight="bold",
# )
# axes[1].set_xlabel("Edit Distance (Character Mismatches)")
# axes[1].set_ylabel("Word Count")

# plt.tight_layout()
# plt.show()






































import re
from typing import Dict, Optional, List, Tuple


class HinglishNormalizer:
    def __init__(self, threshold: float = 0.65):
        """
        Initialize the 3-Tier Normalization Engine.
        :param threshold: Minimum similarity score (0.0 to 1.0) to accept a Tier 2 match.
        """
        self.threshold = threshold

        # Tier 1: Canonical Hashmap Lexicon
        self.canonical_map: Dict[str, str] = {
            "bht": "बहुत",
            "bohot": "बहुत",
            "bahut": "बहुत",
            "namaste": "नमस्ते",
            "namaskar": "नमस्कार",
            "dhanyavad": "धन्यवाद",
            "dhanyawad": "धन्यवाद",
            "khabar": "खबर",
            "khabr": "खबर",
            "kya": "क्या",
            "hal": "हाल",
            "haall": "हाल",
            "kaise": "कैसे",
            "ho": "हो",
            "aap": "आप",
        }

        # Phonetic character groups for Tier 2 penalty matrix
        self.vowels = {'a', 'e', 'i', 'o', 'u'}
        self.phonetic_pairs = [
            ({'v', 'w'}, 0.1),
            ({'z', 'j'}, 0.1),
            ({'f', 'ph'}, 0.1),
            ({'k', 'kh'}, 0.1),
            ({'t', 'th'}, 0.1),
            ({'d', 'dh'}, 0.1),
            ({'s', 'sh'}, 0.1),
        ]

        # Tier 3 Transliteration Engine Setup
        self._init_tier3_engine()

    def _init_tier3_engine(self):
        """Attempts to load IndicXlit if available, otherwise defaults to Pure-Python indic-transliteration."""
        self.ai4bharat_engine = None
        try:
            from ai4bharat.transliteration import XlitEngine
            self.ai4bharat_engine = XlitEngine("hi", beam_width=5, rescore=False)
            print("[INFO] Initialized Tier 3 with AI4Bharat IndicXlit Engine.")
        except Exception:
            print("[INFO] AI4Bharat unavailable. Using pure-Python 'indic-transliteration' as Tier 3 fallback.")

    # =========================================================================
    # TIER 2: PHONETIC WEIGHTED EDIT DISTANCE MECHANICS
    # =========================================================================
    def _get_substitution_cost(self, c1: str, c2: str) -> float:
        if c1 == c2:
            return 0.0

        # Check phonetic pair equivalence (low penalty = 0.1)
        pair = {c1, c2}
        for eq_set, penalty in self.phonetic_pairs:
            if pair.issubset(eq_set) or (c1 in eq_set and c2 in eq_set):
                return penalty

        # Vowel modification penalty (low penalty = 0.2)
        if c1 in self.vowels and c2 in self.vowels:
            return 0.2

        # Standard consonant substitution penalty
        return 1.0

    def _get_deletion_cost(self, char: str) -> float:
        return 0.2 if char in self.vowels else 1.0

    def _get_insertion_cost(self, char: str) -> float:
        return 0.2 if char in self.vowels else 1.0

    def weighted_edit_distance(self, s1: str, s2: str) -> float:
        """Calculates dynamic programming cost with weighted phonetic penalties."""
        m, n = len(s1), len(s2)
        dp = [[0.0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            dp[i][0] = dp[i - 1][0] + self._get_deletion_cost(s1[i - 1])

        for j in range(1, n + 1):
            dp[0][j] = dp[0][j - 1] + self._get_insertion_cost(s2[j - 1])

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                sub_cost = self._get_substitution_cost(s1[i - 1], s2[j - 1])
                dp[i][j] = min(
                    dp[i - 1][j] + self._get_deletion_cost(s1[i - 1]),
                    dp[i][j - 1] + self._get_insertion_cost(s2[j - 1]),
                    dp[i - 1][j - 1] + sub_cost
                )

        return dp[m][n]

    def similarity_score(self, s1: str, s2: str) -> float:
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0
        dist = self.weighted_edit_distance(s1, s2)
        return max(0.0, 1.0 - (dist / max_len))

    # =========================================================================
    # PIPELINE TIERS
    # =========================================================================
    def _tier1_exact_lookup(self, token: str) -> Optional[str]:
        """Tier 1: Hashmap O(1) Lookup"""
        return self.canonical_map.get(token.lower())

    def _tier2_phonetic_match(self, token: str) -> Optional[str]:
        """Tier 2: Weighted Edit Distance Matcher"""
        best_match = None
        highest_sim = 0.0

        for candidate_key, canonical_val in self.canonical_map.items():
            sim = self.similarity_score(token.lower(), candidate_key.lower())
            if sim > highest_sim and sim >= self.threshold:
                highest_sim = sim
                best_match = canonical_val

        return best_match

    def _tier3_fallback(self, token: str) -> str:
        """Tier 3: Transliteration Neural/Rule Fallback for OOV terms"""
        # If IndicXlit is installed and loaded:
        if self.ai4bharat_engine:
            try:
                out = self.ai4bharat_engine.translit_word(token, topk=1)
                if "hi" in out and len(out["hi"]) > 0:
                    return out["hi"][0]
            except Exception:
                pass

        # Pure-Python fallback using indic-transliteration
        try:
            from indic_transliteration import sanscript
            from indic_transliteration.sanscript import transliterate
            return transliterate(token, sanscript.ITRANS, sanscript.DEVANAGARI)
        except Exception:
            return token

    # =========================================================================
    # MAIN QUERY PROCESSING PIPELINE
    # =========================================================================
    def normalize_token(self, token: str) -> Tuple[str, str]:
        """Processes a single token through Tier 1 -> Tier 2 -> Tier 3."""
        # Clean token punctuation
        clean_token = re.sub(r'[^\w\s]', '', token)
        if not clean_token:
            return token, "Passthrough"

        # Tier 1 Check
        res = self._tier1_exact_lookup(clean_token)
        if res:
            return res, "Tier 1 (Exact Map)"

        # Tier 2 Check
        res = self._tier2_phonetic_match(clean_token)
        if res:
            return res, "Tier 2 (Phonetic Edit Distance)"

        # Tier 3 Fallback
        res = self._tier3_fallback(clean_token)
        return res, "Tier 3 (Transliteration Fallback)"

    def normalize_query(self, query: str) -> Tuple[str, List[Tuple[str, str, str]]]:
        """
        Normalizes a full Hinglish query string into canonical Devanagari roots.
        Returns: (Normalized Query, Detailed Step Trace)
        """
        tokens = query.split()
        normalized_tokens = []
        trace = []

        for token in tokens:
            norm_token, source_tier = self.normalize_token(token)
            normalized_tokens.append(norm_token)
            trace.append((token, norm_token, source_tier))

        return " ".join(normalized_tokens), trace


# =========================================================================
# VERIFICATION AND TESTING
# =========================================================================
if __name__ == "__main__":
    normalizer = HinglishNormalizer(threshold=0.65)

    test_queries = [
        "bht dhanyawad aapka",         # Tier 1 + Tier 1/2
        "bohot khabr achi h",          # Tier 1 + Tier 2
        "namaste kaise ho",            # Exact map
        "swagat hai aapka",            # Fallback OOV term (swagat)
    ]

    print("\n" + "=" * 60)
    print("HINGLISH PHONETIC RAG - MIDDLEWARE EXECUTION DEMO")
    print("=" * 60 + "\n")

    for query in test_queries:
        normalized_query, trace = normalizer.normalize_query(query)
        print(f"Original Input   : '{query}'")
        print(f"Normalized Output : '{normalized_query}'")
        print("Pipeline Execution Details:")
        for raw, norm, tier in trace:
            print(f"  * '{raw}' -> '{norm}' [{tier}]")
        print("-" * 60)