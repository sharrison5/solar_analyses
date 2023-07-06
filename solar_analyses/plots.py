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

import matplotlib.pyplot as plt

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
