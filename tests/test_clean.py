"""The bronze->silver->gold cleaning pipeline is correct and reproduces gold."""

from pathlib import Path

import pandas as pd
import pytest

from src import clean

DATA_DIR = Path(__file__).resolve().parent.parent / "datasets"


# ── Unit tests on individual transforms (no file I/O) ───────────────────────
def test_marital_and_gender_decode_and_trim():
    bronze = pd.DataFrame(
        {
            "cst_id": ["1", "2", "3"],
            "cst_key": ["AW1", "AW2", "AW3"],
            "cst_firstname": [" Jon", "Amy ", " Bo "],
            "cst_lastname": ["Yang ", " Lee", "X"],
            "cst_marital_status": ["M", "s", ""],
            "cst_gndr": ["M", "F", ""],
            "cst_create_date": ["2025-01-01", "2025-01-01", "2025-01-01"],
        }
    )
    out = clean.clean_crm_cust_info(bronze)
    assert out["cst_firstname"].tolist() == ["Jon", "Amy", "Bo"]
    assert out["cst_marital_status"].tolist() == ["Married", "Single", "n/a"]
    assert out["cst_gndr"].tolist() == ["Male", "Female", "n/a"]


def test_customer_dedup_keeps_latest():
    bronze = pd.DataFrame(
        {
            "cst_id": ["1", "1"],
            "cst_key": ["AW1", "AW1"],
            "cst_firstname": ["Old", "New"],
            "cst_lastname": ["X", "X"],
            "cst_marital_status": ["M", "S"],
            "cst_gndr": ["M", "F"],
            "cst_create_date": ["2020-01-01", "2025-01-01"],
        }
    )
    out = clean.clean_crm_cust_info(bronze)
    assert len(out) == 1
    assert out.iloc[0]["cst_firstname"] == "New"


def test_product_key_split():
    bronze = pd.DataFrame(
        {
            "prd_id": ["210"],
            "prd_key": ["CO-RF-FR-R92B-58"],
            "prd_nm": [" Frame "],
            "prd_cost": [""],
            "prd_line": ["R "],
            "prd_start_dt": ["2003-07-01"],
            "prd_end_dt": [""],
        }
    )
    out = clean.clean_crm_prd_info(bronze)
    assert out.iloc[0]["cat_id"] == "CO_RF"
    assert out.iloc[0]["prd_key"] == "FR-R92B-58"
    assert out.iloc[0]["prd_cost"] == 0  # null cost -> 0
    assert out.iloc[0]["prd_line"] == "Road"
    assert out.iloc[0]["prd_nm"] == "Frame"


def test_sales_reconstruction():
    bronze = pd.DataFrame(
        {
            "sls_ord_num": ["A", "B", "C"],
            "sls_prd_key": ["P", "P", "P"],
            "sls_cust_id": ["1", "1", "1"],
            "sls_order_dt": ["20130316", "0", "2013"],     # valid, zero, wrong-length
            "sls_ship_dt": ["20130323", "20130323", "20130323"],
            "sls_due_dt": ["20130328", "20130328", "20130328"],
            "sls_sales": ["25", "", "999"],   # ok, missing, inconsistent
            "sls_quantity": ["1", "2", "3"],
            "sls_price": ["25", "10", "-5"],  # ok, ok, negative
        }
    )
    out = clean.clean_crm_sales_details(bronze)
    assert pd.notna(out.iloc[0]["sls_order_dt"])
    assert pd.isna(out.iloc[1]["sls_order_dt"])  # "0" -> NaT
    assert pd.isna(out.iloc[2]["sls_order_dt"])  # wrong length -> NaT
    assert out.iloc[1]["sls_sales"] == 20        # 2 * 10 recomputed
    assert out.iloc[2]["sls_sales"] == 15        # 3 * |−5| recomputed
    assert out.iloc[2]["sls_price"] == 5         # negative -> positive via sales/qty


def test_erp_key_normalisation():
    az = clean.clean_erp_cust_az12(
        pd.DataFrame({"cid": ["NASAW00011000"], "bdate": ["1971-10-06"], "gen": ["F "]})
    )
    assert az.iloc[0]["cid"] == "AW00011000"
    assert az.iloc[0]["gen"] == "Female"

    loc = clean.clean_erp_loc_a101(
        pd.DataFrame({"cid": ["AW-00011000"], "cntry": ["US"]})
    )
    assert loc.iloc[0]["cid"] == "AW00011000"
    assert loc.iloc[0]["cntry"] == "United States"


# ── Integration: rebuilt gold matches the committed artifacts ────────────────
@pytest.fixture(scope="module")
def gold():
    return clean.run_pipeline()


def _committed(name):
    return pd.read_csv(DATA_DIR / f"gold.{name}.csv")


def test_rebuilt_row_counts_match_committed(gold):
    assert len(gold["dim_customers"]) == len(_committed("dim_customers"))
    assert len(gold["dim_products"]) == len(_committed("dim_products"))
    assert len(gold["fact_sales"]) == len(_committed("fact_sales"))


def test_rebuilt_has_no_orphan_keys(gold):
    fs = gold["fact_sales"]
    assert fs["customer_key"].notna().all()
    assert fs["product_key"].notna().all()


def test_rebuilt_revenue_within_tolerance(gold):
    # Exact-match isn't expected: ~30 dirty sales/price rows are reconstructed,
    # which can differ from the warehouse by a handful of euros. Assert it's
    # within 0.01% of the committed total.
    rebuilt = gold["fact_sales"]["sales_amount"].sum()
    committed = _committed("fact_sales")["sales_amount"].sum()
    assert abs(rebuilt - committed) / committed < 1e-4
