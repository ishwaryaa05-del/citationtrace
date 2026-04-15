# CitationTrace

**A SaaS Platform for Verified Scholarly Citations and Provenance Preservation**

> Solving the Provenance Problem in AI-assisted research.

## Project Structure

```
citationtrace/
├── backend/           # FastAPI backend (Python)
│   ├── main.py        # FastAPI app with /query and /health endpoints
│   ├── pipeline.py    # RAG pipeline (Semantic Scholar + LangSmith tracing)
│   ├── verifier.py    # Citation verification via cosine similarity
│   ├── models.py      # Pydantic data models
│   ├── langsmith_config.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── index.html     # Self-contained React-style SPA
├── CitationTrace_Final_Report.pdf
└── CitationTrace_Slides.pptx
```

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Add your LANGSMITH_API_KEY to .env
uvicorn main:app --reload
```

### Frontend
Open `frontend/index.html` in a browser. It will connect to `http://localhost:8000` if the backend is running, otherwise falls back to demo data.

## Key References
- Asai et al. (2026). OpenScholar. *Nature*. https://doi.org/10.1038/s41586-025-10072-4
- Venkit et al. (2025). DeepTRACE. https://arxiv.org/abs/2509.04499
- Earp et al. (2025). The Provenance Problem. https://arxiv.org/abs/2509.13365

## License
MIT
