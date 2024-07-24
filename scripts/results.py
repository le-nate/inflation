"""Plot results from wavelet transformations"""

# %%
import logging
import sys
from typing import Any, Dict, List, Tuple, Type

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pywt
import pycwt as wavelet
import seaborn as sns

from constants import ids
from src import (
    cwt,
    descriptive_stats,
    dwt,
    process_camme,
    phase_diff_key,
    phase_diff_sines,
    regression,
    xwt,
)
from src.utils import helpers, wavelet_helpers
from src.utils.logging_helpers import define_other_module_log_level
from src import retrieve_data

# * Logging settings
logger = logging.getLogger(__name__)
define_other_module_log_level("Warning")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

# * Define constant currency years
CONSTANT_DOLLAR_DATE = "2017-12-01"

# * Define statistical tests to run on data
STATISTICS_TESTS = [
    "count",
    "mean",
    "std",
    "skewness",
    "kurtosis",
    "Jarque-Bera",
    "Shapiro-Wilk",
    "Ljung-Box",
]
HYPOTHESIS_THRESHOLD = [0.1, 0.05, 0.001]

# * Define DWT configs
DWT_MOTHER = "db4"
dwt_mother_wavelet = pywt.Wavelet(DWT_MOTHER)

# * Define CWT configs
CWT_MOTHER = wavelet.Morlet(f0=6)
NORMALIZE = True  # Define normalization
DT = 1 / 12  # In years
S0 = 2 * DT  # Starting scale
DJ = 1 / 12  # Twelve sub-octaves per octaves
J = 7 / DJ  # Seven powers of two with DJ sub-octaves
LEVELS = [0.0625, 0.125, 0.25, 0.5, 1, 2, 4, 8, 16]  # Period scale is logarithmic
CWT_FIG_PROPS = {"figsize": (20, 10), "dpi": 72}
CWT_PLOT_PROPS = {
    "cmap": "jet",
    "sig_colors": "k",
    "sig_linewidths": 2,
    "coi_color": "k",
    "coi_alpha": 0.3,
    "coi_hatch": "--",
}

# * Define XWT configs
XWT_DT = 1 / 12  # Delta t
XWT_DJ = 1 / 8  # Delta j
XWT_S0 = 2 * DT  # Initial scale
XWT_MOTHER = "morlet"  # Morlet wavelet with :math:`\omega_0=6`.
XWT_MOTHER_DICT = {
    "morlet": wavelet.Morlet(6),
    "paul": wavelet.Paul(),
    "DOG": wavelet.DOG(),
    "mexicanhat": wavelet.MexicanHat(),
}

XWT_PLOT_PROPS = {
    "cmap": "jet",
    "sig_colors": "k",
    "sig_linewidths": 2,
    "coi_color": "k",
    "coi_alpha": 0.3,
    "coi_hatch": "--",
    "phase_diff_units": "width",
    "phase_diff_angles": "uv",
    "phase_diff_pivot": "mid",
    "phase_diff_linewidth": 0.5,
    "phase_diff_edgecolor": "k",
    "phase_diff_alpha": 0.7,
}


# %%
def create_dwt_dict(
    data_for_dwt: pd.DataFrame,
    measures_list: List[str],
    **kwargs,
) -> Dict[str, Type[Any]]:
    """Create dict of discrete wavelet transform objects from DataFrame"""
    transform_dict = {}
    logger.debug("df shape: %s", data_for_dwt.shape)
    for measure in measures_list:
        transform_dict[measure] = dwt.DataForDWT(
            y_values=data_for_dwt[measure].to_numpy(), **kwargs
        )
    return transform_dict


def create_cwt_dict(
    data_for_cwt: pd.DataFrame,
    measures_list: List[str],
    **kwargs,
) -> Dict[str, Type[Any]]:
    """Create dict of continuous wavelet transform objects from DataFrame"""
    transform_dict = {}
    for measure in measures_list:
        t_values = data_for_cwt[data_for_cwt[measure].notna()][ids.DATE].to_numpy()
        transform_dict[measure] = cwt.DataForCWT(
            t_values=t_values,
            y_values=data_for_cwt[data_for_cwt[measure].notna()][measure].to_numpy(),
            **kwargs,
        )
    return transform_dict


