"""Domain enumerations for lifecycle states, research classifications, and verdicts."""

from enum import Enum


class NewnessStatus(str, Enum):
    NEW = "NEW"
    EMERGING = "EMERGING"
    RECENTLY_TRENDING = "RECENTLY TRENDING"
    ESTABLISHED = "ESTABLISHED"
    SATURATED = "SATURATED"
    NOT_VERIFIED = "NOT VERIFIED"


class ExposureLevel(str, Enum):
    VERY_LOW = "VERY LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    SATURATED = "SATURATED"
    UNKNOWN = "UNKNOWN"


class VerificationState(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class TrafficBenchmark(str, Enum):
    UNDER_25 = "<25%"
    P_25_50 = "25–50%"
    P_50_75 = "50–75%"
    P_75_100 = "75–100%"
    P_100_150 = "100–150%"
    OVER_150 = "150%+"


class TrafficConfidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY HIGH"


class AudienceBreadth(str, Enum):
    NARROW = "NARROW"
    MODERATE = "MODERATE"
    BROAD = "BROAD"


class WalmartStatus(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT FOUND"
    URL_NOT_FOUND = "URL NOT FOUND"
    NOT_VERIFIED = "NOT VERIFIED"


class RunStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class RunMode(str, Enum):
    SMOKE = "smoke"
    SMALL = "small"
    FULL = "full"


class ProductLifecycleStage(str, Enum):
    DISCOVERED = "DISCOVERED"
    DEDUPLICATED = "DEDUPLICATED"
    VERIFIED = "VERIFIED"
    EXPOSURE_RESEARCHED = "EXPOSURE_RESEARCHED"
    SCORED = "SCORED"
    WALMART_RESEARCHED = "WALMART_RESEARCHED"
    FINAL_WINNER = "FINAL_WINNER"
    REJECTED = "REJECTED"
    COMMITTED = "COMMITTED"
