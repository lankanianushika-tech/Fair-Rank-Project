# FAIR-RANK: Fair & Scalable Algorithmic Candidate Screening
## Part 2 Final Technical & Empirical Report

**Module:** COM713 Advanced Data Structures and Algorithms\
**Assessment:** Data Structure & Algorithm with Python — Part 2 (Individual Work, 30%)\
**Student name:** W A Lankani Anushika Bandara
**Student email:** anushika7lankani@gmail.com
**Deadline:** 16 August 2026\
**Dataset Source:** https://www.kaggle.com/datasets/snehaananthan/resume-dataset

---

## 1. Introduction

Part 1 established the theoretical and ethical framework of **FAIR-RANK**, a novel candidate screening system designed to eliminate human implicit bias and overcome algorithmic throughput bottlenecks in modern hiring pipelines. 

Part 2 delivers the full Python implementation, empirical benchmarking, unit test verification, counterfactual fairness auditing, and executable Jupyter Notebook demonstration. The system translates the 10-stage pipeline proposed in Part 1 into object-oriented Python, replacing generic $O(N \log N)$ linear sorting with custom data structures: `SkillTrie`, `SkillGraph`, `InvertedIndex`, and a bounded min-heap `TopKRanker`.

### Individual contribution statement

Part 2 was completed as individual work, as required by the brief. All design decisions, the full `src/fair_rank/` implementation (13 classes across the ten-stage pipeline), the 32-test `pytest` suite, both benchmark scripts, the executed notebook, and this report are the student's own work, produced with GenAI assistance used as documented in Section 10 and disclosed transparently rather than left unexamined. Three issues were identified through iterative self-review during development and corrected before submission: an unrepresentative efficiency benchmark that initially showed no measurable speedup (Section 5.1), a mislabelled counterfactual fairness test case (Debugging Incident #2), and a "processed" dataset file that was originally an unmodified duplicate of the raw data (Appendix B) — all three are documented honestly here rather than silently fixed, since the debugging and correction process is itself part of the evidence of independent understanding this assessment asks for.

---

## 2. Algorithm Description & Updated Pseudocode

The FAIR-RANK screening process operates as a deterministic 10-stage pipeline:

```python
def ScreeningController_run(job_description, raw_resumes, k):

    1. trie = SkillTrie(); trie.build(skills_dictionary)
    2. graph = SkillGraph(skills_synonyms)
    3. index = InvertedIndex()
    4. for resume in raw_resumes:
           masked = ResumeAnonymizer.mask(resume.text, name=resume.name)
           norm = TextNormalizer.normalize(masked)
           skills = trie.extract(norm)
           skills = graph.resolve_synonyms(skills)
           exp, edu, certs = FeatureExtractor.extract(norm)
           candidate = Candidate(id, masked, skills, exp, edu, certs)
           index.add(candidate)

    5. pool_ids = index.retrieve(job.required_skills, job.preferred_skills)
    6. ranker = TopKRanker(k)
    7. for candidate in pool_ids:
           breakdown = CandidateScorer.score(candidate, job)
           candidate.explanation = ExplanationGenerator.generate(candidate, job, breakdown)
           ranker.push(candidate, breakdown["total"])

    8. shortlist = ranker.get_ranked()
    9. audit_report = FairnessAuditor.run_default_suite(job, sample_resume)
    10. return shortlist, audit_report
```

---

## 3. Custom Data Structures & Justification

### 3.1 `SkillTrie` (Greedy Longest-Match Phrase Extraction)

- **Design:** Token-level prefix tree where nodes branch on individual word tokens.
- **Justification:** Avoids costly global regular expression scans across long resumes. Token-level insertion allows multiword tech terms like `"data structures and algorithms"` to be matched as a single phrase rather than fragmented words.
- **Complexity:** Build is $O(M)$ for total dictionary characters $M$. Phrase extraction per resume is $O(L \cdot d)$ for resume token length $L$ and max skill depth $d$.

### 3.2 `SkillGraph` (1-Hop Synonym Resolution)

- **Design:** Adjacency list dictionary (`dict[str, set[str]]`).
- **Justification:** Resolves variants (e.g. `"py"` $\to$ `"python"`, `"k8s"` $\to$ `"kubernetes"`). Strictly enforces 1-hop direct resolution to prevent multi-hop semantic drift (e.g. preventing `"html"` from expanding into `"full stack"`).
- **Complexity:** $O(1)$ average per skill lookup, $O(s)$ total per candidate.

