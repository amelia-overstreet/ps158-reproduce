"""Download the Survey of Consumer Finances summary extracts (1989-2025) and
compute net worth by education of the family's reference person.

Source: Federal Reserve Board, Summary Extract Public Data, one CSV per survey
year. All years are published in 2025 dollars (CPI-U-RS, September of each
survey year). Each family appears five times (multiple imputation); as in the
Fed's own tables, statistics are computed on the five implicates pooled.

Standard errors follow the Fed's MEANIT macro in the SCF codebook: sampling
variance from the 999 bootstrap replicate weights (weight x multiplicity,
first implicate only), plus imputation variance across the five implicates,
combined as SE = sqrt((6/5) * imputation variance + sampling variance).
The 95% margin of error is 1.96 x SE.

Groups use EDCL, the education of the reference person (the single adult, the
man in a mixed-sex couple, or the older partner in a same-sex couple):
    1 = no high-school diploma, 2 = high-school diploma or GED,
    3 = some college, 4 = bachelor's degree or more.
All families are included.

Output: data/net_worth_by_education.csv
"""

import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

YEARS = [1989, 1992, 1995, 1998, 2001, 2004, 2007, 2010, 2013, 2016, 2019, 2022, 2025]
EXTRACT_URL = "https://www.federalreserve.gov/econres/files/scfp{year}excel.zip"
# Replicate weights (Stata format). Files before 2001 use two-digit years.
REPLICATE_URL = "https://www.federalreserve.gov/econres/files/scf{yr}rw1s.zip"
N_REPLICATES = 999
# The Fed's own published tables by education (2025 dollars), used as a check.
FED_TABLES_URL = "https://www.federalreserve.gov/econres/scf/dataviz/download/zips/scf.zip"

RAW = Path("data/raw")
OUT = Path("data/net_worth_by_education.csv")

GROUPS = {
    "Bachelor's degree or more": [4],
    "High school or less": [1, 2],
    # Single categories, kept so they can be checked against the Fed's tables.
    "No high school diploma": [1],
    "High school diploma": [2],
    "Some college": [3],
}
FED_LABELS = {
    "No high school diploma": "No high school diploma",
    "High school diploma": "High school diploma",
    "Some college": "Some college",
    "Bachelor's degree or more": "College degree",
}
TOLERANCE = 0.01  # max relative gap from the Fed's published values


def download(url: str, dest: Path) -> Path:
    if not dest.exists():
        print(f"downloading {url}")
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    return dest


def read_csv_from_zip(path: Path, usecols=None) -> pd.DataFrame:
    """Read the single CSV inside a zip without extracting it to disk."""
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"{path}: expected one CSV, found {names}")
        with zf.open(names[0]) as f:
            return pd.read_csv(io.BytesIO(f.read()), usecols=usecols)


def weighted_median(x: np.ndarray, w: np.ndarray) -> float:
    order = np.argsort(x)
    x, w = x[order], w[order]
    cum = np.cumsum(w)
    return float(x[np.searchsorted(cum, cum[-1] / 2)])


def load_year(year: int) -> pd.DataFrame:
    path = download(EXTRACT_URL.format(year=year), RAW / f"scfp{year}excel.zip")
    with zipfile.ZipFile(path) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        header = pd.read_csv(zf.open(name), nrows=0).columns
    # The case/implicate id is Y1 in most years but X1 in 1989.
    id_col = "Y1" if "Y1" in header else "X1"
    missing = {id_col, "WGT", "EDCL", "NETWORTH"} - set(header)
    if missing:
        raise ValueError(f"{year}: missing columns {missing}")
    df = read_csv_from_zip(path, usecols=[id_col, "WGT", "EDCL", "NETWORTH"])
    df = df.rename(columns={id_col: "id"})
    df["implicate"] = df["id"] % 10
    if sorted(df["implicate"].unique()) != [1, 2, 3, 4, 5]:
        raise ValueError(f"{year}: unexpected implicate ids")
    return df


