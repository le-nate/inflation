"""Statistical tests for time series analysis"""

import logging
from pathlib import Path
import sys

from typing import Dict, List, Tuple, Union

import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats
import statsmodels.graphics.tsaplots
import statsmodels.stats.diagnostic

from src.helpers import define_other_module_log_level
from src import ids
from src import retrieve_data

# * Logging settings
logger = logging.getLogger(__name__)
define_other_module_log_level("info")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

DESCRIPTIVE_STATS = [
    "count",
    "mean",
    "std",
    "skewness",
    "kurtosis",
    "Jarque-Bera",
    "Shapiro-Wilk",
    "Ljung-Box",
]
NORMALITY_TESTS = {"Jarque-Bera": stats.jarque_bera, "Shapiro-Wilk": stats.shapiro}
HYPOTHESIS_THRESHOLD = [0.1, 0.05, 0.001]


def parse_results_dict(
    complete_dict: Dict[str, Dict[str, Union[float, str]]], stats_to_keep: List[str]
) -> Dict[str, Dict[str, float]]:
    """Extract only required statistics from dictionary"""
    parsed_dict = {}
    for measure, result_dict in complete_dict.items():
        parsed_dict[measure] = {stat: result_dict[stat] for stat in stats_to_keep}
    return parsed_dict


def include_statistic(
    statistic: str,
    statistic_data: Dict[str, float],
    results_dict: Dict[str, Dict[str, float]],
) -> Dict[str, Dict[str, float]]:
    """Add skewness data for each measure"""
    for measure, result_dict in results_dict.items():
        result_dict[statistic] = statistic_data[measure]
    return results_dict


def test_normality(
    normality_test: str,
    data: pd.DataFrame,
    date_column: str = "date",
    add_pvalue_stars: bool = False,
) -> Dict[str, str]:
    """Generate dictionary with Jarque-Bera test results for each dataset"""
    results_dict = {}
    cols_to_test = data.drop(date_column, axis=1).columns.to_list()
    for col in cols_to_test:
        x = data[col].dropna().to_numpy()
        test_stat, p_value = NORMALITY_TESTS[normality_test](x)
        if add_pvalue_stars:
            result = str(test_stat)
            for p_threshold in sorted(HYPOTHESIS_THRESHOLD):
                result += "*" if p_value <= p_threshold else ""
        results_dict[col] = result
    return results_dict


# TODO Calculate Ljung-Box
def conduct_ljung_box(
    data: pd.DataFrame,
    lags: List[int],
    date_column: str = "date",
    add_pvalue_stars: bool = False,
) -> Dict[str, str]:
    """Generate dictionary with Ljung-Box test results for each dataset"""
    results_dict = {}
    cols_to_test = data.drop(date_column, axis=1).columns.to_list()
    for col in cols_to_test:
        test_results = statsmodels.stats.diagnostic.acorr_ljungbox(data[col], lags=lags)
        test_stat, p_value = (
            test_results["lb_stat"].iat[0],
            test_results["lb_pvalue"].iat[0],
        )
        if add_pvalue_stars:
            result = str(test_stat)
            for p_threshold in sorted(HYPOTHESIS_THRESHOLD):
                result += "*" if p_value <= p_threshold else ""
        results_dict[col] = result
    return results_dict


# TODO Generate correlation matrix


# TODO Generate summary table
def create_summary_table(
    data_dict: Dict[str, Dict[str, Union[float, str]]], export_table: bool = False
) -> Union[Tuple[pd.DataFrame, None], pd.DataFrame]:
    """Create table with descriptive statistics for all datasets with option to export"""
    df = pd.DataFrame(data_dict)
    if export_table:
        # * Get data directory folder
        parent_dir = Path(__file__).parents[1]
        export_file = parent_dir / "results" / "descriptive_stats.html"

        return df, df.to_html(export_file)
    return df


