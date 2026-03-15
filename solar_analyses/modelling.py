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

from pathlib import Path
from cmdstanpy import CmdStanModel

from solar_analyses import utilities

# -----------------------------------------------------------------------------


def fit_model(df):
    """Estimates the posterior over key parameters using Stan."""
    stan_data = {
        "N": len(df),
        "production": (df["Total production"]).to_numpy(),
        "t_year": utilities.date_to_offset_in_year(df.index).to_numpy(),
    }

    stan_file = Path(__file__).parent / "model.stan"
    stan_model = CmdStanModel(stan_file=stan_file)

    stan_fit = stan_model.sample(
        data=stan_data,
        chains=4,
        parallel_chains=4,
        iter_warmup=5000,
        iter_sampling=5000,
        thin=25,
        inits={
            "min": 20.0,
            "amplitude": 40.0,
            "phase": 0.17,
            "beta_c1": 0.0,
            "beta_s1": 0.0,
        },
    )
    # print(stan_fit.summary())

    return stan_fit.stan_variables()


# -----------------------------------------------------------------------------
