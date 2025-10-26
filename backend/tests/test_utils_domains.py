"""Tests for domain classification utilities."""
import pytest
from app.utils.domains import get_domain_tier, is_ecommerce_domain, get_tier_name


def test_get_domain_tier_manufacturer():
    """Test manufacturer domain tier classification."""
    assert get_domain_tier("https://www.apple.com/products") == 3
    assert get_domain_tier("https://samsung.com/tv") == 3
    assert get_domain_tier("https://sony.com") == 3


def test_get_domain_tier_major_retailer():
    """Test major retailer domain tier classification."""
    assert get_domain_tier("https://www.amazon.com/product/123") == 2
    assert get_domain_tier("https://bestbuy.com/tv") == 2
    assert get_domain_tier("https://walmart.com") == 2


def test_get_domain_tier_marketplace():
    """Test marketplace domain tier classification."""
    assert get_domain_tier("https://www.ebay.com/item/123") == 1
    assert get_domain_tier("https://etsy.com/listing/456") == 1


def test_get_domain_tier_unknown():
    """Test unknown domain tier classification."""
    assert get_domain_tier("https://unknown-store.com") == 0
    assert get_domain_tier("https://random-blog.com") == 0


def test_is_ecommerce_domain():
    """Test ecommerce domain detection."""
    assert is_ecommerce_domain("https://www.amazon.com/product/123") is True
    assert is_ecommerce_domain("https://apple.com") is True
    assert is_ecommerce_domain("https://random-blog.com") is False


def test_get_tier_name():
    """Test tier name retrieval."""
    assert get_tier_name(3) == "manufacturer"
    assert get_tier_name(2) == "major retailer"
    assert get_tier_name(1) == "marketplace"
    assert get_tier_name(0) == "other"
    assert get_tier_name(99) == "other"



