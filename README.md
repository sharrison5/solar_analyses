# Solar Analyses

This repository contains an analysis of the energy production of an installed
solar system. A probabilistic model for energy output is inverted using
[(Py)Stan](https://mc-stan.org/).

All figures are clickable links to higher quality versions.


### System details

 + 16 x Hyundai HiE-S400VG panels (400W).
 + Fronius Primo GEN24 5.0 Inverter (5kW).
 + Fronius Ohmpilot (connected to 3kW element).
 + Installed in Dunedin, NZ.

---------

<a href="figures/production.pdf">
<img src="figures/production.jpg" width="90%">
</a>

**Figure**: Recorded energy production over the life of the system.

---------


### Model

The model assumes that the maximum available energy generation varies
sinusoidally over the course of the year, with each day's realised production
being a random fraction of this (i.e. dependent on the weather). The plots
below show the distributions over the key parameters.

---------

<a href="figures/optimal_production.pdf">
<img src="figures/optimal_production.jpg" width="90%">
</a>

**Figure**: Distribution of the theoretical maximum daily energy production
over the life of the system, plotted against the actual production.

---------

<a href="figures/weather_effect.pdf">
<img src="figures/weather_effect.jpg" width="90%">
</a>

<a href="figures/weather_effect_distribution.pdf">
<img src="figures/weather_effect_distribution.jpg" width="45%">
</a>

**Figure**: Proportion of the theoretical maximum daily energy production
actually achieved over the life of the system, and the marginal distribution of
this plotted against its prior.

---------
