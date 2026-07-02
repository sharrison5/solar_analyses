# -*- coding: utf-8 -*-

# SPDX-License-Identifier: Apache-2.0

# Copyright 2026 Sam Harrison
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

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------

_PricePerkWh = Annotated[Decimal, Field(ge=0)]
_PricePerDay = Annotated[Decimal, Field(ge=0)]


class _TimeVaryingRate(BaseModel):
    """Rate in NZD/kWh split by time-of-day period."""

    peak: _PricePerkWh
    off_peak: _PricePerkWh


_Rate = _TimeVaryingRate | _PricePerkWh


def extract_price_per_kwh(rate: _Rate, *, is_peak: bool) -> Decimal:
    """Map from a rate to a single NZD/kWh value."""
    if isinstance(rate, Decimal):
        return rate
    return rate.peak if is_peak else rate.off_peak


# -----------------------------------------------------------------------------


class _ImportExportRate(BaseModel):
    """Import and export rates."""

    import_rate: _Rate
    export_rate: _Rate = Decimal("0")


class _FlatNetworkCharges(_ImportExportRate):
    """Lines company charges with a single (non-seasonal) rate."""

    kind: Literal["flat"]
    daily: _PricePerDay


class _SeasonalNetworkCharges(BaseModel):
    """Lines company charges with separate winter/summer rates."""

    kind: Literal["seasonal"]
    daily: _PricePerDay
    winter: _ImportExportRate
    summer: _ImportExportRate


# -----------------------------------------------------------------------------


class _TimeVaryingRateWithLosses(_TimeVaryingRate):
    """Electricity import rate with an optional line-loss factor."""

    loss_factor: Annotated[Decimal, Field(gt=0)] = Decimal("1")
    """
    Multiplicative factor accounting for extra charges due to line losses.

    See e.g. https://www.auroraenergy.co.nz/disclosures/loss-factors
    """


class _ElectricityCharges(BaseModel):
    """Electricity retailer (Ecotricity) charges."""

    daily: _PricePerDay
    import_rate: _TimeVaryingRateWithLosses | _PricePerkWh
    export_rate: _Rate


# -----------------------------------------------------------------------------


class _OtherCharges(BaseModel):
    """Electricity Authority levy and metering charges."""

    authority_levy: _PricePerkWh
    metering: _PricePerDay


# -----------------------------------------------------------------------------


class Tariff(BaseModel):
    """All charges applicable over a contiguous billing period."""

    start: date  # inclusive
    end: date  # inclusive
    description: str | None = None
    network: Annotated[
        _FlatNetworkCharges | _SeasonalNetworkCharges, Field(discriminator="kind")
    ]
    electricity: _ElectricityCharges
    other: _OtherCharges


# -----------------------------------------------------------------------------
