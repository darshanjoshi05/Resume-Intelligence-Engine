# Resume Intelligence Engine 🚀

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115-blue?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square" alt="Status">
</p>

> An intelligent job application management system that helps you land your dream tech role. Track applications, generate tailored resumes, score JD compatibility, and continuously improve your job search strategy.

---

## ✨ Key Features

### 📊 Application Tracking
- **Centralized Dashboard** - Track all your job applications in one place
- **Match Scoring** - AI-powered resume-to-JD compatibility scoring (0-100%)
- **Application Analytics** - View daily/weekly progress and average match scores
- **Follow-up Reminders** - Never miss a follow-up opportunity

### 📄 Resume Generation
- **Smart Tailoring** - Automatically adjust your resume for each job description
- **Multi-Format Output** - Generate professional resumes in DOCX and PDF formats
- **ATS Optimization** - ATS-safe formatting with proper keyword optimization
- **Cover Letters** - Auto-generate tailored cover letters

### 🎯 JD Intelligence
- **Skill Extraction** - Automatically extract required skills from job descriptions
- **Role Detection** - Identify role families (Frontend, Backend, Fullstack, Data)
- **Work Mode Detection** - Detect Remote/Hybrid/Onsite requirements
- **Role Level Analysis** - Determine if position is Intern, Entry, Mid, or Senior

### 🧠 Smart Matching
- **Skill Bridging** - Connect related skills (e.g., "state management" → Redux/Zustand)
- **Concept Matching** - Understand conceptual relationships between technologies
- **Partial Matching** - Fuzzy matching for similar but not exact skills
- **Missing Skills** - Identify gaps and get learning recommendations

### 📈 Learning System
- **JD Learning** - System learns from job descriptions you process
- **Term Weighting** - Prioritize skills based on market demand
- **Concept Expansion** - Expand abstract concepts to concrete technologies
- **Continuous Improvement** - Gets smarter with every application

---

## 🏗️ Architecture

```
Resume Intelligence Engine
├── app.py                    # FastAPI main application
├── db.py                     # SQLite database management
├── profile_store.py          # Profile persistence & parsing
├── generator.py              # Resume/DOCX/PDF generation
├── jd_extract.py             # Job description parsing
├── skill_bridge.py           # Skill matching & bridging
├── matcher.py                # Term matching engine
├── suitability.py            # Candidate lane inference
├── role_detect.py            # Role family detection
├── resume_intel.py           # AI resume tailoring
├── learn_jd.py              # JD learning module
├── learning_store.py        # Learning data persistence
├── ats_sanitize.py          # ATS text sanitization
├── templates/               # Jinja2 HTML templates
├── static/                  # CSS, JS, images
├── data/                    # Data storage (SQLite, JSON)
├── outputs/                 # Generated resumes/PDFs
└── tests/                   # Test suite
```

---

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| **Web Framework** | FastAPI 0.115 |
| **Server** | Uvicorn 0.30 |
| **Templating** | Jinja2 3.1 |
| **Validation** | Pydantic 2.8 |
| **DOCX Generation** | python-docx 1.1 |
| **PDF Generation** | ReportLab 4.2 |
| **Database** | SQLite (built-in) |
| **Python** | 3.11+ |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
   
```
bash
   git clone https://github.com/darshanjoshi05/Resume-Intelligence-Engine.git
   cd Resume-Intelligence-Engine
   
```

2. **Create a virtual environment** (recommended)
   
```
bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
```

3. **Install dependencies**
   
```
bash
   pip install -r requirements.txt
   
```

4. **Run the application**
   
```
bash
   uvicorn app:app --reload
   
```

5. **Open your browser**
   
```
   http://localhost:8000
   
```

---

## 📖 User Guide

### 1. Setting Up Your Profile

Navigate to **Settings → Profile** and enter:
- Personal information (name, email, phone, LinkedIn)
- Professional summary
- Skills organized by category
- Work experience
- Projects
- Education
- Publications

### 2. Creating an Application

