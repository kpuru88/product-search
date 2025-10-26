"""Product ranking and deduplication utilities."""
from typing import List
from app.domain.product import ProductItem
from app.utils.domains import get_domain_tier
from app.utils.config import MIN_MATCH_SCORE


def filter_by_match_score(products: List[ProductItem], min_score: float = MIN_MATCH_SCORE) -> List[ProductItem]:
    """
    Filter products by minimum match score.
    
    Args:
        products: List of products to filter
        min_score: Minimum match score threshold
        
    Returns:
        Filtered list of products
    """
    return [p for p in products if p.match_score >= min_score]


def deduplicate_products(products: List[ProductItem]) -> List[ProductItem]:
    """
    Deduplicate products by normalized title and source.
    
    Args:
        products: List of products to deduplicate
        
    Returns:
        Deduplicated list of products
    """
    seen_products = set()
    deduped_products = []
    for p in products:
        key = f"{p.normalized_title}|{p.source}"
        if key not in seen_products:
            seen_products.add(key)
            deduped_products.append(p)
    return deduped_products


def rank_products(products: List[ProductItem]) -> List[ProductItem]:
    """
    Sort products by relevance using multiple ranking factors.
    
    Ranking priority:
    1. Match score (higher is better)
    2. Category match (matched products first)
    3. Product detail pages over listing pages
    4. Domain tier (manufacturer > retailer > marketplace)
    5. Price availability (products with prices first)
    
    Args:
        products: List of products to rank
        
    Returns:
        Sorted list of products
    """
    return sorted(
        products,
        key=lambda p: (
            -p.match_score,
            -(1 if p.category_match else 0),
            -(0 if p.is_listing_page else 1),
            -(1 if getattr(p, 'page_type', 'pdp') == 'pdp' else 0),
            -(1 if getattr(p, 'page_type', 'pdp') == 'listing' else 0),
            -get_domain_tier(p.url),
            -(1 if p.price is not None else 0)
        )
    )


