"""Tests for ranking utilities."""
import pytest
from app.domain.product import ProductItem
from app.utils.ranking import filter_by_match_score, deduplicate_products


def test_filter_by_match_score():
    """Test filtering products by match score."""
    products = [
        ProductItem(
            title="Product 1",
            url="https://example.com/1",
            source="example.com",
            match_score=0.8
        ),
        ProductItem(
            title="Product 2",
            url="https://example.com/2",
            source="example.com",
            match_score=0.3
        ),
        ProductItem(
            title="Product 3",
            url="https://example.com/3",
            source="example.com",
            match_score=0.5
        ),
    ]
    
    filtered = filter_by_match_score(products, min_score=0.35)
    assert len(filtered) == 2
    assert filtered[0].match_score == 0.8
    assert filtered[1].match_score == 0.5


def test_deduplicate_products():
    """Test deduplication of products."""
    products = [
        ProductItem(
            title="Black Chair",
            normalized_title="black chair",
            url="https://example.com/1",
            source="example.com",
            match_score=0.8
        ),
        ProductItem(
            title="Black Chair (Duplicate)",
            normalized_title="black chair",
            url="https://example.com/2",
            source="example.com",
            match_score=0.7
        ),
        ProductItem(
            title="Blue Chair",
            normalized_title="blue chair",
            url="https://example.com/3",
            source="example.com",
            match_score=0.6
        ),
    ]
    
    deduped = deduplicate_products(products)
    assert len(deduped) == 2
    assert deduped[0].normalized_title == "black chair"
    assert deduped[1].normalized_title == "blue chair"



