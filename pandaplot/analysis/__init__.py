"""
Analysis module for mathematical operations on data.
"""

from .analysis_engine import AnalysisEngine
from .analysis_types import AnalysisParameters, AnalysisResult, AnalysisType, DerivativeMethod, InterpolationMethod, SmoothingMethod
from .stats_engine import StatsEngine
from .stats_types import STAT_TESTS, Alternative, InputMode, StatTestInfo, StatTestResult, StatTestType
from .signal.signal_engine import SignalEngine
from .signal.signal_types import SIGNAL_ANALYSES, SignalAnalysisType, SignalAnalysisResult

__all__ = [
    "AnalysisEngine",
    "AnalysisType",
    "AnalysisResult",
    "AnalysisParameters",
    "DerivativeMethod",
    "SmoothingMethod",
    "InterpolationMethod",
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
    "SIGNAL_ANALYSES"
]
