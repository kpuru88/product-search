"""Listing page expansion utilities."""
import json
import re
from urllib.parse import urljoin
from typing import List, Dict


async def expand_listing(url: str, html: str, max_products: int = 5) -> List[Dict[str, any]]:
    """
    Extract individual product URLs and prices from a listing page.
    
    Args:
        url: URL of the listing page
        html: HTML content of the listing page
        max_products: Maximum number of products to extract
        
    Returns:
        List of product dictionaries with url, title, price, currency
    """
    products = []
    
    try:
        jsonld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        jsonld_blocks = re.findall(jsonld_pattern, html, re.DOTALL | re.IGNORECASE)
        
        for block in jsonld_blocks:
            try:
                data = json.loads(block)
                
                def extract_products_from_jsonld(obj):
                    if isinstance(obj, dict):
                        if obj.get('@type') == 'ItemList' and 'itemListElement' in obj:
                            for item in obj['itemListElement']:
                                if isinstance(item, dict):
                                    product_obj = item.get('item', item)
                                    if isinstance(product_obj, dict):
                                        product_url = product_obj.get('url')
                                        product_name = product_obj.get('name')
                                        
                                        price = None
                                        currency = None
                                        
                                        if 'offers' in product_obj:
                                            offers = product_obj['offers']
                                            if isinstance(offers, dict):
                                                price = offers.get('price') or offers.get('lowPrice')
                                                currency = offers.get('priceCurrency', 'USD')
                                            elif isinstance(offers, list) and len(offers) > 0:
                                                price = offers[0].get('price')
                                                currency = offers[0].get('priceCurrency', 'USD')
                                        
                                        if product_url:
                                            products.append({
                                                'url': urljoin(url, product_url),
                                                'title': product_name,
                                                'price': float(price) if price else None,
                                                'currency': currency
                                            })
                        
                        elif obj.get('@type') == 'Product':
                            product_url = obj.get('url')
                            product_name = obj.get('name')
                            
                            price = None
                            currency = None
                            
                            if 'offers' in obj:
                                offers = obj['offers']
                                if isinstance(offers, dict):
                                    price = offers.get('price') or offers.get('lowPrice')
                                    currency = offers.get('priceCurrency', 'USD')
                                elif isinstance(offers, list) and len(offers) > 0:
                                    price = offers[0].get('price')
                                    currency = offers[0].get('priceCurrency', 'USD')
                            
                            if product_url:
                                products.append({
                                    'url': urljoin(url, product_url),
                                    'title': product_name,
                                    'price': float(price) if price else None,
                                    'currency': currency
                                })
                        
                        for value in obj.values():
                            if isinstance(value, (dict, list)):
                                extract_products_from_jsonld(value)
                    
                    elif isinstance(obj, list):
                        for item in obj:
                            extract_products_from_jsonld(item)
                
                extract_products_from_jsonld(data)
            except:
                continue
    except:
        pass
    
    if len(products) < max_products:
        link_patterns = [
            r'<a[^>]*href=["\']([^"\']*(?:/product/|/p/|/dp/|/sku/|/item/)[^"\']*)["\']',
            r'<a[^>]*data-asin=["\']([^"\']+)["\']',
            r'<a[^>]*data-sku=["\']([^"\']+)["\']',
        ]
        
        for pattern in link_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches[:max_products * 2]:
                if match.startswith('http'):
                    product_url = match
                else:
                    product_url = urljoin(url, match)
                
                if product_url not in [p['url'] for p in products]:
                    products.append({
                        'url': product_url,
                        'title': None,
                        'price': None,
                        'currency': 'USD'
                    })
                
                if len(products) >= max_products:
                    break
            
            if len(products) >= max_products:
                break
    
    seen_urls = set()
    unique_products = []
    for p in products:
        if p['url'] not in seen_urls:
            seen_urls.add(p['url'])
            unique_products.append(p)
    
    print(f"Expanded listing {url}: found {len(unique_products)} products")
    return unique_products[:max_products]