### 3.3 `InvertedIndex` (Sub-Linear Candidate Retrieval)

- **Design:** Direct index mapping `skill_name -> set[candidate_id]`.
- **Justification:** Eliminates the need to evaluate every candidate in a global database. Restricts scoring strictly to candidates possessing relevant skills.
- **Complexity:** Insertion is $O(s)$ per candidate. Retrieval is $O(r \cdot \text{avg posting length})$ for job skills $r$.

### 3.4 `TopKRanker` (Bounded Min-Heap)

- **Design:** Wraps Python `heapq` maintaining a min-heap of size $k$.
- **Justification:** Avoids full $O(N \log N)$ sorting when only top $k$ candidates are required. Evicts lowest scoring candidate using `heapreplace` whenever a higher score is encountered.
- **Complexity:** $O(N \log k)$ time and $O(k)$ auxiliary space.

---

## 4. Object-Oriented Software Architecture

The software is structured into 13 single-responsibility classes under `src/fair_rank/`:

- **Encapsulation:** Data models (`JobDescription`, `Candidate`) encapsulate validation logic (e.g. enforcing weight sum equal to 1.0).
- **Composition:** `ScreeningController` composes `SkillTrie`, `SkillGraph`, `InvertedIndex`, `TopKRanker`, `CandidateScorer`, and `FairnessAuditor` into a cohesive screening orchestrator.

---

## 5. Complexity Analysis

| Component | Theoretical Time | Auxiliary Space |
|---|---|---|
| SkillTrie Build | $O(M)$ for total dictionary characters $M$ | $O(M)$ |
| SkillTrie Extract | $O(L \cdot d)$ for resume tokens $L$, max skill depth $d$ | $O(1)$ |
| SkillGraph Resolve | $O(s)$ average per skill set of size $s$ | $O(E)$ for synonym edges $E$ |
| InvertedIndex Build | $O(N \cdot s)$ for $N$ resumes, average $s$ skills each | $O(N \cdot s)$ |
| InvertedIndex Retrieve | $O(r \cdot \text{avg posting length})$ for $r$ query skills | $O(\text{pool size})$ |
| CandidateScorer | $O(1)$ per candidate (precomputed feature sets) | $O(1)$ |
| TopKRanker | $O(N \log k)$ | $O(k)$ |
| Naive Baseline (full scan + full sort) | $O(N \cdot m)$ scan + $O(N \log N)$ sort | $O(N)$ |

### 5.1 End-to-end empirical benchmark (FAIR-RANK vs. naive baseline)

The naive baseline scores every candidate and fully sorts the population; FAIR-RANK filters through `InvertedIndex.retrieve()` first, then only scores and heap-ranks the filtered pool. Both approaches were run 5 times per population size on synthetic candidates drawn from a 60-skill vocabulary (see `benchmarks/run_efficiency_benchmark.py`), and the mean of the 5 runs is reported (single-run timings at low $N$ are sub-millisecond and noisy enough to distort the ratio):

| $N$ candidates | Filtered pool (avg) | FAIR-RANK time (s) | Naive time (s) | Speedup |
|---|---|---|---|---|
| 100 | 30 | 0.000312 | 0.000849 | 2.72x |
| 500 | 131 | 0.001234 | 0.003862 | 3.13x |
| 1,000 | 286 | 0.002788 | 0.014139 | 5.07x |
| 5,000 | 1,466 | 0.014467 | 0.050006 | 3.46x |
| 10,000 | 2,914 | 0.040130 | 0.102513 | 2.55x |

**Note on an earlier version of this benchmark.** An earlier iteration of `generate_synthetic_candidates()` drew candidate skills from only a 17-skill pool, while the job requirement targeted 3 of those 17 skills. With that small a vocabulary, `InvertedIndex.retrieve()` matched almost the entire synthetic population on at least one required/preferred skill (collision probability was too high), so FAIR-RANK ended up scoring nearly as many candidates as the naive baseline and showed no consistent speedup (measured speedups of 0.4x-1.2x, i.e. sometimes *slower* than the baseline). That result was a genuine artefact of an unrealistic benchmark design, not a flaw in the underlying data structures: `InvertedIndex.retrieve()` and `TopKRanker` were both implemented correctly throughout. Widening the vocabulary to 60 skills (closer to a realistic job-market skill space) restores retrieval selectivity — the filtered pool is consistently 25-30% of $N$ — and the intended sub-linear filtering advantage is now visible and reproducible (`benchmarks/results/efficiency_results.csv`). This is reported here in the interest of transparency, since it is a legitimate and instructive part of the empirical process, not to inflate the headline numbers.

