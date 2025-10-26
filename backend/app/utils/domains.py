"""Domain classification and tier utilities."""
from urllib.parse import urlparse
from app.utils.config import MANUFACTURER_DOMAINS, MAJOR_RETAILERS, MARKETPLACES


def get_domain_tier(url: str) -> int:
    """
    Get the tier level of a domain based on its classification.
    
    Args:
        url: URL to classify
        
    Returns:
        Tier level: 3 (manufacturer), 2 (major retailer), 1 (marketplace), 0 (other)
    """
    domain = urlparse(url).netloc.replace("www.", "").lower()
    
    if any(mfr in domain for mfr in MANUFACTURER_DOMAINS):
        return 3
    if any(retailer in domain for retailer in MAJOR_RETAILERS):
        return 2
    if any(market in domain for market in MARKETPLACES):
        return 1
    return 0


def is_ecommerce_domain(url: str) -> bool:
    """
    Check if a URL belongs to a known ecommerce domain.
    
    Args:
        url: URL to check
        
    Returns:
        True if the domain is a known ecommerce site
    """
    tier = get_domain_tier(url)
    return tier > 0


def get_tier_name(tier: int) -> str:
    """
    Get the human-readable name for a domain tier.
    
    Args:
        tier: Tier level (0-3)
        
    Returns:
        Name of the tier
    """
    tier_names = {
        3: "manufacturer",
        2: "major retailer",
        1: "marketplace",
        0: "other"
    }
    return tier_names.get(tier, "other")

