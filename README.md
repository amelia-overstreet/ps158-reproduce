# Wealth gap by education, 1989–2025

How the net worth gap between U.S. families headed by a college graduate and
families headed by someone with a high-school education or less has changed
since 1989, using the Federal Reserve's Survey of Consumer Finances (SCF).

## Figure

**Figure 1** — [`figures/net_worth_by_education_median.png`](figures/net_worth_by_education_median.png):
median net worth for families whose reference person has a bachelor's degree or
more and for families whose reference person has a high-school education or
less, with 95% confidence intervals. Medians are used because they describe the
typical family; means, which the wealthiest families pull up, are still in the
data files for comparison.

Definitions:

- **Families:** all families in the survey. There is no filter on age or children.
- **Reference person:** the single adult, the man in a mixed-sex couple, or the
  older partner in a same-sex couple. Only this person's education counts.
- **High school or less:** no high-school diploma, or a diploma or GED. Families
  with some college are left out.
- **Dollars:** 2025 dollars, adjusted by the Federal Reserve with the CPI-U-RS.

## Data

All data are downloaded by `get_data.py` from the Federal Reserve Board's
[SCF page](https://www.federalreserve.gov/econres/scfindex.htm), for the 13
surveys from 1989 to 2025:

- **Summary extract public data** (`scfp{YEAR}excel.zip`): one CSV per survey,
  already in 2025 dollars. The script uses `NETWORTH`, `WGT` (survey weight),
  `EDCL` (education of the reference person) and the case ID.
- **Replicate weight files** (`scf{YEAR}rw1s.zip`, two-digit years before 2001):
  used for margins of error.
- **The Fed's published chart tables** (`scf.zip`): used only to check the
  results.

How the estimates are made:

- **Point estimates:** computed on all five imputed copies (implicates) of each
  family pooled, as the Fed does.
- **Standard errors:** follow the Fed's MEANIT macro in the SCF codebook. They
  combine sampling error from the 999 replicate weights with imputation error
  across the five implicates.

## Rerunning

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python get_data.py
.venv/bin/python plot.py
```

`get_data.py` downloads about 380 MB into `data/raw/` on the first run, about
350 MB of which is replicate weights. Later runs reuse the cached files. It then
writes:

- `data/net_worth_by_education.csv`: median and mean net worth, with standard
  errors and 95% margins of error, by year and education group.
- `data/net_worth_ratio.csv`: the bachelor's-or-more to high-school-or-less
  ratio of medians and of means, with margins of error.

The script stops if any single-category median or mean differs from the Fed's
published tables by more than 1%.

`plot.py` reads `data/net_worth_by_education.csv` and draws Figure 1 into
`figures/`.