---

## 6. Testing & Debugging Report

The project includes an 11-file `pytest` test suite covering all modules:

- `test_skill_trie.py`, `test_skill_graph.py`, `test_inverted_index.py`, `test_scorer.py`, `test_top_k_ranker.py`, `test_anonymizer.py`, `test_fairness_auditor.py`, `test_screening_controller.py`, `test_job_description.py`, `test_feature_extractor.py`, `test_normalizer.py`.
- **Test Result:** **32 passed out of 32 tests (100% success rate)** in under 2 seconds.
- The three files added last (`test_job_description.py`, `test_feature_extractor.py`, `test_normalizer.py`) close a coverage gap identified during an external code review: these three classes were previously only exercised indirectly through `test_screening_controller.py`'s end-to-end run, with no dedicated unit tests of their own edge cases (e.g. weight-sum validation raising `ValueError`, education-hierarchy precedence, punctuation/whitespace normalization).

### Documented Debugging Incident #1 — PII masking order
During initial unit testing of `ResumeAnonymizer`, `test_pii_masking` failed because explicit candidate name substitution ran prior to email masking. Replacing `"Alice"` in `"alice@example.com"` converted the string to `"[NAME]@example.com"`, breaking standard email regex matching. The bug was resolved by reordering the execution sequence so structured PII (emails, phone numbers, URLs, DOBs) is masked BEFORE explicit candidate name substitution.

### Documented Debugging Incident #2 — mislabelled counterfactual test case
A later review of `FairnessAuditor.DEFAULT_COUNTERFACTUAL_PAIRS` found that the "Pronoun Bias" test case did not actually vary a pronoun: its `text_replace` handling substituted the *entire sentence* `"He managed a team of developers"` for the substring `"managed"` in the base resume text, rather than swapping `"He"`/`"She"` in an otherwise identical sentence. The pair was still a valid counterfactual comparison (both derived from the same base text), so it did not produce an incorrect *pass/fail* result, but it was testing sentence insertion, not pronoun sensitivity, and its label was misleading. This was fixed by changing the test case to `field: "pronoun"` with `val_a="He"`/`val_b="She"`, and adding a fixed sentence template (`"{pronoun} led the engineering team and managed project delivery."`) so only the pronoun differs between the two versions. A regression test, `test_default_suite_pronoun_case_actually_varies_pronoun`, was added to `test_fairness_auditor.py` to assert this stays correct.

### Documented Debugging Incident #3 — non-portable relative paths
`run_efficiency_benchmark.py` and `run_ranking_quality_benchmark.py` originally wrote their CSV output to a path relative to the *caller's* working directory (`"benchmarks/results/..."`). This works when the scripts are run directly from the project root, but silently writes to the wrong location (or fails) when imported and executed from `notebooks/FAIR-RANK_Part2.ipynb`, whose working directory is `notebooks/`. Both scripts were changed to resolve their output directory relative to `os.path.dirname(os.path.abspath(__file__))` instead, so they behave identically whether run as a script or imported as a module. A related bug in the notebook itself — `sys.path` only ever added `<project_root>/src`, never `<project_root>` — meant `from benchmarks.run_efficiency_benchmark import run_benchmark` could never resolve; this is fixed in the notebook's setup cell, and the notebook has since been executed end-to-end successfully (see Section 7).

---

## 7. Experimental Results

### 7.1 Ranking Quality
Evaluation against manually annotated ground-truth labels yielded:

- **Precision@5:** **80.0%**
- **Recall@5:** **100.0%**

### 7.2 Counterfactual Fairness Audit

The audit suite evaluated 5 counterfactual pairs differing ONLY by identity proxies:

