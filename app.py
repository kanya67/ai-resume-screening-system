"""
AI Resume Screening System - Backend API
Uses NLP/ML techniques to score and rank resumes against job descriptions
"""

import os
import re
import json
import math
import string
import zipfile
import io
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# PDF / DOCX parsing
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from docx import Document
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False

# ─────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=str(BASE_DIR / "frontend"), static_url_path="")
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt"}

# ─────────────────────────────────────────────────────────────
# NLTK bootstrap (download only once)
# ─────────────────────────────────────────────────────────────
def bootstrap_nltk():
    resources = {
        "punkt": "tokenizers/punkt",
        "punkt_tab": "tokenizers/punkt_tab/english",
        "stopwords": "corpora/stopwords",
        "wordnet": "corpora/wordnet",
    }
    download_dir = os.environ.get("NLTK_DATA")
    for package, resource_path in resources.items():
        try:
            nltk.data.find(resource_path)
        except LookupError:
            if not nltk.download(package, download_dir=download_dir, quiet=True):
                raise RuntimeError(
                    f"Required NLTK resource '{package}' is missing and could not be downloaded."
                )

bootstrap_nltk()

# ─────────────────────────────────────────────────────────────
# Skill taxonomy – used for keyword extraction
# ─────────────────────────────────────────────────────────────
TECH_SKILLS = {
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go", "rust",
    "kotlin", "swift", "r", "matlab", "scala", "php", "perl", "bash", "shell",
    # Web
    "html", "css", "react", "angular", "vue", "node.js", "nodejs", "django", "flask",
    "fastapi", "spring", "express", "next.js", "nextjs", "tailwind", "bootstrap",
    # Data / ML
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn",
    "pandas", "numpy", "matplotlib", "seaborn", "opencv", "huggingface", "transformers",
    "bert", "gpt", "llm", "rag", "langchain",
    # Data Engineering
    "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "cassandra",
    "spark", "hadoop", "kafka", "airflow", "dbt", "etl", "data warehouse",
    # Cloud / DevOps
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "terraform",
    "ansible", "jenkins", "github actions", "ci/cd", "devops", "linux",
    # Other
    "git", "agile", "scrum", "rest", "graphql", "microservices", "api",
    "excel", "power bi", "tableau", "jira", "confluence",
}

SOFT_SKILLS = {
    "communication", "leadership", "teamwork", "problem solving", "analytical",
    "critical thinking", "creativity", "adaptability", "time management",
    "project management", "collaboration", "presentation", "negotiation",
}

EDUCATION_KEYWORDS = {
    "bachelor", "master", "phd", "doctorate", "b.e", "b.tech", "m.tech", "m.e",
    "mba", "bsc", "msc", "b.s", "m.s", "undergraduate", "graduate", "degree",
    "diploma", "certification", "certified",
}

EXPERIENCE_PATTERNS = [
    r"(\d+)\+?\s*years?\s*(?:of\s+)?experience",
    r"experience\s*(?:of\s+)?(\d+)\+?\s*years?",
    r"(\d+)\+?\s*yrs?\s*(?:of\s+)?exp",
]

# ─────────────────────────────────────────────────────────────
# Text extraction helpers
# ─────────────────────────────────────────────────────────────
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(file_bytes: bytes) -> str:
    if not PDF_SUPPORT:
        return ""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        return f"[PDF parse error: {e}]"


def extract_text_from_docx(file_bytes: bytes) -> str:
    if not DOCX_SUPPORT:
        return ""
    try:
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(para.text for para in doc.paragraphs)
    except Exception as e:
        return f"[DOCX parse error: {e}]"


def extract_text(file_bytes: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext in ("docx", "doc"):
        return extract_text_from_docx(file_bytes)
    else:  # txt
        return file_bytes.decode("utf-8-sig", errors="ignore")


# ─────────────────────────────────────────────────────────────
# NLP preprocessing
# ─────────────────────────────────────────────────────────────
_lemmatizer = WordNetLemmatizer()
_stop_words: set = set()

def _get_stop_words() -> set:
    global _stop_words
    if not _stop_words:
        try:
            _stop_words = set(stopwords.words("english"))
        except Exception:
            _stop_words = set()
    return _stop_words


def preprocess(text: str) -> str:
    """Lowercase, remove punctuation, remove stopwords, lemmatize."""
    text = text.lower()
    text = re.sub(r"[^\w\s\+\#]", " ", text)  # keep + and # for c++, c#
    tokens = word_tokenize(text)
    stop = _get_stop_words()
    tokens = [_lemmatizer.lemmatize(t) for t in tokens if t not in stop and len(t) > 1]
    return " ".join(tokens)


def extract_skills(text: str) -> Dict[str, List[str]]:
    """Extract technical and soft skills found in text."""
    text_lower = text.lower()

    def contains_term(term: str) -> bool:
        pattern = rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])"
        return re.search(pattern, text_lower) is not None

    found_tech = [s for s in TECH_SKILLS if contains_term(s)]
    found_soft = [s for s in SOFT_SKILLS if contains_term(s)]
    found_edu = [s for s in EDUCATION_KEYWORDS if contains_term(s)]
    return {
        "technical": sorted(found_tech),
        "soft": sorted(found_soft),
        "education": sorted(found_edu),
    }


