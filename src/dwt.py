"""
Smoothing of signals via wavelet reconstruction
"""

from dataclasses import dataclass
import logging
import sys
from typing import Dict, Generator, List, Tuple, Type, Union

import matplotlib.pyplot as plt
import matplotlib.figure
import numpy as np
import numpy.typing as npt
import pywt

from src.helpers import define_other_module_log_level
from src import retrieve_data

# * Logging settings
logger = logging.getLogger(__name__)
define_other_module_log_level("debug")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))


def trim_signal(
    original_signal: npt.NDArray, reconstructed: npt.NDArray
) -> npt.NDArray:
    """Removes first or last observation for odd-numbered datasets"""
    ## Time series with uneven result in mismatched lengths with the reconstructed
    ## signal, so we remove a value from the approximated signal
    if len(reconstructed) % 2 != 0:
        trim = input(
            f"""Odd number of observations dectected (Length: {len(original_signal)}).
             Trim data? (y/n)"""
        )
        while trim not in ["y", "n"]:
            trim = input("Please respond with either 'y' or 'n'")
        if trim == "y":
            trim2 = input("Trim beginning or end of time series? (b/e)")
            while trim2 not in ["b", "e"]:
                trim2 = input("Please respond with either 'b' or 'e'")
            if trim2 == "b":
                return reconstructed[1:]
            return reconstructed[1:]
    else:
        return reconstructed[:]


def run_dwt(
    signal: npt.NDArray, wavelet: str, levels: int = None
) -> tuple[int, npt.NDArray]:
    """Generate levels and coefficients from discrete wavelet transform with
    given wavelet function"""
    ## Define the wavelet type
    w = pywt.Wavelet(wavelet)
    ## Choose the maximum decomposition level
    if levels is None:
        dwt_levels = pywt.dwt_max_level(data_len=len(signal), filter_len=w.dec_len)
        print(
            f"Max decomposition level of {dwt_levels} for time series length of {len(signal)}"
        )
    else:
        dwt_levels = levels
        print(f"DWT with {dwt_levels} levels as defined in levels={levels}")
    dwt_coeffs = pywt.wavedec(signal, wavelet, level=dwt_levels)
    return dwt_levels, dwt_coeffs


def smooth_signal(
    signal: npt.NDArray, wavelet: str, levels: int = None
) -> Tuple[dict, int]:
    """Generate smoothed signals based off wavelet coefficients for each pre-defined level"""
    ## Initialize dict for reconstructed signals
    signals_dict = {}

    if levels is None:
        dwt_levels, coeffs = run_dwt(signal, wavelet)
    else:
        dwt_levels, coeffs = run_dwt(signal, wavelet, levels)

    ## Loop through levels and remove detail level component(s)
    # ! Note: signal_dict[l] provides the signal with levels <= l removed
    for l in range(dwt_levels, 0, -1):
        print(f"s_{l} stored with key {l}")
        smooth_coeffs = coeffs.copy()
        signals_dict[l] = {}
        ## Set remaining detail coefficients to zero
        for coeff in range(1, l + 1):
            smooth_coeffs[-1 * coeff] = np.zeros_like(smooth_coeffs[-1 * coeff])
        signals_dict[l]["coeffs"] = smooth_coeffs
        # Reconstruct the signal using only the approximation coefficients
        reconst = pywt.waverec(smooth_coeffs, wavelet)
        signals_dict[l]["signal"] = trim_signal(signal, reconst)

    return signals_dict, dwt_levels


def reconstruct_signal_component(
    signal_coeffs: list, wavelet: str, level: int
) -> tuple[dict, int]:
    """Reconstruct individual component"""
    component_coeffs = signal_coeffs.copy()
    for l in range(len(signal_coeffs)):
        if l == level:
            component_coeffs[l] = component_coeffs[l]
        else:
            component_coeffs[l] = np.zeros_like(component_coeffs[l])
    return pywt.waverec(component_coeffs, wavelet)


def plot_smoothing(
    smooth_signals: dict,
    x: npt.NDArray,
    y: npt.NDArray,
    name: str,
    ascending: bool = False,
    **kwargs,
) -> matplotlib.figure.Figure:
    """Graph series of smoothed signals with original signal"""
    fig = plt.figure()
    # * Loop through levels and add detail level components
    if ascending:
        order = reversed(list(smooth_signals.items()))
    else:
        order = list(smooth_signals.items())
    for i, (level, signal) in enumerate(order, 1):
        smooth_level = len(smooth_signals) - level
        ## Subplot for each smooth signal
        plt.subplot(len(smooth_signals), 1, i)
        plt.plot(x, y, label=name.title())
        plt.plot(x, signal["signal"])
        plt.xlabel("Year")
        plt.grid()
        plt.title(rf"Approximation: $S_{{j-{smooth_level}}}$")
        plt.legend()
    return fig


def main() -> None:
    """Run script"""
    # ## Matplotlib Settings
    # small_size = 8
    # medium_size = 10
    # bigger_size = 12
    # plt.rc("font", size=bigger_size)  # controls default text sizes
    # plt.rc("axes", titlesize=bigger_size)  # fontsize of the axes title
    # plt.rc("axes", labelsize=medium_size)  # fontsize of the x and y labels
    # plt.rc("xtick", labelsize=small_size)  # fontsize of the tick labels
    # plt.rc("ytick", labelsize=small_size)  # fontsize of the tick labels
    # plt.rc("legend", fontsize=small_size)  # legend fontsize
    # plt.rc("figure", titlesize=bigger_size)  # fontsize of the figure title

    raw_data = retrieve_data.get_insee_data("000857180")
    _, t, y = retrieve_data.clean_insee_data(raw_data)

    ## Define the wavelet type
    wavelet_type = "sym12"
    smooth_signals, _ = smooth_signal(y, wavelet_type)

    ## Input name of time series
    print("Enter name of time series (to be included in plot)")
    name = input()

    fig = plot_smoothing(smooth_signals, x=t, y=y, name=name, figsize=(10, 10))

    plt.xlabel("Year")
    plt.ylabel(f"{name.capitalize()}")
    fig.suptitle(f"Wavelet smoothing of {name.lower()}")
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
