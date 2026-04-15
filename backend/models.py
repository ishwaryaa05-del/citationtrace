from pydantic import BaseModel
from typing import List, Optional


class QueryRequest(BaseModel):
    query: str


class CitationItem(BaseModel):
    id: int
    title: str
    authors: List[str]
    year: Optional[int]
    doi: Optional[str]
    abstract_snippet: str
    url: str
    confidence_score: float  # 0.0 - 1.0
    verified: bool
    nli_class: Optional[str] = None   # supported/partially-supported/low-confidence/unverified
    source: Optional[str] = None      # OpenAlex/CrossRef/PubMed
    cited_by_count: Optional[int] = 0


class AuditEntry(BaseModel):
    claim: str
    source_id: int
    confidence: float
    status: str  # supported / partially-supported / low-confidence / unverified


class QueryResponse(BaseModel):
    query: str
    answer: str  # answer text with [1], [2] inline citation markers
    citations: List[CitationItem]
    audit_trail: List[AuditEntry]
    total_claims: int
    verified_claims: int
    citation_accuracy: float  # verified/total
    sources_queried: Optional[dict] = None
