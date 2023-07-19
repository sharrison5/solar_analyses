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

import pandas as pd

# -----------------------------------------------------------------------------


def load_report(path):
    """Loads a Fronius report into a pandas.DataFrame."""
    df = pd.read_csv(path, skiprows=[1])
    df["Date and time"] = pd.to_datetime(df["Date and time"], format="%d.%m.%Y")
    df = df.set_index("Date and time")
    return df


def load_predictions():
    """Loads the predicted monthly output into a pandas.DataFrame."""
    df = pd.read_csv("predicted_production.csv", index_col="Month")
    return df


# -----------------------------------------------------------------------------


def date_to_offset_in_year(dates):
    """Transform dates into the proportion of the current year that has passed."""
    return (dates.day_of_year - 1) / (365 + dates.is_leap_year)


# -----------------------------------------------------------------------------


def extract_posterior_timeseries(parameter, df, stan_fit):
    """Extract a posterior timeseries into a properly indexed DataFrame."""

    # Extract relevant columns
    ts = stan_fit.loc[:, stan_fit.columns.str.startswith(parameter)]
    # Convert "parameter.1", "parameter.2", etc. to numbers and sort
    ts = ts.rename(columns=lambda x: x.replace(f"{parameter}.", ""))
    ts.columns = ts.columns.astype(int)
    ts = ts.reindex(sorted(ts.columns), axis=1)
    # Replace with real dates
    ts.columns = df.index
    # And reshape!
    ts = ts.transpose()

    return ts


# -----------------------------------------------------------------------------