def extract_years_experience(text: str) -> Optional[int]:
    """Return the maximum years of experience found in text."""
    years = []
    for pattern in EXPERIENCE_PATTERNS:
        for match in re.finditer(pattern, text.lower()):
            try:
                years.append(int(match.group(1)))
            except (IndexError, ValueError):
                pass
    return max(years) if years else None


def extract_email(text: str) -> Optional[str]:
    match = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", text)
    return match.group(0) if match else None


def extract_phone(text: str) -> Optional[str]:
    match = re.search(
        r"(?:\+91[-.\s]?)?(?:\(?\d{3,5}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4}", text
    )
    return match.group(0).strip() if match else None


def extract_name_heuristic(text: str) -> str:
    """Best-effort: first non-empty line that looks like a name."""
    for line in text.strip().split("\n")[:8]:
        line = line.strip()
        if 2 <= len(line.split()) <= 5 and line.replace(" ", "").replace(".", "").isalpha():
            return line
    return "Unknown Candidate"

# ─────────────────────────────────────────────────────────────
# Scoring Engine
# ─────────────────────────────────────────────────────────────
def compute_tfidf_similarity(jd_text: str, resume_text: str) -> float:
    """Cosine similarity between JD and resume using TF-IDF."""
    processed = [preprocess(jd_text), preprocess(resume_text)]
    try:
        vec = TfidfVectorizer(ngram_range=(1, 2), max_features=5000)
        tfidf = vec.fit_transform(processed)
        sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return round(float(sim) * 100, 2)
    except Exception:
        return 0.0


def compute_skill_overlap(jd_skills: Dict, resume_skills: Dict) -> float:
    """Percentage of JD technical skills covered by the resume."""
    jd_tech = set(jd_skills.get("technical", []))
    res_tech = set(resume_skills.get("technical", []))
    if not jd_tech:
        return 50.0  # neutral if JD has no detectable skills
    overlap = jd_tech & res_tech
    return round(len(overlap) / len(jd_tech) * 100, 2)


def compute_education_score(jd_text: str, resume_edu: List[str]) -> float:
    """Simple score based on education keywords present in resume vs JD."""
    jd_lower = jd_text.lower()
    score = 50.0  # base
    degree_levels = {
        "phd": 100, "doctorate": 100,
        "master": 90, "m.tech": 90, "m.e": 90, "m.s": 90, "msc": 90, "mba": 85,
        "bachelor": 70, "b.tech": 70, "b.e": 70, "b.s": 70, "bsc": 70,
        "diploma": 55, "certification": 55, "certified": 55,
    }
    if "phd" in jd_lower or "doctorate" in jd_lower:
        required_level = 100
    elif "master" in jd_lower or "m.tech" in jd_lower or "m.s" in jd_lower:
        required_level = 90
    elif "bachelor" in jd_lower or "b.tech" in jd_lower or "degree" in jd_lower:
        required_level = 70
    else:
        required_level = 55

    candidate_level = max((degree_levels.get(e, 0) for e in resume_edu), default=0)

    if candidate_level >= required_level:
        score = 100.0
    elif candidate_level > 0:
        score = round(candidate_level / required_level * 100, 2)
    return score


def compute_experience_score(jd_text: str, resume_exp_years: Optional[int]) -> float:
    """Score experience match."""
    jd_exp = extract_years_experience(jd_text)
    if resume_exp_years is None:
        return 50.0  # no info
    if jd_exp is None:
        return 70.0  # JD doesn't specify – give reasonable score
    if resume_exp_years >= jd_exp:
        bonus = min((resume_exp_years - jd_exp) * 5, 20)
        return min(100.0, 80.0 + bonus)
    else:
        ratio = resume_exp_years / jd_exp
        return round(ratio * 80, 2)