def create_xwt_dict(
    data_for_xwt: pd.DataFrame, xwt_list: List[Tuple[str, str]], **kwargs
) -> Dict[Tuple[str, str], Type[xwt.DataForXWT]]:
    """Create dict of cross-wavelet transform objects from DataFrame"""
    transform_dict = {}
    for comparison in xwt_list:
        y1 = data_for_xwt.dropna()[comparison[0]].to_numpy()
        y2 = data_for_xwt.dropna()[comparison[1]].to_numpy()
        y1 = wavelet_helpers.standardize_series(y1, **kwargs)
        y2 = wavelet_helpers.standardize_series(y2, **kwargs)

        transform_dict[comparison] = xwt.DataForXWT(
            y1_values=y1,
            y2_values=y2,
            mother_wavelet=XWT_MOTHER_DICT[XWT_MOTHER],
            delta_t=XWT_DT,
            delta_j=XWT_DJ,
            initial_scale=XWT_S0,
            levels=LEVELS,
        )
    return transform_dict


def create_dwt_results_dict(
    dwt_data_dict: Dict[str, Type[dwt.DataForDWT]], measures_list: List[str], **kwargs
) -> Dict[str, Type[dwt.ResultsFromDWT]]:
    """Create dict of DWT results instances"""
    results_dict = {}
    for measure in measures_list:
        results_dict[measure] = dwt.run_dwt(dwt_data_dict[measure], **kwargs)
    return results_dict


def create_cwt_results_dict(
    cwt_data_dict: Dict[str, Type[cwt.DataForCWT]], measures_list: List[str], **kwargs
) -> Dict[str, Type[cwt.ResultsFromCWT]]:
    """Create dict of CWT results instances"""
    results_dict = {}
    for measure in measures_list:
        results_dict[measure] = cwt.run_cwt(cwt_data_dict[measure], **kwargs)
    return results_dict


def create_xwt_results_dict(
    xwt_data_dict: Dict[str, Type[xwt.DataForXWT]],
    xwt_list: List[Tuple[str, str]],
    **kwargs,
) -> Type[xwt.ResultsFromXWT]:
    """Create dict of XWT results instances"""
    results_dict = {}
    for comparison in xwt_list:
        results_dict[comparison] = xwt.run_xwt(xwt_data_dict[comparison], **kwargs)
    return results_dict


# %% [markdown]
## Pre-process data
# US data

#  %%
# * CPI
raw_data = retrieve_data.get_fed_data(ids.US_CPI)
cpi, _, _ = retrieve_data.clean_fed_data(raw_data)
cpi.rename(columns={"value": ids.CPI}, inplace=True)

# * Inflation rate
raw_data = retrieve_data.get_fed_data(ids.US_CPI, units="pc1", freq="m")
measured_inf, _, _ = retrieve_data.clean_fed_data(raw_data)
measured_inf.rename(columns={"value": ids.INFLATION}, inplace=True)

# * Inflation expectations
raw_data = retrieve_data.get_fed_data(ids.US_INF_EXPECTATIONS)
inf_exp, _, _ = retrieve_data.clean_fed_data(raw_data)
inf_exp.rename(columns={"value": ids.EXPECTATIONS}, inplace=True)

# * Non-durables consumption, monthly
raw_data = retrieve_data.get_fed_data(ids.US_NONDURABLES_CONSUMPTION)
nondur_consump, _, _ = retrieve_data.clean_fed_data(raw_data)
nondur_consump.rename(columns={"value": ids.NONDURABLES}, inplace=True)

# * Durables consumption, monthly
raw_data = retrieve_data.get_fed_data(ids.US_DURABLES_CONSUMPTION)
dur_consump, _, _ = retrieve_data.clean_fed_data(raw_data)
dur_consump.rename(columns={"value": ids.DURABLES}, inplace=True)

# * Non-durables consumption change, monthly
raw_data = retrieve_data.get_fed_data(
    ids.US_NONDURABLES_CONSUMPTION, units="pc1", freq="m"
)
nondur_consump_chg, _, _ = retrieve_data.clean_fed_data(raw_data)
nondur_consump_chg.rename(columns={"value": ids.NONDURABLES_CHG}, inplace=True)