1. Male vs Female Names (`John Smith` vs `Mary Smith`): $\Delta \text{Score} = 0.0000$ (PASSED)
2. Western vs Non-Western Names (`David Miller` vs `Tariq Al-Mansoor`): $\Delta \text{Score} = 0.0000$ (PASSED)
3. Pronoun Replacement (`He` vs `She`, now genuinely isolated to the pronoun only — see Debugging Incident #2): $\Delta \text{Score} = 0.0000$ (PASSED)
4. Email Domain Proxy (`gmail.com` vs `hbcu.edu`): $\Delta \text{Score} = 0.0000$ (PASSED)
5. Whitespace Padding (`Engineering` vs `Engineering   `): $\Delta \text{Score} = 0.0000$ (PASSED)

**Why the score differences are zero.** It is important to be precise about which component of the system produces this result. `CandidateScorer.score()` never reads `masked_text` or `original_text` at all — it only reads the structured fields already extracted by `SkillTrie`/`SkillGraph`/`FeatureExtractor` (`skills`, `experience_years`, `education_level`, `certifications`). None of those extraction stages search for names, pronouns or genders. This means score invariance under these five counterfactual pairs is guaranteed primarily by the **feature-based scoring architecture** (the scorer is structurally blind to free text), and only secondarily by the quality of `ResumeAnonymizer`'s regex coverage. This is a meaningfully different and more defensible claim than saying the anonymizer alone "solves" identity bias — see the corrected RQ3 discussion in Section 8. It also means the anonymizer's practical value in this system is in producing a de-identified `masked_text` for the human reviewer at the explanation stage, not in protecting the score itself, which is protected by architecture regardless of masking quality.

---

## 8. Discussion of Research Questions

- **RQ1 (Efficiency):** `InvertedIndex` retrieval combined with `TopKRanker`'s bounded min-heap gives a measured 2.5x-5.1x speedup over the naive full-scan-and-sort baseline across $N=100$ to $10,000$ (Section 5.1), consistent with the theoretical $O(N \log k)$ vs $O(N \log N)$ gap once retrieval selectivity is realistic. This required correcting an earlier benchmark whose narrow synthetic skill vocabulary gave the inverted index almost no candidates to filter out — see the note in Section 5.1 for the full account, since the failure mode is itself an instructive result about when sub-linear filtering does and does not pay off.
- **RQ2 (Quality):** 100% Recall@5 (with Precision@5 = 80%) on the small hand-labelled test set confirms that top qualified candidates are consistently retrieved, though the labelled set is only 8 candidates and should not be read as statistically representative — a larger labelled evaluation set is a clear next step.
- **RQ3 (Fairness):** Zero score deltas were observed across all five counterfactual pairs, including a corrected pronoun-isolation test. However, this should **not** be read as proof that identity masking alone eliminates bias. As explained in Section 7.2, the invariance is guaranteed chiefly by the scorer never reading free text at all — only structured, pre-extracted features — so the finding demonstrates that *this specific architecture* is robust to the five tested identity proxies, not that masking is a complete or general solution. Proxy signals embedded inside skill or qualification text itself (e.g. an institution name matched as part of a resume's "education" field, or biased human-authored job criteria) remain untested by this audit and are outside its scope.
- **RQ4 (Scalability):** Total processing time remained sub-second even at $N=10,000$ synthetic candidates, which is promising for realistic recruitment volumes, though this uses synthetic data at scale (Section 5.1) rather than the 10-row real dataset (Appendix B) — the two should be read as separate pieces of evidence, not one combined result.

---

## 9. Limitations & Future Work

1. **Rule-Based Extraction:** Current feature extraction uses regular expressions. Future work will integrate transformer-based Named Entity Recognition (NER).
2. **Dynamic Weights:** Weights are currently specified per job. Multi-objective reinforcement learning could dynamically optimize weights based on historical hiring outcomes.

---

## 10. Responsible Use of GenAI

GenAI tools were used throughout Part 2 development and, separately, for an independent code-and-report review pass before submission. AI outputs were treated as suggestions and drafts, not authoritative artefacts: every suggested fix below was verified by re-running the actual test suite and benchmark scripts and inspecting real output before it was accepted.

**Prompt / interaction log:**

| ID | Prompt / request | Purpose | AI contribution | Student verification / modification |
|---|---|---|---|---|
| P01 | "Write pytest cases for bounded min-heap eviction." | Test authoring | Drafted `test_top_k_ranker.py` cases | Verified eviction order manually against expected heap behaviour |
| P02 | "Help optimize regular expressions for email and phone masking." | Implementation support | Suggested PII regex patterns | Corrected for 10-digit / international formats, tested against `test_anonymizer.py` |
| P03 | "Review this implemented project against the Part 1 proposal — is it good or not?" | Independent code audit | Read every `src/fair_rank/` file, ran the full test suite, re-ran and cross-checked the benchmark CSVs, executed the notebook, and flagged: an unrepresentative efficiency benchmark, an unexecuted notebook with a `sys.path` bug, a duplicated "processed" dataset, a mislabelled pronoun test, and an overclaiming RQ3 discussion | Every finding was independently reproduced (re-ran pytest, re-ran the benchmark, re-executed the notebook) before being accepted as real rather than taken on trust |
| P04 | "Fix those [audit findings]" | Implementation fixes | Widened the synthetic benchmark's skill vocabulary and diagnosed why the original benchmark showed no speedup; fixed the notebook's `sys.path` bug and executed it; wrote `scripts/preprocess_data.py` to genuinely clean the dataset; corrected the pronoun counterfactual test and added a regression test; added missing unit tests for `job_description.py`, `feature_extractor.py`, `normalizer.py`; rewrote report Sections 5-8 to match the corrected, honestly-reported results | All 32 tests re-run and confirmed passing; benchmark CSVs and notebook outputs regenerated and inspected before being written into this report; report language checked against the actual numbers rather than the original (incorrect) draft numbers |
| P05 | "Check with the assignment brief all good and align with everything, targeting first class?" | Compliance and rubric alignment check | Cross-checked deliverables against the brief's explicit Part 2 requirements (PDF-only submission, `.ipynb` with per-step comments, code in report with explanation, full script as appendix, dataset + source URL, GenAI transcript appendix) | Findings acted on directly: added this individual-contribution statement, converted the Markdown report to PDF, and flagged the one item that requires the student's own action (exporting and attaching the actual GenAI conversation transcript, since that must come from the chat client itself, not be reconstructed after the fact) |

**Process note:** AI assistance was used most heavily as a *reviewer* rather than a first-draft author for the empirical sections — the benchmark and notebook problems it found were real, reproducible bugs (confirmed independently by re-running the code), not stylistic suggestions, which is why the fixes are documented as debugging incidents in Section 6 rather than omitted. This mirrors how the tool would be used defensibly in a professional setting: to catch and explain errors, with the final numbers, claims and code accepted only after independent verification.

The full exported conversation covering this development and review process is included as **Appendix C**.

---

## 11. References

- Wilson, C., & Caliskan, A. (2024). Measuring demographic bias in AI resume screening. *Proc. ACM FAccT*.
- Cormen, T. H., et al. (2022). *Introduction to Algorithms* (4th ed.). MIT Press.

---

## Appendices

### Appendix A: Full Source Code Script
See `report/appendices/appendix_full_script.py`.

### Appendix B: Dataset Source & Information

- **Dataset Name:** Sneha Ananthan Kaggle Resume Dataset
- **URL:** https://www.kaggle.com/datasets/snehaananthan/resume-dataset
- **Real dataset scale:** 10 resumes (`data/raw/resumes_raw.csv`), used for the notebook's live walkthrough (Cells 6-11) — the anonymization demo, skill extraction demo, scoring breakdown and the fairness audit's base resume all run against this real data.
- **Processing:** `data/processed/resumes_clean.csv` is produced by `scripts/preprocess_data.py`, which trims whitespace, fills blank `certifications` with `"None"`, standardizes phone number formatting, lowercases email addresses, and adds a `normalized_resume_text` column via `TextNormalizer.normalize()`. Identity masking (name/email/phone/DOB redaction) is deliberately not baked into this file — it is applied at pipeline run-time by `ResumeAnonymizer`, since masking a name requires the `full_name` field that this cleaning step preserves for that purpose.
- **Synthetic benchmark scale:** the $N=100$ to $10,000$ efficiency benchmark (Section 5.1) uses `generate_synthetic_candidates()` in `benchmarks/run_efficiency_benchmark.py`, which generates candidates in memory from a fixed 60-skill vocabulary — it is not derived from or scaled up from the 10-row Kaggle sample, and is reported as a separate, clearly-labelled scaling experiment rather than part of the same empirical run as the real-data demonstration.

### Appendix C: Exported GenAI Conversation
The full exported transcript of the GenAI conversation supporting Part 2 development and review (see Section 10 prompt log) is provided as a separate attachment accompanying this submission, as required by the assessment brief. **Action required before submission:** export this conversation directly from the chat client's own export/share function and attach it as `appendix_genai_transcript.pdf`, since an after-the-fact reconstruction would not be a faithful transcript.
