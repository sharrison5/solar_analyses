# -*- coding: utf-8 -*-

# SPDX-License-Identifier: Apache-2.0

# Copyright 2023 Sam Harrison
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import calendar
import math
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats

from solar_analyses import utilities

# -----------------------------------------------------------------------------


def plot_raw_data(df):
    """Generate summary plots of key parameters from Fronius reports."""

    figures = {}

    # Plot production over time
    fig, ax = plt.subplots(figsize=[8.0, 4.0])
    ax.bar(df.index, df["Total production"], label="Production")
    ax.bar(df.index, df["Own consumption"], label="Self consumption", width=0.4)
    ax.set_xlabel("Date")
    ax.set_ylabel("Energy (kWh)")
    ax.legend()
    fig.autofmt_xdate()
    figures["production"] = fig

    return figures


# -----------------------------------------------------------------------------


def plot_annual_variation(df, stan_fit):
    """Summarise the posterior over the seasonal fluctuation in production."""

    figures = {}

    # Plot posterior over energy curves for a year
    dates = pd.to_datetime(np.arange(365), origin="2001-01-01", unit="D")
    E_available = utilities.extract_posterior_timeseries(
        "E_available_ref", dates, stan_fit
    )
    E_optimal = utilities.extract_posterior_timeseries("E_optimal_ref", dates, stan_fit)
    # And make the plot
    fig, ax = plt.subplots(figsize=[8.0, 4.0])
    # Plot a large proportion of the samples
    ax.plot(
        dates,
        E_optimal.sample(n=100, replace=False, axis="columns"),
        color=[0.7] * 3,
        linewidth=0.2,
    )
    # Plot a smaller random subset to highlight how these vary
    ax.plot(
        dates,
        E_optimal.sample(n=5, replace=False, axis="columns"),
        color=[0.3] * 3,
        linewidth=0.5,
    )
    # Then the median over samples (illustrative only, doesn't account for
    # temporal dependencies)
    ax.plot(dates, E_optimal.median(axis="columns"), "k", label=r"$E_{opt}(t)$")
    # And finally the available energy (i.e. without saturation) for comparison
    ax.plot(dates, E_available.mean(axis="columns"), "w", linewidth=3.0)
    ax.plot(dates, E_available.mean(axis="columns"), "tab:red", label=r"$E_{avail}(t)$")
    ax.set_xlim(dates[0], dates[-1])
    ax.xaxis.set_major_locator(mpl.dates.MonthLocator(bymonthday=15))
    ax.xaxis.set_major_formatter(mpl.dates.DateFormatter("%b"))
    ax.set_xlabel("Time of year")
    ax.set_ylabel("Energy (kWh)")
    ax.legend()
    fig.autofmt_xdate()
    figures["annual_variation"] = fig

    # Plot the date at which the maximum occurs
    max_date_hist = E_optimal.idxmax(axis="index").round("D").value_counts()
    # Wrap Jan to after December rather than at start of year
    max_date_hist.index = max_date_hist.index.map(
        lambda x: x + pd.DateOffset(years=(x.month <= 6))
    )
    fig, ax = plt.subplots(figsize=[5.0, 4.0])
    ax.bar(max_date_hist.index, max_date_hist / len(stan_fit))
    ax.xaxis.set_major_formatter(mpl.dates.DateFormatter("%d-%b"))
    ax.set_xlabel(r"Date of peak production (argmax $E_{opt}(t)$)")
    ax.set_ylabel("Probability")
    fig.autofmt_xdate()
    figures["annual_variation_peak_date"] = fig

    # Plot saturation v amplitude
    fig, ax = plt.subplots(figsize=[5.0, 4.0])
    ax.plot(stan_fit["saturation_limit"], stan_fit["amplitude"] + stan_fit["min"], ".")
    ax.grid(which="major", linestyle=":")
    ax.set_xlabel(r"Saturation limit ($\gamma$, kWh)")
    ax.set_ylabel(r"Maximum $E_{avail}(t)$ (kWh)")
    figures["annual_variation_saturation"] = fig

    # Plot beta coefficients modulating sine shape
    fig, ax = plt.subplots(figsize=[5.0, 4.0])
    ax.axhline(0.0, c="k", ls="--")
    ax.axvline(0.0, c="k", ls="--")
    ax.plot(stan_fit["beta_c1"], stan_fit["beta_s1"], ".")
    ax.axis("equal")
    ax.grid(which="major", linestyle=":")
    ax.set_xlabel(r"$\beta_{c1}$")
    ax.set_ylabel(r"$\beta_{s1}$")
    figures["annual_variation_betas"] = fig

    return figures