# * Durables consumption change, monthly
raw_data = retrieve_data.get_fed_data(
    ids.US_DURABLES_CONSUMPTION, units="pc1", freq="m"
)
dur_consump_chg, _, _ = retrieve_data.clean_fed_data(raw_data)
dur_consump_chg.rename(columns={"value": ids.DURABLES_CHG}, inplace=True)

# * Personal savings
raw_data = retrieve_data.get_fed_data(ids.US_SAVINGS)
save, _, _ = retrieve_data.clean_fed_data(raw_data)
save.rename(columns={"value": ids.SAVINGS}, inplace=True)

# * Personal savings change
raw_data = retrieve_data.get_fed_data(ids.US_SAVINGS, units="pc1", freq="m")
save_chg, _, _ = retrieve_data.clean_fed_data(raw_data)
save_chg.rename(columns={"value": ids.SAVINGS_CHG}, inplace=True)

# * Personal savings rate
raw_data = retrieve_data.get_fed_data(ids.US_SAVINGS_RATE)
save_rate, _, _ = retrieve_data.clean_fed_data(raw_data)
save_rate.rename(columns={"value": ids.SAVINGS_RATE}, inplace=True)

# * Merge dataframes to align dates and remove extras
dataframes = [
    cpi,
    measured_inf,
    inf_exp,
    nondur_consump,
    nondur_consump_chg,
    dur_consump,
    dur_consump_chg,
    save,
    save_chg,
    save_rate,
]
us_data = helpers.combine_series(dataframes, on=[ids.DATE], how="left")
# us_data = cpi.merge(measured_inf, how="left")
# us_data = us_data.merge(inf_exp, how="left")
# us_data = us_data.merge(nondur_consump, how="left")
# us_data = us_data.merge(dur_consump, how="left")
# us_data = us_data.merge(save, how="left")
# us_data = us_data.merge(save_rate, how="left")

# # * Remove rows without data for all measures
# us_data.dropna(inplace=True)

# * Add real value columns
logger.info(
    "Using constant dollars from %s, CPI: %s",
    CONSTANT_DOLLAR_DATE,
    us_data[us_data[ids.DATE] == pd.Timestamp(CONSTANT_DOLLAR_DATE)][ids.CPI].iat[0],
)
us_data = helpers.add_real_value_columns(
    data=us_data,
    nominal_columns=[ids.NONDURABLES, ids.DURABLES, ids.SAVINGS],
    cpi_column=ids.CPI,
    constant_date=CONSTANT_DOLLAR_DATE,
)
us_data = helpers.calculate_diff_in_log(
    data=us_data,
    columns=[
        ids.CPI,
        ids.EXPECTATIONS,
        ids.NONDURABLES,
        ids.DURABLES,
        ids.SAVINGS,
        ids.REAL_NONDURABLES,
        ids.REAL_DURABLES,
        ids.REAL_SAVINGS,
    ],
)

usa_sliced = pd.concat([us_data.head(), us_data.tail()])
usa_sliced

# %% [markdown]
# French data
# %%
# * CPI
raw_data = retrieve_data.get_fed_data(ids.FR_CPI)
fr_cpi, _, _ = retrieve_data.clean_fed_data(raw_data)
fr_cpi.rename(columns={"value": ids.CPI}, inplace=True)

# * Measured inflation
raw_data = retrieve_data.get_fed_data(ids.FR_CPI, units="pc1", freq="m")
fr_inf, _, _ = retrieve_data.clean_fed_data(raw_data)
fr_inf.rename(columns={"value": ids.INFLATION}, inplace=True)

# * Inflation expectations
_, fr_exp = process_camme.preprocess(process_camme.camme_dir)
## Remove random lines with month as letter
fr_exp = fr_exp[fr_exp["month"].apply(isinstance, args=(int,))]
## Create date column
fr_exp[ids.DATE] = pd.to_datetime(fr_exp[["year", "month"]].assign(DAY=1))
## Use just quantitative expectations and date
fr_exp = fr_exp[[ids.DATE, "inf_exp_val_inc", "inf_exp_val_dec"]]
## Convert to negative for averaging
fr_exp["inf_exp_val_dec"] = fr_exp["inf_exp_val_dec"] * -1
## Melt then pivot to get average expectation for each month
fr_exp_melt = pd.melt(fr_exp, [ids.DATE])
fr_exp = pd.pivot_table(fr_exp_melt, index=ids.DATE, aggfunc="mean")
fr_exp.rename(columns={"value": ids.EXPECTATIONS}, inplace=True)

