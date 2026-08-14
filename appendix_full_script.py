# ==============================================================================
# FAIR-RANK: PART 2 FULL CONCATENATED SOURCE CODE SCRIPT
# Module: COM713 Advanced Data Structures and Algorithms
# Regenerated from src/fair_rank/ after the Part 2 review fixes
# ==============================================================================

# --- src/fair_rank/job_description.py ---
from typing import Set, Dict, Optional

class JobDescription:
    """
    Data model representing a job posting requirement specification.
    Validates that candidate scoring component weights sum strictly to 1.0.
    """

    DEFAULT_WEIGHTS = {
        "required_skills": 0.50,
        "preferred_skills": 0.20,
        "experience": 0.15,
        "education": 0.10,
        "certifications": 0.05,
    }

    def __init__(
        self,
        title: str,
        required_skills: Set[str],
        preferred_skills: Optional[Set[str]] = None,
        min_experience_years: float = 0.0,
        required_education: str = "Bachelor",
        required_certifications: Optional[Set[str]] = None,
        k: int = 10,
        weights: Optional[Dict[str, float]] = None,
        job_id: str = "JOB_001",
    ):
        self.job_id = job_id
        self.title = title
        self.required_skills = {s.lower().strip() for s in required_skills}
        self.preferred_skills = {s.lower().strip() for s in (preferred_skills or set())}
        self.min_experience_years = float(min_experience_years)
        self.required_education = required_education.strip()
        self.required_certifications = {c.lower().strip() for c in (required_certifications or set())}
        self.k = int(k)
        
        self.weights = weights if weights is not None else dict(self.DEFAULT_WEIGHTS)
        self._validate_weights()

    def _validate_weights(self) -> None:
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-5:
            raise ValueError(f"JobDescription weights must sum to 1.0, got {total:.4f}")

    def __repr__(self) -> str:
        return f"<JobDescription title='{self.title}' required_skills={len(self.required_skills)} k={self.k}>"

# --- src/fair_rank/candidate.py ---
from typing import Set, Dict, Optional

class Candidate:
    """
    Data model representing an anonymized candidate profile.
    Original text is stored separately and never exposed to scoring to preserve fairness.
    """

    def __init__(
        self,
        candidate_id: str,
        masked_text: str,
        original_text: str = "",
        skills: Optional[Set[str]] = None,
        experience_years: float = 0.0,
        education_level: str = "Unknown",
        certifications: Optional[Set[str]] = None,
        score_breakdown: Optional[Dict[str, float]] = None,
        explanation: Optional[str] = None,
    ):
        self.candidate_id = candidate_id
        self.masked_text = masked_text
        self.original_text = original_text
        self.skills = skills if skills is not None else set()
        self.experience_years = float(experience_years)
        self.education_level = education_level
        self.certifications = certifications if certifications is not None else set()
        self.score_breakdown = score_breakdown
        self.explanation = explanation

    @property
    def total_score(self) -> float:
        if self.score_breakdown and "total" in self.score_breakdown:
            return self.score_breakdown["total"]
        return 0.0

    def __repr__(self) -> str:
        return f"<Candidate id='{self.candidate_id}' skills={len(self.skills)} exp={self.experience_years}y score={self.total_score:.2f}>"

# --- src/fair_rank/anonymizer.py ---
import re

class ResumeAnonymizer:
    """
    Masks Personally Identifiable Information (PII) such as full names, email addresses,
    phone numbers, dates of birth, and URLs from resume text before scoring.
    """

    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'(\+?\d{1,4}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b')
    URL_PATTERN = re.compile(r'https?://\S+|www\.\S+')
    DOB_PATTERN = re.compile(r'\b(dob|date of birth|born)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', re.IGNORECASE)

    @classmethod
    def mask(cls, text: str, name: str = "") -> str:
        """
        Masks PII patterns in the provided text. If an explicit candidate name is passed,
        occurrences of that name are replaced with [NAME].
        """
        if not text:
            return ""

        masked = text
        masked = cls.EMAIL_PATTERN.sub("[EMAIL]", masked)
        masked = cls.PHONE_PATTERN.sub("[PHONE]", masked)
        masked = cls.URL_PATTERN.sub("[URL]", masked)
        masked = cls.DOB_PATTERN.sub("[DOB]", masked)

        if name and name.strip():
            # Escape regex special characters in name and match case-insensitively
            name_parts = [re.escape(part) for part in name.strip().split() if len(part) > 1]
            if name_parts:
                pattern = re.compile(r'\b(' + '|'.join(name_parts) + r')\b', re.IGNORECASE)
                masked = pattern.sub("[NAME]", masked)

        return masked

