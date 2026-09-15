"""System constants, category URLs, scoring weights, and rules."""

# Amazon Source URL
MAIN_AMAZON_SOURCE = (
    "https://www.amazon.com/gp/new-releases/automotive/2258019011/ref=zg_bsnr_nav_automotive_1"
)
RV_PARTS_CATEGORY_ID = "2258019011"

# Scoring Weights (Must sum exactly to 1.0 / 100%)
WEIGHT_FACEBOOK_DISCOVERY = 0.20
WEIGHT_RV_FACEBOOK_EXPOSURE = 0.15
WEIGHT_RV_RELEVANCE = 0.15
WEIGHT_NOVELTY_NEWNESS = 0.15
WEIGHT_PROBLEM_SOLVING = 0.10
WEIGHT_VISUAL_WOW = 0.10
WEIGHT_SPACE_CONVENIENCE = 0.05
WEIGHT_IMPULSE_CLICK = 0.05
WEIGHT_AUDIENCE_BREADTH = 0.05

TOTAL_WEIGHT = (
    WEIGHT_FACEBOOK_DISCOVERY
    + WEIGHT_RV_FACEBOOK_EXPOSURE
    + WEIGHT_RV_RELEVANCE
    + WEIGHT_NOVELTY_NEWNESS
    + WEIGHT_PROBLEM_SOLVING
    + WEIGHT_VISUAL_WOW
    + WEIGHT_SPACE_CONVENIENCE
    + WEIGHT_IMPULSE_CLICK
    + WEIGHT_AUDIENCE_BREADTH
)
assert abs(TOTAL_WEIGHT - 1.0) < 1e-9, "Scoring weights must sum to exactly 1.0"

# Scoring Thresholds
WINNER_SCORE_THRESHOLD = 80.0
EXCEPTION_SCORE_MIN = 75.0
EXCEPTION_LABEL = "EXCEPTION — HIGH-POTENTIAL BELOW THRESHOLD"
SHOULD_TEST_SCORE_MIN = 70.0
SHOULD_TEST_LABEL = "SHOULD BE TESTED"

# No Winner Message Template
NO_WINNER_MESSAGE_TEMPLATE = (
    "I reviewed {number} products from the link. None met the hidden-winner criteria today."
)

# Search Variants Required for Public RV Exposure
EXPOSURE_SEARCH_VARIANTS = [
    "{product_name}",
    "{brand} {product_type}",
    "{product_type}",
    "{key_function}",
    "{product_type} RV",
    "{product_type} motorhome",
    "{product_type} camper",
    "{product_type} travel trailer",
    "{product_type} fifth wheel",
]

# Public Signal Disclaimer
PUBLIC_SIGNAL_DISCLAIMER = "(public signal only — private groups not visible)"

# RV Pain Points
RV_PAIN_POINTS = [
    "limited space",
    "temperature",
    "power",
    "charging",
    "storage",
    "organization",
    "cleaning",
    "privacy",
    "comfort",
    "sleeping",
    "cooking",
    "water",
    "condensation",
    "noise",
    "setup",
    "maintenance",
    "outdoor living",
    "convenience",
]

# Price Preference Threshold (USD)
PREFERRED_MAX_PRICE = 100.0

# 25K Winner Benchmark default reference URL
DEFAULT_REFERENCE_WINNER_URL = "https://www.amazon.com/dp/B0EXAMPLE"