# * Food consumption
raw_data = retrieve_data.get_insee_data(ids.FR_FOOD_CONSUMPTION)
fr_food_cons, _, _ = retrieve_data.clean_insee_data(raw_data)
fr_food_cons.rename(columns={"value": "food"}, inplace=True)

# * Goods consumption
raw_data = retrieve_data.get_insee_data(ids.FR_GOODS_CONSUMPTION)
fr_goods_cons, _, _ = retrieve_data.clean_insee_data(raw_data)
fr_goods_cons.rename(columns={"value": "goods"}, inplace=True)

# * Durables consumption
raw_data = retrieve_data.get_insee_data(ids.FR_DURABLES_CONSUMPTION)
fr_dur_cons, _, _ = retrieve_data.clean_insee_data(raw_data)
fr_dur_cons.rename(columns={"value": "durables"}, inplace=True)

# %%
dataframes = [fr_cpi, fr_inf, fr_exp, fr_food_cons, fr_goods_cons, fr_dur_cons]
fr_data = helpers.combine_series(dataframes, on=[ids.DATE], how="left")

fr_sliced = pd.concat([fr_data.head(), fr_data.tail()])
fr_sliced

# %%
# * Create measured inflation dataframe
inf_data = pd.merge(
    us_data[[ids.DATE, ids.INFLATION, ids.EXPECTATIONS]],
    fr_data[[ids.DATE, ids.INFLATION, ids.EXPECTATIONS]],
    on=ids.DATE,
    suffixes=("_us", "_fr"),
)

inf_data.columns = [
    "Date",
    "Measured (US)",
    "Expectations (US)",
    "Measured (France)",
    "Expectations (France)",
]

# %%
inf_melt = pd.melt(inf_data, ["Date"])
inf_melt.rename(columns={"value": "Measured (%)"}, inplace=True)

# %% [markdown]
##### Figure XX - Time series: Measured Inflation (US and France)
# %%
_, (ax, bx) = plt.subplots(2, 1, sharex=True)

# * US subplot
measures_to_plot = ["Measured (US)", "Expectations (US)"]
data = inf_melt[inf_melt["variable"].isin(measures_to_plot)]
ax = sns.lineplot(data=data, x="Date", y="Measured (%)", hue="variable", ax=ax)
ax.legend().set_title(None)

# * French subplot
measures_to_plot = ["Measured (France)", "Expectations (France)"]
data = inf_melt[inf_melt["variable"].isin(measures_to_plot)]
bx = sns.lineplot(data=data, x="Date", y="Measured (%)", hue="variable", ax=bx)
bx.legend().set_title(None)
plt.suptitle("Inflation Rates, US and France")
plt.tight_layout()

# %%[markdown]
## Table 1 Descriptive statistics

# %%
usa_melt = pd.melt(us_data, [ids.DATE])
usa_melt.rename(columns={"value": "Billions ($)"}, inplace=True)

# %% [markdown]
##### Figure 2 - Time series: Inflation Expectations, Nondurables Consumption, Durables Consumption, and Savings (US)
# %%
_, (bx) = plt.subplots(1, 1)
measures_to_plot = [ids.NONDURABLES, ids.DURABLES]
data = usa_melt[usa_melt["variable"].isin(measures_to_plot)]
bx = sns.lineplot(data=data, x=ids.DATE, y="Billions ($)", hue="variable", ax=bx)
plt.title("Real consumption levels, United States (2017 dollars)")

# %% [markdown]
##### Figure 3 - Distribution of Inflation Expectations, Nondurables Consumption, Durables Consumption, and Savings (US)
# %%
plot_columns = [
    ids.DIFF_LOG_CPI,
    ids.DIFF_LOG_EXPECTATIONS,
    ids.DIFF_LOG_NONDURABLES,
    ids.DIFF_LOG_DURABLES,
    ids.DIFF_LOG_SAVINGS,
    ids.DIFF_LOG_REAL_NONDURABLES,
    ids.DIFF_LOG_REAL_DURABLES,
    ids.DIFF_LOG_REAL_SAVINGS,
]
sns.pairplot(us_data[plot_columns], corner=True, kind="reg", plot_kws={"ci": None})

