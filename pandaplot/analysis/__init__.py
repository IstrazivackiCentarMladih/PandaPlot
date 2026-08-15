"""
Analysis module for mathematical operations on data.
"""

from .analysis_engine import AnalysisEngine
from .analysis_types import AnalysisParameters, AnalysisResult, AnalysisType, DerivativeMethod, InterpolationMethod, SmoothingMethod
from .descriptive_engine import DescriptiveStatsEngine
from .descriptive_types import DESCRIPTIVE_STATS, DescriptiveStatsResult
from .preprocessing_engine import PreprocessingEngine
from .preprocessing_types import (
    PREPROCESSING_METHODS,
    PreprocessingInfo,
    PreprocessingMethod,
    PreprocessingResult,
)
from .signal.signal_engine import SignalEngine
from .signal.signal_types import SIGNAL_ANALYSES, SignalAnalysisResult, SignalAnalysisType
from .stats_engine import StatsEngine
from .stats_types import STAT_TESTS, Alternative, InputMode, StatTestInfo, StatTestResult, StatTestType

__all__ = [
    "AnalysisEngine",
    "AnalysisType",
    "AnalysisResult",
    "AnalysisParameters",
    "DerivativeMethod",
    "SmoothingMethod",
    "InterpolationMethod",
    "DescriptiveStatsEngine",
    "DescriptiveStatsResult",
    "DESCRIPTIVE_STATS",
    "StatsEngine",
    "StatTestType",
    "StatTestInfo",
    "StatTestResult",
    "InputMode",
    "Alternative",
    "STAT_TESTS",
    "SignalEngine",
    "SignalAnalysisType",
    "SignalAnalysisResult",
    "SIGNAL_ANALYSES",
    "PreprocessingEngine",
    "PreprocessingMethod",
    "PreprocessingInfo",
    "PreprocessingResult",
    "PREPROCESSING_METHODS",
]
