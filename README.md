# FAIR-RANK: Fair & Efficient Resume Screening System (Part 2)

**Module:** COM713 Advanced Data Structures and Algorithms  
**Assessment:** Data Structure & Algorithm with Python — Part 2 (Individual Work, 30%)  
**Dataset Source URL:** https://www.kaggle.com/datasets/snehaananthan/resume-dataset (Anonymized Tech Resumes Dataset)

## Overview
FAIR-RANK is an algorithmic candidate screening framework designed to address bias and scalability limits in automated recruitment. Part 2 delivers a working Python implementation of custom data structures (`SkillTrie`, `SkillGraph`, `InvertedIndex`, `TopKRanker` bounded min-heap), feature extraction, scoring, counterfactual fairness auditing (`FairnessAuditor`), empirical benchmarking, and executable Jupyter Notebook demonstration.

## Repository Structure
```
fair-rank/
├── data/
│   ├── raw/resumes_raw.csv              # Unmodified downloaded dataset
│   ├── processed/resumes_clean.csv      # Cleaned & normalized dataset
│   ├── skills_dictionary.json           # Canonical skills vocabulary for SkillTrie
│   ├── skills_synonyms.json             # Synonym adjacency list for SkillGraph
│   └── job_descriptions.json            # Target job descriptions for testing
├── src/fair_rank/
│   ├── __init__.py
│   ├── job_description.py               # JobDescription class (validated weights)
│   ├── candidate.py                     # Candidate class data model
│   ├── anonymizer.py                    # ResumeAnonymizer (PII masking)
│   ├── normalizer.py                    # TextNormalizer (lowercasing, tokenization)
│   ├── skill_trie.py                    # SkillTrie & TrieNode (greedy phrase matching)
│   ├── skill_graph.py                   # SkillGraph (1-hop synonym resolution)
│   ├── feature_extractor.py             # FeatureExtractor (experience, education, certs)
│   ├── inverted_index.py                # InvertedIndex (candidate posting lookup)
│   ├── scorer.py                        # CandidateScorer (5-component breakdown)
│   ├── top_k_ranker.py                  # TopKRanker (bounded min-heap O(n log k))
│   ├── fairness_auditor.py             # FairnessAuditor (counterfactual pair auditing)
│   ├── explanation_generator.py     # ExplanationGenerator (human-readable reasoning)
│   ├── screening_controller.py      # ScreeningController (10-stage pipeline orchestrator)
│   └── utils.py                         # Timing & memory benchmarking helpers
├── scripts/preprocess_data.py           # Builds data/processed/resumes_clean.csv from raw
├── tests/                               # Pytest test suite (32 tests, all classes covered)
├── benchmarks/                          # Empirical efficiency and quality benchmarks (+ results/)
└── notebooks/                           # Executable Jupyter Notebook submission
```

The final PDF report, executed notebook copy, full-script appendix and dataset submitted for
grading live one level up, in `../../Deliverables/Part2/` — not inside this project folder.
This folder (`project/fair-rank/`) is the working codebase the report and notebook are built from.

## Setup & Running
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run unit tests
pytest --maxfail=1 -v

# 3. Run efficiency & quality benchmarks
python benchmarks/run_efficiency_benchmark.py
python benchmarks/run_ranking_quality_benchmark.py

# 4. Launch Jupyter Notebook
jupyter notebook notebooks/FAIR-RANK_Part2.ipynb
```
