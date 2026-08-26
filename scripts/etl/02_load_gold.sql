/*
===============================================================================
Stored Procedure: Load Gold Layer (Silver -> Gold)
===============================================================================
Purpose:
    - Assembles the dimensional star schema (dim_customers, dim_products, fact_sales)
    - Rebuilds surrogate keys and resolves relationships.
===============================================================================
*/

CREATE OR ALTER PROCEDURE gold.load_gold AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @start_time DATETIME2 = GETDATE();
    PRINT '>> Loading Gold Layer...';

    -- 1. Dim Customers
    PRINT '>> Truncating and loading gold.dim_customers...';
    TRUNCATE TABLE gold.dim_customers;
    INSERT INTO gold.dim_customers (
        customer_id, customer_number, first_name, last_name,
        country, marital_status, gender, birthdate, create_date
    )
    SELECT
        ci.cst_id,
        ci.cst_key,
        ci.cst_firstname,
        ci.cst_lastname,
        ISNULL(la.cntry, 'n/a'),
        ci.cst_marital_status,
        CASE WHEN ci.cst_gndr != 'n/a' THEN ci.cst_gndr ELSE ISNULL(ca.gen, 'n/a') END,
        ca.bdate,
        ci.cst_create_date
    FROM silver.crm_cust_info ci
    LEFT JOIN silver.erp_cust_az12 ca ON ci.cst_key = ca.cid
    LEFT JOIN silver.erp_loc_a101 la ON ci.cst_key = la.cid
    ORDER BY ci.cst_id;

    -- 2. Dim Products
    PRINT '>> Truncating and loading gold.dim_products...';
    TRUNCATE TABLE gold.dim_products;
    INSERT INTO gold.dim_products (
        product_id, product_number, product_name, category_id,
        category, subcategory, maintenance, cost, product_line, start_date
    )
    SELECT
        pn.prd_id,
        pn.prd_key,
        pn.prd_nm,
        pn.cat_id,
        pc.cat,
        pc.subcat,
        pc.maintenance,
        pn.prd_cost,
        pn.prd_line,
        pn.prd_start_dt
    FROM (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY prd_key ORDER BY prd_start_dt DESC) as rn
        FROM silver.crm_prd_info
    ) pn
    LEFT JOIN silver.erp_px_cat_g1v2 pc ON pn.cat_id = pc.id
    WHERE pn.rn = 1
    ORDER BY pn.prd_id;

    -- 3. Fact Sales
    PRINT '>> Truncating and loading gold.fact_sales...';
    TRUNCATE TABLE gold.fact_sales;
    INSERT INTO gold.fact_sales (
        order_number, product_key, customer_key,
        order_date, shipping_date, due_date,
        sales_amount, quantity, price
    )
    SELECT
        sd.sls_ord_num,
        dp.product_key,
        dc.customer_key,
        sd.sls_order_dt,
        sd.sls_ship_dt,
        sd.sls_due_dt,
        sd.sls_sales,
        sd.sls_quantity,
        sd.sls_price
    FROM silver.crm_sales_details sd
    LEFT JOIN gold.dim_products dp ON sd.sls_prd_key = dp.product_number
    LEFT JOIN gold.dim_customers dc ON sd.sls_cust_id = dc.customer_id
    ORDER BY sd.sls_order_dt, sd.sls_ord_num;

    PRINT '>> Gold Layer loaded successfully in ' + CAST(DATEDIFF(millisecond, @start_time, GETDATE()) AS VARCHAR) + ' ms.';
END;
GO
