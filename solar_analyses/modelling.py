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

import stan

# -----------------------------------------------------------------------------

_stan_code = """
data {
  int<lower=0> N;
  // Total daily production
  vector<lower=0>[N] production;
  // Proportion of current year that has passed
  vector<lower=0, upper=1>[N] t_year;
}

// transformed data {}

parameters {
  // Min optimal production (cloudless shortest day)
  real<lower=0> min;
  // Difference in optimal production (i.e. longest v. shortest day)
  real<lower=0> amplitude;
  // Offset of max in year
  real<lower=-pi(), upper=pi()> phase;
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
  // Max optimal production (cloudless longest day)
  real<lower=min> max = min + amplitude;
}
"""


def fit_model(df):
    """Estimates the posterior over key parameters using Stan."""
    stan_data = {
        "N": len(df),
        "production": (df["Total production"]).to_numpy(),
        "t_year": (((df.index.day_of_year - 1) % 365) / 365).to_numpy(),
    }

    stan_model = stan.build(_stan_code, data=stan_data)

    stan_fit = stan_model.sample(
        num_chains=4,
        num_samples=5000,
        num_warmup=5000,
        num_thin=100,
        init=4 * [{"min": 25.0, "amplitude": 25.0, "phase": 0.17}],
    ).to_frame()

    return [stan_data, stan_fit]


# -----------------------------------------------------------------------------
