#!/usr/bin/env python
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
import matplotlib as mpl, matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

from solar_analyses import analysis, modelling, plots, utilities

# -----------------------------------------------------------------------------

figure_dir = Path("figures")

figures = {}

# -----------------------------------------------------------------------------
# Load and preprocess data

reports = list(Path("reports").glob("Energy_balance_Monthly_report_*.csv"))
df = pd.concat([utilities.load_report(report) for report in reports])
df = df.sort_index()
# Convert to kWh
df = df / 1000.0
# Exclude data from before solar system was switched on
df = df.loc[df.index >= "2022-12-21", :]

# -----------------------------------------------------------------------------
# Basic analyses of the raw data

# Summarise total production by year
print(
    df["Total production"]
    .groupby(lambda x: x.year)
    .aggregate(["sum", "count"])
    .rename_axis("Year", axis="index")
    .rename(columns={"sum": "Total production (kWh)", "count": "# days"})
    .to_markdown()
)
print()

# Compare monthly breakdown to the predictions from Dunedin Solar
print(
    analysis.compare_with_predictions(df, utilities.load_predictions()).to_markdown(
        floatfmt=".0f"
    )
)
print()

# Generate some initial plots
figures = {**figures, **plots.plot_raw_data(df)}

# -----------------------------------------------------------------------------
# Fit the model

stan_fit = modelling.fit_model(df)

# -----------------------------------------------------------------------------
# Generate summary plots of posterior

figures = {
    **figures,
    **plots.plot_annual_variation(df, stan_fit),
    **plots.plot_optimal_production(df, stan_fit),
    **plots.plot_weather_effect(df, stan_fit),
}

# -----------------------------------------------------------------------------
# Save and display figures

for name, fig in figures.items():
    for extension in ["jpg", "pdf"]:
        fig.savefig(figure_dir / (name + "." + extension))

plt.show()

# -----------------------------------------------------------------------------
# Prototype code

# for n in range(10):
#     plt.figure()
#     plt.hist(
#         stan_fit.loc[n, stan_fit.columns.str.startswith("weather_effect")],
#         bins=25,
#         density=True,
#         rwidth=0.9,
#     )
#     x = np.linspace(0.0001, 0.9999, 500)
#     p = 0.25
#     plt.plot(
#         x,
#         (1.0 - p) * scipy.stats.beta.pdf(x, 2.0, 2.0)
#         + p * scipy.stats.beta.pdf(x, 10.0, 1.0),
#     )

# plt.figure()
# plt.hist(stan_fit["max"], bins=99)
# plt.figure()
# plt.hist(stan_fit["min"], bins=99)
# plt.figure()
# plt.hist(stan_fit["saturation"], bins=99)

# fig, ax = plt.subplots()
# plt.plot(
#     stan_fit.loc[:, stan_fit.columns.str.startswith("weather_effect")]
#     .to_numpy()
#     .flatten(),
#     stan_fit.loc[:, stan_fit.columns.str.startswith("lambda")].to_numpy().flatten(),
#     ".",
#     markersize=2,
# )

phase = (
    (365 * stan_fit.loc[:, "phase"] / (2 * math.pi))
    .apply(lambda x: pd.to_datetime("2001-01-01") - pd.DateOffset(math.floor(x)))
    .value_counts()
)
fig, ax = plt.subplots()
ax.bar(phase.index, phase / len(stan_fit))
ax.xaxis.set_major_formatter(mpl.dates.DateFormatter("%d-%b"))
ax.set_xlabel(r"Phase ($\delta$)")
ax.set_ylabel("Probability density")
fig.autofmt_xdate()

plt.show()

# -----------------------------------------------------------------------------
