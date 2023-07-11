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

import math
import matplotlib.pyplot as plt
import numpy as np
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

# To do:
#  Turn weather_effect / optimal production into proper multi-index dataframes


def plot_optimal_production(df, stan_fit):
    """Summarise the posterior over the optimal production curve."""

    figures = {}

    optimal_production = (
        stan_fit.loc[:, stan_fit.columns.str.startswith("optimal_production")]
        .to_numpy()
        .transpose()
    )

    fig, ax = plt.subplots(figsize=[8.0, 4.0])
    # Raw data
    ax.bar(df.index, df["Total production"])
    # Distribution of optimal production over time
    ax.plot(df.index, optimal_production, color=[0.7] * 3, linewidth=0.2)
    ax.plot(
        df.index,
        np.quantile(optimal_production, [0.25, 0.75], axis=1).transpose(),
        color=[0.4] * 3,
    )
    ax.plot(df.index, np.median(optimal_production, axis=1), "r")
    ax.set_xlabel("Date")
    ax.set_ylabel("Production (kWh)")
    fig.autofmt_xdate()
    figures["optimal_production"] = fig

    fig, ax = plt.subplots(figsize=[5.0, 4.0])
    ax.plot(stan_fit["min"], stan_fit["max"], ".")
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

    weather_effect = (
        stan_fit.loc[:, stan_fit.columns.str.startswith("weather_effect")]
        .to_numpy()
        .transpose()
    )
    offset_in_year = utilities.date_to_offset_in_year(df.index)

    # Plot weather effect over time
    fig, ax = plt.subplots(figsize=[8.0, 4.0])
    ax.bar(
        df.index,
        np.median(weather_effect, axis=1),
        yerr=np.abs(
            np.median(weather_effect, axis=1)
            - np.quantile(weather_effect, [0.25, 0.75], axis=1)
        ),
    )
    # Plot the seasonality as a sinusoid
    ax.plot(
        df.index,
        0.5 + 0.3 * np.cos(2.0 * math.pi * offset_in_year),
        "w",
        linewidth=3.0,
    )
    ax.plot(df.index, 0.5 + 0.3 * np.cos(2.0 * math.pi * offset_in_year), "r")
    ax.set_xlabel("Date")
    ax.set_ylabel("Weather effect")
    fig.autofmt_xdate()
    ax.set_ylim(0.0, 1.0)
    figures["weather_effect"] = fig

    # Compare marginal distribution to prior
    fig, ax = plt.subplots(figsize=[5.0, 4.0])
    ax.hist(
        weather_effect.flatten(),
        bins=np.linspace(0.0, 1.0, 50),
        density=True,
        rwidth=0.9,
        label="Posterior samples",
    )
    x = np.linspace(0.0001, 0.9999, 500)
    p = 0.25
    ax.plot(
        x,
        (1.0 - p) * scipy.stats.beta.pdf(x, 2.0, 2.0)
        + p * scipy.stats.beta.pdf(x, 10.0, 1.0),
        label="Prior",
    )
    ax.set_xlabel("Weather effect")
    ax.set_ylabel("Probability density")
    ax.legend()
    figures["weather_effect_distribution"] = fig

    return figures


# -----------------------------------------------------------------------------
