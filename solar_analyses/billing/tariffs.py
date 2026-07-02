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

from dataclasses import dataclass
from datetime import date, timedelta, time
from decimal import Decimal

from .schema import Tariff, extract_price_per_kwh

# -----------------------------------------------------------------------------

GST_RATE = Decimal("0.15")

# -----------------------------------------------------------------------------

_Periods = tuple[tuple[time, time], ...]


@dataclass(frozen=True, kw_only=True)
class _PeakPeriod:
    """Peak/off-peak time windows, optionally differing between weekdays and weekends."""

    weekday: _Periods
    weekend: _Periods

    def is_peak(self, *, hour: int, is_weekday: bool) -> bool:
        periods = self.weekday if is_weekday else self.weekend
        t = time(hour)
        return any(start <= t < end for start, end in periods)


# -----------------------------------------------------------------------------
# Aurora (i.e. network) peak/off-peak periods
# https://www.auroraenergy.co.nz/disclosures/pricing-methodologies

# "The peak periods on our networks are between 7am – 12pm (7 days per week) and
# 5pm – 10pm (7 days per week)."
_NETWORK_PEAK_PERIOD = _PeakPeriod(
    weekday=((time(7), time(12)), (time(17), time(22))),
    weekend=((time(7), time(12)), (time(17), time(22))),
)

# "Winter months: May to September (inclusive)"
_NETWORK_WINTER_MONTHS: frozenset[int] = frozenset(range(5, 10))

# -----------------------------------------------------------------------------
# Ecotricity (i.e. retailer) peak/off-peak periods

_RETAILER_IMPORT_PEAK_PERIOD = _PeakPeriod(
    weekday=((time(7), time(12)), (time(17), time(22))),
    weekend=((time(7), time(12)), (time(17), time(22))),
)
# "The PEAK period runs from 7am - 11am and 5pm - 9pm." (Monday–Friday only)
_RETAILER_EXPORT_PEAK_PERIOD = _PeakPeriod(
    weekday=((time(7), time(11)), (time(17), time(21))),
    weekend=(),
)

# -----------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class _TimeVaryingTariff:
    """
    Rate (NZD/kWh) for every hour of the day.

    Rates are indexed by hour (0-23) and whether the day is a weekday.
    """

    weekday: tuple[Decimal, ...]  # length 24
    weekend: tuple[Decimal, ...]  # length 24

    def __post_init__(self) -> None:
        if len(self.weekday) != 24 or len(self.weekend) != 24:
            raise ValueError(
                "weekday and weekend must each have exactly 24 hourly rates"
            )


@dataclass(frozen=True, kw_only=True)
class TariffSummary:
    """All-in effective rates for a single billing period."""

    daily: Decimal
    imports: _TimeVaryingTariff
    exports: _TimeVaryingTariff


# -----------------------------------------------------------------------------
# Helpers


def _import_rate(
    tariff: Tariff, *, hour: int, is_weekday: bool, is_winter: bool
) -> Decimal:
    network = tariff.network
    if network.kind == "flat":
        network_rate = network.import_rate
    else:
        network_rate = (
            network.winter.import_rate if is_winter else network.summer.import_rate
        )
    network_kwh = extract_price_per_kwh(
        network_rate,
        is_peak=_NETWORK_PEAK_PERIOD.is_peak(hour=hour, is_weekday=is_weekday),
    )

    retailer_rate = tariff.electricity.import_rate
    retailer_kwh = extract_price_per_kwh(
        retailer_rate,
        is_peak=_RETAILER_IMPORT_PEAK_PERIOD.is_peak(hour=hour, is_weekday=is_weekday),
    )
    if hasattr(retailer_rate, "loss_factor"):
        retailer_kwh *= retailer_rate.loss_factor

    return (network_kwh + retailer_kwh + tariff.other.authority_levy) * (1 + GST_RATE)


def _export_rate(
    tariff: Tariff, *, hour: int, is_weekday: bool, is_winter: bool
) -> Decimal:
    network = tariff.network
    if network.kind == "flat":
        network_rate = network.export_rate
    else:
        network_rate = (
            network.winter.export_rate if is_winter else network.summer.export_rate
        )
    network_kwh = extract_price_per_kwh(
        network_rate,
        is_peak=_NETWORK_PEAK_PERIOD.is_peak(hour=hour, is_weekday=is_weekday),
    )

    retailer_rate = tariff.electricity.export_rate
    retailer_kwh = extract_price_per_kwh(
        retailer_rate,
        is_peak=_RETAILER_EXPORT_PEAK_PERIOD.is_peak(hour=hour, is_weekday=is_weekday),
    )

    return (network_kwh + retailer_kwh) * (1 + GST_RATE)


# -----------------------------------------------------------------------------
# Public API


def _compute_tariff_summary(tariff: Tariff, is_winter: bool) -> TariffSummary:
    daily = (
        tariff.network.daily + tariff.electricity.daily + tariff.other.metering
    ) * (1 + GST_RATE)
    return TariffSummary(
        daily=daily,
        imports=_TimeVaryingTariff(
            weekday=tuple(
                _import_rate(tariff, hour=h, is_weekday=True, is_winter=is_winter)
                for h in range(24)
            ),
            weekend=tuple(
                _import_rate(tariff, hour=h, is_weekday=False, is_winter=is_winter)
                for h in range(24)
            ),
        ),
        exports=_TimeVaryingTariff(
            weekday=tuple(
                _export_rate(tariff, hour=h, is_weekday=True, is_winter=is_winter)
                for h in range(24)
            ),
            weekend=tuple(
                _export_rate(tariff, hour=h, is_weekday=False, is_winter=is_winter)
                for h in range(24)
            ),
        ),
    )


def _next_season_start(from_date: date) -> date:
    """Return the first day of the next month where the season differs from from_date."""
    is_winter = from_date.month in _NETWORK_WINTER_MONTHS
    year, month = from_date.year, from_date.month
    while True:
        month += 1
        if month > 12:
            year, month = year + 1, 1
        if (month in _NETWORK_WINTER_MONTHS) != is_winter:
            return date(year, month, 1)


def compute_tariff_summaries(tariff: Tariff) -> dict[tuple[date, date], TariffSummary]:
    """Split a tariff into seasonal sub-periods and return the tariff for each."""
    if tariff.network.kind == "flat":
        return {(tariff.start, tariff.end): _compute_tariff_summary(tariff, False)}

    result: dict[tuple[date, date], TariffSummary] = {}
    period_start = tariff.start
    while period_start <= tariff.end:
        is_winter = period_start.month in _NETWORK_WINTER_MONTHS
        next_start = _next_season_start(period_start)
        period_end = min(next_start - timedelta(days=1), tariff.end)
        result[(period_start, period_end)] = _compute_tariff_summary(tariff, is_winter)
        period_start = next_start

    return result


# -----------------------------------------------------------------------------
