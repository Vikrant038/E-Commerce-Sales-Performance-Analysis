/*
===============================================================================
Stored Procedure: Load Silver Layer (Bronze -> Silver)
===============================================================================
Purpose:
    - Cleans, standardizes, deduplicates, and conforms data from Bronze to Silver.
===============================================================================
*/

CREATE OR ALTER PROCEDURE silver.load_silver AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @start_time DATETIME2 = GETDATE();
    PRINT '>> Loading Silver Layer...';

    -- 1. Clean CRM Customer Info
    PRINT '>> Truncating and loading silver.crm_cust_info...';
    TRUNCATE TABLE silver.crm_cust_info;
    INSERT INTO silver.crm_cust_info (
        cst_id, cst_key, cst_firstname, cst_lastname,
        cst_marital_status, cst_gndr, cst_create_date
    )
    SELECT
        cst_id,
        cst_key,
        TRIM(cst_firstname),
        TRIM(cst_lastname),
        CASE UPPER(TRIM(cst_marital_status))
            WHEN 'M' THEN 'Married'
            WHEN 'S' THEN 'Single'
            ELSE 'n/a'
        END,
        CASE UPPER(TRIM(cst_gndr))
            WHEN 'M' THEN 'Male'
            WHEN 'F' THEN 'Female'
            ELSE 'n/a'
        END,
        TRY_CAST(cst_create_date AS DATE)
    FROM (
        SELECT *,
            ROW_NUMBER() OVER (PARTITION BY cst_id ORDER BY TRY_CAST(cst_create_date AS DATE) DESC) as rn
        FROM bronze.crm_cust_info
        WHERE NULLIF(TRIM(cst_id), '') IS NOT NULL
    ) ranked
    WHERE rn = 1;

    -- 2. Clean CRM Product Info
    PRINT '>> Truncating and loading silver.crm_prd_info...';
    TRUNCATE TABLE silver.crm_prd_info;
    INSERT INTO silver.crm_prd_info (
        prd_id, cat_id, prd_key, prd_nm,
        prd_cost, prd_line, prd_start_dt, prd_end_dt
    )
    SELECT
        CAST(prd_id AS INT),
        REPLACE(SUBSTRING(prd_key, 1, 5), '-', '_'),
        SUBSTRING(prd_key, 7, LEN(prd_key)),
        TRIM(prd_nm),
        ISNULL(TRY_CAST(prd_cost AS INT), 0),
        CASE UPPER(TRIM(prd_line))
            WHEN 'M' THEN 'Mountain'
            WHEN 'R' THEN 'Road'
            WHEN 'S' THEN 'Other Sales'
            WHEN 'T' THEN 'Touring'
            ELSE 'n/a'
        END,
        TRY_CAST(prd_start_dt AS DATE),
        TRY_CAST(prd_end_dt AS DATE)
    FROM bronze.crm_prd_info;

    -- 3. Clean CRM Sales Details
    PRINT '>> Truncating and loading silver.crm_sales_details...';
    TRUNCATE TABLE silver.crm_sales_details;
    INSERT INTO silver.crm_sales_details (
        sls_ord_num, sls_prd_key, sls_cust_id,
        sls_order_dt, sls_ship_dt, sls_due_dt,
        sls_sales, sls_quantity, sls_price
    )
    SELECT
        sls_ord_num,
        sls_prd_key,
        TRY_CAST(sls_cust_id AS INT),
        CASE WHEN LEN(TRIM(sls_order_dt)) = 8 AND TRIM(sls_order_dt) != '00000000'
             THEN TRY_CAST(sls_order_dt AS DATE) ELSE NULL END,
        CASE WHEN LEN(TRIM(sls_ship_dt)) = 8 AND TRIM(sls_ship_dt) != '00000000'
             THEN TRY_CAST(sls_ship_dt AS DATE) ELSE NULL END,
        CASE WHEN LEN(TRIM(sls_due_dt)) = 8 AND TRIM(sls_due_dt) != '00000000'
             THEN TRY_CAST(sls_due_dt AS DATE) ELSE NULL END,
        CASE 
            WHEN sls_sales IS NULL OR TRY_CAST(sls_sales AS INT) <= 0 
                 OR TRY_CAST(sls_sales AS INT) != TRY_CAST(sls_quantity AS INT) * ABS(TRY_CAST(sls_price AS INT))
            THEN TRY_CAST(sls_quantity AS INT) * ABS(TRY_CAST(sls_price AS INT))
            ELSE TRY_CAST(sls_sales AS INT)
        END,
        TRY_CAST(sls_quantity AS INT),
        CASE
            WHEN sls_price IS NULL OR TRY_CAST(sls_price AS INT) <= 0
            THEN (TRY_CAST(sls_sales AS INT) / NULLIF(TRY_CAST(sls_quantity AS INT), 0))
            ELSE TRY_CAST(sls_price AS INT)
        END
    FROM bronze.crm_sales_details;

    -- 4. Clean ERP Customer AZ12
    PRINT '>> Truncating and loading silver.erp_cust_az12...';
    TRUNCATE TABLE silver.erp_cust_az12;
    INSERT INTO silver.erp_cust_az12 (cid, bdate, gen)
    SELECT
        CASE WHEN cid LIKE 'NAS%' THEN SUBSTRING(cid, 4, LEN(cid)) ELSE cid END,
        CASE WHEN TRY_CAST(bdate AS DATE) > '2014-01-31' THEN NULL ELSE TRY_CAST(bdate AS DATE) END,
        CASE UPPER(TRIM(gen))
            WHEN 'F' THEN 'Female'
            WHEN 'FEMALE' THEN 'Female'
            WHEN 'M' THEN 'Male'
            WHEN 'MALE' THEN 'Male'
            ELSE 'n/a'
        END
    FROM bronze.erp_cust_az12;

    -- 5. Clean ERP Location A101
    PRINT '>> Truncating and loading silver.erp_loc_a101...';
    TRUNCATE TABLE silver.erp_loc_a101;
    INSERT INTO silver.erp_loc_a101 (cid, cntry)
    SELECT
        REPLACE(cid, '-', ''),
        CASE UPPER(TRIM(cntry))
            WHEN 'DE' THEN 'Germany'
            WHEN 'US' THEN 'United States'
            WHEN 'USA' THEN 'United States'
            WHEN '' THEN 'n/a'
            WHEN NULL THEN 'n/a'
            ELSE TRIM(cntry)
        END
    FROM bronze.erp_loc_a101;

    -- 6. Clean ERP Product Categories
    PRINT '>> Truncating and loading silver.erp_px_cat_g1v2...';
    TRUNCATE TABLE silver.erp_px_cat_g1v2;
    INSERT INTO silver.erp_px_cat_g1v2 (id, cat, subcat, maintenance)
    SELECT TRIM(id), TRIM(cat), TRIM(subcat), TRIM(maintenance)
    FROM bronze.erp_px_cat_g1v2;

    PRINT '>> Silver Layer loaded successfully in ' + CAST(DATEDIFF(millisecond, @start_time, GETDATE()) AS VARCHAR) + ' ms.';
END;
GO
