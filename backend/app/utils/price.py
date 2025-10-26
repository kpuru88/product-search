"""Price extraction utilities."""
import json
import re
from typing import Dict, Optional


async def extract_price_range(content: str) -> Dict[str, Optional[float]]:
    """
    Extract price range from listing page content using JSON-LD and regex.
    
    Args:
        content: HTML content to extract prices from
        
    Returns:
        Dictionary with price_min and price_max keys
    """
    try:
        prices = []
        
        try:
            jsonld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
            jsonld_blocks = re.findall(jsonld_pattern, content, re.DOTALL | re.IGNORECASE)
            
            for block in jsonld_blocks:
                try:
                    data = json.loads(block)
                    
                    def extract_prices_from_jsonld(obj):
                        if isinstance(obj, dict):
                            if obj.get('@type') == 'AggregateOffer':
                                if 'lowPrice' in obj:
                                    try:
                                        prices.append(float(str(obj['lowPrice']).replace(',', '')))
                                    except (ValueError, TypeError):
                                        pass
                                if 'highPrice' in obj:
                                    try:
                                        prices.append(float(str(obj['highPrice']).replace(',', '')))
                                    except (ValueError, TypeError):
                                        pass
                            
                            if obj.get('@type') in ['Offer', 'Product']:
                                if 'price' in obj:
                                    try:
                                        prices.append(float(str(obj['price']).replace(',', '')))
                                    except (ValueError, TypeError):
                                        pass
                                if 'offers' in obj:
                                    extract_prices_from_jsonld(obj['offers'])
                            
                            if obj.get('@type') == 'ItemList' and 'itemListElement' in obj:
                                for item in obj['itemListElement']:
                                    if isinstance(item, dict):
                                        if 'item' in item:
                                            extract_prices_from_jsonld(item['item'])
                                        else:
                                            extract_prices_from_jsonld(item)
                            
                            for value in obj.values():
                                if isinstance(value, (dict, list)):
                                    extract_prices_from_jsonld(value)
                        
                        elif isinstance(obj, list):
                            for item in obj:
                                extract_prices_from_jsonld(item)
                    
                    extract_prices_from_jsonld(data)
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            print(f"JSON-LD parsing failed: {str(e)}")
        
        price_patterns = [
            r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'(?:From|from|Starting at|starting at)\s+\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'(?:Now|now|Sale|sale|SALE)\s+\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*[-–—]\s*\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    for price_str in match:
                        try:
                            price = float(price_str.replace(',', ''))
                            if 5 <= price <= 100000:
                                prices.append(price)
                        except ValueError:
                            continue
                else:
                    try:
                        price = float(match.replace(',', ''))
                        if 5 <= price <= 100000:
                            prices.append(price)
                    except ValueError:
                        continue
        
        if not prices:
            print(f"No prices found in content (length: {len(content)} chars)")
            return {"price_min": None, "price_max": None}
        
        prices = sorted(set(prices))
        print(f"Found {len(prices)} unique prices: {prices[:10]}...")
        
        return {
            "price_min": min(prices),
            "price_max": max(prices)
        }
    except Exception as e:
        print(f"Price range extraction failed: {str(e)}")
        return {"price_min": None, "price_max": None}

