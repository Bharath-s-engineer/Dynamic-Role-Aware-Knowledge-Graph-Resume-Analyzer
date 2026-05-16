# Build & Run Guide
## Dynamic Role-Aware Knowledge Graph — Resume Analyzer

---

## Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Anthropic API Key | — | From console.anthropic.com |

---

## Step-by-Step Setup

### 1. Create project folder

```bash
mkdir knowledge-graph-resume
cd knowledge-graph-resume
```

### 2. Copy all files into this structure

```
knowledge-graph-resume/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_all.py
│   └── app/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── json_parser.py
│       │   └── llm_client.py
│       ├── extraction/
│       │   ├── __init__.py
│       │   ├── pdf_extractor.py
│       │   └── text_cleaner.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── jd_models.py
│       │   ├── resume_models.py
│       │   ├── graph_models.py
│       │   └── response_models.py
│       ├── parsing/
│       │   ├── __init__.py
│       │   ├── jd_parser.py
│       │   └── resume_parser.py
│       ├── graph/
│       │   ├── __init__.py
│       │   ├── skill_expander.py
│       │   ├── graph_builder.py
│       │   ├── propagation.py
│       │   └── visualization.py
│       ├── scoring/
│       │   ├── __init__.py
│       │   └── readiness.py
│       └── recommendations/
│           ├── __init__.py
│           └── engine.py
│
└── frontend/
    ├── package.json
    ├── public/
    │   └── index.html
    └── src/
        ├── index.js
        ├── index.css
        ├── App.jsx
        ├── components/
        │   ├── UploadPanel.jsx
        │   ├── ScoreCard.jsx
        │   ├── SkillLists.jsx
        │   ├── GraphCanvas.jsx
        │   └── Legend.jsx
        ├── hooks/
        │   └── useAnalysis.js
        └── utils/
            └── graphTransform.js
```

---

### 3. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
# macOS / Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
```

Open `.env` and replace the placeholder:
```
ANTHROPIC_API_KEY=sk-ant-YOUR_REAL_KEY_HERE
```

Get your key at: https://console.anthropic.com/settings/api-keys

---

### 4. Run backend tests (no API key needed)

```bash
cd backend
pytest tests/test_all.py -v
```

Expected: **19 tests pass** in ~2 seconds.

---

### 5. Start the backend server

```bash
cd backend
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

Verify it works:
```bash
curl http://127.0.0.1:8000/
# → {"status":"ok","service":"knowledge-graph-resume v2"}
```

Or open http://127.0.0.1:8000/docs in your browser for the interactive Swagger UI.

---

### 6. Frontend setup (new terminal)

```bash
cd frontend
npm install
npm start
```

The browser opens at http://localhost:3000 automatically.

---

## Using the App

1. **Upload Resume** — drag a PDF or click to browse
2. **Upload Job Description** — drag a PDF or click to browse
3. Click **Analyze Match**
4. Wait ~10–20 seconds (3 AI calls: parse JD, parse resume, expand graph)
5. View results across 3 tabs:
   - **Skills** — Matched / Inferred / Missing columns
   - **Graph** — Interactive dependency knowledge graph
   - **Recommendations** — Prioritised action items

---

## API Reference

### POST /analyze

```
curl -X POST http://127.0.0.1:8000/analyze \
  -F "resume=@/path/to/resume.pdf" \
  -F "jd=@/path/to/jd.pdf"
```

Response shape:
```json
{
  "job_title": "Senior Backend Engineer",
  "job_role": "Backend Engineer",
  "experience_level": "senior",
  "resume_skills": ["Python", "FastAPI", ...],
  "jd_required_skills": ["FastAPI", "PostgreSQL", ...],
  "jd_preferred_skills": ["Kubernetes", ...],
  "readiness": {
    "readiness_score": 74.5,
    "matched_skills": ["Python", "FastAPI"],
    "inferred_skills": [{"skill": "REST API", "coverage": 0.6}],
    "missing_skills": ["Kubernetes"]
  },
  "recommendations": ["Learn Kubernetes — required by this role..."],
  "graph_data": {
    "nodes": [...],
    "edges": [...]
  }
}
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ANTHROPIC_API_KEY not set` | Add key to `backend/.env` |
| `PDFExtractionError: No extractable text` | PDF may be scanned; use a text-based PDF |
| `npm install` fails | Run `node --version`; need Node 18+ |
| `CORS error` in browser | Make sure backend runs on port 8000 |
| `Module not found` on backend | Activate venv: `source venv/bin/activate` |
| Graph is empty | Check browser console; may be a React Flow version mismatch — ensure `reactflow@11.x` |

---

## How the Pipeline Works

```
Resume PDF + JD PDF
       ↓
  [PDF Extractor]  fitz → raw text → text_cleaner
       ↓
  [JD Parser]      LLM call 1 → JDProfile (role, level, skills)
  [Resume Parser]  LLM call 2 → ResumeProfile (skills, experience)
       ↓
  [Skill Expander] LLM call 3 → additional nodes + dependency edges
       ↓
  [Graph Builder]  NetworkX DiGraph (JD-specific, not static)
       ↓
  [Propagation]    BFS with decay=0.6, depth=3 → coverage scores
       ↓
  [Readiness]      Weighted score (required=2x, preferred=1x)
       ↓
  [Visualization]  nx.DiGraph → React Flow JSON
       ↓
  JSON response → Frontend → Interactive UI
```

---

## Customisation

**Change decay factor** (how far inferred skills propagate):
```
# .env
PROPAGATION_DECAY=0.5        # more aggressive cutoff
PROPAGATION_MAX_DEPTH=4      # allow 4 hops
```

**Change score thresholds**:
```
# .env
MATCH_THRESHOLD=0.9          # require 90%+ to count as "matched"
INFER_THRESHOLD=0.2          # require 20%+ to count as "inferred"
```

**Point to different backend URL** (production deploy):
```
# frontend/.env
REACT_APP_API_URL=https://your-api.example.com
```
