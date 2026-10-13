# 🤖 AI Resume Screening System

An end-to-end **AI-powered Resume Screening System** that automatically analyzes and ranks resumes against a job description using **NLP** and **Machine Learning** techniques.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 Multi-format Support | Accepts **PDF**, **DOCX**, and **TXT** resumes |
| 🔍 Skill Extraction | Identifies 70+ technical skills, soft skills, and education keywords |
| 📊 TF-IDF Similarity | Measures content relevance between JD and resumes |
| 🎯 Composite Scoring | Weighted scoring across 4 dimensions |
| 🏅 Auto Ranking | Ranks candidates from best to least relevant |
| 🏷️ Recommendations | Classifies candidates (Highly Recommended / Recommended / Consider / Not Recommended) |
| 📥 JSON Export | Download full screening report |
| 🌙 Dark UI | Modern, responsive dark-themed web interface |

---

## 🏗️ Project Structure

```
Ai resume system/
│
├── app.py                  ← Flask backend (NLP + ML engine)
├── requirements.txt        ← Python dependencies
├── setup.bat               ← One-click setup script
├── start.bat               ← One-click launch script
│
└── frontend/
    ├── index.html          ← Main web interface
    ├── style.css           ← Dark theme stylesheet
    └── app.js              ← Interactive UI logic
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.9+** — Download from [python.org](https://www.python.org/downloads/)
  - ✅ Check **"Add Python to PATH"** during installation

### Step 1 — Setup (first time only)
Double-click **`setup.bat`**

This will:
- Create a Python virtual environment
- Install all required packages
- Download NLTK language data

### Step 2 — Run the Application
Double-click **`start.bat`**

The browser will open automatically at `http://localhost:5000`

---

## ☁️ Deploy to Render

The project includes a Render Blueprint in `render.yaml`.

1. Create a **private GitHub repository** and push this project to it. Do not include `venv/`, uploaded resumes, or secrets; `.gitignore` excludes these.
2. In the [Render Dashboard](https://dashboard.render.com), choose **New → Blueprint**, connect the repository, and apply the `render.yaml` configuration. The build installs the dependencies and required NLTK data.
3. Wait for the deploy to finish. Render provides a public `onrender.com` URL; `/api/health` is configured as the health check.

The free service may sleep when idle and take a short time to wake on the next request. This app has no login or access control, so anyone who has the public URL can submit job descriptions and resumes. Use test or appropriately authorized data unless access control is added.

---

## 🔬 How It Works

### Scoring Engine (4 Dimensions)

```
Final Score = 40% × TF-IDF Similarity
            + 35% × Skill Overlap
            + 15% × Experience Match
            + 10% × Education Match
```

| Dimension | Method | Weight |
|---|---|---|
| **Content Similarity** | TF-IDF + Cosine Similarity (bigrams) | 40% |
| **Skill Overlap** | Keyword matching against 70+ skill taxonomy | 35% |
| **Experience Match** | Regex extraction of years from text | 15% |
| **Education Match** | Degree-level hierarchy matching | 10% |

### Recommendation Bands

| Score | Recommendation |
|---|---|
| ≥ 80% | 🏆 Highly Recommended |
| 65–79% | ✅ Recommended |
| 50–64% | 🔶 Consider |
| < 50% | ❌ Not Recommended |

---

## 🛠️ Tech Stack

**Backend**
- Python 3.9+
- Flask (REST API)
- NLTK (tokenization, lemmatization, stopwords)
- scikit-learn (TF-IDF vectorizer, cosine similarity)
- PyPDF2 (PDF parsing)
- python-docx (DOCX parsing)

**Frontend**
- Vanilla JavaScript (ES6+)
- CSS3 with CSS Variables (dark theme)
- Google Fonts (Inter)
- No frameworks — zero dependencies

---

## 📡 API Reference

### `POST /api/screen`

**Form fields:**

| Field | Type | Description |
|---|---|---|
| `job_description` | `string` | Full text of the job description |
| `resumes` | `file[]` | One or more resume files (PDF/DOCX/TXT) |

**Response:**
```json
{
  "job_description_summary": {
    "required_skills": ["python", "flask", "docker"],
    "soft_skills": ["teamwork"],
    "required_experience_years": 3
  },
  "candidates": [
    {
      "rank": 1,
      "filename": "john_doe.pdf",
      "candidate_name": "John Doe",
      "email": "john@email.com",
      "scores": {
        "final": 84.5,
        "tfidf_similarity": 78.2,
        "skill_overlap": 90.0,
        "education": 100.0,
        "experience": 80.0
      },
      "skills": {
        "matched": ["python", "flask"],
        "missing": ["docker"],
        "candidate_technical": ["python", "flask", "sql"],
        "candidate_soft": ["communication"]
      },
      "experience_years": 4,
      "recommendation": {
        "label": "Highly Recommended",
        "color": "green",
        "icon": "🏆"
      }
    }
  ],
  "total_processed": 5,
  "total_errors": 0
}
```

### `GET /api/health`
Returns server status and feature availability.

---

## 📸 Workflow

1. **Recruiter** pastes the job description
2. **Recruiter** uploads multiple resumes (drag & drop supported)
3. **AI Engine** extracts skills, education, experience from each resume
4. **Scoring Engine** computes weighted match scores
5. **Results** show ranked candidates with detailed breakdown
6. **Recruiter** filters by recommendation band and downloads the report
