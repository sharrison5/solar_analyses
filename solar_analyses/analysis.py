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


def compare_with_predictions(observations, predictions):
    """Combines the predictions with the observed monthly output."""

    predictions = predictions.rename(columns={"Production (kWh)": "Predicted (kWh)"})

    observations = (
        observations[["Total production"]]
        # Pull out some useful extra columns
        .assign(Month=lambda x: x.index.strftime("%b"), Year=lambda x: x.index.year)
        # Exclude early incomplete data
        .query("Year >= 2023")
        # Get the total for each month
        .groupby(["Year", "Month"])
        .aggregate("sum")
        # And collect statistics for each month, over the different years
        .groupby("Month")
        .aggregate(["min", "mean", "max"])
        # Tidy up column names
        .droplevel(0, axis="columns")
        .rename(
            columns={
                "min": "Min (kWh)",
                "mean": "Mean (kWh)",
                "max": "Max (kWh)",
            }
        )
    )

    # And combine!
    df = pd.concat([predictions, observations], axis="columns")
    return df


# -----------------------------------------------------------------------------