def main() -> None:
    """Run script"""
    # * Retrieve data

    ## Inflation
    raw_data = retrieve_data.get_fed_data(ids.US_CPI, units="pc1")
    inf, _, _ = retrieve_data.clean_fed_data(raw_data)
    inf.rename(columns={"value": "inflation"}, inplace=True)

    ## Inflation expectations
    raw_data = retrieve_data.get_fed_data(ids.US_INF_EXPECTATIONS)
    inf_exp, _, _ = retrieve_data.clean_fed_data(raw_data)
    inf_exp.rename(columns={"value": "expectation"}, inplace=True)

    ## Non-durables consumption, monthly
    raw_data = retrieve_data.get_fed_data(ids.US_NONDURABLES_CONSUMPTION, units="pc1")
    nondur_consump, _, _ = retrieve_data.clean_fed_data(raw_data)
    nondur_consump.rename(columns={"value": "nondurable"}, inplace=True)

    ## Durables consumption, monthly
    raw_data = retrieve_data.get_fed_data(ids.US_DURABLES_CONSUMPTION, units="pc1")
    dur_consump, _, _ = retrieve_data.clean_fed_data(raw_data)
    dur_consump.rename(columns={"value": "durable"}, inplace=True)

    ## Personal savings rate
    raw_data = retrieve_data.get_fed_data(ids.US_SAVINGS)
    save, _, _ = retrieve_data.clean_fed_data(raw_data)
    save.rename(columns={"value": "savings"}, inplace=True)

    # * Merge dataframes to align dates and remove extras
    us_data = inf.merge(inf_exp, how="left")
    us_data = us_data.merge(nondur_consump, how="left")
    us_data = us_data.merge(dur_consump, how="left")
    us_data = us_data.merge(save, how="left")

    # * Drop NaNs
    us_data.dropna(inplace=True)

    print(us_data.head())

    results = us_data.describe(percentiles=[0.5]).to_dict()
    skewness = us_data.skew(numeric_only=True).to_dict()
    kurtosis = us_data.kurtosis(numeric_only=True).to_dict()
    jarque_bera = test_normality(
        normality_test="Jarque-Bera",
        data=us_data,
        date_column="date",
        add_pvalue_stars=True,
    )
    shapiro_wilk = test_normality(
        normality_test="Shapiro-Wilk",
        data=us_data,
        date_column="date",
        add_pvalue_stars=True,
    )
    ljung_box = conduct_ljung_box(
        data=us_data, lags=[15], date_column="date", add_pvalue_stars=True
    )
    logger.debug(
        "skewness: %s \n kurtosis: %s \n Jarque-Bera: %s \n Shapiro-Wilk: %s \n Ljung-Box: %s",
        skewness,
        kurtosis,
        jarque_bera,
        shapiro_wilk,
        ljung_box,
    )
    results = include_statistic(
        statistic="skewness", statistic_data=skewness, results_dict=results
    )
    results = include_statistic(
        statistic="kurtosis", statistic_data=kurtosis, results_dict=results
    )
    results = include_statistic(
        statistic="Jarque-Bera", statistic_data=jarque_bera, results_dict=results
    )
    results = include_statistic(
        statistic="Shapiro-Wilk", statistic_data=shapiro_wilk, results_dict=results
    )
    results = include_statistic(
        statistic="Ljung-Box", statistic_data=ljung_box, results_dict=results
    )
    results = parse_results_dict(results, DESCRIPTIVE_STATS)
    results_df = create_summary_table(results, export_table=True)
    print(results_df)

    us_data.plot.hist(bins=150, subplots=True, legend=True, layout=(1, 5))
    fig, axs = plt.subplots(5)
    for ax, c in zip(axs, us_data.drop("date", axis=1).columns.to_list()):
        statsmodels.graphics.tsaplots.plot_acf(us_data[c], lags=36, ax=ax)
        ax.title.set_text(c)
    plt.show()


if __name__ == "__main__":
    main()
