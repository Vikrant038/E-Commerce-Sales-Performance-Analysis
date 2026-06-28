"""
Bronze -> Silver -> Gold cleaning pipeline (pandas).

@size-exception: cohesive-algorithm — a single end-to-end ETL pipeline (>200 lines).
The Silver transforms and Gold builders are one cohesive data flow; splitting across
files would obscure the Bronze->Silver->Gold lineage. @reviewer: PR review.

This is the Python counterpart to the SQL warehouse: it takes the **raw** CRM/ERP
extracts in ``datasets/bronze.*`` and reproduces the cleaned Silver layer and the
Gold star schema (``dim_customers``, ``dim_products``, ``fact_sales``). It exists
so the "messy data -> clean model" skill is *visible in this repo*, not just
assumed from the committed Gold CSVs.

Design choices (deliberate, not shortcuts):
- Each transform is a small pure function ``(bronze_df) -> clean_df`` so it can be
  unit-tested in isolation (see ``tests/test_clean.py``).
- No row is silently dropped except true duplicates and null primary keys; every
  other dirty value is *repaired*, mirroring the SQL.
- Outputs are written to a separate directory (default ``datasets/_rebuilt``),
  never over the committed ``datasets/gold.*`` artifacts (see agent.md "Never Do").

Run it:
    python -m src.clean                 # writes datasets/_rebuilt/gold.*.csv
    python -m src.clean --out /tmp/x    # custom output dir
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "datasets"

# ── Code → label lookups (mirror the SQL CASE expressions) ──────────────────
_MARITAL = {"M": "Married", "S": "Single"}
_GENDER = {"M": "Male", "F": "Female"}
_PRODUCT_LINE = {"M": "Mountain", "R": "Road", "S": "Other Sales", "T": "Touring"}
_COUNTRY = {"DE": "Germany", "US": "United States", "USA": "United States"}


def _read_bronze(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / f"bronze.{name}.csv", dtype=str, keep_default_na=False)


# ─────────────────────────────────────────────────────────────────────────────
# Silver transforms
# ─────────────────────────────────────────────────────────────────────────────
def clean_crm_cust_info(bronze: pd.DataFrame) -> pd.DataFrame:
    """Trim names, decode marital/gender, dedupe by latest record per customer."""
    df = bronze.copy()
    df = df[df["cst_id"].str.strip() != ""].copy()
    df["cst_id"] = df["cst_id"].astype(int)
    for col in ("cst_firstname", "cst_lastname"):
        df[col] = df[col].str.strip()
    df["cst_marital_status"] = (
        df["cst_marital_status"].str.strip().str.upper().map(_MARITAL).fillna("n/a")
    )
    df["cst_gndr"] = df["cst_gndr"].str.strip().str.upper().map(_GENDER).fillna("n/a")
    df["cst_create_date"] = pd.to_datetime(df["cst_create_date"], errors="coerce")
    # Keep the most recent record per customer (latest create_date wins).
    df = df.sort_values("cst_create_date").drop_duplicates("cst_id", keep="last")
    return df.reset_index(drop=True)


def clean_crm_prd_info(bronze: pd.DataFrame) -> pd.DataFrame:
    """Split the product key into category id + product number, decode line, fix cost."""
    df = bronze.copy()
    df["cat_id"] = df["prd_key"].str[:5].str.replace("-", "_", regex=False)
    df["prd_key"] = df["prd_key"].str[6:]
    df["prd_nm"] = df["prd_nm"].str.strip()
    df["prd_cost"] = pd.to_numeric(df["prd_cost"], errors="coerce").fillna(0).astype(int)
    df["prd_line"] = df["prd_line"].str.strip().str.upper().map(_PRODUCT_LINE).fillna("n/a")
    df["prd_start_dt"] = pd.to_datetime(df["prd_start_dt"], errors="coerce")
    df["prd_end_dt"] = pd.to_datetime(df["prd_end_dt"], errors="coerce")
    return df.reset_index(drop=True)


def _parse_yyyymmdd(raw_dates: pd.Series) -> pd.Series:
    """Integer-like YYYYMMDD -> date; 0, blanks, and wrong-length values -> NaT."""
    trimmed = raw_dates.str.strip()
    is_valid = trimmed.str.fullmatch(r"\d{8}") & (trimmed != "00000000")
    return pd.to_datetime(trimmed.where(is_valid), format="%Y%m%d", errors="coerce")


def clean_crm_sales_details(bronze: pd.DataFrame) -> pd.DataFrame:
    """Repair dates, and reconstruct sales/price where they are missing or inconsistent."""
    df = bronze.copy()
    for col in ("sls_order_dt", "sls_ship_dt", "sls_due_dt"):
        df[col] = _parse_yyyymmdd(df[col])
    for col in ("sls_sales", "sls_quantity", "sls_price"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    qty, price, sales = df["sls_quantity"], df["sls_price"], df["sls_sales"]
    # sales must equal quantity * |price|; otherwise recompute it.
    bad_sales = sales.isna() | (sales <= 0) | (sales != qty * price.abs())
    df["sls_sales"] = np.where(bad_sales, qty * price.abs(), sales)
    # price must be positive; derive from sales/quantity when it isn't.
    bad_price = price.isna() | (price <= 0)
    df["sls_price"] = np.where(
        bad_price, df["sls_sales"] / qty.replace(0, np.nan), price
    )
    df["sls_sales"] = df["sls_sales"].astype("Int64")
    df["sls_price"] = df["sls_price"].round().astype("Int64")
    return df.reset_index(drop=True)


def clean_erp_cust_az12(bronze: pd.DataFrame) -> pd.DataFrame:
    """Strip the 'NAS' key prefix, null out future birthdates, normalise gender."""
    df = bronze.copy()
    df["cid"] = df["cid"].str.replace(r"^NAS", "", regex=True).str.strip()
    df["bdate"] = pd.to_datetime(df["bdate"], errors="coerce")
    df.loc[df["bdate"] > pd.Timestamp.now(), "bdate"] = pd.NaT
    gender_raw = df["gen"].str.strip().str.upper()
    df["gen"] = np.select(
        [gender_raw.isin(["F", "FEMALE"]), gender_raw.isin(["M", "MALE"])],
        ["Female", "Male"],
        default="n/a",
    )
    return df.reset_index(drop=True)


def clean_erp_loc_a101(bronze: pd.DataFrame) -> pd.DataFrame:
    """Remove the dash from the key, standardise country names."""
    df = bronze.copy()
    df["cid"] = df["cid"].str.replace("-", "", regex=False).str.strip()
    country_raw = df["cntry"].str.strip()
    df["cntry"] = country_raw.map(_COUNTRY).fillna(country_raw.where(country_raw != "", "n/a"))
    return df.reset_index(drop=True)


def clean_erp_px_cat(bronze: pd.DataFrame) -> pd.DataFrame:
    """Category lookup is already clean — pass through with stripped values."""
    df = bronze.copy()
    for col in df.columns:
        df[col] = df[col].str.strip()
    return df.reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# Gold star schema (one builder per table, assembled by build_gold)
# ─────────────────────────────────────────────────────────────────────────────
def _build_dim_customers(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Customer dimension — CRM is master; gender falls back to ERP when CRM is n/a."""
    joined = silver["crm_cust_info"].merge(
        silver["erp_cust_az12"], left_on="cst_key", right_on="cid", how="left"
    ).merge(
        silver["erp_loc_a101"], left_on="cst_key", right_on="cid", how="left"
    )
    gender = np.where(
        joined["cst_gndr"] != "n/a", joined["cst_gndr"], joined["gen"].fillna("n/a")
    )
    dim_customers = pd.DataFrame(
        {
            "customer_id": joined["cst_id"],
            "customer_number": joined["cst_key"],
            "first_name": joined["cst_firstname"],
            "last_name": joined["cst_lastname"],
            "country": joined["cntry"].fillna("n/a"),
            "marital_status": joined["cst_marital_status"],
            "gender": gender,
            "birthdate": joined["bdate"],
            "create_date": joined["cst_create_date"],
        }
    ).sort_values("customer_id").reset_index(drop=True)
    dim_customers.insert(0, "customer_key", dim_customers.index + 1)
    return dim_customers