# -----------------------------------------------------------------------------


def plot_optimal_production(df, stan_fit):
    """Summarise the posterior over the optimal production curve."""

    figures = {}

    optimal_production = utilities.extract_posterior_timeseries(
        "E_optimal", df.index, stan_fit
    )

    fig, ax = plt.subplots(figsize=[8.0, 4.0])
    # Raw data
    ax.bar(df.index, df["Total production"])
    # Distribution of optimal production over time
    ax.plot(
        optimal_production.index,
        optimal_production.sample(n=100, replace=False, axis="columns"),
        color=[0.7] * 3,
        linewidth=0.2,
    )
    ax.plot(
        optimal_production.index,
        optimal_production.quantile([0.25, 0.75], axis="columns").T,
        color=[0.4] * 3,
    )
    ax.plot(
        optimal_production.index,
        optimal_production.median(axis="columns"),
        "tab:red",
    )
    ax.set_xlabel("Date")
    ax.set_ylabel(r"Production / $E_{opt}(t)$ (kWh)")
    fig.autofmt_xdate()
    figures["optimal_production"] = fig

    # Posterior over min/max
    fig, ax = plt.subplots(figsize=[5.0, 4.0])
    ax.plot(stan_fit["E_optimal_min"], stan_fit["E_optimal_max"], ".")
    ax.axis("equal")
    ax.grid(which="major", linestyle=":")
    ax.set_xlabel(r"Minimum $E_{opt}(t)$ (kWh)")
    ax.set_ylabel(r"Maximum $E_{opt}(t)$ (kWh)")
    figures["optimal_production_limits"] = fig

    return figures


# -----------------------------------------------------------------------------


