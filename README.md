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

> The frontend works fully standalone — it queries OpenAlex, CrossRef, and PubMed directly from the browser. The backend is optional (adds LangSmith tracing).

---

### 3. Run the backend (optional)

```bash
cd backend
bash start.sh
```

That's it. The script will:
- Check your Python version
- Create and activate a virtual environment
- Install all dependencies from `requirements.txt`
- Copy `.env.example` → `.env` on first run
- Start the FastAPI server on **http://localhost:8000**

> **LangSmith is optional.** The backend runs without an API key. To enable tracing, open `backend/.env` and fill in your `LANGSMITH_API_KEY` from [smith.langchain.com](https://smith.langchain.com).

---

## Project Structure

```
citationtrace/
├── backend/
│   ├── main.py              # FastAPI app — /query POST + /health GET
│   ├── pipeline.py          # Multi-source RAG (OpenAlex + CrossRef + PubMed)
│   │                        # BM25 reranking, extractive summarization
│   ├── verifier.py          # NLI verification via sentence-transformers
│   ├── models.py            # Pydantic models
│   ├── langsmith_config.py  # LangSmith tracing setup
│   ├── requirements.txt
│   ├── .env.example
│   └── start.sh             # ← One-command setup & start
├── frontend/
│   ├── index.html           # Single-file SPA (no framework, no build needed)
│   ├── package.json         # Vite dev server
│   └── vite.config.js
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
- **Citation export** — BibTeX, APA bibliography, in-text `(Author et al., Year)` with copy buttons
- **Batch export** — download all results as `.bib` or `.txt` APA reference list
- **Source Validator** — validate any source by URL, DOI, ISBN, PubMed ID, paper title, or author + year + keywords
- **Search history** — last 10 queries saved in localStorage
- **Atomic audit trail** — synthesized answer broken into claims, each mapped to a citation with NLI status
- **Filter & sort** — by source, year, confidence, citation count

---

## APIs Used

All free, no API keys required in the frontend.

| API | Coverage | Docs |
|-----|----------|------|
| OpenAlex | 250M+ scholarly works | [openalex.org](https://openalex.org) |
| CrossRef | 140M+ metadata records | [crossref.org](https://www.crossref.org) |
| PubMed NCBI | 37M+ biomedical articles | [ncbi.nlm.nih.gov](https://www.ncbi.nlm.nih.gov) |
| Open Library | Books via ISBN | [openlibrary.org](https://openlibrary.org) |

---

## Key References

- Asai et al. (2026). OpenScholar. *Nature*. https://doi.org/10.1038/s41586-025-10072-4  
- Venkit et al. (2025). DeepTRACE. https://arxiv.org/abs/2509.04499  
- Earp et al. (2025). The Provenance Problem. https://arxiv.org/abs/2509.13365  

---

## License

MIT
