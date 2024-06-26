# inflation-macro
Use `conda env create -f environment.yml` to create virtual environment
Use `pip install -e .` in cmd to install package(s).
Run `conda activate inflation` to run virtual environment

## API access
You will need to create personal accounts on the different database's websites and request API credentials. Save them to a file named `.env` in a root folder.

See `.example_env` for how you should store the credentials.

<b>Make sure that the file name is exactly `.env` (nothing before the `.` nor after `env`) so that your credentials are not exposed in your git repository!</b>

# Survey data
CAMME (INSEE) -- (Translation from Andrade et al. (2023))
<b>Inflation expectations (qualitative)</b>
<i>In comparison with the past 12 months, how do you expect consumer prices will develop in the next 12 months? They will...</i>
1. Increase more rapidly, 2. Increase at the same rate, 3. Increase at a slower rate, 4. Stay about the same, 5. Fall, 6. Don’t Know.

<b>Inflation expectations (quantitative)</b>
<i>By how many percent do you think consumer prices will go up/down over the next 12 months? Consumer prices will increase/decrease by XX.X%</i>

<b>Personal consumption (last 12 months)</b>
<i>Have you made any major purchase over the last 12 months? (washing machine, refrigerator, furniture, dishwasher, ...)</i>
1. Yes, 2. No, 3. Don’t know.

<b>General consumption (current)</b>
<i>In view of the current general economic situation, do you think now is the right time for people to make major purchases (such as furniture, washing machines, electronic or computer equipment ...)?</i>
1. Yes, now is the right time, 2. It is neither the right time nor the wrong time, 3. No, it is the wrong time, 4. Don’t know.

# Simulated data
Simple cyclical income and consumption functions, per:
Ramsey, J. B., Gallegati, M., Gallegati, M., & Semmler, W. (2010). Instrumental variables and wavelet decompositions. Economic Modelling, 27(6), 1498–1513. https://doi.org/10.1016/j.econmod.2010.07.011

Continuous wavelet and cross-wavelet transforms
...

## References
Project structure inspired by [The Good Research Code Handbook](https://goodresearch.dev/#the-good-research-code-handbook) by Patrick Mineault.

Benchmarks models for time scale regression
Andrade, P., Gautier, E., & Mengus, E. (2023). What matters in households’ inflation expectations? Journal of Monetary Economics, 138(April), 50–68. https://doi.org/10.1016/j.jmoneco.2023.05.007

Coibion, O., Gorodnichenko, Y., & Weber, M. (2021). Monetary Policy Communications and Their Effects on Household Inflation Expectations. SSRN Electronic Journal. https://doi.org/10.2139/ssrn.3338818
