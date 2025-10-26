"""Shared dependencies for API endpoints."""
from app.adapters.parallel_chat import ParallelChatClient
from app.adapters.parallel_search import ParallelSearchClient
from app.adapters.parallel_extract import ParallelExtractClient
from app.application.chat_intake_service import ChatIntakeService
from app.application.extraction_service import ExtractionService
from app.application.review_service import ReviewService
from app.application.search_service import SearchService


# Initialize clients
_chat_client = None
_search_client = None
_extract_client = None

# Initialize services
_chat_intake_service = None
_extraction_service = None
_review_service = None
_search_service = None


def get_chat_client() -> ParallelChatClient:
    """Get or create the shared Parallel chat client."""
    global _chat_client
    if _chat_client is None:
        _chat_client = ParallelChatClient()
    return _chat_client


def get_search_client() -> ParallelSearchClient:
    """Get or create the shared Parallel search client."""
    global _search_client
    if _search_client is None:
        _search_client = ParallelSearchClient()
    return _search_client


def get_extract_client() -> ParallelExtractClient:
    """Get or create the shared Parallel extract client."""
    global _extract_client
    if _extract_client is None:
        _extract_client = ParallelExtractClient()
    return _extract_client


def get_chat_intake_service() -> ChatIntakeService:
    """Get or create the shared chat intake service."""
    global _chat_intake_service
    if _chat_intake_service is None:
        _chat_intake_service = ChatIntakeService(get_chat_client())
    return _chat_intake_service


def get_extraction_service() -> ExtractionService:
    """Get or create the shared extraction service."""
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = ExtractionService(
            get_chat_client(),
            get_extract_client()
        )
    return _extraction_service


def get_review_service() -> ReviewService:
    """Get or create the shared review service."""
    global _review_service
    if _review_service is None:
        _review_service = ReviewService(get_chat_client())
    return _review_service


def get_search_service() -> SearchService:
    """Get or create the shared search service."""
    global _search_service
    if _search_service is None:
        _search_service = SearchService(
            get_search_client(),
            get_extraction_service(),
            get_review_service()
        )
    return _search_service