def load_replicates(year: int) -> pd.DataFrame:
    """Replicate weights times multiplicities, indexed by first-implicate id.

    A family not drawn in a replicate has missing values there; it gets 0.
    """
    yr = f"{year % 100:02d}" if year < 2001 else str(year)
    path = download(REPLICATE_URL.format(yr=yr), RAW / f"scf{yr}rw1s.zip")
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".dta")]
        if len(names) != 1:
            raise ValueError(f"{path}: expected one .dta file, found {names}")
        rw = pd.read_stata(io.BytesIO(zf.read(names[0])))
    rw.columns = rw.columns.str.lower()
    id_col = "y1" if "y1" in rw.columns else "x1"
    k = range(1, N_REPLICATES + 1)
    wt = rw[[f"wt1b{i}" for i in k]].fillna(0).clip(lower=0).to_numpy()
    mm = rw[[f"mm{i}" for i in k]].fillna(0).clip(lower=0).to_numpy()
    return pd.DataFrame(wt * mm, index=rw[id_col].astype(int))


def standard_errors(sub: pd.DataFrame, reps: pd.DataFrame) -> dict:
    """Standard errors of the median and mean of NETWORTH for one group."""
    by_imp = list(sub.groupby("implicate"))
    imp_median = [weighted_median(d["NETWORTH"].to_numpy(float), d["WGT"].to_numpy(float))
                  for _, d in by_imp]
    imp_mean = [np.average(d["NETWORTH"], weights=d["WGT"]) for _, d in by_imp]

    first = sub[sub["implicate"] == 1]
    w = reps.reindex(first["id"]).to_numpy()
    if np.isnan(w).any():
        raise ValueError("families missing from the replicate weight file")
    x = first["NETWORTH"].to_numpy(float)
    rep_mean = (w * x[:, None]).sum(axis=0) / w.sum(axis=0)
    order = np.argsort(x)
    cum = np.cumsum(w[order], axis=0)
    rep_median = x[order][np.argmax(cum >= cum[-1] / 2, axis=0)]

    def se(imp_values, rep_values):
        return np.sqrt(6 / 5 * np.var(imp_values, ddof=1) + np.var(rep_values, ddof=1))

    return {"median_se": se(imp_median, rep_median), "mean_se": se(imp_mean, rep_mean)}


def summarize(year: int, df: pd.DataFrame, reps: pd.DataFrame) -> list[dict]:
    rows = []
    for group, codes in GROUPS.items():
        sub = df[df["EDCL"].isin(codes)]
        x, w = sub["NETWORTH"].to_numpy(float), sub["WGT"].to_numpy(float)
        errors = standard_errors(sub, reps)
        rows.append({
            "year": year,
            "group": group,
            "median_net_worth": weighted_median(x, w),
            "median_se": errors["median_se"],
            "median_moe95": 1.96 * errors["median_se"],
            "mean_net_worth": np.average(x, weights=w),
            "mean_se": errors["mean_se"],
            "mean_moe95": 1.96 * errors["mean_se"],
            "share_of_families": w.sum() / df["WGT"].sum(),
            "n_families": len(sub) // 5,
        })
    return rows


def check_against_fed(result: pd.DataFrame) -> None:
    path = download(FED_TABLES_URL, RAW / "scf_dataviz.zip")
    ours = result[result["group"].isin(FED_LABELS)].copy()
    ours["fed_label"] = ours["group"].map(FED_LABELS)
    for stat in ["median", "mean"]:
        with zipfile.ZipFile(path) as zf:
            fed = pd.read_csv(zf.open(f"interactive_bulletin_charts_edcl_{stat}.csv"))
        fed = fed[["year", "Category", "Net_Worth"]].rename(columns={"Category": "fed_label"})
        fed["fed"] = fed["Net_Worth"] * 1000  # Fed tables are in thousands

        cmp = ours.merge(fed, on=["year", "fed_label"], how="left")
        if cmp["fed"].isna().any():
            raise ValueError("some year/group pairs have no Fed table value")
        cmp["rel_gap"] = cmp[f"{stat}_net_worth"] / cmp["fed"] - 1

        worst = cmp.loc[cmp["rel_gap"].abs().idxmax()]
        print(f"check {stat}s vs Fed tables: worst gap {worst['rel_gap']:+.1%} "
              f"({worst['year']}, {worst['group']})")
        bad = cmp[cmp["rel_gap"].abs() > TOLERANCE]
        if not bad.empty:
            print(bad[["year", "group", f"{stat}_net_worth", "fed", "rel_gap"]])
            raise SystemExit(f"{stat}s differ from the Fed's published tables")


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for year in YEARS:
        rows += summarize(year, load_year(year), load_replicates(year))
    result = pd.DataFrame(rows)
    check_against_fed(result)
    dollars = [c for c in result.columns if c.startswith(("median", "mean"))]
    result = result.round({**{c: 0 for c in dollars}, "share_of_families": 3})
    result.to_csv(OUT, index=False)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
