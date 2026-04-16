# CitationTrace

**A SaaS Platform for Verified Scholarly Citations and Provenance Preservation**

> Solving the Provenance Problem in AI-assisted research.  
> Queries OpenAlex (250M+ works), CrossRef (140M+ records), and PubMed (37M+ articles) in parallel — ranked by BM25 relevance × citation count, verified with NLI scoring.

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/ishwaryaa05-del/citationtrace.git
cd citationtrace
```

---

### 2. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Opens automatically at **http://localhost:5173**

> The frontend works fully standalone — it queries OpenAlex, CrossRef, and PubMed directly from the browser. The backend is optional and adds LangSmith tracing.

---

### 3. Run the backend (optional)

```bash
cd backend
bash start.sh
```

The script will automatically:
1. Check your Python 3 installation
2. Create and activate a virtual environment (`backend/venv/`)
3. Install all dependencies from `requirements.txt`
4. Copy `.env.example` → `.env` on first run
5. Start the FastAPI server on **http://localhost:8000**

Health check: http://localhost:8000/health

---

## LangSmith Tracing Setup

LangSmith traces every search pipeline run so you can inspect retrieval steps, NLI scores, and latency. It is **optional** — the backend works without it.

### Step 1 — Create a LangSmith account

Go to [smith.langchain.com](https://smith.langchain.com) and sign up (free tier available).

### Step 2 — Get your API key

1. Click your avatar → **Settings** → **API Keys**
2. Click **Create API Key**
3. Copy the key (starts with `lsv2_...`)

### Step 3 — Configure your `.env`

After running `bash start.sh` once, a `backend/.env` file is created. Open it and fill in your key:

```env
LANGSMITH_API_KEY=lsv2_your_key_here
LANGSMITH_PROJECT=citationtrace
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

> `LANGSMITH_PROJECT` is the project name that will appear in the LangSmith dashboard. You can change it to anything.

### Step 4 — Restart the backend

```bash
# From backend/
bash start.sh
```

You should see traces appear in your LangSmith dashboard at [smith.langchain.com/o/your-org/projects](https://smith.langchain.com).

### What gets traced

| Trace | What it captures |
|-------|-----------------|
| `pipeline.search` | Raw results from OpenAlex, CrossRef, PubMed |
| `pipeline.rerank` | BM25 scores × citation count per result |
| `pipeline.verify` | NLI class + confidence per (claim, abstract) pair |
| `pipeline.synthesize` | Final answer + claim-to-citation mapping |

---

## Local Deployment — Full Stack

Run both services together for the complete experience:

**Terminal 1 — Backend**
```bash
cd citationtrace/backend
bash start.sh
# → FastAPI running on http://localhost:8000
```

**Terminal 2 — Frontend**
```bash
cd citationtrace/frontend
npm install   # first time only
npm run dev
# → Vite dev server on http://localhost:5173
```

The frontend auto-detects the backend at `localhost:8000`. If the backend is not running, it falls back to direct browser API calls.

---

## Project Structure

```
citationtrace/
├── backend/
│   ├── main.py              # FastAPI app — POST /query, GET /health
│   ├── pipeline.py          # Multi-source RAG (OpenAlex + CrossRef + PubMed)
│   │                        # BM25 reranking, extractive summarization
│   ├── verifier.py          # NLI verification via sentence-transformers
│   ├── models.py            # Pydantic models
│   ├── langsmith_config.py  # LangSmith tracing setup
│   ├── requirements.txt
│   ├── .env.example         # Copy to .env and fill in your keys
│   └── start.sh             # One-command setup & start
├── frontend/
│   ├── index.html           # Single-file SPA (no framework, no build step)
│   ├── package.json         # Vite 5 dev server
│   └── vite.config.js       # Serves on port 5173
├── CitationTrace_Final_Report.pdf
├── CitationTrace_Slides.pptx
└── README.md
```

---

## Features

- **Multi-source search** — OpenAlex + CrossRef + PubMed queried in parallel, deduplicated by DOI
- **BM25 + citation reranking** — relevance × citation count scoring
- **NLI verification** — 4-class badge per result (Supported / Partial / Low Confidence / Unverified)
- **Expandable abstracts** — click any card to read the full abstract
- **Citation export** — BibTeX, APA bibliography, in-text `(Author et al., Year)` with one-click copy
- **Batch export** — download all results as `.bib` or `.txt` APA reference list
- **Source Validator** — validate any source by URL, DOI, ISBN, PubMed ID, paper title, or author + year + keywords
- **Search history** — last 10 queries saved in localStorage
- **Atomic audit trail** — synthesized answer broken into claims, each mapped to a citation with NLI status
- **Filter & sort** — by source, year, confidence, citation count
- **LangSmith tracing** — full observability over every pipeline run (optional)

---

## APIs Used

All free, no API keys required for the frontend.

| API | Coverage | Docs |
|-----|----------|------|
| OpenAlex | 250M+ scholarly works | [openalex.org](https://openalex.org) |
| CrossRef | 140M+ metadata records | [crossref.org](https://www.crossref.org) |
| PubMed NCBI | 37M+ biomedical articles | [ncbi.nlm.nih.gov](https://www.ncbi.nlm.nih.gov) |
| Open Library | Books via ISBN / author | [openlibrary.org](https://openlibrary.org) |

---

## Key References

- Asai et al. (2026). OpenScholar. *Nature*. https://doi.org/10.1038/s41586-025-10072-4  
- Venkit et al. (2025). DeepTRACE. https://arxiv.org/abs/2509.04499  
- Earp et al. (2025). The Provenance Problem. https://arxiv.org/abs/2509.13365  

---

## License

MIT