def compute_final_score(
    tfidf_sim: float,
    skill_overlap: float,
    edu_score: float,
    exp_score: float,
) -> float:
    """Weighted composite score."""
    weights = {
        "tfidf": 0.40,
        "skills": 0.35,
        "education": 0.10,
        "experience": 0.15,
    }
    score = (
        tfidf_sim * weights["tfidf"]
        + skill_overlap * weights["skills"]
        + edu_score * weights["education"]
        + exp_score * weights["experience"]
    )
    return round(min(score, 100.0), 2)


def get_matched_missing_skills(
    jd_skills: Dict, resume_skills: Dict
) -> Tuple[List[str], List[str]]:
    jd_tech = set(jd_skills.get("technical", []))
    res_tech = set(resume_skills.get("technical", []))
    matched = sorted(jd_tech & res_tech)
    missing = sorted(jd_tech - res_tech)
    return matched, missing


def assign_recommendation(score: float) -> Dict:
    if score >= 80:
        return {"label": "Highly Recommended", "color": "green", "icon": "🏆"}
    elif score >= 65:
        return {"label": "Recommended", "color": "blue", "icon": "✅"}
    elif score >= 50:
        return {"label": "Consider", "color": "yellow", "icon": "🔶"}
    else:
        return {"label": "Not Recommended", "color": "red", "icon": "❌"}


# ─────────────────────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "pdf_support": PDF_SUPPORT, "docx_support": DOCX_SUPPORT})


@app.route("/api/screen", methods=["POST"])
def screen_resumes():
    """
    POST /api/screen
    Form fields:
      - job_description: str
      - resumes: one or more files (pdf, docx, txt)
    """
    # ── Validate inputs ──────────────────────────────────────
    job_description = request.form.get("job_description", "").strip()
    if not job_description:
        return jsonify({"error": "job_description is required"}), 400

    files = request.files.getlist("resumes")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "At least one resume file is required"}), 400

    # ── Analyse JD ───────────────────────────────────────────
    jd_skills = extract_skills(job_description)
    jd_exp_req = extract_years_experience(job_description)

    results = []

    for f in files:
        if not f or f.filename == "":
            continue
        if not allowed_file(f.filename):
            results.append({
                "filename": f.filename,
                "error": "Unsupported file type. Use PDF, DOCX, or TXT.",
            })
            continue

        file_bytes = f.read()
        raw_text = extract_text(file_bytes, f.filename)

        if not raw_text.strip():
            results.append({"filename": f.filename, "error": "Could not extract text."})
            continue

        # Extract candidate info
        candidate_name = extract_name_heuristic(raw_text)
        email = extract_email(raw_text)
        phone = extract_phone(raw_text)
        resume_skills = extract_skills(raw_text)
        exp_years = extract_years_experience(raw_text)

        # Compute sub-scores
        tfidf_sim = compute_tfidf_similarity(job_description, raw_text)
        skill_overlap = compute_skill_overlap(jd_skills, resume_skills)
        edu_score = compute_education_score(job_description, resume_skills["education"])
        exp_score = compute_experience_score(job_description, exp_years)
        final_score = compute_final_score(tfidf_sim, skill_overlap, edu_score, exp_score)

        matched_skills, missing_skills = get_matched_missing_skills(jd_skills, resume_skills)
        recommendation = assign_recommendation(final_score)

        results.append({
            "filename": secure_filename(f.filename),
            "candidate_name": candidate_name,
            "email": email,
            "phone": phone,
            "scores": {
                "final": final_score,
                "tfidf_similarity": tfidf_sim,
                "skill_overlap": skill_overlap,
                "education": edu_score,
                "experience": exp_score,
            },
            "skills": {
                "matched": matched_skills,
                "missing": missing_skills,
                "candidate_technical": resume_skills["technical"],
                "candidate_soft": resume_skills["soft"],
            },
            "experience_years": exp_years,
            "recommendation": recommendation,
        })

    if not results:
        return jsonify({"error": "No valid resumes processed"}), 400

    # Rank by final score (descending)
    valid = [r for r in results if "error" not in r]
    errors = [r for r in results if "error" in r]
    valid.sort(key=lambda x: x["scores"]["final"], reverse=True)
    for i, r in enumerate(valid):
        r["rank"] = i + 1

    return jsonify({
        "job_description_summary": {
            "required_skills": jd_skills["technical"],
            "soft_skills": jd_skills["soft"],
            "required_experience_years": jd_exp_req,
        },
        "candidates": valid + errors,
        "total_processed": len(valid),
        "total_errors": len(errors),
    })


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  AI Resume Screening System")
    print("  Backend running at http://localhost:5000")
    print("=" * 60)
    app.run(debug=False, host="0.0.0.0", port=5000)
