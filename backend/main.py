"""
CitationTrace API — FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models import QueryRequest, QueryResponse
from pipeline import run_citation_pipeline

app = FastAPI(
    title="CitationTrace API",
    description=(
        "A SaaS platform for verified scholarly citation retrieval. "
        "Submit a research query and receive top papers from Semantic Scholar "
        "with inline citation markers, confidence scores, and an audit trail."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Retrieve and verify scholarly citations for the given research query.

    - Fetches top-5 papers from Semantic Scholar
    - Synthesises an answer with inline [N] citation markers
    - Verifies each citation using cosine-similarity on paper abstracts
    - Returns a full audit trail with confidence scores
    """
    return await run_citation_pipeline(request.query)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
