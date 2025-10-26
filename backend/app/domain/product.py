"""Product domain models."""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class Image(BaseModel):
    """Product image metadata."""
    url: str
    width: Optional[int] = None
    height: Optional[int] = None
    alt: Optional[str] = None


class ProductItem(BaseModel):
    """Individual product item with all metadata."""
    title: str
    normalized_title: Optional[str] = None
    price: Optional[float] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    currency: Optional[str] = "USD"
    url: str
    source: str
    match_score: float
    review_sentiment: Literal["positive", "neutral", "negative", "unknown"] = "unknown"
    sentiment_score: Optional[float] = None
    fake_review_probability: Optional[float] = None
    availability: Optional[str] = None
    primary_image_url: Optional[str] = None
    images: List[Image] = Field(default_factory=list)
    sentiment_reason: Optional[str] = None
    sentiment_highlights: List[str] = Field(default_factory=list)
    product_type: Optional[str] = None
    category_match: Optional[bool] = None
    is_listing_page: Optional[bool] = False


class SearchResponse(BaseModel):
    """Response containing search results."""
    query: str
    items: List[ProductItem]

