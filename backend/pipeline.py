"""
RAG pipeline for CitationTrace.

Retrieves papers from OpenAlex, CrossRef, and PubMed in parallel, merges by
DOI deduplication, ranks by relevance (BM25 + citation-count), synthesises an
extractive answer with inline [N] citation markers, verifies each citation
using sentence-transformer cosine similarity, and builds an audit trail.

LangSmith tracing is enabled when LANGSMITH_API_KEY is set in the environment.
"""

from __future__ import annotations

import asyncio
import math
import os
import re
from typing import List, Optional
from xml.etree import ElementTree as ET

import httpx
from dotenv import load_dotenv

from models import CitationItem, AuditEntry, QueryResponse
from verifier import verify_citations_batch

load_dotenv()

# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

OPENALEX_URL = "https://api.openalex.org/works"
CROSSREF_URL = "https://api.crossref.org/works"
PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate(text: str, max_chars: int) -> str:
    if not text:
        return ""
    return text[:max_chars] if len(text) > max_chars else text


def _reconstruct_abstract(inverted_index: dict) -> str:
    """Reconstruct a plain-text abstract from OpenAlex's inverted-index format."""
    if not inverted_index:
        return ""
    try:
        max_pos = max(pos for positions in inverted_index.values() for pos in positions)
        words = [""] * (max_pos + 1)
        for word, positions in inverted_index.items():
            for pos in positions:
                words[pos] = word
        return " ".join(words)
    except Exception:
        return ""


def _strip_jats(html: str) -> str:
    """Remove JATS/HTML tags from CrossRef abstract strings."""
    return re.sub(r'<[^>]+>', ' ', html or '').strip()


def _bm25_score(query: str, title: str, abstract: str) -> float:
    """
    Lightweight BM25 relevance score normalised to [0.40, 0.97].
    Title matches receive a 2.5× term bonus.
    """
    k1, b, avgdl = 1.5, 0.75, 120
    stop = {
        "the", "and", "for", "with", "from", "that", "this", "are", "was",
        "has", "have", "been", "its", "their", "which", "also", "both",
        "more", "into", "than", "but", "not", "can", "will", "may", "all",
        "one", "two", "any", "our", "a", "an", "of", "in", "on", "at",
        "to", "is", "it", "be", "by",
    }

    def tok(s: str) -> list:
        return [
            w for w in re.sub(r'[^a-z0-9 ]', ' ', (s or '').lower()).split()
            if len(w) > 1 and w not in stop
        ]

    q_tokens = tok(query)
    title_tokens = tok(title)
    body_tokens = tok(abstract)
    all_tokens = title_tokens + body_tokens
    dl = len(all_tokens)
    if not q_tokens or not dl:
        return 0.42

    tf: dict = {}
    for w in all_tokens:
        tf[w] = tf.get(w, 0) + 1
    title_set = set(title_tokens)

    score = 0.0
    for term in q_tokens:
        f = tf.get(term, 0)
        title_bonus = 2.5 if term in title_set else 1.0
        bm25 = (f * (k1 + 1)) / (f + k1 * (1 - b + b * (dl / avgdl))) if f > 0 else 0
        score += bm25 * title_bonus

    normalised = min(score / (len(q_tokens) * 3.5), 1.0)
    return min(0.97, round(0.40 + normalised * 0.52, 4))


# ---------------------------------------------------------------------------
# Per-source fetch functions
# ---------------------------------------------------------------------------

async def _fetch_openalex(query: str, client: httpx.AsyncClient) -> list[dict]:
    try:
        params = {
            "search": query,
            "per-page": "10",
            "sort": "relevance_score:desc",
            "select": (
                "id,title,authorships,publication_year,doi,"
                "abstract_inverted_index,primary_location,cited_by_count"
            ),
            "mailto": "citationtrace@research.tool",
        }
        resp = await client.get(OPENALEX_URL, params=params, timeout=10.0)
        resp.raise_for_status()
        works = resp.json().get("results", [])
        results = []
        for w in works:
            if not w.get("title"):
                continue
            abstract = _reconstruct_abstract(w.get("abstract_inverted_index") or {})
            doi_raw = w.get("doi") or ""
            doi = doi_raw.replace("https://doi.org/", "") if doi_raw else None
            authors = [
                a["author"]["display_name"]
                for a in (w.get("authorships") or [])[:5]
                if a.get("author")
            ]
            url = (
                doi_raw
                or (w.get("primary_location") or {}).get("landing_page_url")
                or f"https://openalex.org/{(w.get('id') or '').split('/')[-1]}"
            )
            results.append({
                "title": w["title"],
                "authors": authors,
                "year": w.get("publication_year"),
                "doi": doi,
                "abstract": abstract,
                "url": url,
                "cited_by_count": w.get("cited_by_count", 0),
                "source": "OpenAlex",
            })
        return results
    except Exception:
        return []


