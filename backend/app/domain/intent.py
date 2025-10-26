"""Search intent domain models."""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class SearchIntent(BaseModel):
    """Structured search intent parsed from user query."""
    query_text: str
    category: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    core_specs: List[str] = Field(default_factory=list)
    price_expectation: Optional[str] = None
    region: str = "US"
    strictness: Literal["exact", "close", "fuzzy"] = "close"

