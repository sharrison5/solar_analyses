# Solar Analyses

This repository contains an analysis of the energy production of an installed
solar system. A probabilistic model for energy output is inverted using
[(Py)Stan](https://mc-stan.org/).

All figures are clickable links to higher quality versions.


### System details

 + 16 x Hyundai HiE-S400VG panels (400W).
 + Fronius Primo GEN24 5.0 Inverter (5kW).
   Connected as two strings: one for the 4 east facing panels, and the other
   for the 12 north facing panels (wired as two parallel sets of 6 panels).
 + Fronius Ohmpilot (connected to 3kW element).
 + Installed in Dunedin, NZ.

### Raw data

The average monthly output (as compared to the predictions as quoted) are
tabulated below, as well as a plot of the recorded daily output.

| Month   |   Predicted (kWh) |   Observed (kWh) |
|:--------|------------------:|-----------------:|
| Jan     |               805 |              987 |
| Feb     |               731 |              824 |
| Mar     |               568 |              714 |
| Apr     |               401 |              504 |
| May     |               251 |              360 |
| Jun     |               183 |              289 |
| Jul     |               238 |              311 |
| Aug     |               330 |              473 |
| Sep     |               516 |              599 |
| Oct     |               687 |              837 |
| Nov     |               827 |              836 |
| Dec     |               786 |              889 |

---------

<a href="figures/production.pdf">
<img src="figures/production.jpg" width="90%">
</a>

**Figure**: Recorded energy production over the life of the system.

---------


### Model

The model assumes that the maximum available energy generation varies
sinusoidally over the course of the year, with each day's realised production
being a random fraction of this (i.e. dependent on the weather). The below is a
sketch of the key components of the model:

 + Instantaneous phase: $\phi(t) = 2 \pi p(t) + \delta$, where $p(t)$
   represents the proportion of the current year that has passed and the phase
   $\delta$ represents the offset between the start of the year and the date of
   peak energy generation.

 + Seasonal oscillation:
   $s(t) = (\cos(\phi(t) + \beta_{c1}\cos(\phi(t)) + \beta_{s1}\sin(\phi(t))) + 1) / 2$.
   This is a dimensionless representation of the fluctuation in available
   energy over the year. The sinusoidal basis and $\beta$ terms allow the shape
   of the underlying sinusoidal oscillation to be tweaked.

 + Available energy: $E_{avail}(t) = a + b s(t)$ where $a$ represents the
   maximum possible energy production from the panels on the shortest day of
   the year, and $b$ represents the amplitude of the seasonal oscillation in
   kWh. The maximum achievable production will be less than this due to the
   limit to the power output from the inverter.

 + Weather effect: $w(t)$ represents the proportion of the theoretical optimal
   available energy that actually reaches the panels. This takes a prior which
   is a mixture of gamma distributions, to capture clear sunny days separately
   from those with cloud cover.

 + Realised production: $E(t) = \mathop{\text{sat}}(w(t) E_{avail}(t))$. The
   actual amount of energy generated is lower than the theoretical limit due to
   both the weather effect and the inverter clipping power output. The latter
   is modelled as
   $\mathop{\text{sat}}(e) = (-1 / \tau) \mathop{\text{LSE}}(- \tau e, - \tau \gamma)$
   where the LogSumExp function is used as a softmin of the incident energy and
   a hard upper limit on production $\gamma$. The sharpness of the transition
   between the linear and saturating regimes is governed by $\tau$.

 + Optimal production: $E_{opt}(t) = \mathop{\text{sat}}(E_{avail}(t))$
   is a convenience representation of the above. It illustrates what production
   would be achievable per day without weather effects.

The plots below show the distributions over the key parameters.

---------

<a href="figures/optimal_production.pdf">
<img src="figures/optimal_production.jpg" width="90%">
</a>

**Figure**: Distribution of the theoretical maximum daily energy production
($`E_{opt}(t)`$) over the life of the system, plotted against the actual
production.

---------

<a href="figures/annual_variation.pdf">
<img src="figures/annual_variation.jpg" width="90%">
</a>

**Figure**: Annual variation in available energy. This illustrates the
fluctuation in the theoretical limits to production over the year.

---------

<a href="figures/optimal_production_limits.pdf">
<img src="figures/optimal_production_limits.jpg" width="45%">
</a>
<a href="figures/annual_variation_saturation.pdf">
<img src="figures/annual_variation_saturation.jpg" width="45%">
</a>

<a href="figures/annual_variation_peak_date.pdf">
<img src="figures/annual_variation_peak_date.jpg" width="45%">
</a>
<a href="figures/annual_variation_betas.pdf">
<img src="figures/annual_variation_betas.jpg" width="45%">
</a>

**Figure**: Parameters controlling the optimal production curve
($`E_{opt}(t)`$).
**Top Left**: Posterior distribution over the maximum and minimum
of the optimal production curve ($`E_{opt}(t)`$).
**Top Right**: Posterior distribution over the saturation limit
($`\gamma`$) showing its correlation with the maximum available energy
($`a + b`$).
**Bottom Left**: Posterior distribution of the day of the year for which the
theoretical maximum daily energy production peaks ($`\arg\max(E_{opt}(t))`$).
**Bottom Right**: Posterior distribution of the $\beta$ terms that modulate the
shape of the sinusoid that the seasonal oscillation ($`s(t)`$) curve is based
on.

---------

<a href="figures/weather_effect.pdf">
<img src="figures/weather_effect.jpg" width="90%">
</a>

**Figure**: Impact of the weather effect ($`w(t)`$) on production over the life
of the system.

---------

<a href="figures/weather_effect_distribution.pdf">
<img src="figures/weather_effect_distribution.jpg" width="45%">
</a>
<a href="figures/weather_effect_autocorr.pdf">
<img src="figures/weather_effect_autocorr.jpg" width="45%">
</a>

**Figure**: Structure of the posterior over the weather effect terms.
**Left**: Marginal posterior distribution of the weather effect
($`w(t)`$) plotted against its prior.
**Right**: Autocorrelation of the posterior weather effect parameters
($`w(t)`$) over time.

---------