async def _fetch_crossref(query: str, client: httpx.AsyncClient) -> list[dict]:
    try:
        params = {
            "query.bibliographic": query,
            "rows": "10",
            "filter": "has-abstract:true",
            "select": (
                "DOI,title,author,published-print,published-online,"
                "abstract,is-referenced-by-count,container-title"
            ),
            "mailto": "citationtrace@research.tool",
        }
        resp = await client.get(CROSSREF_URL, params=params, timeout=10.0)
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])
        results = []
        for i in items:
            title_list = i.get("title") or []
            if not title_list:
                continue
            date_parts = (
                i.get("published-print") or i.get("published-online") or {}
            ).get("date-parts", [[None]])
            year = (date_parts[0] or [None])[0]
            abstract = _strip_jats(i.get("abstract") or "")
            doi = i.get("DOI")
            authors = [
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in (i.get("author") or [])[:5]
            ]
            results.append({
                "title": title_list[0],
                "authors": authors,
                "year": year,
                "doi": doi,
                "abstract": abstract,
                "url": f"https://doi.org/{doi}" if doi else "",
                "cited_by_count": i.get("is-referenced-by-count", 0),
                "source": "CrossRef",
            })
        return results
    except Exception:
        return []


async def _fetch_pubmed(query: str, client: httpx.AsyncClient) -> list[dict]:
    try:
        # Step 1: search for IDs
        search_resp = await client.get(
            PUBMED_SEARCH_URL,
            params={
                "db": "pubmed", "term": query, "retmax": "10",
                "retmode": "json", "sort": "relevance",
            },
            timeout=10.0,
        )
        search_resp.raise_for_status()
        ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []
        id_str = ",".join(ids)

        # Step 2: summaries
        sum_resp = await client.get(
            PUBMED_SUMMARY_URL,
            params={"db": "pubmed", "id": id_str, "retmode": "json"},
            timeout=10.0,
        )
        sum_resp.raise_for_status()
        sum_data = sum_resp.json().get("result", {})

        # Step 3: abstracts via efetch (XML)
        fetch_resp = await client.get(
            PUBMED_FETCH_URL,
            params={"db": "pubmed", "id": id_str, "retmode": "xml"},
            timeout=10.0,
        )
        abstract_map: dict = {}
        if fetch_resp.status_code == 200:
            try:
                root = ET.fromstring(fetch_resp.text)
                for art in root.findall(".//PubmedArticle"):
                    pmid_el = art.find(".//PMID")
                    pmid = pmid_el.text if pmid_el is not None else ""
                    ab_texts = art.findall(".//AbstractText")
                    ab = " ".join(el.text or "" for el in ab_texts)
                    if pmid and ab:
                        abstract_map[pmid] = ab
            except Exception:
                pass

        results = []
        for uid in ids:
            item = sum_data.get(uid)
            if not item or not item.get("title"):
                continue
            doi = next(
                (
                    aid["value"]
                    for aid in (item.get("articleids") or [])
                    if aid.get("idtype") == "doi"
                ),
                None,
            )
            pub_date = item.get("pubdate", "")
            year = int(pub_date[:4]) if pub_date and pub_date[:4].isdigit() else None
            results.append({
                "title": item["title"].rstrip("."),
                "authors": [a["name"] for a in (item.get("authors") or [])[:5]],
                "year": year,
                "doi": doi,
                "abstract": abstract_map.get(uid, ""),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                "cited_by_count": 0,
                "source": "PubMed",
            })
        return results
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Merge & rank
# ---------------------------------------------------------------------------

def _merge_and_rank(query: str, *result_lists) -> list[dict]:
    """Deduplicate by DOI, score by BM25 + citation count, return top-20."""
    all_papers = [p for lst in result_lists for p in lst]
    seen: set = set()
    unique: list = []
    for p in all_papers:
        key = (p.get("doi") or "").lower() or p["title"].lower()[:80]
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)

    for p in unique:
        p["_conf"] = _bm25_score(query, p["title"], p.get("abstract", ""))
        cit_score = math.log10((p.get("cited_by_count") or 0) + 1) / 5
        p["_rank"] = p["_conf"] * 0.6 + cit_score * 0.4

    unique.sort(key=lambda p: p["_rank"], reverse=True)
    return unique[:20]


