"""Search service orchestrating the end-to-end product search flow."""
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from app.domain.intent import SearchIntent
from app.domain.product import ProductItem, Image, SearchResponse
from app.adapters.parallel_search import ParallelSearchClient
from app.adapters.http_fetch import fetch_html
from app.application.extraction_service import ExtractionService
from app.application.review_service import ReviewService
from app.utils.config import (
    MANUFACTURER_DOMAINS, MAJOR_RETAILERS, 
    MAX_SEARCH_RESULTS, MAX_PRODUCTS_TO_PROCESS, MAX_PRODUCTS_TO_RETURN,
    MAX_LISTING_EXPANSION
)
from app.utils.domains import is_ecommerce_domain
from app.utils.classify import classify_page
from app.utils.expand import expand_listing
from app.utils.ranking import filter_by_match_score, deduplicate_products, rank_products


class SearchService:
    """Service orchestrating the complete product search pipeline."""
    
    def __init__(
        self,
        search_client: ParallelSearchClient,
        extraction_service: ExtractionService,
        review_service: ReviewService
    ):
        """
        Initialize the search service.
        
        Args:
            search_client: Parallel search client
            extraction_service: Product extraction service
            review_service: Review analysis service
        """
        self.search_client = search_client
        self.extraction_service = extraction_service
        self.review_service = review_service
    
    def _build_search_objective(
        self,
        normalized_query: str,
        brand_hint: str = "",
        model_hint: str = "",
        specs_hint: str = ""
    ) -> str:
        """
        Build search objective for Parallel AI search using strict PDP requirements.

        Args:
            normalized_query: Normalized search query
            brand_hint: Optional brand hint string for the prompt
            model_hint: Optional model hint string for the prompt
            specs_hint: Optional core specs hint string for the prompt

        Returns:
            Search objective string
        """
        manufacturer_domains = ", ".join(MANUFACTURER_DOMAINS[:5])
        retailer_domains = ", ".join(MAJOR_RETAILERS[:10])

        objective = (
            f'You are selecting ONLY ecommerce product detail pages (PDPs) for the exact item described by: '
            f'"{normalized_query}".\n'
            f'Return pages where a shopper can BUY the item now (visible price and a Buy/Add to Cart button).'
            f'{brand_hint}{model_hint}{specs_hint}\n\n'
            f'STRICT PRIORITY (in order):\n'
            f'1) Manufacturer PDPs: {manufacturer_domains}\n'
            f'2) Major retailers & marketplaces: {retailer_domains}\n'
            f'3) Other reputable US ecommerce PDPs\n\n'
            f'HARD EXCLUSIONS (title or URL contains any):\n'
            f'support, manual, help, guide, how-to, setup, warranty, service, community, forum, blog, news, press, '
            f'compare, comparison, accessories, case, charger, cable, trade-in, refurbished, renewed, used, open-box, '
            f'auction (unless no new PDPs exist).\n\n'
            f'PAGE TYPE REQUIREMENTS:\n'
            f'- Must be a single product page (not a category/search/listing/PLP).\n'
            f'- Must show a current new price OR a clear purchase path (Add to Cart/Buy).\n'
            f'- Prefer pages that mention SKU/model explicitly and match "{normalized_query}".\n'
            f'- If the query names a model family (e.g., "iPhone 16 Pro Max"), match that family; avoid accessories '
            f'or unrelated variants.\n\n'
            f'REGION & CONDITION:\n'
            f'- US region, English pages, NEW condition. Only fall back to refurbished/used if no new PDPs exist.\n\n'
            f'RESULTS:\n'
            f'- Provide at least 8 PDPs if available; otherwise return the most precise PDPs you can find that satisfy '
            f'the constraints above.\n'
        )
        return objective

    async def _search_products(
        self, 
        intent: SearchIntent, 
        normalized_query: str
    ) -> List[Dict[str, Any]]:
        """
        Perform product search using Parallel AI.
        
        Args:
            intent: Structured search intent
            normalized_query: Normalized search query
            
        Returns:
            List of search result dictionaries
        """
        try:
            objective = self._build_search_objective(normalized_query)
            
            search_result = await self.search_client.search(
                objective=objective,
                processor="base",
                max_results=MAX_SEARCH_RESULTS
            )
            
            results = self.search_client.get_results(search_result)
            
            ecommerce_results = [r for r in results if is_ecommerce_domain(r.get("url", ""))]
            
            if len(ecommerce_results) >= 5:
                return ecommerce_results
            else:
                return results
        
        except Exception as e:
            print(f"Search failed: {str(e)}")
            return []
    
    async def _process_single_product(
        self, 
        result: Dict[str, Any], 
        normalized_query: str
    ) -> Optional[ProductItem]:
        """
        Process a single search result into a ProductItem.
        
        Args:
            result: Search result dictionary
            normalized_query: Normalized search query
            
        Returns:
            ProductItem or None if processing fails
        """
        try:
            url = result.get("url", "")
            excerpts = result.get("excerpts", [])
            
            if not url:
                return None
            
            product_data = await self.extraction_service.extract_product_details(
                url, excerpts, normalized_query
            )
            
            if not product_data:
                return None
            
            review_snippets = product_data.get("review_snippets", [])
            normalized_title = product_data.get("normalized_title", "")
            sentiment_data = await self.review_service.analyze_reviews(
                review_snippets, normalized_title
            )
            
            source = urlparse(url).netloc.replace("www.", "")
            
            images = []
            for img in product_data.get("images", []):
                if isinstance(img, dict):
                    images.append(Image(
                        url=img.get("url", ""),
                        width=img.get("width"),
                        height=img.get("height"),
                        alt=img.get("alt")
                    ))
            
            product = ProductItem(
                title=product_data["title"],
                normalized_title=normalized_title,
                price=product_data.get("price"),
                price_min=product_data.get("price_min"),
                price_max=product_data.get("price_max"),
                currency=product_data.get("currency", "USD"),
                url=url,
                source=source,
                match_score=product_data["match_score"],
                availability=product_data.get("availability"),
                review_sentiment=sentiment_data["review_sentiment"],
                sentiment_score=sentiment_data.get("sentiment_score"),
                fake_review_probability=sentiment_data.get("fake_review_probability"),
                primary_image_url=product_data.get("primary_image_url"),
                images=images,
                sentiment_reason=sentiment_data.get("reason"),
                sentiment_highlights=sentiment_data.get("highlights", []),
                product_type=product_data.get("product_type"),
                category_match=product_data.get("category_match", True),
                is_listing_page=product_data.get("is_listing_page", False)
            )
            
            return product
        except Exception as e:
            print(f"Failed to process product {result.get('url', 'unknown')}: {str(e)}")
            return None
    
    async def search(
        self, 
        intent: SearchIntent, 
        normalized_query: str
    ) -> SearchResponse:
        """
        Execute the complete search pipeline.
        
        Args:
            intent: Structured search intent
            normalized_query: Normalized search query
            
        Returns:
            SearchResponse with ranked product results
        """
        # Step 1: Search for products
        search_results = await self._search_products(intent, normalized_query)
        
        if not search_results:
            return SearchResponse(query=normalized_query, items=[])
        
        # Step 2: Classify and expand listings
        url_queue = []
        
        for result in search_results[:8]:
            url = result.get("url", "")
            if not url:
                continue
            
            html = await fetch_html(url)
            if not html:
                url_queue.append({
                    "url": url, 
                    "page_type": "pdp", 
                    "excerpts": result.get("excerpts", [])
                })
                continue
            
            classification = await classify_page(url, html)
            page_type = classification["type"]
            
            print(f"Classified {url} as {page_type}: {', '.join(classification['reasons'])}")
            
            if page_type == "homepage":
                url_queue.append({
                    "url": url, 
                    "page_type": "homepage", 
                    "excerpts": result.get("excerpts", [])
                })
            elif page_type == "listing":
                expanded_products = await expand_listing(url, html, max_products=MAX_LISTING_EXPANSION)
                for exp_product in expanded_products:
                    url_queue.append({
                        "url": exp_product["url"],
                        "page_type": "pdp",
                        "excerpts": [],
                        "from_listing": url
                    })
                if len(expanded_products) == 0:
                    url_queue.append({
                        "url": url, 
                        "page_type": "listing", 
                        "excerpts": result.get("excerpts", [])
                    })
            else:
                url_queue.append({
                    "url": url, 
                    "page_type": "pdp", 
                    "excerpts": result.get("excerpts", [])
                })
        
        # Step 3: Extract product details in parallel
        tasks = [
            self._process_single_product(item, normalized_query) 
            for item in url_queue[:MAX_PRODUCTS_TO_PROCESS]
        ]
        products_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        products = [p for p in products_results if isinstance(p, ProductItem)]
        
        # Step 4: Filter, deduplicate, and rank
        filtered_products = filter_by_match_score(products)
        deduped_products = deduplicate_products(filtered_products)
        ranked_products = rank_products(deduped_products)
        
        return SearchResponse(
            query=normalized_query, 
            items=ranked_products[:MAX_PRODUCTS_TO_RETURN]
        )

