"""
============================================================
Chile CO2 Dashboard - Data Preprocessing Script
Assignment: Climate Change, Sustainability and Development
TISS BS Analytics and Sustainability Studies (2024-28)
Student: Shikhar Srivastava | M2024BSASS026 | Chile
============================================================
USAGE:
  Keep this script in the project root next to app.py.
  Your Excel files must be in:  <project>/data/
  Cleaned CSVs will be saved to: <project>/data/processed/
  Then run:
      python Preprocessing.py
============================================================
"""

import os
import warnings
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────
# 0.  CONFIGURATION  ← only change things in this block
# ─────────────────────────────────────────────────────────────

YEAR_START = 1999
YEAR_END   = 2024

_BASE = os.path.dirname(os.path.abspath(__file__))
# Folder where your Excel files live (same as dashboard app.py)
RAW_DIR = os.path.join(_BASE, "data")

# Folder where cleaned CSVs will be saved (created automatically)
PROCESSED_DIR = os.path.join(_BASE, "data", "processed")

# Exact filenames on your disk (with spaces, as they actually appear)
FILE_CHILE    = "Chile Dataset (CCSD).xlsx"
FILE_ANNUAL   = "Annual CO2 emissions.xlsx"
FILE_PERCAP   = "CO2 Emission per-capita Dataset.xlsx"
FILE_ENERGY   = "Co2 emissions per unit energy.xlsx"
FILE_CUMUL    = "Cumulative CO2 Emissions.xlsx"
FILE_SHARED   = "Shared Annual CO2 emissions.xlsx"

# Countries to include in the comparison / dashboard charts
COMPARATOR_COUNTRIES = [
    "Chile",
    "World",
    "India",
    "United States",
    "China",
    "Brazil",
    "South Africa",
    "Germany",
    "Norway",
]

os.makedirs(PROCESSED_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────
# 1.  HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────

def load_raw(filename: str) -> pd.DataFrame:
    """Load a raw Excel file from RAW_DIR."""
    path = os.path.join(RAW_DIR, filename)
    if not os.path.exists(path):
        # List what IS in the folder to help the user debug
        try:
            available = os.listdir(RAW_DIR)
            available_xlsx = [f for f in available if f.endswith(".xlsx")]
        except Exception:
            available_xlsx = ["(could not read folder)"]
        raise FileNotFoundError(
            f"\n[ERROR] File not found:\n  {path}"
            f"\n\nExcel files found in {RAW_DIR}:\n  "
            + "\n  ".join(available_xlsx) if available_xlsx
            else f"\n  (none found — check RAW_DIR path)"
        )
    print(f"  ↳ Loading: {filename}")
    return pd.read_excel(path)


def filter_years(df: pd.DataFrame, year_col: str = "year") -> pd.DataFrame:
    return df[(df[year_col] >= YEAR_START) & (df[year_col] <= YEAR_END)].copy()


def remove_duplicates(df: pd.DataFrame, subset: list) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates(subset=subset)
    removed = before - len(df)
    if removed:
        print(f"  ↳ Removed {removed} duplicate rows")
    return df


def fill_missing_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """
    Linear interpolation within each country group.
    Edge NaNs are forward-/back-filled.
    Compatible with pandas 3.x.
    """
    num_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c != "year"]
    if "country" in df.columns:
        for col in num_cols:
            df[col] = (
                df.groupby("country")[col]
                .transform(
                    lambda s: s
                    .interpolate(method="linear", limit_direction="both")
                    .ffill()
                    .bfill()
                )
            )
    else:
        df[num_cols] = (
            df[num_cols]
            .interpolate(method="linear", limit_direction="both")
            .ffill()
            .bfill()
        )
    return df


def report_missing(df: pd.DataFrame):
    total   = df.shape[0] * df.shape[1]
    missing = df.isnull().sum().sum()
    pct     = 100 * missing / total if total else 0
    print(f"  ↳ Missing values: {missing}/{total} ({pct:.2f}%)")


