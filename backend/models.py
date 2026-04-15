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


class AuditEntry(BaseModel):
    claim: str
    source_id: int
    confidence: float
    status: str  # "verified" | "unverified" | "low_confidence"


class QueryResponse(BaseModel):
    query: str
    answer: str  # answer text with [1], [2] inline citation markers
    citations: List[CitationItem]
    audit_trail: List[AuditEntry]
    total_claims: int
    verified_claims: int
    citation_accuracy: float  # verified/total
