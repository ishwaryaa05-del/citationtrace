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
        "Submit a research query and receive top papers from OpenAlex, CrossRef, "
        "and PubMed — ranked by BM25 relevance x citation count, verified with "
        "4-class NLI scoring, and returned with a full audit trail."
    ),
    version="2.0.0",
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

    - Queries OpenAlex, CrossRef, and PubMed in parallel (up to 10 results each)
    - Deduplicates results by DOI
    - Reranks using BM25 relevance x citation count
    - Verifies each citation with 4-class NLI (Supported / Partially Supported /
      Refuted / Unverifiable)
    - Returns synthesised answer with inline [N] citation markers and audit trail
    """
    return await run_citation_pipeline(request.query)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