# %% [markdown]
##### Table 1: Descriptive statistics
# %%
descriptive_statistics_results = descriptive_stats.generate_descriptive_statistics(
    us_data, STATISTICS_TESTS, export_table=False
)
descriptive_statistics_results

# %% [markdown]
##### Table XX: Correlation matrix
# %%
us_corr = descriptive_stats.correlation_matrix_pvalues(
    data=us_data[[c for c in us_data.columns if "log" in c]],
    hypothesis_threshold=HYPOTHESIS_THRESHOLD,
    decimals=2,
    display=False,
    export_table=False,
)
us_corr

# %% [markdown]
##### Figure XX - Time series: Inflation Expectations, Food Consumption, Durables Consumption (France)
# %%
fr_melt = pd.melt(fr_data, [ids.DATE])
fr_melt.rename(columns={"value": "Billions (€)"}, inplace=True)

fig, (ax, bx) = plt.subplots(1, 2)
measures_to_plot = ["food", "durables"]
data = fr_melt[fr_melt["variable"].isin(measures_to_plot)]
ax = sns.lineplot(data=data, x=ids.DATE, y="Billions (€)", hue="variable", ax=ax)
plt.title("Consumption levels, France")

# %% [markdown]
##### Figure XX - Distribution of Inflation Expectations, Nondurables Consumption, Durables Consumption (France)
# %%
sns.pairplot(fr_data, corner=True, kind="reg", plot_kws={"ci": None})

# %% [markdown]
##### Table 1: Descriptive statistics
# %%
fr_data.describe()

# %% [markdown]
## 3.2) Exploratory analysis

# %% [markdown]
### 3.2.1) Time scale decomposition

# %%
# * Create dwt dict
dwt_measures = [
    ids.EXPECTATIONS,
    ids.NONDURABLES_CHG,
    ids.DURABLES_CHG,
    ids.SAVINGS_CHG,
    ids.DIFF_LOG_EXPECTATIONS,
    ids.DIFF_LOG_REAL_NONDURABLES,
    ids.DIFF_LOG_REAL_DURABLES,
    ids.DIFF_LOG_REAL_SAVINGS,
]
dwt_dict = create_dwt_dict(
    us_data.dropna(), dwt_measures, mother_wavelet=dwt_mother_wavelet
)

# * Run DWTs
dwt_results_dict = create_dwt_results_dict(dwt_dict, dwt_measures)

# * Numpy array for date
t = us_data.dropna()[ids.DATE].to_numpy()

# %% [markdown]
# Figure 4 - Time scale decomposition of expectations and nondurables consumption (US)
# %%
# * Plot comparison decompositions of expectations and other measure
_ = regression.plot_compare_components(
    a_label=ids.EXPECTATIONS,
    b_label=ids.NONDURABLES_CHG,
    a_coeffs=dwt_results_dict[ids.EXPECTATIONS].coeffs,
    b_coeffs=dwt_results_dict[ids.NONDURABLES_CHG].coeffs,
    time=t,
    levels=dwt_results_dict[ids.EXPECTATIONS].levels,
    wavelet=dwt_mother_wavelet,
    figsize=(15, 10),
)
# %%
# * Plot comparison decompositions of expectations and other measure
_ = regression.plot_compare_components(
    a_label=ids.EXPECTATIONS,
    b_label=ids.DURABLES_CHG,
    a_coeffs=dwt_results_dict[ids.EXPECTATIONS].coeffs,
    b_coeffs=dwt_results_dict[ids.DURABLES_CHG].coeffs,
    time=t,
    levels=dwt_results_dict[ids.EXPECTATIONS].levels,
    wavelet=dwt_mother_wavelet,
    figsize=(15, 10),
)
# %%
# * Plot comparison decompositions of expectations and other measure
_ = regression.plot_compare_components(
    a_label=ids.EXPECTATIONS,
    b_label=ids.SAVINGS_CHG,
    a_coeffs=dwt_results_dict[ids.EXPECTATIONS].coeffs,
    b_coeffs=dwt_results_dict[ids.SAVINGS_CHG].coeffs,
    time=t,
    levels=dwt_results_dict[ids.EXPECTATIONS].levels,
    wavelet=dwt_mother_wavelet,
    figsize=(15, 10),
)
# %%
# * Plot comparison decompositions of expectations and other measure
_ = regression.plot_compare_components(
    a_label=ids.EXPECTATIONS,
    b_label=ids.DIFF_LOG_REAL_NONDURABLES,
    a_coeffs=dwt_results_dict[ids.EXPECTATIONS].coeffs,
    b_coeffs=dwt_results_dict[ids.DIFF_LOG_REAL_NONDURABLES].coeffs,
    time=t,
    levels=dwt_results_dict[ids.EXPECTATIONS].levels,
    wavelet=dwt_mother_wavelet,
    figsize=(15, 10),
)
# %%
_ = regression.plot_compare_components(
    a_label=ids.DIFF_LOG_EXPECTATIONS,
    b_label=ids.DIFF_LOG_REAL_NONDURABLES,
    a_coeffs=dwt_results_dict[ids.DIFF_LOG_EXPECTATIONS].coeffs,
    b_coeffs=dwt_results_dict[ids.DIFF_LOG_REAL_NONDURABLES].coeffs,
    time=t,
    levels=dwt_results_dict[ids.DIFF_LOG_EXPECTATIONS].levels,
    wavelet=dwt_mother_wavelet,
    figsize=(15, 10),
)

