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
import scipy.stats
import stan

from solar_analyses import utils

# -----------------------------------------------------------------------------

reports = list(Path("Reports").glob("Energy_balance_Monthly_report_*.csv"))
df = pd.concat([utils.load_report(report) for report in reports])
df = df.sort_index()
# Convert to kWh
df = df / 1000.0
# Exclude data from before solar system was switched on
df = df.loc[df.index >= "2022-12-21", :]

fig, ax = plt.subplots(figsize=[8.0, 4.0])
ax.plot(df.index, df["Total production"])
ax.set_xlabel("Date")
ax.set_ylabel("Production (kWh)")
fig.autofmt_xdate()
plt.savefig("Figures/Production.jpg")
plt.savefig("Figures/Production.pdf")

plt.show()

# -----------------------------------------------------------------------------

stan_code = """
data {
  int<lower=0> N;
  vector<lower=0>[N] production; // Total daily production
  vector<lower=0, upper=1>[N] t_year; // Proportion of current year that has passed
}
// transformed data
parameters {
  real<lower=0> min; // Min achievable production (cloudless shortest day)
  real<lower=0> amplitude; // Difference in achievable production (cloudless longest v. shorted day)
  real<lower=-pi(), upper=pi()> phase; // Offset in year
  // real<lower=0, upper=1> lambda; // Probability of a nice day
}
transformed parameters {
  vector<lower=0>[N] optimal_production
    = min + amplitude *
      0.5 * (1.0 + cos(2 * pi() * t_year + phase)
    );
  vector[N] weather_effect = production ./ optimal_production;
}
model {
  // Gamma: m = a/b, v = a/b^2 --> a = m^2/v, b = m/v
  min ~ gamma(16.0, 0.8); // m: 20, v: 5^2
  amplitude ~ gamma(36.0, 1.2); // m: 30, v: 5^2

  // von Mises: v = 1/k
  // Summer solstice ≈10 days from end of year
  phase ~ von_mises(0.17, 135.0); // m=2*pi*(10/365), v=(2*pi*(5/365))**2

  // weather_effect ~ beta(1.0, 1.0);
  // Do we want to infer on lambda / the beta parameters?
  real lambda = 0.25;
  // lambda ~ beta(2.0, 20.0);
  for (n in 1:N) {
    target += log_sum_exp(
      log1m(lambda) + beta_lpdf(weather_effect[n] | 2.0, 2.0),
      log(lambda) + beta_lpdf(weather_effect[n] | 10.0, 1.0)
    );
  };
}
generated quantities {
  real<lower=min> max = min + amplitude; // Max achievable production (cloudless longest day)
}
"""

stan_data = {
    "N": len(df),
    "production": (df["Total production"]).to_numpy(),
    "t_year": (((df.index.day_of_year - 1) % 365) / 365).to_numpy(),
}
stan_model = stan.build(stan_code, data=stan_data)
stan_fit = stan_model.sample(
    num_chains=4,
    num_samples=5000,
    num_warmup=5000,
    num_thin=100,
    init=[
        {
            "min": 25.0,
            "amplitude": 25.0,
            "phase": 0.17
            # "lambda": 0.05 + 0.9 * ((stan_data["production"]
            # / (20.0 + 30.0 * 0.5 * (1.0 + np.cos(2.0 * math.pi *
            #     stan_data["t_year"])))) > 0.9),
        }
    ]
    * 4,
).to_frame()

# -----------------------------------------------------------------------------

# To do:
#  Turn weather_effect / optimal production into proper multi-index dataframes

weather_effect = (
    stan_fit.loc[:, stan_fit.columns.str.startswith("weather_effect")]
    .to_numpy()
    .transpose()
)
fig, ax = plt.subplots(figsize=[8.0, 4.0])
# ax.plot(df.index, weather_effect)
# ax.plot(df.index, df["Total production"] / 50000, "k")
# ax.plot(df.index, weather_effect, color=[0.7] * 3, linewidth=0.2)
# ax.plot(
#    df.index,
#    np.quantile(weather_effect, [0.25, 0.75], axis=1).transpose(),
#    color=[0.4] * 3,
# )
# ax.plot(df.index, np.median(weather_effect, axis=1), "k")
ax.bar(
    df.index,
    np.median(weather_effect, axis=1),
    yerr=np.abs(
        np.median(weather_effect, axis=1)
        - np.quantile(weather_effect, [0.25, 0.75], axis=1)
    ),
)
ax.plot(
    df.index,
    0.5 + 0.3 * np.cos(2.0 * math.pi * stan_data["t_year"]),
    "w",
    linewidth=3.0,
)
ax.plot(df.index, 0.5 + 0.3 * np.cos(2.0 * math.pi * stan_data["t_year"]), "r")
# ax.plot(
#    df.index,
#    0.8 * df["Total production"] / np.max(df["Total production"]), "r")
ax.set_xlabel("Date")
ax.set_ylabel("Weather effect")
fig.autofmt_xdate()
ax.set_ylim(0.0, 1.0)

plt.savefig("Figures/WeatherEffect.jpg")
plt.savefig("Figures/WeatherEffect.pdf")

fig, ax = plt.subplots()
h1 = ax.hist(
    weather_effect.flatten(),
    bins=np.linspace(0.0, 1.0, 50),
    density=True,
    rwidth=0.9,
    label="Posterior samples",
)
x = np.linspace(0.0001, 0.9999, 500)
p = 0.25
h2 = ax.plot(
    x,
    (1.0 - p) * scipy.stats.beta.pdf(x, 2.0, 2.0)
    + p * scipy.stats.beta.pdf(x, 10.0, 1.0),
    label="Prior",
)
ax.set_xlabel("Weather effect")
ax.set_ylabel("Probability density")
ax.legend()

plt.savefig("Figures/WeatherEffectDistribution.jpg")
plt.savefig("Figures/WeatherEffectDistribution.pdf")

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

optimal_production = (
    stan_fit.loc[:, stan_fit.columns.str.startswith("optimal_production")]
    .to_numpy()
    .transpose()
)
fig, ax = plt.subplots(figsize=[8.0, 4.0])
# ax.plot(df.index, df["Total production"])
ax.bar(df.index, df["Total production"])
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

plt.savefig("Figures/OptimalProduction.jpg")
plt.savefig("Figures/OptimalProduction.pdf")

plt.figure()
plt.hist(stan_fit["max"], bins=99)
plt.figure()
plt.hist(stan_fit["min"], bins=99)
fig, ax = plt.subplots()
ax.plot(stan_fit["min"], stan_fit["max"], ".")
ax.axis("equal")
ax.set_xlabel("Min (kWh)")
ax.set_ylabel("Max (kWh)")


# fig, ax = plt.subplots()
# plt.plot(
#     stan_fit.loc[:, stan_fit.columns.str.startswith("weather_effect")]
#     .to_numpy()
#     .flatten(),
#     stan_fit.loc[:, stan_fit.columns.str.startswith("lambda")].to_numpy().flatten(),
#     ".",
#     markersize=2,
# )

fig, ax = plt.subplots()
ax.hist(  # 365 * stan_fit["phase"] / (2 * math.pi), bins=99)
    (365 * stan_fit.loc[:, "phase"] / (2 * math.pi)).apply(
        lambda x: pd.to_datetime("2000-01-01") - pd.DateOffset(math.floor(x))
    ),
    bins=99,
)
ax.xaxis.set_major_formatter(mpl.dates.DateFormatter("%d-%b"))
fig.autofmt_xdate()

plt.show()
