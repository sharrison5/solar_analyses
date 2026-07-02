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
from pathlib import Path

import yaml

from solar_analyses.billing.schema import Tariff
from solar_analyses.billing.tariffs import TariffSummary, compute_tariff_summaries

# -----------------------------------------------------------------------------

INDENT = "  "


def tick_header(prefix_width: int) -> str:
    return " " * prefix_width + (" " * 11).join(f"{h:02d}" for h in (0, 6, 12, 18, 24))


def print_tariff(
    start: date, end: date, summary: TariffSummary, description: str | None
) -> None:
    rows: list[tuple[str, tuple[Decimal, ...]]] = [
        ("import weekday", summary.imports.weekday),
        ("import weekend", summary.imports.weekend),
        ("export weekday", summary.exports.weekday),
        ("export weekend", summary.exports.weekend),
    ]

    seen: dict[Decimal, str] = {}
    for _, rates in rows:
        for r in rates:
            if r not in seen:
                seen[r] = chr(ord("A") + len(seen))

    col_width = max(len(label) for label, _ in rows) + len(": ")
    header = tick_header(len(INDENT) + col_width)

    def format_row(label: str, rates: tuple[Decimal, ...]) -> str:
        blocks = [
            " ".join(seen[r] for r in rates[b * 6 : (b + 1) * 6]) for b in range(4)
        ]
        return INDENT + (label + ":").ljust(col_width) + "  " + "  ".join(blocks)

    print(f"{start} to {end}")
    if description:
        print(description)
    print()
    print(header)
    for label, rates in rows:
        print(format_row(label, rates))
    print()
    print("Rates (inc. GST, losses)")
    for rate, letter in sorted(seen.items(), key=lambda x: x[1]):
        print(f"  {letter}: ${rate:.6f}/kWh")
    print(f"  Daily charge: ${summary.daily:.6f}/day")


# -----------------------------------------------------------------------------

with Path("tariffs.yaml").open() as f:
    raw_tariffs = yaml.safe_load(f)

print("-" * 80)
print()
for raw_tariff in raw_tariffs:
    tariff = Tariff.model_validate(raw_tariff)

    for (start, end), summary in compute_tariff_summaries(tariff).items():
        print_tariff(start, end, summary, tariff.description)
        print()
        print("-" * 80)

# -----------------------------------------------------------------------------