def save_csv(df: pd.DataFrame, filename: str):
    path = os.path.join(PROCESSED_DIR, filename)
    df.to_csv(path, index=False)
    print(f"  ✔  Saved → {path}  [{len(df)} rows × {df.shape[1]} cols]")


# ─────────────────────────────────────────────────────────────
# 2.  CLEAN CHILE MAIN DATASET
# ─────────────────────────────────────────────────────────────

def clean_chile_main():
    print("\n[1/7]  Cleaning Chile Main Dataset (CCSD)...")

    df = load_raw(FILE_CHILE)

    # Drop columns that are entirely empty
    df = df.dropna(axis=1, how="all")

    # Rename to clean snake_case
    rename_map = {
        "Country":                                                      "country",
        "Code":                                                         "code",
        "Year":                                                         "year",
        "Population, Total":                                            "population",
        "GDP per capita (current US$) ":                                "gdp_per_capita_usd",
        "GDP per capita (current US$)":                                 "gdp_per_capita_usd",
        "GDP per capita growth (annual %) ":                            "gdp_per_capita_growth_pct",
        "GDP per capita growth (annual %)":                             "gdp_per_capita_growth_pct",
        "GDP (current US$) ":                                           "gdp_usd",
        "GDP (current US$)":                                            "gdp_usd",
        "CO2 emissions per Capita (in tonnes)":                         "co2_per_capita_t",
        "Annual CO2 Emissions (in tonnes)":                             "annual_co2_t",
        "Share of global annual CO2 emissions (in tonnes)":             "share_global_annual_co2_pct",
        "Cumulative CO2 emissions (in tonnes)":                         "cumulative_co2_t",
        "Share of global cumulative CO2 emissions (in tonnes)":         "share_global_cumulative_co2_pct",
        "Territorial emissions (in tonnes)":                            "territorial_co2_t",
        "Consumption-based emissions (in tonnes)":                      "consumption_co2_t",
        "Flaring (in tonnes)":                                          "flaring_co2_t",
        "Cement (in tonnes)":                                           "cement_co2_t",
        "Gas (in tonnes)":                                              "gas_co2_t",
        "Oil (in tonnes)":                                              "oil_co2_t",
        "Coal (in tonnes)":                                             "coal_co2_t",
        "Annual CO2 emissions per unit energy (kg per kilowatt-hour)":  "co2_per_unit_energy_kg_kwh",
        "Human Development Index (HDI)":                                "hdi",
    }
    df = df.rename(columns=rename_map)

    # Keep only recognised columns
    keep = [v for v in rename_map.values() if v in df.columns]
    # Deduplicate keep list while preserving order
    seen = set()
    keep = [c for c in keep if not (c in seen or seen.add(c))]
    df   = df[keep]

    # Filter years
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = filter_years(df, year_col="year")
    df["year"] = df["year"].astype(int)

    # Numeric coercion
    for col in df.columns:
        if col not in ("country", "code"):
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = remove_duplicates(df, subset=["country", "year"])
    report_missing(df)
    df = fill_missing_numeric(df)
    df = df.sort_values("year").reset_index(drop=True)

    print(f"  ↳ Shape: {df.shape} | Years: {df['year'].min()}–{df['year'].max()}")
    save_csv(df, "chile_main_clean.csv")
    return df


# ─────────────────────────────────────────────────────────────
# 3.  CLEAN GLOBAL SUPPORTING DATASETS
# ─────────────────────────────────────────────────────────────

def clean_global_dataset(filename, raw_col, clean_col, output_filename, step_label):
    """Generic cleaner for the four global files: Entity | Code | Year | <metric>"""
    print(f"\n{step_label}  Cleaning {filename}...")

    df = load_raw(filename)

    # Rename
    rename_map = {
        "Entity": "country",
        "Code":   "code",
        "Year":   "year",
        raw_col:  clean_col,
    }
    df = df.rename(columns=rename_map)

    # Filter years BEFORE selecting columns
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = filter_years(df, year_col="year")

    # Keep needed columns only
    df = df[["country", "code", "year", clean_col]].copy()

    # Type coercion
    df["year"]    = df["year"].astype(int)
    df[clean_col] = pd.to_numeric(df[clean_col], errors="coerce")

    df = remove_duplicates(df, subset=["country", "year"])
    report_missing(df)
    df = fill_missing_numeric(df)
    df = df.sort_values(["country", "year"]).reset_index(drop=True)

    print(f"  ↳ Shape: {df.shape} | Countries: {df['country'].nunique()} | "
          f"Years: {df['year'].min()}–{df['year'].max()}")
    save_csv(df, output_filename)
    return df