1. Click **+ Create Application** on the dashboard
2. Enter the company name and role title
3. Paste the full job description (include responsibilities + requirements)
4. Click **Generate**

The system will:
- Extract structured JD data
- Score your resume-JD compatibility
- Generate a tailored resume
- Create recruiter message variants
- Suggest learning paths for missing skills

### 3. Viewing Application Details

Each application shows:
- **Match Score** - Overall compatibility percentage
- **Matched Skills** - Skills from JD that appear in your profile
- **Bridged Skills** - Related skills the system identified
- **Missing Skills** - Skills you might want to learn
- **Learning Plan** - Suggested skills to acquire
- **Generated Resume** - Downloadable DOCX/PDF
- **Recruiter Messages** - Pre-written outreach templates

### 4. Configuring Settings

Access **Settings** to configure:
- **Output** - Default role, resume length, keyword mode
- **Learning** - Enable/disable learning, confidence threshold
- **Workflow** - Daily and weekly application targets

---

## 🔧 Configuration

### Settings File (`data/settings.json`)

```
json
{
  "targets": {
    "daily": 3,
    "weekly": 15
  },
  "output": {
    "default_role": "frontend",
    "resume_length": "1_page",
    "keyword_mode": "balanced",
    "summary_mode": "dynamic_with_override"
  },
  "learning": {
    "enabled": true,
    "confidence_threshold": 0.62,
    "learn_from_jds": true
  },
  "ui": {
    "accent": "light_orange"
  }
}
```

---

## 🎯 Match Scoring Algorithm

The scoring system evaluates resume-JD compatibility through multiple layers:

1. **Exact Matches** - Direct skill matches (full weight)
2. **Concept Matches** - Related skills via concept mapping (0.5x weight)
3. **Partial Matches** - Fuzzy matches for similar terms (0.5x weight)

**Score Formula:**
```
Score = (matched_count + 0.5 * bridged_count) / max(8, jd_term_count) * 100
```

---

## 🧠 AI Intelligence Features

### Resume Tailoring (`resume_intel.py`)

The AI engine automatically:
- Rewrites summaries based on job description keywords
- Reorders skills by relevance
- Selects most relevant projects
- Tailors project bullets with JD terminology
- Strengthens action verbs

### Concept Expansion

| Concept | Expanded To |
|---------|-------------|
| State Management | Redux, Redux Toolkit, Zustand, MobX |
| Data Fetching | React Query, Apollo Client, GraphQL, SWR |
| UI Testing | Jest, Cypress, Playwright, Testing Library |
| Performance | Code Splitting, Lazy Loading, Lighthouse |

---

## 📁 Data Storage

### SQLite Database (`data/jobs.db`)

**applications table:**
- id, company, role_title, role_family
- jd_text, match_score, created_at
- job_location, work_mode, relocation_required
- status, followup_date
- resume_docx_path, resume_pdf_path, cover_letter_path
- recruiter_msg, report_json

**notifications table:**
- id, app_id, title, body, due_at, is_read, created_at

### JSON Profiles (`data/`)

- `master_profile.json` - Your main profile
- `settings.json` - Application settings
- `learned_store.json` - Learned JD terms
- `learning_store.json` - Concept learning data

---

## 🧪 Running Tests

```
bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_scorecard_and_clean_output.py

# Run with verbose output
pytest -v
```

---

## 🔐 Security Features

- **Path Traversal Protection** - Safe file serving for outputs
- **Input Sanitization** - Text cleaning for generated documents
- **SQL Injection Prevention** - Parameterized queries
- **Control Character Removal** - Clean JD processing

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 👤 Author

**Darshan Joshi**
- GitHub: [@darshanjoshi05](https://github.com/darshanjoshi05)

---

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- ReportLab for PDF generation
- python-docx for Word document creation
- The open-source community for inspiration

---

<div align="center">
  <p>Made with ❤️ for job seekers everywhere</p>
  <p>⭐ Star this repo if it helped you!</p>
</div>

Developed by Darshan Joshi.
