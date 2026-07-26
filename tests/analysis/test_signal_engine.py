""" Tests for SignalEngine. """

import numpy as np
import pandas as pd
import pytest

from pandaplot.analysis import (
    SignalEngine,
    SignalAnalysisType,
)


def create_test_signal():
    """Create a simple sine wave signal."""

    sampling_rate = 1000

    t = np.linspace(
        0,
        1,
        sampling_rate,
        endpoint=False,
    )

    signal = (
        np.sin(2 * np.pi * 50 * t)
        +
        0.5 * np.sin(2 * np.pi * 120 * t)
    )

    return (
        pd.Series(
            signal,
            name="test_signal",
        ),
        sampling_rate,
    )


def test_fft_analysis():
    series, fs = create_test_signal()

    result = SignalEngine.run_analysis(
        SignalAnalysisType.FFT,
        series,
        sampling_rate=fs,
    )

    assert result.analysis_type == SignalAnalysisType.FFT

    assert not result.data.empty

    assert "Frequency (Hz)" in result.data.columns

    assert "Amplitude" in result.data.columns


def test_fft_detects_dominant_frequency():
    series, fs = create_test_signal()

    result = SignalEngine.run_analysis(
        SignalAnalysisType.FFT,
        series,
        sampling_rate=fs,
    )

    dominant = result.metadata["dominant_frequencies"]

    frequencies = [
        freq
        for freq, amplitude in dominant
    ]

    assert any(
        abs(freq - 50) < 1
        for freq in frequencies
    )

    assert any(
        abs(freq - 120) < 1
        for freq in frequencies
    )


def test_fft_metadata():
    series, fs = create_test_signal()

    result = SignalEngine.run_analysis(
        SignalAnalysisType.FFT,
        series,
        sampling_rate=fs,
    )

    assert result.metadata["sampling_rate"] == fs

    assert "signal_length" in result.metadata

    assert "nfft" in result.metadata

    assert "window" in result.metadata

    assert "dominant_frequencies" in result.metadata


def test_fft_invalid_sampling_rate():

    series, _ = create_test_signal()

    with pytest.raises(ValueError):

        SignalEngine.run_analysis(
            SignalAnalysisType.FFT,
            series,
            sampling_rate=0,
        )


def test_signal_requires_samples():

    with pytest.raises(ValueError):

        SignalEngine.run_analysis(
            SignalAnalysisType.FFT,
            pd.Series([1]),
            sampling_rate=1000,
        )


def test_stft_analysis():
    series, fs = create_test_signal()

    result = SignalEngine.run_analysis(
        SignalAnalysisType.STFT,
        series,
        sampling_rate=fs,
    )

    assert result.analysis_type == SignalAnalysisType.STFT

    assert not result.data.empty


def test_psd_analysis():
    series, fs = create_test_signal()

    result = SignalEngine.run_analysis(
        SignalAnalysisType.PSD,
        series,
        sampling_rate=fs,
    )

    assert result.analysis_type == SignalAnalysisType.PSD

    assert not result.data.empty


def test_autocorrelation_analysis():
    series, _ = create_test_signal()

    result = SignalEngine.run_analysis(
        SignalAnalysisType.AUTOCORRELATION,
        series,
    )

    assert result.analysis_type == SignalAnalysisType.AUTOCORRELATION

    assert "Lag" in result.data.columns

    assert "Autocorrelation" in result.data.columns


def test_peak_detection():
    series, _ = create_test_signal()

    result = SignalEngine.run_analysis(
        SignalAnalysisType.PEAKS,
        series,
        prominence=0.1,
    )

    assert result.analysis_type == SignalAnalysisType.PEAKS

    assert "Index" in result.data.columns

    assert "Value" in result.data.columns