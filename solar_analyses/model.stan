// SPDX-License-Identifier: Apache-2.0

// Copyright 2023 Sam Harrison
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// ----------------------------------------------------------------------------

functions {
  // Models the saturation as the softmin of the input (i.e. a linear region)
  // and a hard upper limit.
  // https://en.wikipedia.org/wiki/LogSumExp
  vector saturation(vector E, real limit, real smoothness){
    real sharpness = 1.0 / smoothness;
    vector[size(E)] E_sat;
    for (i in 1:size(E)) {
      E_sat[i] = (-1.0 / sharpness) * log_sum_exp(
        - sharpness * E[i],
        - sharpness * limit
      );
    }
    return E_sat;
  }

  vector inv_saturation(vector E_sat, real limit, real smoothness){
    real sharpness = 1.0 / smoothness;
    vector[size(E_sat)] E;
    for (i in 1:size(E_sat)) {
      E[i] = (-1.0 / sharpness) * log_diff_exp(
        - sharpness * E_sat[i],
        - sharpness * limit
      );
    }
    return E;
  }

  vector instantaneous_phase(vector t_year, real phase) {
    return 2.0 * pi() * t_year + phase;
  }

  vector seasonal_oscillation(
    vector instantaneous_phase, real beta_c1, real beta_s1
  ) {
    return 0.5 * (1.0 + cos(
      instantaneous_phase
      + beta_c1 * cos(instantaneous_phase)
      + beta_s1 * sin(instantaneous_phase)
    ));
  }
}

// ----------------------------------------------------------------------------

data {
  int<lower=0> N;
  // Total daily production
  vector<lower=0>[N] production;
  // Proportion of current year that has passed
  vector<lower=0, upper=1>[N] t_year;
}

// ----------------------------------------------------------------------------

transformed data {
  // Reference version of `t_year` for a single year
  vector<lower=0, upper=1>[365] t_year_ref;
  for (i in 1:365) {
    t_year_ref[i] = (i - 1) / 365.0;
  }

  // Minimum value of the limit parameter controlling inverter clipping
  real saturation_limit_baseline = 50.0;
}

// ----------------------------------------------------------------------------

parameters {
  // Min available energy (cloudless shortest day)
  real<lower=0> min;
  // Difference in available energy (i.e. longest v. shortest day)
  real<lower=0> amplitude;

  // Offset of day of peak production in year
  real<lower=-pi(), upper=pi()> phase;
  // Coefficients controlling how much sinusoidal basis affects seasonal
  // oscillation
  real beta_c1, beta_s1;

  // Parameters describing how much inverter limit causes clipping of production
  real<lower=0> saturation_limit_increase;
  real<lower=0> saturation_smoothness;
}

// ----------------------------------------------------------------------------

transformed parameters {
  // Daily timeseries of total energy available from the panels
  vector<lower=0>[N] E_available
    = min + amplitude * seasonal_oscillation(
      instantaneous_phase(t_year, phase), beta_c1, beta_s1
    );

  // Daily variables describing the factor by which clouds etc. reduced
  // energy generation
  // production = saturation(weather-effect * E_available)
  real<lower=0> saturation_limit
    = saturation_limit_baseline + saturation_limit_increase;
  vector[N] weather_effect
    = inv_saturation(
      production,
      saturation_limit,
      saturation_smoothness
    ) ./ E_available;
}

// ----------------------------------------------------------------------------

model {
  // Gamma: m = a/b, v = a/b^2 --> a = m^2/v, b = m/v
  min ~ gamma(16.0, 0.8); // m: 20, v: 5^2
  amplitude ~ gamma(64.0, 1.6); // m: 40, v: 5^2
  saturation_limit_increase ~ gamma(0.25, 0.25); // m: 1, v: 2^2
  saturation_smoothness ~ gamma(25.0, 2.5); // m: 10, v: 2^2

  // Normal
  beta_c1 ~ normal(0.0, 0.25); // m: 0, s: 0.5
  beta_s1 ~ normal(0.0, 0.25); // m: 0, s: 0.5

  // von Mises: v = 1/k
  // Summer solstice ≈10 days from end of year
  phase ~ von_mises(0.17, 135.0); // m=2*pi*(10/365), v=(2*pi*(5/365))**2

  // Beta: m = a / (a + b)
  real lambda = 0.25;
  for (n in 1:N) {
    target += log_sum_exp(
      log1m(lambda) + beta_lpdf(weather_effect[n] | 2.0, 2.0),
      log(lambda) + beta_lpdf(weather_effect[n] | 15.0, 2.0)
    );
  };
}

// ----------------------------------------------------------------------------

generated quantities {
  // Daily optimal production (i.e. accounting for clipping from inverter)
  // weather_effect = 1.0
  vector<lower=0>[N] E_optimal
    = saturation(
      E_available,
      saturation_limit,
      saturation_smoothness
    );

  // Max/min optimal production (cloudless longest/shortest day)
  // weather_effect = 1.0, seasonal_oscillation = 1.0 / 0.0
  real E_optimal_max
    = saturation(
      [min + amplitude]',
      saturation_limit,
      saturation_smoothness
    )[1];
  real E_optimal_min
    = saturation(
      [min]',
      saturation_limit,
      saturation_smoothness
    )[1];

  // Versions of the above for the timeseries of the reference year
  vector<lower=0>[365] E_available_ref
    = min + amplitude * seasonal_oscillation(
      instantaneous_phase(t_year_ref, phase), beta_c1, beta_s1
    );
  vector<lower=0>[365] E_optimal_ref
    = saturation(
      E_available_ref,
      saturation_limit,
      saturation_smoothness
    );
}

// ----------------------------------------------------------------------------
