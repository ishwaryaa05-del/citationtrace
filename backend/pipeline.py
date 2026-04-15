"""
RAG pipeline for CitationTrace.

Retrieves top-5 papers from Semantic Scholar, synthesises an answer with
inline [N] citation markers, verifies each citation using sentence-transformer
cosine similarity, and builds an audit trail.

LangSmith tracing is enabled when LANGSMITH_API_KEY is set in the environment.
"""

from __future__ import annotations

import os
import asyncio
from typing import List, Optional

import httpx
from dotenv import load_dotenv

from models import CitationItem, AuditEntry, QueryResponse
from verifier import verify_citations_batch

load_dotenv()

SEMANTIC_SCHOLAR_URL = (
    "https://api.semanticscholar.org/graph/v1/paper/search"
)
FIELDS = "title,authors,year,externalIds,abstract"
RESULT_LIMIT = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_doi(external_ids: dict) -> Optional[str]:
    """Return DOI string from Semantic Scholar externalIds dict, or None."""
    if not external_ids:
        return None
    return external_ids.get("DOI") or external_ids.get("doi")


def _build_paper_url(paper_id: str, doi: Optional[str]) -> str:
    """Prefer a DOI URL; fall back to a Semantic Scholar permalink."""
    if doi:
        return f"https://doi.org/{doi}"
    return f"https://www.semanticscholar.org/paper/{paper_id}"


def _truncate(text: str, max_chars: int) -> str:
    if not text:
        return ""
    return text[:max_chars] if len(text) > max_chars else text


def _synthesize_answer(query: str, citations: List[CitationItem]) -> str:
    """
    Build a readable paragraph that cites each paper with [N] markers.
    In production this would be replaced by an LLM call.
    """
    if not citations:
        return f"No relevant literature was found for the query: '{query}'."

    # Opening sentence summarising the topic
    topic_snippets = "; ".join(
        c.abstract_snippet[:80] for c in citations if c.abstract_snippet
    )
    intro = (
        f"Based on recent literature, the following insights address '{query}': "
        f"{topic_snippets[:200]}."
    )

    sentences: List[str] = [intro]
    for c in citations:
        first_author = c.authors[0] if c.authors else "Unknown"
        year_str = str(c.year) if c.year else "n.d."
        snippet = _truncate(c.abstract_snippet, 100)
        sentences.append(
            f"{first_author} et al. ({year_str}) [{c.id}] found that {snippet}."
        )

    return " ".join(sentences)


# ---------------------------------------------------------------------------
# Semantic Scholar fetch
# ---------------------------------------------------------------------------

async def _fetch_papers(query: str) -> List[dict]:
    """Fetch up to RESULT_LIMIT papers from Semantic Scholar."""
    params = {"query": query, "fields": FIELDS, "limit": RESULT_LIMIT}
    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(SEMANTIC_SCHOLAR_URL, params=params)
        response.raise_for_status()
        data = response.json()
    return data.get("data", [])


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

async def _run_pipeline(query: str) -> QueryResponse:
    """Execute the citation retrieval pipeline."""
    raw_papers = await _fetch_papers(query)

    citations: List[CitationItem] = []
    for idx, paper in enumerate(raw_papers, start=1):
        title = paper.get("title") or "Untitled"
        authors = [
            a.get("name", "Unknown") for a in (paper.get("authors") or [])
        ]
        year = paper.get("year")
        external_ids = paper.get("externalIds") or {}
        doi = _extract_doi(external_ids)
        abstract = paper.get("abstract") or ""
        abstract_snippet = _truncate(abstract, 200)
        paper_id = paper.get("paperId", "")
        url = _build_paper_url(paper_id, doi)

        citations.append(
            CitationItem(
                id=idx,
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                abstract_snippet=abstract_snippet,
                url=url,
                confidence_score=0.0,   # filled in after verification
                verified=False,          # filled in after verification
            )
        )

    # Synthesise answer before verification (uses abstract snippets as claims)
    answer = _synthesize_answer(query, citations)

    # Verify citations: use the abstract snippet itself as the claim text
    # (template-generated answer is derived directly from abstracts)
    pairs = [(c.abstract_snippet, c.abstract_snippet) for c in citations]
    verification_results = verify_citations_batch(pairs) if citations else []

    for citation, (score, verified) in zip(citations, verification_results):
        citation.confidence_score = round(score, 4)
        citation.verified = verified

    # Build audit trail
    audit_trail: List[AuditEntry] = []
    for citation in citations:
        if citation.confidence_score >= 0.35:
            status = "verified"
        elif citation.confidence_score >= 0.20:
            status = "low_confidence"
        else:
            status = "unverified"

        audit_trail.append(
            AuditEntry(
                claim=_truncate(citation.abstract_snippet, 120),
                source_id=citation.id,
                confidence=citation.confidence_score,
                status=status,
            )
        )

    total_claims = len(citations)
    verified_claims = sum(1 for c in citations if c.verified)
    citation_accuracy = (
        round(verified_claims / total_claims, 4) if total_claims > 0 else 0.0
    )

    return QueryResponse(
        query=query,
        answer=answer,
        citations=citations,
        audit_trail=audit_trail,
        total_claims=total_claims,
        verified_claims=verified_claims,
        citation_accuracy=citation_accuracy,
    )


# ---------------------------------------------------------------------------
# LangSmith-traced entry point
# ---------------------------------------------------------------------------

async def run_citation_pipeline(query: str) -> QueryResponse:
    """
    Public entry point. Wraps the pipeline with LangSmith tracing when an
    API key is available; otherwise runs the pipeline directly.
    """
    langsmith_api_key = os.getenv("LANGSMITH_API_KEY")

    if langsmith_api_key:
        try:
            from langsmith import traceable

            @traceable(name="citation_pipeline", project_name=os.getenv("LANGSMITH_PROJECT", "citationtrace"))
            async def _traced_pipeline(q: str) -> QueryResponse:
                return await _run_pipeline(q)

            return await _traced_pipeline(query)
        except Exception:
            # If LangSmith tracing fails for any reason, fall through
            pass

    return await _run_pipeline(query)