# %% [markdown]
# Figure 5 - Time scale decomposition of expectations and durables consumption (US)
# %%
_ = regression.plot_compare_components(
    a_label=ids.DIFF_LOG_EXPECTATIONS,
    b_label=ids.DIFF_LOG_REAL_DURABLES,
    a_coeffs=dwt_results_dict[ids.DIFF_LOG_EXPECTATIONS].coeffs,
    b_coeffs=dwt_results_dict[ids.DIFF_LOG_REAL_DURABLES].coeffs,
    time=t,
    levels=dwt_results_dict[ids.DIFF_LOG_EXPECTATIONS].levels,
    wavelet=dwt_mother_wavelet,
    figsize=(15, 10),
)

# %% [markdown]
# Figure XX - Time scale decomposition of expectations and savings (US)
# %%
_ = regression.plot_compare_components(
    a_label=ids.DIFF_LOG_EXPECTATIONS,
    b_label=ids.DIFF_LOG_REAL_SAVINGS,
    a_coeffs=dwt_results_dict[ids.DIFF_LOG_EXPECTATIONS].coeffs,
    b_coeffs=dwt_results_dict[ids.DIFF_LOG_REAL_SAVINGS].coeffs,
    time=t,
    levels=dwt_results_dict[ids.DIFF_LOG_EXPECTATIONS].levels,
    wavelet=DWT_MOTHER,
    figsize=(15, 10),
)

# %% [markdown]
### 3.2.2) Individual time series: Continuous wavelet transforms
# %%
cwt_measures = [
    # ids.INFLATION,
    ids.EXPECTATIONS,
    ids.SAVINGS_RATE,
    # ids.NONDURABLES,
    # ids.DURABLES,
    ids.NONDURABLES_CHG,
    ids.DURABLES_CHG,
    ids.SAVINGS_CHG,
    # ids.SAVINGS,
    # ids.REAL_NONDURABLES,
    # ids.REAL_DURABLES,
    # ids.REAL_SAVINGS,
    ids.DIFF_LOG_CPI,
    ids.DIFF_LOG_EXPECTATIONS,
    ids.DIFF_LOG_REAL_NONDURABLES,
    ids.DIFF_LOG_REAL_DURABLES,
    ids.DIFF_LOG_REAL_SAVINGS,
]
cwt_dict = create_cwt_dict(
    us_data.dropna(),
    cwt_measures,
    mother_wavelet=CWT_MOTHER,
    delta_t=DT,
    delta_j=DJ,
    initial_scale=S0,
    levels=LEVELS,
)

cwt_results_dict = create_cwt_results_dict(cwt_dict, cwt_measures, normalize=True)

# %%
# * Plot CWTs
plt.close("all")
_, axs = plt.subplots(len(cwt_results_dict), **CWT_FIG_PROPS)