# --- src/fair_rank/normalizer.py ---
import re
from typing import List

class TextNormalizer:
    """
    Handles lowercasing, punctuation stripping, unicode cleaning, and tokenization.
    """

    PUNCTUATION_PATTERN = re.compile(r'[^\w\s\+\#\/\.\-]')

    @classmethod
    def normalize(cls, text: str) -> str:
        """
        Converts text to lowercase, removes sentence punctuation, and cleans whitespace.
        Preserves special tech terms like C++, C#, .NET, Node.js, CI/CD.
        """
        if not text:
            return ""

        lowercased = text.lower()
        # Remove dots that are at word boundaries / sentence ends (e.g. "science.")
        cleaned = re.sub(r'(?<=\w)\.(?=\s|$)', ' ', lowercased)
        cleaned = cls.PUNCTUATION_PATTERN.sub(' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """
        Splits normalized text into word tokens.
        """
        norm = cls.normalize(text)
        return norm.split() if norm else []

# --- src/fair_rank/skill_trie.py ---
from typing import Dict, Optional, Set, List
from .normalizer import TextNormalizer

class TrieNode:
    """
    Node structure for the token-level SkillTrie.
    Children dict maps word tokens to child TrieNodes.
    """
    def __init__(self):
        self.children: Dict[str, TrieNode] = {}
        self.is_end: bool = False
        self.skill_name: Optional[str] = None

class SkillTrie:
    """
    Token-level Prefix Trie data structure for fast dictionary-based skill extraction.
    Supports multiword skills (e.g. "data structures and algorithms") via word-by-word token insertion
    and greedy longest-match sliding window extraction over resume text.
    """

    def __init__(self):
        self.root = TrieNode()
        self.skill_count = 0

    def insert(self, skill: str) -> None:
        """
        Tokenizes the skill phrase into words and inserts word-by-word into the trie.
        Time Complexity: O(length of skill in words)
        """
        if not skill:
            return

        canonical_skill = skill.lower().strip()
        tokens = TextNormalizer.tokenize(canonical_skill)
        if not tokens:
            return

        curr = self.root
        for token in tokens:
            if token not in curr.children:
                curr.children[token] = TrieNode()
            curr = curr.children[token]
        
        if not curr.is_end:
            curr.is_end = True
            curr.skill_name = canonical_skill
            self.skill_count += 1

    def build(self, skills: List[str]) -> None:
        """
        Populates the trie with a list of canonical skills.
        """
        for skill in skills:
            self.insert(skill)

    def extract(self, text: str) -> Set[str]:
        """
        Extracts matched canonical skills from text using a greedy longest-match algorithm.
        Slides across tokenized resume text, matching as far into the trie as possible at each start position.
        Time Complexity: O(L * d) where L = tokens in text, d = maximum trie depth (words per skill).
        """
        matched_skills: Set[str] = set()
        tokens = TextNormalizer.tokenize(text)
        if not tokens:
            return matched_skills

        n = len(tokens)
        i = 0
        while i < n:
            curr = self.root
            longest_match: Optional[str] = None
            longest_match_len = 0

            j = i
            while j < n and tokens[j] in curr.children:
                curr = curr.children[tokens[j]]
                j += 1
                if curr.is_end and curr.skill_name:
                    longest_match = curr.skill_name
                    longest_match_len = j - i

            if longest_match:
                matched_skills.add(longest_match)
                # Advance pointer by the length of the matched phrase
                i += max(1, longest_match_len)
            else:
                i += 1

        return matched_skills

# --- src/fair_rank/skill_graph.py ---
import json
from typing import Dict, Set, List, Union

class SkillGraph:
    """
    Skill Synonym Graph implemented as an adjacency list dictionary (dict[str, set[str]]).
    Resolves skill variants and acronyms (e.g. "py" -> "python", "k8s" -> "kubernetes")
    to canonical terms using strict 1-hop direct mapping to preserve auditable transparency.
    """

    def __init__(self, synonym_dict_or_path: Union[Dict[str, List[str]], str]):
        self.adj_list: Dict[str, Set[str]] = {}
        if isinstance(synonym_dict_or_path, str):
            self.load_from_json(synonym_dict_or_path)
        else:
            self._build_from_dict(synonym_dict_or_path)

    def _build_from_dict(self, data: Dict[str, List[str]]) -> None:
        for term, canonical_terms in data.items():
            norm_term = term.lower().strip()
            norm_canonicals = {c.lower().strip() for c in canonical_terms}
            self.adj_list[norm_term] = norm_canonicals

    def load_from_json(self, path: str) -> None:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self._build_from_dict(data)

    def resolve_synonyms(self, skills: Set[str]) -> Set[str]:
        """
        Resolves a set of extracted skills to include direct 1-hop canonical equivalents.
        Does NOT perform multi-hop BFS/DFS traversal to prevent semantic drift.
        Time Complexity: O(1) average lookup per skill, O(s) for candidate skill set size s.
        """
        resolved: Set[str] = set()
        for skill in skills:
            norm_skill = skill.lower().strip()
            resolved.add(norm_skill)
            if norm_skill in self.adj_list:
                resolved.update(self.adj_list[norm_skill])
        return resolved

# --- src/fair_rank/feature_extractor.py ---
import re
from typing import Tuple, Set

class FeatureExtractor:
    """
    Extracts experience years, education level, and certifications from text using rule-based pattern matching.
    """

    EXP_PATTERNS = [
        re.compile(r'(\d+(?:\.\d+)?)\s*(?:\+\s*)?(?:years?|yrs?)(?:\s+of)?\s+experience', re.IGNORECASE),
        re.compile(r'experience[:\s]*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)', re.IGNORECASE),
    ]

    EDU_HIERARCHY = ["High School", "Associate", "Bachelor", "Master", "Doctorate"]

    CERT_KEYWORDS = [
        "aws certified developer",
        "aws certified solutions architect",
        "certified information systems security professional",
        "cissp",
        "pmp",
        "scrum master",
        "google cloud certified",
        "microsoft certified",
    ]

    @classmethod
    def extract_experience(cls, text: str) -> float:
        for pattern in cls.EXP_PATTERNS:
            match = pattern.search(text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
        return 0.0

    @classmethod
    def extract_education(cls, text: str) -> str:
        lowercased = text.lower()
        if any(term in lowercased for term in ["ph.d", "phd", "doctorate"]):
            return "Doctorate"
        if any(term in lowercased for term in ["master", "m.s", "ms", "m.sc"]):
            return "Master"
        if any(term in lowercased for term in ["bachelor", "b.s", "bs", "b.sc", "b.a"]):
            return "Bachelor"
        if any(term in lowercased for term in ["associate", "a.s", "a.a"]):
            return "Associate"
        return "High School"

    @classmethod
    def extract_certifications(cls, text: str) -> Set[str]:
        lowercased = text.lower()
        found_certs = set()
        for cert in cls.CERT_KEYWORDS:
            if cert in lowercased:
                found_certs.add(cert)
        return found_certs

    @classmethod
    def extract(cls, text: str) -> Tuple[float, str, Set[str]]:
        exp = cls.extract_experience(text)
        edu = cls.extract_education(text)
        certs = cls.extract_certifications(text)
        return exp, edu, certs

# --- src/fair_rank/inverted_index.py ---
from typing import Dict, Set, Iterable
from .candidate import Candidate

class InvertedIndex:
    """
    Inverted Index data structure mapping skill terms to candidate IDs (dict[str, set[str]]).
    Enables sub-linear candidate retrieval so only candidates possessing relevant required/preferred
    skills are evaluated during scoring.
    """

    def __init__(self):
        self.index: Dict[str, Set[str]] = {}
        self.total_candidates = 0

    def add(self, candidate: Candidate) -> None:
        """
        Indexes a candidate under each of their extracted skills.
        Time Complexity: O(s) per candidate where s is candidate skill count.
        """
        for skill in candidate.skills:
            norm_skill = skill.lower().strip()
            if norm_skill not in self.index:
                self.index[norm_skill] = set()
            self.index[norm_skill].add(candidate.candidate_id)
        self.total_candidates += 1

    def retrieve(self, required_skills: Iterable[str], preferred_skills: Iterable[str] = ()) -> Set[str]:
        """
        Retrieves candidate IDs possessing at least one required or preferred skill.
        If no skills are specified, returns empty set.
        Time Complexity: O(r * avg posting length) where r is total required + preferred skills.
        """
        relevant_candidates: Set[str] = set()
        all_query_skills = set(required_skills) | set(preferred_skills)

        for skill in all_query_skills:
            norm_skill = skill.lower().strip()
            if norm_skill in self.index:
                relevant_candidates.update(self.index[norm_skill])

        return relevant_candidates

# --- src/fair_rank/scorer.py ---
from typing import Dict
from .candidate import Candidate
from .job_description import JobDescription
from .feature_extractor import FeatureExtractor

class CandidateScorer:
    """
    Computes a candidate's fit score against a JobDescription using a 5-component weighted scoring function:
      1. Required Skills Match (Default Weight 0.50)
      2. Preferred Skills Match (Default Weight 0.20)
      3. Experience Match (Default Weight 0.15)
      4. Education Level Match (Default Weight 0.10)
      5. Certifications Match (Default Weight 0.05)
    
    Time Complexity: O(1) per candidate evaluation given pre-extracted sets.
    """

    EDU_RANKS = {
        "High School": 1,
        "Associate": 2,
        "Bachelor": 3,
        "Master": 4,
        "Doctorate": 5,
        "Unknown": 1,
    }

    @classmethod
    def score(cls, candidate: Candidate, job: JobDescription) -> Dict[str, float]:
        w = job.weights

        # 1. Required Skills Score
        if job.required_skills:
            req_matched = candidate.skills & job.required_skills
            req_score = len(req_matched) / len(job.required_skills)
        else:
            req_score = 1.0

        # 2. Preferred Skills Score
        if job.preferred_skills:
            pref_matched = candidate.skills & job.preferred_skills
            pref_score = len(pref_matched) / len(job.preferred_skills)
        else:
            pref_score = 1.0

        # 3. Experience Score (bounded ratio up to 1.0)
        if job.min_experience_years > 0:
            exp_score = min(1.0, candidate.experience_years / job.min_experience_years)
        else:
            exp_score = 1.0

        # 4. Education Score
        cand_edu_rank = cls.EDU_RANKS.get(candidate.education_level, 1)
        req_edu_rank = cls.EDU_RANKS.get(job.required_education, 3)
        if cand_edu_rank >= req_edu_rank:
            edu_score = 1.0
        else:
            edu_score = max(0.0, cand_edu_rank / req_edu_rank)

        # 5. Certifications Score
        if job.required_certifications:
            cert_matched = candidate.certifications & job.required_certifications
            cert_score = len(cert_matched) / len(job.required_certifications)
        else:
            cert_score = 1.0

        total_score = (
            w["required_skills"] * req_score +
            w["preferred_skills"] * pref_score +
            w["experience"] * exp_score +
            w["education"] * edu_score +
            w["certifications"] * cert_score
        )

        breakdown = {
            "required_skills": req_score,
            "preferred_skills": pref_score,
            "experience": exp_score,
            "education": edu_score,
            "certifications": cert_score,
            "total": total_score,
        }

        candidate.score_breakdown = breakdown
        return breakdown

# --- src/fair_rank/top_k_ranker.py ---
import heapq
from typing import List, Tuple, Dict
from .candidate import Candidate

class TopKRanker:
    """
    Bounded Min-Heap data structure for efficient Top-K candidate ranking.
    Maintains a heap of max size k containing tuples of (score, tie_breaker, candidate_object).
    
    Time Complexity: O(n log k) for n candidates, compared to O(n log n) for full sorting.
    Space Complexity: O(k).
    """

    def __init__(self, k: int):
        if k <= 0:
            raise ValueError("k must be greater than 0")
        self.k = k
        self.heap: List[Tuple[float, int, Candidate]] = []
        self._counter = 0  # Tie-breaker counter for stable heap ordering

    def push(self, candidate: Candidate, score: float) -> None:
        """
        Pushes a candidate into the min-heap. If heap exceeds size k, evicts the lowest scoring element.
        """
        self._counter += 1
        item = (score, self._counter, candidate)

        if len(self.heap) < self.k:
            heapq.heappush(self.heap, item)
        else:
            if score > self.heap[0][0]:
                heapq.heapreplace(self.heap, item)

    def get_ranked(self) -> List[Candidate]:
        """
        Returns top K candidates sorted in descending order of score.
        """
        sorted_items = sorted(self.heap, key=lambda x: (x[0], x[1]), reverse=True)
        return [item[2] for item in sorted_items]

    def clear(self) -> None:
        self.heap.clear()
        self._counter = 0

# --- src/fair_rank/fairness_auditor.py ---
from typing import List, Dict, Tuple, Any
from .candidate import Candidate
from .job_description import JobDescription
from .anonymizer import ResumeAnonymizer
from .normalizer import TextNormalizer
from .skill_trie import SkillTrie
from .skill_graph import SkillGraph
from .feature_extractor import FeatureExtractor
from .scorer import CandidateScorer

class FairnessAuditor:
    """
    Evaluates algorithmic bias by generating counterfactual resume pairs that differ ONLY by
    a single protected attribute or identity proxy (name, pronoun, email format, text padding),
    running both through the complete pipeline, and recording score and rank differentials.
    """

    DEFAULT_COUNTERFACTUAL_PAIRS = [
        {"test_type": "Name Bias (Male vs Female)", "field": "name", "val_a": "John Smith", "val_b": "Mary Smith"},
        {"test_type": "Name Bias (Western vs Non-Western)", "field": "name", "val_a": "David Miller", "val_b": "Tariq Al-Mansoor"},
        {"test_type": "Pronoun Bias", "field": "pronoun", "val_a": "He", "val_b": "She"},
        {"test_type": "Email Domain Proxy Bias", "field": "email", "val_a": "john.smith@gmail.com", "val_b": "john.smith@hbcu.edu"},
        {"test_type": "Formatting Whitespace Padding", "field": "text_padding", "val_a": "Software Engineer with Python experience", "val_b": "Software Engineer   with   Python   experience  "},
    ]

    def __init__(self, trie: SkillTrie, graph: SkillGraph):
        self.trie = trie
        self.graph = graph

    def process_raw_text(self, candidate_id: str, raw_text: str, candidate_name: str = "") -> Candidate:
        """
        Passes a single raw resume text through anonymization, normalization, skill extraction,
        synonym resolution, and feature extraction to return a Candidate object.
        """
        masked = ResumeAnonymizer.mask(raw_text, name=candidate_name)
        norm = TextNormalizer.normalize(masked)
        extracted_skills = self.trie.extract(norm)
        resolved_skills = self.graph.resolve_synonyms(extracted_skills)
        exp, edu, certs = FeatureExtractor.extract(norm)

        return Candidate(
            candidate_id=candidate_id,
            masked_text=masked,
            original_text=raw_text,
            skills=resolved_skills,
            experience_years=exp,
            education_level=edu,
            certifications=certs,
        )

    def audit_pair(
        self,
        job: JobDescription,
        test_type: str,
        cand_a: Candidate,
        cand_b: Candidate
    ) -> Dict[str, Any]:
        """
        Scores two candidates against a job description and computes absolute score differential.
        """
        breakdown_a = CandidateScorer.score(cand_a, job)
        breakdown_b = CandidateScorer.score(cand_b, job)

        score_a = breakdown_a["total"]
        score_b = breakdown_b["total"]
        score_diff = abs(score_a - score_b)

        return {
            "test_type": test_type,
            "candidate_a_id": cand_a.candidate_id,
            "candidate_b_id": cand_b.candidate_id,
            "score_a": score_a,
            "score_b": score_b,
            "score_difference": score_diff,
            "passed": score_diff < 1e-4,
        }

    def run_default_suite(self, job: JobDescription, base_resume_text: str) -> List[Dict[str, Any]]:
        """
        Runs the full default counterfactual audit suite on a given base resume.
        """
        audit_results = []
        for idx, test_case in enumerate(self.DEFAULT_COUNTERFACTUAL_PAIRS, start=1):
            test_type = test_case["test_type"]
            field = test_case["field"]
            val_a = test_case["val_a"]
            val_b = test_case["val_b"]

            if field == "name":
                text_a = f"{val_a}\n" + base_resume_text
                text_b = f"{val_b}\n" + base_resume_text
                c_a = self.process_raw_text(f"AUDIT_{idx}_A", text_a, candidate_name=val_a)
                c_b = self.process_raw_text(f"AUDIT_{idx}_B", text_b, candidate_name=val_b)
            elif field == "email":
                text_a = f"Email: {val_a}\n" + base_resume_text
                text_b = f"Email: {val_b}\n" + base_resume_text
                c_a = self.process_raw_text(f"AUDIT_{idx}_A", text_a)
                c_b = self.process_raw_text(f"AUDIT_{idx}_B", text_b)
            elif field == "pronoun":
                # Varies only the pronoun in an otherwise identical sentence,
                # so this genuinely isolates pronoun influence rather than
                # substituting a whole sentence for a keyword (the previous
                # implementation replaced the substring "managed" with a full
                # sentence, which tested text insertion, not pronoun choice).
                text_a = f"{val_a} led the engineering team and managed project delivery.\n" + base_resume_text
                text_b = f"{val_b} led the engineering team and managed project delivery.\n" + base_resume_text
                c_a = self.process_raw_text(f"AUDIT_{idx}_A", text_a)
                c_b = self.process_raw_text(f"AUDIT_{idx}_B", text_b)
            elif field == "text_padding":
                text_a = val_a + "\n" + base_resume_text
                text_b = val_b + "\n" + base_resume_text
                c_a = self.process_raw_text(f"AUDIT_{idx}_A", text_a)
                c_b = self.process_raw_text(f"AUDIT_{idx}_B", text_b)
            else:
                continue

            result = self.audit_pair(job, test_type, c_a, c_b)
            audit_results.append(result)

        return audit_results

# --- src/fair_rank/explanation_generator.py ---
from typing import Dict
from .candidate import Candidate
from .job_description import JobDescription

class ExplanationGenerator:
    """
    Generates deterministic, audit-friendly, human-readable explanations summarizing
    why a candidate received a given score breakdown for a job posting.
    """

    @classmethod
    def generate(cls, candidate: Candidate, job: JobDescription, breakdown: Dict[str, float]) -> str:
        total = breakdown.get("total", 0.0) * 100.0
        req_pct = breakdown.get("required_skills", 0.0) * 100.0
        pref_pct = breakdown.get("preferred_skills", 0.0) * 100.0

        matched_req = candidate.skills & job.required_skills
        missing_req = job.required_skills - candidate.skills
        
        matched_pref = candidate.skills & job.preferred_skills

        explanation_parts = [
            f"Overall Match Score: {total:.1f}%.",
            f"Required Skills ({req_pct:.0f}% match): Matched [{', '.join(sorted(matched_req)) or 'None'}]."
        ]

        if missing_req:
            explanation_parts.append(f"Missing required skills: [{', '.join(sorted(missing_req))}].")
        
        if matched_pref:
            explanation_parts.append(f"Preferred Skills ({pref_pct:.0f}% match): Matched [{', '.join(sorted(matched_pref))}].")

        explanation_parts.append(
            f"Experience: {candidate.experience_years} years (Required: {job.min_experience_years} yrs)."
        )
        explanation_parts.append(
            f"Education: {candidate.education_level} (Required: {job.required_education})."
        )

        full_exp = " ".join(explanation_parts)
        candidate.explanation = full_exp
        return full_exp

# --- src/fair_rank/screening_controller.py ---
import json
from typing import List, Dict, Tuple, Any, Optional
from .job_description import JobDescription
from .candidate import Candidate
from .anonymizer import ResumeAnonymizer
from .normalizer import TextNormalizer
from .skill_trie import SkillTrie
from .skill_graph import SkillGraph
from .feature_extractor import FeatureExtractor
from .inverted_index import InvertedIndex
from .scorer import CandidateScorer
from .top_k_ranker import TopKRanker
from .fairness_auditor import FairnessAuditor
from .explanation_generator import ExplanationGenerator

class ScreeningController:
    """
    Orchestrates the complete 10-stage FAIR-RANK recruitment pipeline:
      Stage 1: Build SkillTrie from controlled dictionary
      Stage 2: Load SkillGraph from synonym adjacency list
      Stage 3: Instantiate InvertedIndex
      Stage 4: Mask candidate PII (ResumeAnonymizer)
      Stage 5: Normalize resume text (TextNormalizer)
      Stage 6: Extract & resolve skills/features (SkillTrie, SkillGraph, FeatureExtractor)
      Stage 7: Populate InvertedIndex with processed candidates
      Stage 8: Sub-linear candidate retrieval via InvertedIndex
      Stage 9: Score candidates and push to TopKRanker min-heap with generated explanations
      Stage 10: Run FairnessAuditor suite and return ranked shortlist + audit report
    """

    def __init__(
        self,
        skills_dict_path: str = "data/skills_dictionary.json",
        synonyms_path: str = "data/skills_synonyms.json"
    ):
        # Stage 1: SkillTrie
        self.trie = SkillTrie()
        with open(skills_dict_path, 'r', encoding='utf-8') as f:
            skills_data = json.load(f)
            self.trie.build(skills_data.get("skills", []))

        # Stage 2: SkillGraph
        self.graph = SkillGraph(synonyms_path)

        # Stage 3: InvertedIndex
        self.index = InvertedIndex()
        
        self.candidates_dict: Dict[str, Candidate] = {}

    def process_and_index_resumes(self, raw_resumes: List[Dict[str, Any]]) -> List[Candidate]:
        """
        Executes Stages 4 through 7 over a batch of raw candidate resume dictionaries.
        """
        processed_candidates = []
        for raw in raw_resumes:
            cand_id = raw.get("candidate_id", f"C_{len(processed_candidates)+1:03d}")
            raw_text = raw.get("resume_text", "")
            name = raw.get("full_name", "")

            # Stage 4: Mask PII
            masked = ResumeAnonymizer.mask(raw_text, name=name)

            # Stage 5: Normalize text
            norm = TextNormalizer.normalize(masked)

            # Stage 6: Extract & resolve skills and features
            extracted_skills = self.trie.extract(norm)
            resolved_skills = self.graph.resolve_synonyms(extracted_skills)
            exp, edu, certs = FeatureExtractor.extract(norm)

            # Fallback to explicit CSV values if available and non-zero
            if raw.get("experience_years"):
                try:
                    exp = max(exp, float(raw["experience_years"]))
                except ValueError:
                    pass
            if raw.get("education_level") and raw["education_level"] != "Unknown":
                edu = raw["education_level"]

            cand = Candidate(
                candidate_id=cand_id,
                masked_text=masked,
                original_text=raw_text,
                skills=resolved_skills,
                experience_years=exp,
                education_level=edu,
                certifications=certs,
            )

            # Stage 7: Add to InvertedIndex
            self.index.add(cand)
            self.candidates_dict[cand_id] = cand
            processed_candidates.append(cand)

        return processed_candidates

    def run_screening(
        self,
        job: JobDescription,
        raw_resumes: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[List[Candidate], List[Dict[str, Any]]]:
        """
        Executes Stages 8 through 10 of the pipeline to produce a Top-K shortlist and fairness audit.
        """
        if raw_resumes:
            self.process_and_index_resumes(raw_resumes)

        # Stage 8: Sub-linear Candidate Retrieval
        relevant_ids = self.index.retrieve(job.required_skills, job.preferred_skills)
        pool = [self.candidates_dict[cid] for cid in relevant_ids if cid in self.candidates_dict]
        if not pool:
            pool = list(self.candidates_dict.values())

        # Stage 9: Candidate Scoring & Top-K Min-Heap Ranking
        ranker = TopKRanker(job.k)
        for cand in pool:
            breakdown = CandidateScorer.score(cand, job)
            cand.explanation = ExplanationGenerator.generate(cand, job, breakdown)
            ranker.push(cand, breakdown["total"])

        shortlist = ranker.get_ranked()

        # Stage 10: Fairness Audit
        auditor = FairnessAuditor(self.trie, self.graph)
        sample_resume_text = pool[0].original_text if pool else "Software Engineer with Python and SQL experience."
        audit_report = auditor.run_default_suite(job, sample_resume_text)

        return shortlist, audit_report

# --- src/fair_rank/utils.py ---
import time
import tracemalloc
from typing import Callable, Any, Tuple

class Timer:
    """High-precision execution wall-clock timer using time.perf_counter()."""

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end = time.perf_counter()
        self.interval = self.end - self.start

def measure_execution(func: Callable, *args, **kwargs) -> Tuple[Any, float, float]:
    """
    Executes func(*args, **kwargs) and measures wall-clock time (seconds)
    and peak memory allocation (MB).
    """
    tracemalloc.start()
    start_time = time.perf_counter()
    
    result = func(*args, **kwargs)
    
    elapsed_time = time.perf_counter() - start_time
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    peak_mb = peak_bytes / (1024 * 1024)
    return result, elapsed_time, peak_mb