def _build_dim_products(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Product dimension — current version per product key, enriched with category."""
    latest = (
        silver["crm_prd_info"].sort_values("prd_start_dt")
        .drop_duplicates("prd_key", keep="last")
    )
    enriched = latest.merge(silver["erp_px_cat"], left_on="cat_id", right_on="id", how="left")
    dim_products = pd.DataFrame(
        {
            "product_id": enriched["prd_id"].astype(int),
            "product_number": enriched["prd_key"],
            "product_name": enriched["prd_nm"],
            "category_id": enriched["cat_id"],
            "category": enriched["cat"],
            "subcategory": enriched["subcat"],
            "maintenance": enriched["maintenance"],
            "cost": enriched["prd_cost"],
            "product_line": enriched["prd_line"],
            "start_date": enriched["prd_start_dt"],
        }
    ).sort_values("product_id").reset_index(drop=True)
    dim_products.insert(0, "product_key", dim_products.index + 1)
    return dim_products


def _build_fact_sales(
    silver: dict[str, pd.DataFrame],
    dim_products: pd.DataFrame,
    dim_customers: pd.DataFrame,
) -> pd.DataFrame:
    """Sales fact — resolve surrogate keys from the dimensions."""
    sales = silver["crm_sales_details"]
    sales_keyed = sales.copy()
    sales_keyed["sls_cust_id"] = pd.to_numeric(
        sales_keyed["sls_cust_id"], errors="coerce"
    ).astype("Int64")
    joined = sales_keyed.merge(
        dim_products[["product_key", "product_number"]],
        left_on="sls_prd_key", right_on="product_number", how="left",
    ).merge(
        dim_customers[["customer_key", "customer_id"]],
        left_on="sls_cust_id", right_on="customer_id", how="left",
    )
    return pd.DataFrame(
        {
            "order_number": sales["sls_ord_num"],
            "product_key": joined["product_key"],
            "customer_key": joined["customer_key"],
            "order_date": sales["sls_order_dt"],
            "shipping_date": sales["sls_ship_dt"],
            "due_date": sales["sls_due_dt"],
            "sales_amount": sales["sls_sales"],
            "quantity": sales["sls_quantity"],
            "price": sales["sls_price"],
        }
    )


def build_gold(silver: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Assemble the Gold star schema (dim_customers, dim_products, fact_sales)."""
    dim_customers = _build_dim_customers(silver)
    dim_products = _build_dim_products(silver)
    fact_sales = _build_fact_sales(silver, dim_products, dim_customers)
    return {
        "dim_customers": dim_customers,
        "dim_products": dim_products,
        "fact_sales": fact_sales,
    }


def run_pipeline() -> dict[str, pd.DataFrame]:
    """Full bronze -> silver -> gold run. Returns the three gold tables."""
    silver = {
        "crm_cust_info": clean_crm_cust_info(_read_bronze("crm_cust_info")),
        "crm_prd_info": clean_crm_prd_info(_read_bronze("crm_prd_info")),
        "crm_sales_details": clean_crm_sales_details(_read_bronze("crm_sales_details")),
        "erp_cust_az12": clean_erp_cust_az12(_read_bronze("erp_cust_az12")),
        "erp_loc_a101": clean_erp_loc_a101(_read_bronze("erp_loc_a101")),
        "erp_px_cat": clean_erp_px_cat(_read_bronze("erp_px_cat_g1v2")),
    }
    return build_gold(silver)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild the Gold layer from Bronze.")
    parser.add_argument(
        "--out", default=str(DATA_DIR / "_rebuilt"),
        help="Output directory (never the committed datasets/gold.* files).",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)
    gold_tables = run_pipeline()
    for table_name, table in gold_tables.items():
        destination = output_dir / f"gold.{table_name}.csv"
        table.to_csv(destination, index=False)
        LOGGER.info("wrote %s: %s rows -> %s", table_name, f"{len(table):,}", destination)


if __name__ == "__main__":
    main()
