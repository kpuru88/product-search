"""Review sentiment analysis service."""
import json
from typing import List, Dict, Any
from app.adapters.parallel_chat import ParallelChatClient


class ReviewService:
    """Service for analyzing product reviews and sentiment."""
    
    def __init__(self, chat_client: ParallelChatClient):
        """
        Initialize the review service.
        
        Args:
            chat_client: Parallel chat client for LLM calls
        """
        self.chat_client = chat_client
    
    def _build_sentiment_prompt(
        self, 
        review_snippets: List[str], 
        normalized_title: str = ""
    ) -> list:
        """
        Build prompt for sentiment analysis of review snippets.
        
        Args:
            review_snippets: List of review text snippets
            normalized_title: Normalized product title for context
            
        Returns:
            List of message dictionaries for the LLM
        """
        product_context = f"Product: {normalized_title}\n" if normalized_title else ""
        
        return [
            {
                "role": "system",
                "content": "You evaluate product reviews and exclude likely fake content before summarizing sentiment. Provide detailed reasoning and evidence."
            },
            {
                "role": "user",
                "content": f"""{product_context}SNIPPETS: {json.dumps(review_snippets[:10])}

Analyze these review snippets. First, label each snippet as positive/neutral/negative and identify fake ones (repetitive, templated, generic, bursty patterns).

Filter out snippets with fake_review_probability >0.7. Then compute sentiment from the remaining snippets.

Return ONLY JSON with these fields:
- review_sentiment: "positive" or "neutral" or "negative"
- sentiment_score: number 0-1 (based on proportion of positive vs negative in kept snippets, NOT a default 0.85)
- fake_review_probability: number 0-1 (aggregate of kept snippets, e.g., 95th percentile)
- reason: string (1-3 sentences explaining WHY this sentiment, citing specific themes)
- highlights: array of 3-5 strings (concise points extracted from kept snippets, e.g., "Comfortable seating", "Easy assembly", "Great value")

Example:
{{"review_sentiment": "positive", "sentiment_score": 0.78, "fake_review_probability": 0.2, "reason": "Most reviews praise the chair's comfort and sturdy build quality, though some mention minor assembly issues.", "highlights": ["Very comfortable padding", "Sturdy metal frame", "Easy to assemble", "Good value for price", "Stylish design"]}}

Return ONLY JSON, no other text."""
            }
        ]
    
    async def analyze_reviews(
        self, 
        review_snippets: List[str], 
        normalized_title: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze review snippets for sentiment and fake review detection.
        
        Args:
            review_snippets: List of review text snippets
            normalized_title: Normalized product title for context
            
        Returns:
            Dictionary with review_sentiment, sentiment_score, fake_review_probability,
            reason, and highlights
        """
        if not review_snippets or len(review_snippets) == 0:
            return {
                "review_sentiment": "unknown",
                "sentiment_score": None,
                "fake_review_probability": None,
                "sentiment_reason": None,
                "sentiment_highlights": []
            }
        
        try:
            messages = self._build_sentiment_prompt(review_snippets, normalized_title)
            
            response = await self.chat_client.create_completion(
                messages=messages,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            
            try:
                sentiment_data = json.loads(content)
                if "reason" not in sentiment_data:
                    sentiment_data["reason"] = None
                if "highlights" not in sentiment_data:
                    sentiment_data["highlights"] = []
                return sentiment_data
            except json.JSONDecodeError:
                return {
                    "review_sentiment": "unknown",
                    "sentiment_score": None,
                    "fake_review_probability": None,
                    "sentiment_reason": None,
                    "sentiment_highlights": []
                }
        
        except Exception as e:
            print(f"Sentiment analysis failed: {str(e)}")
            return {
                "review_sentiment": "unknown",
                "sentiment_score": None,
                "fake_review_probability": None,
                "sentiment_reason": None,
                "sentiment_highlights": []
            }