for i, m in enumerate(cwt_results_dict):
    cwt.plot_cwt(
        axs[i],
        cwt_dict[m],
        cwt_results_dict[m],
        **CWT_PLOT_PROPS,
    )

    # * Set labels/title
    axs[i].set_xlabel("")
    axs[i].set_ylabel("Period (years)")
    axs[i].set_title(m)

plt.show()


# %% [markdown]
### 3.2.3) Time series co-movements: Cross wavelet transforms and phase difference
phase_diff_key.plot_phase_difference_key(export=False)

# %%
xwt_comparisons = [
    (ids.EXPECTATIONS, ids.NONDURABLES_CHG),
    (ids.EXPECTATIONS, ids.DURABLES_CHG),
    (ids.EXPECTATIONS, ids.SAVINGS_CHG),
    (ids.DIFF_LOG_CPI, ids.DIFF_LOG_EXPECTATIONS),
    (ids.DIFF_LOG_CPI, ids.DIFF_LOG_REAL_NONDURABLES),
    (ids.DIFF_LOG_CPI, ids.DIFF_LOG_REAL_DURABLES),
    (ids.DIFF_LOG_CPI, ids.DIFF_LOG_REAL_SAVINGS),
    (ids.DIFF_LOG_EXPECTATIONS, ids.DIFF_LOG_NONDURABLES),
    (ids.DIFF_LOG_EXPECTATIONS, ids.DIFF_LOG_DURABLES),
    (ids.DIFF_LOG_EXPECTATIONS, ids.DIFF_LOG_SAVINGS),
    (ids.DIFF_LOG_EXPECTATIONS, ids.DIFF_LOG_REAL_NONDURABLES),
    (ids.DIFF_LOG_EXPECTATIONS, ids.DIFF_LOG_REAL_DURABLES),
    (ids.DIFF_LOG_EXPECTATIONS, ids.DIFF_LOG_REAL_SAVINGS),
]

# * Pre-process data: Standardize and detrend
xwt_dict = create_xwt_dict(us_data, xwt_comparisons, detrend=False, remove_mean=True)

xwt_results_dict = create_xwt_results_dict(
    xwt_dict, xwt_comparisons, ignore_strong_trends=False
)

# * Plot XWT power spectrum
_, axs = plt.subplots(len(xwt_comparisons), 1, figsize=(10, 8), sharex=True)

for i, comp in enumerate(xwt_comparisons):
    xwt.plot_xwt(
        axs[i],
        xwt_dict[comp],
        xwt_results_dict[comp],
        include_significance=True,
        include_cone_of_influence=True,
        include_phase_difference=True,
        **XWT_PLOT_PROPS,
    )

    # * Invert y axis
    axs[i].set_ylim(axs[i].get_ylim()[::-1])

    # * Set y axis tick labels
    y_ticks = 2 ** np.arange(
        np.ceil(np.log2(xwt_results_dict[comp].period.min())),
        np.ceil(np.log2(xwt_results_dict[comp].period.max())),
    )
    axs[i].set_yticks(np.log2(y_ticks))
    axs[i].set_yticklabels(y_ticks)

    axs[i].set_title(f"{comp[0]} X {comp[1]} (US)")
    axs[i].set_ylabel("Period (years)")

plt.show()

# %% [markdown]
## 3.3) Regression analysis
### 3.3.1) Baseline model
# Nondurables consumption
# %%
results_nondur = regression.simple_regression(
    us_data.dropna(), ids.EXPECTATIONS, ids.NONDURABLES_CHG
)
results_nondur.summary()

# %% [markdown]
# Durables consumption
# %%
results_dur = regression.simple_regression(
    us_data.dropna(), ids.EXPECTATIONS, ids.DURABLES_CHG
)
results_dur.summary()

# %% [markdown]
# Savings
# %%
results_dur = regression.simple_regression(
    us_data.dropna(), ids.EXPECTATIONS, ids.SAVINGS_CHG
)
results_dur.summary()

# %% [markdown]
## 3.3.2) Wavelet approximation
# Figure 12 - Wavelet Smoothing of Inflation Expectations (US)

# %%
fig, title = dwt.plot_smoothing(
    dwt_results_dict[ids.EXPECTATIONS].smoothed_signal_dict,
    t,
    dwt_dict[ids.EXPECTATIONS].y_values,
    figsize=(10, 10),
)
plt.xlabel("Year")
plt.ylabel(f"{title.capitalize()}")
fig.tight_layout()
plt.show()


