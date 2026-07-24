""" Fast Fourier Transform (FFT) signal analysis. """

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..signal_types import SignalAnalysisResult, SignalAnalysisType


def run(
    column: pd.Series,
    sampling_rate: float,
    nfft: int | None = None,
    window: str = "hann",
    **_: Any,
) -> SignalAnalysisResult:
    """ Compute the one-sided Fast Fourier Transform of a signal. """

    if sampling_rate <= 0:
        raise ValueError("Sampling rate must be greater than zero.")

    signal = pd.to_numeric(column, errors="coerce").dropna().to_numpy(dtype=float)
    signal = _apply_window(signal, window)

    if signal.size < 2:
        raise ValueError("Signal must contain at least two valid samples.")

    if nfft is None:
        nfft = signal.size

    if nfft < signal.size:
        raise ValueError("NFFT must be greater than or equal to the signal length.")

    # Remove DC component
    signal = signal - np.mean(signal)

    # FFT
    spectrum = np.fft.rfft(signal, n=nfft)
    frequencies = np.fft.rfftfreq(nfft, d=1.0 / sampling_rate)
    amplitude = np.abs(spectrum) / signal.size

    result_df = pd.DataFrame(
        {
            "Frequency (Hz)": frequencies,
            "Amplitude": amplitude,
        }
    )

    return SignalAnalysisResult(
        analysis_type=SignalAnalysisType.FFT,
        analysis_name="Fast Fourier Transform (FFT)",
        source_columns=[str(column.name)],
        data=result_df,
        metadata={
            "sampling_rate": sampling_rate,
            "signal_length": signal.size,
            "nfft": nfft,
            "window": window,
        },
    )

def _apply_window(signal: np.ndarray, window: str) -> np.ndarray:
    """
    Apply selected window function before FFT.
    """

    if window == "hann":
        w = np.hanning(len(signal))

    elif window == "hamming":
        w = np.hamming(len(signal))

    elif window == "blackman":
        w = np.blackman(len(signal))

    elif window == "rectangular":
        w = np.ones(len(signal))

    else:
        raise ValueError(
            f"Unsupported window '{window}'. "
            "Choose: hann, hamming, blackman, rectangular."
        )

    return signal * w