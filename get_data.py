"""Download the Survey of Consumer Finances summary extracts (1989-2025) and
compute net worth by education of the family's reference person.

Source: Federal Reserve Board, Summary Extract Public Data, one CSV per survey
year. All years are published in 2025 dollars (CPI-U-RS, September of each
survey year). Each family appears five times (multiple imputation); as in the
Fed's own tables, statistics are computed on the five implicates pooled.

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
    if sorted((df[id_col] % 10).unique()) != [1, 2, 3, 4, 5]:
        raise ValueError(f"{year}: unexpected implicate ids")
    return df


def summarize(year: int, df: pd.DataFrame) -> list[dict]:
    rows = []
    for group, codes in GROUPS.items():
        sub = df[df["EDCL"].isin(codes)]
        x, w = sub["NETWORTH"].to_numpy(float), sub["WGT"].to_numpy(float)
        rows.append({
            "year": year,
            "group": group,
            "median_net_worth": weighted_median(x, w),
            "mean_net_worth": np.average(x, weights=w),
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
        rows += summarize(year, load_year(year))
    result = pd.DataFrame(rows)
    check_against_fed(result)
    result = result.round({"median_net_worth": 0, "mean_net_worth": 0, "share_of_families": 3})
    result.to_csv(OUT, index=False)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