# %% [markdown]
# Table 4 - Wavelet Approximation: OLS Regression Inflation Expectations and
# Nondurables Consumption (US) <br><br>

# For our wavelet approximation of the OLS regression of nondurables consumption
# on inflation expectations, we use S_2, removing D_1 and D_2. Table 4 shows
# the results. Overall, there is little change in the results compared to the
# simple regression.

# %%
approximations = regression.wavelet_approximation(
    smooth_t_dict=dwt_results_dict[ids.EXPECTATIONS].smoothed_signal_dict,
    original_y=dwt_dict[ids.NONDURABLES_CHG].y_values,
    levels=dwt_results_dict[ids.EXPECTATIONS].levels,
)

# * Remove D_1 and D_2
apprx = approximations[2]
apprx.summary()

# %% [markdown]
# Table 5 - Wavelet Approximation: OLS Regression Inflation Expectations and
# Durables Consumption with S_2 (US) <br><br>

# The same is true for durables, when removing components D_1 and D_2 (Table 5).
# Given how absolutely inconclusive the OLS regression is, we further test the
# impact of a regression with almost purely smoothed expectations in S_5=S_6+D_6
# as well. Again, we cannot reject the null hypothesis (Table 6).

# %%
approximations = regression.wavelet_approximation(
    smooth_t_dict=dwt_results_dict[ids.EXPECTATIONS].smoothed_signal_dict,
    original_y=dwt_dict[ids.DURABLES_CHG].y_values,
    levels=dwt_results_dict[ids.EXPECTATIONS].levels,
)

# * Remove D_1 and D_2
apprx = approximations[2]
apprx.summary()

# %% [markdown]
# Table 6 - Wavelet Approximation: OLS Regression Inflation Expectations and
# Durables Consumption with S_5 (US) <br><br>

# %%
# * Remove D_1 through D_5
apprx = approximations[5]
apprx.summary()

# %% [markdown]
# Table XX - Wavelet Approximation: OLS Regression Inflation Expectations and
# Savings (US) <br><br>

# %%
approximations = regression.wavelet_approximation(
    smooth_t_dict=dwt_results_dict[ids.EXPECTATIONS].smoothed_signal_dict,
    original_y=dwt_dict[ids.SAVINGS_CHG].y_values,
    levels=dwt_results_dict[ids.EXPECTATIONS].levels,
)

# * Remove D_1 and D_2
apprx = approximations[2]
apprx.summary()


# %% [markdown]
## 3.3) Time scale regression
# Table 7 - Time Scale Decomposition: OLS Regression of Nondurables Consumption
# on Inflation Expectations (US)

# %%
time_scale_results = regression.time_scale_regression(
    input_coeffs=dwt_results_dict[ids.EXPECTATIONS].coeffs,
    output_coeffs=dwt_results_dict[ids.NONDURABLES_CHG].coeffs,
    levels=dwt_results_dict[ids.EXPECTATIONS].levels,
    mother_wavelet=dwt_mother_wavelet,
)
time_scale_results

# %% [markdown]
# Table 8 - Time Scale Decomposition: OLS Regression of Durables Consumption on
# Inflation Expectations (US)

# %%
time_scale_results = regression.time_scale_regression(
    input_coeffs=dwt_results_dict[ids.EXPECTATIONS].coeffs,
    output_coeffs=dwt_results_dict[ids.DURABLES_CHG].coeffs,
    levels=dwt_results_dict[ids.EXPECTATIONS].levels,
    mother_wavelet=dwt_mother_wavelet,
)
time_scale_results


# %% [markdown]
# Table XX - Time Scale Decomposition: OLS Regression of Savings on
# Inflation Expectations (US)

# %%
time_scale_results = regression.time_scale_regression(
    input_coeffs=dwt_results_dict[ids.EXPECTATIONS].coeffs,
    output_coeffs=dwt_results_dict[ids.SAVINGS_CHG].coeffs,
    levels=dwt_results_dict[ids.EXPECTATIONS].levels,
    mother_wavelet=dwt_mother_wavelet,
)
time_scale_results


# %% [markdown]
# Figure 13 - Example, Phase differences
# %%
phase_diff_sines.plot_phase_diff(export=False)