# ─────────────────────────────────────────────────────────────
# 4.  BUILD COMBINED WORLD DATASET
# ─────────────────────────────────────────────────────────────

def build_world_combined(dfs: dict):
    print("\n[7/7]  Building combined world dataset...")

    combined = None
    for col_name, df in dfs.items():
        subset = df[["country", "code", "year", col_name]]
        combined = subset if combined is None else pd.merge(
            combined, subset, on=["country", "code", "year"], how="outer"
        )

    combined = combined.sort_values(["country", "year"]).reset_index(drop=True)
    report_missing(combined)
    print(f"  ↳ Shape: {combined.shape}")
    save_csv(combined, "world_combined_clean.csv")

    # Chile + comparators subset
    comp_df = combined[combined["country"].isin(COMPARATOR_COUNTRIES)].copy().reset_index(drop=True)
    found   = sorted(comp_df["country"].unique().tolist())
    print(f"  ↳ Comparator countries found: {found}")
    save_csv(comp_df, "chile_vs_comparators_clean.csv")

    return combined


# ─────────────────────────────────────────────────────────────
# 5.  MAIN PIPELINE
# ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  CHILE CO2 DASHBOARD  ─  DATA PREPROCESSING PIPELINE")
    print("=" * 60)
    print(f"  Year range  : {YEAR_START}–{YEAR_END}")
    print(f"  Raw data    : {RAW_DIR}")
    print(f"  Output      : {PROCESSED_DIR}")

    chile_df  = clean_chile_main()

    annual_df = clean_global_dataset(
        filename        = FILE_ANNUAL,
        raw_col         = "Annual CO2 emissions",
        clean_col       = "annual_co2_t",
        output_filename = "world_annual_co2_clean.csv",
        step_label      = "[2/7]",
    )

    percap_df = clean_global_dataset(
        filename        = FILE_PERCAP,
        raw_col         = "CO2 Emissions per capita (t)",
        clean_col       = "co2_per_capita_t",
        output_filename = "world_per_capita_clean.csv",
        step_label      = "[3/7]",
    )

    energy_df = clean_global_dataset(
        filename        = FILE_ENERGY,
        raw_col         = "Annual CO2 emissions per unit energy (kg per kilowatt-hour)",
        clean_col       = "co2_per_unit_energy_kg_kwh",
        output_filename = "world_per_unit_energy_clean.csv",
        step_label      = "[4/7]",
    )

    cumul_df  = clean_global_dataset(
        filename        = FILE_CUMUL,
        raw_col         = "Cumulative CO2 emissions",
        clean_col       = "cumulative_co2_t",
        output_filename = "world_cumulative_clean.csv",
        step_label      = "[5/7]",
    )

    shared_df = clean_global_dataset(
        filename        = FILE_SHARED,
        raw_col         = "Share of global annual CO2 emissions",
        clean_col       = "share_global_annual_co2_pct",
        output_filename = "world_shared_annual_clean.csv",
        step_label      = "[6/7]",
    )

    build_world_combined({
        "annual_co2_t":               annual_df,
        "co2_per_capita_t":           percap_df,
        "co2_per_unit_energy_kg_kwh": energy_df,
        "cumulative_co2_t":           cumul_df,
        "share_global_annual_co2_pct": shared_df,
    })

    print("\n" + "=" * 60)
    print("  ✅  ALL PREPROCESSING COMPLETE")
    print(f"  Cleaned files saved to: {PROCESSED_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
    
    