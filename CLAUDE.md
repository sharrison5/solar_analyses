# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Overview

This is a Bayesian statistical analysis of a residential solar installation in
Dunedin, New Zealand. This is a personal project so the focus is on learning
new techniques rather than producing a production-ready library.

The pipeline is:

1. **Data loading** (`utilities.py`) — reads monthly Fronius inverter CSV
   reports from `reports/` and a `predicted_production.csv` from the installer
2. **Analysis** (`analysis.py`) — basic descriptive statistics, e.g. compares
   actual vs. predicted monthly production
3. **Modelling** (`modelling.py` + `model.stan`) — fits a Bayesian model via
   CmdStanPy; the model infers seasonal variation, inverter saturation, and a
   mixture-of-gammas weather effect
4. **Plotting** (`plots.py`) — generates figures as both JPG and PDF into
   `figures/`

`analyses.py` is the single entry point that runs all four stages in sequence.

## Commands

Run the full analysis pipeline:
```bash
CMDSTAN=.cmdstan/cmdstan-2.38.0 uv run analyses.py
```
You can assume CmdStan is already available.

Lint, format, etc.:
```bash
uv run ruff check
uv run ruff format
```
Note that these will also be run as pre-commit hooks.

There are no automated tests in this project.

## Stan Model

The core of the project is `solar_analyses/model.stan`, which models daily
energy production as:

- **Available energy:** sinusoidal seasonal curve with shape modulation
  (`beta_c1`, `beta_s1`)
- **Weather effect:** mixture of two gamma distributions (clear ~85%, cloudy
  ~15%)
- **Saturation:** smooth tanh-based function modeling inverter clipping at the
  5 kW limit
- **Realized production:** `saturation(weather × available_energy)`

`solar_equations.py` provides physics-based solar radiation calculations (from
Duffie & Beckman 2013) used to justify the core modelling decisions but is
currently unused by the main analysis scripts.

## Key conventions

- Package manager is `uv` (Python pinned in `.python-version`); use `uv run`
  for all commands
- CmdStan is installed locally in `.cmdstan/` and referenced via the `CMDSTAN`
  env var at runtime
- The compiled Stan model binary (`solar_analyses/model`) is in `.gitignore`
  and rebuilt automatically
- Figures are committed to the repo; reports CSV data is committed as the data
  source
