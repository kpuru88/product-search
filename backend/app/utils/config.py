"""Application configuration and constants."""
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
PARALLEL_API_KEY = os.getenv("PARALLEL_API_KEY")
if not PARALLEL_API_KEY:
    raise ValueError("PARALLEL_API_KEY environment variable is required")

# API Base URLs
PARALLEL_BASE_URL = "https://api.parallel.ai"

# Timeouts (seconds)
HTTP_TIMEOUT = 15.0
API_TIMEOUT = 30.0
IMAGE_TIMEOUT = 4.0
EXTRACT_TIMEOUT = 10.0

# Domain Classifications
MANUFACTURER_DOMAINS = [
    "apple.com", "samsung.com", "sony.com", "lg.com", "dell.com", 
    "hp.com", "microsoft.com", "google.com", "lenovo.com", "asus.com"
]

MAJOR_RETAILERS = [
    "amazon.com", "bestbuy.com", "walmart.com", "target.com", 
    "homedepot.com", "wayfair.com", "ikea.com", "crateandbarrel.com", 
    "lowes.com", "overstock.com", "ebay.com", "etsy.com", 
    "costco.com", "macys.com"
]

MARKETPLACES = [
    "ebay.com", "etsy.com", "mercari.com", "poshmark.com", "offerup.com"
]

# Search Configuration
MAX_SEARCH_RESULTS = 10
MAX_PRODUCTS_TO_PROCESS = 10
MAX_PRODUCTS_TO_RETURN = 6
MIN_MATCH_SCORE = 0.35
MAX_LISTING_EXPANSION = 5

# Retry Configuration
MAX_RETRIES = 2
RETRY_BASE_WAIT = 1

