"""Product name normalization utilities."""
import json
from typing import Dict


async def normalize_name(text: str, chat_client) -> Dict[str, any]:
    """
    Normalize a product name to a compact, standardized form.
    
    Args:
        text: Raw product name to normalize
        chat_client: Parallel chat client for normalization
        
    Returns:
        Dictionary with normalized_query, keywords, and keep_model
    """
    try:
        response = await chat_client.create_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You normalize retail product names. Output "
                        "compact, literal phrases that capture the core "
                        "item. Keep color and one or two critical "
                        "qualifiers (size, model family). Drop pack "
                        "counts, marketing adjectives, and usage "
                        "contexts. Max ~3 tokens (2-4 words). Return "
                        "JSON only per schema."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Normalize this product name: {text}\n\n"
                        "Return ONLY JSON with these fields:\n"
                        "- normalized_query: string "
                        "(e.g., \"black accent chair\")\n"
                        "- keywords: array of strings "
                        "(e.g., [\"accent chair\", \"black\", \"vanity\"])\n"
                        "- keep_model: boolean "
                        "(true if a model id must be preserved)\n\n"
                        "Examples:\n"
                        "\"Yaheetech Black Accent Chairs Set of 2, "
                        "Cozy Velvet Barrel Chair...\" → "
                        "{{\"normalized_query\": \"black accent chair\", "
                        "\"keywords\": [\"accent chair\", \"black\", "
                        "\"vanity\"], \"keep_model\": false}}\n"
                        "\"Apple iPhone 16 Pro Max 256GB "
                        "(Model XYZ123)\" → "
                        "{{\"normalized_query\": \"iPhone 16 Pro Max\", "
                        "\"keywords\": [\"iPhone\", \"16 Pro Max\"], "
                        "\"keep_model\": true}}\n"
                        "\"Samsung 75-inch QLED 4K Smart TV\" → "
                        "{{\"normalized_query\": \"75-inch QLED TV\", "
                        "\"keywords\": [\"QLED TV\", \"75-inch\", "
                        "\"Samsung\"], \"keep_model\": false}}\n\n"
                        "Return ONLY JSON, no other text."
                    )
                }
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content.strip()
        
        try:
            normalized_data = json.loads(content)
            return normalized_data
        except json.JSONDecodeError:
            return {
                "normalized_query": text,
                "keywords": [text],
                "keep_model": False
            }
    
    except Exception as e:
        print(f"Normalization failed: {str(e)}")
        return {
            "normalized_query": text,
            "keywords": [text],
            "keep_model": False
        }