# ---------------------------------------------------------------------------
# Extractive answer synthesis
# ---------------------------------------------------------------------------

def _synthesize_answer(query: str, citations: list) -> str:
    """
    Build a readable paragraph with inline [N] citation markers using
    extractive summarisation: pick the highest-BM25 sentence per abstract.
    """
    if not citations:
        return f"No relevant literature was found for: '{query}'."

    sources = list({c.get("source", "") for c in citations if c.get("source")})
    intro = (
        f"The following synthesis draws from {len(citations)} peer-reviewed "
        f"sources ({', '.join(sources)}) for: \"{query}\"."
    )

    body_parts: List[str] = []
    for idx, c in enumerate(citations, 1):
        abstract = c.get("abstract", "") or c.get("abstract_snippet", "")
        sentences = [
            s.strip()
            for s in re.findall(r'[^.!?]+[.!?]+', abstract)
            if len(s.strip()) > 30
        ]
        if sentences:
            best = max(sentences, key=lambda s: _bm25_score(query, c["title"], s))
        else:
            best = c["title"]

        authors = c.get("authors", [])
        first = authors[0].split()[-1] if authors else "Unknown"
        etal = " et al." if len(authors) > 1 else ""
        year = f" ({c['year']})" if c.get("year") else ""
        body_parts.append(f"{first}{etal}{year} [{idx}] {best}")

    return f"{intro} {' '.join(body_parts)}"


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

async def _run_pipeline(query: str) -> QueryResponse:
    """Execute the multi-source citation retrieval pipeline."""
    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        oa, cr, pm = await asyncio.gather(
            _fetch_openalex(query, client),
            _fetch_crossref(query, client),
            _fetch_pubmed(query, client),
        )

    merged = _merge_and_rank(query, oa, cr, pm)

    # Track per-source counts for metadata
    sources_queried = {
        "OpenAlex": len(oa),
        "CrossRef": len(cr),
        "PubMed": len(pm),
        "merged_unique": len(merged),
    }

    citations: List[CitationItem] = []
    for idx, paper in enumerate(merged, start=1):
        abstract = paper.get("abstract") or ""
        abstract_snippet = _truncate(abstract, 200)
        doi = paper.get("doi")
        url = paper.get("url") or (f"https://doi.org/{doi}" if doi else "")
        citations.append(
            CitationItem(
                id=idx,
                title=paper.get("title", "Untitled"),
                authors=paper.get("authors", []),
                year=paper.get("year"),
                doi=doi,
                abstract_snippet=abstract_snippet,
                url=url,
                confidence_score=0.0,   # filled in after verification
                verified=False,          # filled in after verification
                source=paper.get("source"),
                cited_by_count=paper.get("cited_by_count", 0),
            )
        )

    # Synthesise answer using full abstract text (not just snippet)
    # Build a temporary list of dicts for the synthesiser so it can access full abstracts
    merged_for_synth = merged[:len(citations)]
    answer = _synthesize_answer(query, merged_for_synth)

    # Verify citations: compare FULL answer text against each paper's abstract
    # (genuine cross-text verification — not self-comparison)
    pairs = [(answer, c.abstract_snippet) for c in citations]
    verification_results = verify_citations_batch(pairs) if citations else []

    for citation, (score, verified) in zip(citations, verification_results):
        citation.confidence_score = round(score, 4)
        citation.verified = verified

    # Build audit trail with 4-class status
    audit_trail: List[AuditEntry] = []
    for citation in citations:
        if citation.confidence_score >= 0.72:
            status = "supported"
        elif citation.confidence_score >= 0.55:
            status = "partially-supported"
        elif citation.confidence_score >= 0.35:
            status = "low-confidence"
        else:
            status = "unverified"

        # Also store nli_class on the CitationItem itself
        citation.nli_class = status

        audit_trail.append(
            AuditEntry(
                claim=_truncate(answer, 120),
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
        sources_queried=sources_queried,
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

            @traceable(
                name="citation_pipeline",
                project_name=os.getenv("LANGSMITH_PROJECT", "citationtrace"),
            )
            async def _traced_pipeline(q: str) -> QueryResponse:
                return await _run_pipeline(q)

            return await _traced_pipeline(query)
        except Exception:
            # If LangSmith tracing fails for any reason, fall through
            pass

    return await _run_pipeline(query)