def plot_weather_effect(df, stan_fit):
    """Summarise the posterior over the weather effect parameters."""

    figures = {}

    weather_effect = utilities.extract_posterior_timeseries(
        "weather_effect", df.index, stan_fit
    )
    offset_in_year = utilities.date_to_offset_in_year(weather_effect.index)

    # Plot weather effect over time
    fig, ax = plt.subplots(figsize=[8.0, 4.0])
    ax.bar(
        weather_effect.index,
        weather_effect.median(axis="columns"),
        yerr=(
            weather_effect.median(axis="columns")
            - weather_effect.quantile([0.25, 0.75], axis="columns")
        ).abs(),
    )
    # Plot the seasonality as a sinusoid
    seasonality = 0.5 + 0.3 * np.cos(2.0 * math.pi * offset_in_year)
    ax.plot(weather_effect.index, seasonality, "w", linewidth=4.0)
    ax.plot(weather_effect.index, seasonality, "tab:red", label=r"$\cos(2 \pi p(t))$")
    # Add rolling averages
    fortnightly_average = (
        weather_effect.rolling(window=14, center=True).mean().median(axis="columns")
    )
    ax.plot(weather_effect.index, fortnightly_average, "w", linewidth=4.0)
    ax.plot(
        weather_effect.index,
        fortnightly_average,
        "tab:pink",
        label="Fortnightly average",
    )
    # Labels etc.
    ax.set_xlabel("Date")
    ax.set_ylabel(r"Weather effect ($w(t)$)")
    ax.grid(which="major", axis="y")
    ax.legend(loc="lower left")
    fig.autofmt_xdate()
    ax.set_ylim(0.0, 1.1)
    figures["weather_effect"] = fig

    # Plot weather effect over time, binned by month
    monthly_weather_effect = (
        weather_effect.groupby(by=lambda x: x.month)
        .agg(list)
        .agg(lambda x: sum(x, []), axis="columns")
    )
    positions = monthly_weather_effect.index
    # Make a boxplot with the raw data
    fig, ax = plt.subplots(figsize=[8.0, 4.0])
    props = {"color": [0.7] * 3}
    bplot = ax.boxplot(
        monthly_weather_effect,
        positions=positions,
        patch_artist=True,
        boxprops={**props},
        capprops={**props},
        whiskerprops={**props},
        medianprops={"color": "k", "linewidth": 2.0},
    )
    for patch in bplot["boxes"]:
        patch.set_facecolor([0.9] * 3)
    # Plot the seasonality as a sinusoid fit to the median and IQR
    quantiles = np.stack(
        [
            np.quantile(values, [0.25, 0.5, 0.75])
            for _, values in monthly_weather_effect.items()
        ]
    )

    def basis(positions):
        return np.stack(
            [
                np.sin(2.0 * math.pi * positions / 12),
                np.cos(2.0 * math.pi * positions / 12),
                np.ones_like(positions),
            ]
        )

    high_res_positions = np.linspace(positions[0] - 0.5, positions[-1] + 0.5, 100)
    high_res_fit = (
        basis(high_res_positions).T @ np.linalg.pinv(basis(positions).T) @ quantiles
    )
    ax.plot(high_res_positions, high_res_fit, linewidth=2)
    # Labels etc.
    ax.set_xticks(positions, [calendar.month_abbr[p] for p in positions])
    ax.set_xlabel("Month")
    ax.set_ylabel(r"Weather effect ($w(t)$)")
    figures["weather_effect_monthly"] = fig

    # Compare marginal distribution to prior
    fig, ax = plt.subplots(figsize=[5.0, 4.0])
    ax.hist(
        weather_effect.stack(),
        bins=np.linspace(0.0, 1.1, 50),
        density=True,
        rwidth=0.9,
        label="Posterior samples",
    )
    x = np.linspace(0.0, 1.1, 500)
    p = 0.15
    ax.plot(
        x,
        (1.0 - p) * scipy.stats.gamma.pdf(x, 5.0, 0.0, 1.0 / 8.0)
        + p * scipy.stats.gamma.pdf(x, 180.0, 0.0, 1.0 / 200.0),
        label="Prior",
    )
    ax.set_xlabel(r"Weather effect ($w(t)$)")
    ax.set_ylabel("Probability density")
    ax.legend()
    figures["weather_effect_distribution"] = fig

    # Autocorrelation
    fig, ax = plt.subplots(figsize=[5.0, 4.0])
    lags = np.arange(0, 20)
    autocorr = pd.DataFrame(
        [weather_effect.apply(lambda s: s.autocorr(lag), axis="rows") for lag in lags],
        index=lags,
    )
    # Null
    # https://en.wikipedia.org/wiki/Pearson_correlation_coefficient#Testing_using_Student's_t-distribution
    n = weather_effect.shape[0]
    t = scipy.stats.t.ppf([0.025, 0.975], df=n - 2)
    null = t / np.sqrt(n - 2 + t**2)
    ax.axhline(null[0], c="k", ls="--", label="Null (95% CI)")
    ax.axhline(null[1], c="k", ls="--")
    # 95% CI over samples
    quantiles = autocorr.quantile([0.025, 0.975], axis="columns")
    ax.fill_between(
        lags,
        quantiles.iloc[0],
        quantiles.iloc[1],
        alpha=0.2,
        label="95% CI over samples",
    )
    # Then the median over samples (illustrative only, doesn't account for
    # temporal dependencies)
    ax.plot(lags, autocorr.median(axis="columns"), label="Median over samples")
    ax.xaxis.set_major_locator(mpl.ticker.MaxNLocator(integer=True))
    ax.grid(which="major", linestyle=":")
    ax.set_ylabel(r"Autocorrelation of weather effect ($w(t)$)")
    ax.set_xlabel("Lag (days)")
    ax.legend()
    figures["weather_effect_autocorr"] = fig

    return figures


# -----------------------------------------------------------------------------
