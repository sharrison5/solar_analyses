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
  // Models the saturation as tanh of the input, with a tunable sharpness
  // parameter (between 0 and 1) that determines how quickly the function
  // transitions from the approximately linear region to the saturated region.
  vector saturation(vector E, real limit, real sharpness){
    // Equation: f(x) = a * tanh(b * sinh(x / b) / a)
    // a represents the limit at which the function saturates, and for small
    // values of b the sinh term causes the saturation to happen earlier. We
    // want f(0) = 0, f(x) < x, f'(x) <= 1, f'(0) = 1 (i.e. starts linear and
    // progressively drops off, as per tanh). For small b the sinh term
    // dominates and f(x) can rise above x before saturating. To prevent this
    // we limit b. The critical value isn't trivial to derive, but the way to
    // do it is to only allow functions where f'''(x) < 0 (i.e. f'(x) is a
    // maximum at 0). This leads to the key equality a / b < sqrt(2).
    real smoothness = limit / (sqrt2() * sharpness);
    return limit * tanh(smoothness * sinh(E / smoothness) / limit);
  }

  vector inv_saturation(vector E_sat, real limit, real sharpness){
    real smoothness = limit / (sqrt2() * sharpness);
    return smoothness * asinh(limit * atanh(E_sat / limit) / smoothness);
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
  real<lower=0, upper=1> saturation_sharpness;
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
  // production = saturation(weather_effect * E_available)
  real<lower=0> saturation_limit
    = saturation_limit_baseline + saturation_limit_increase;
  vector[N] weather_effect
    = inv_saturation(
      production,
      saturation_limit,
      saturation_sharpness
    ) ./ E_available;
}

// ----------------------------------------------------------------------------

model {
  // Gamma: m = a/b, v = a/b^2 --> a = m^2/v, b = m/v
  // This will be approximately normal as the shape parameter increases
  // https://stats.stackexchange.com/a/497002
  // I.e. 95% of the probability mass will be +/- 2 std
  min ~ gamma(16.0, 0.8); // m: 20, v: 5^2
  amplitude ~ gamma(64.0, 1.6); // m: 40, v: 5^2
  saturation_limit_increase ~ gamma(1.0, 1.0); // m: 1, v: 1^2
  // Beta: m = a / (a + b)
  saturation_sharpness ~ beta(1.0, 1.0); // m: 0.5

  // Normal
  beta_c1 ~ normal(0.0, 0.25); // m: 0, s: 0.5
  beta_s1 ~ normal(0.0, 0.25); // m: 0, s: 0.5

  // von Mises: v = 1/k
  // Summer solstice ≈10 days from end of year
  phase ~ von_mises(0.17, 135.0); // m=2*pi*(10/365), v=(2*pi*(5/365))**2

  // Gamma: m = a/b, v = a/b^2 --> a = m^2/v, b = m/v
  real lambda = 0.15;
  for (n in 1:N) {
    target += log_sum_exp(
      log1m(lambda) + gamma_lpdf(weather_effect[n] | 5.0, 8.0), // m: 0.625, v: 0.28^2
      log(lambda) + gamma_lpdf(weather_effect[n] | 180.0, 200.0) // m: 0.9, v: 0.067^2
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
      saturation_sharpness
    );

  // Max/min optimal production (cloudless longest/shortest day)
  // weather_effect = 1.0, seasonal_oscillation = 1.0 / 0.0
  real E_optimal_max
    = saturation(
      [min + amplitude]',
      saturation_limit,
      saturation_sharpness
    )[1];
  real E_optimal_min
    = saturation(
      [min]',
      saturation_limit,
      saturation_sharpness
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
      saturation_sharpness
    );
}

// ----------------------------------------------------------------------------
