/*
===============================================================================
Database & Schema Initialization Script
===============================================================================
Purpose:
    - Creates the Medallion schemas (bronze, silver, gold).
    - Creates all Bronze, Silver, and Gold tables with proper data types.
    - Provides BULK INSERT templates for seeding data directly from CSV files.
===============================================================================
*/

-- =============================================================================
-- 1. Create Database & Schemas
-- =============================================================================
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'bronze')
    EXEC('CREATE SCHEMA bronze');
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'silver')
    EXEC('CREATE SCHEMA silver');
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'gold')
    EXEC('CREATE SCHEMA gold');
GO

-- =============================================================================
-- 2. Bronze Layer Tables (Raw Ingestion)
-- =============================================================================
IF OBJECT_ID('bronze.crm_cust_info', 'U') IS NOT NULL DROP TABLE bronze.crm_cust_info;
CREATE TABLE bronze.crm_cust_info (
    cst_id             NVARCHAR(50),
    cst_key            NVARCHAR(50),
    cst_firstname      NVARCHAR(50),
    cst_lastname       NVARCHAR(50),
    cst_marital_status NVARCHAR(50),
    cst_gndr           NVARCHAR(50),
    cst_create_date    NVARCHAR(50)
);
GO

IF OBJECT_ID('bronze.crm_prd_info', 'U') IS NOT NULL DROP TABLE bronze.crm_prd_info;
CREATE TABLE bronze.crm_prd_info (
    prd_id       NVARCHAR(50),
    prd_key      NVARCHAR(50),
    prd_nm       NVARCHAR(100),
    prd_cost     NVARCHAR(50),
    prd_line     NVARCHAR(50),
    prd_start_dt NVARCHAR(50),
    prd_end_dt   NVARCHAR(50)
);
GO

IF OBJECT_ID('bronze.crm_sales_details', 'U') IS NOT NULL DROP TABLE bronze.crm_sales_details;
CREATE TABLE bronze.crm_sales_details (
    sls_ord_num  NVARCHAR(50),
    sls_prd_key  NVARCHAR(50),
    sls_cust_id  NVARCHAR(50),
    sls_order_dt NVARCHAR(50),
    sls_ship_dt  NVARCHAR(50),
    sls_due_dt   NVARCHAR(50),
    sls_sales    NVARCHAR(50),
    sls_quantity NVARCHAR(50),
    sls_price    NVARCHAR(50)
);
GO

IF OBJECT_ID('bronze.erp_cust_az12', 'U') IS NOT NULL DROP TABLE bronze.erp_cust_az12;
CREATE TABLE bronze.erp_cust_az12 (
    cid   NVARCHAR(50),
    bdate NVARCHAR(50),
    gen   NVARCHAR(50)
);
GO

IF OBJECT_ID('bronze.erp_loc_a101', 'U') IS NOT NULL DROP TABLE bronze.erp_loc_a101;
CREATE TABLE bronze.erp_loc_a101 (
    cid   NVARCHAR(50),
    cntry NVARCHAR(50)
);
GO

IF OBJECT_ID('bronze.erp_px_cat_g1v2', 'U') IS NOT NULL DROP TABLE bronze.erp_px_cat_g1v2;
CREATE TABLE bronze.erp_px_cat_g1v2 (
    id          NVARCHAR(50),
    cat         NVARCHAR(50),
    subcat      NVARCHAR(50),
    maintenance NVARCHAR(50)
);
GO

-- =============================================================================
-- 3. Silver Layer Tables (Cleaned & Conformed)
-- =============================================================================
IF OBJECT_ID('silver.crm_cust_info', 'U') IS NOT NULL DROP TABLE silver.crm_cust_info;
CREATE TABLE silver.crm_cust_info (
    cst_id             INT,
    cst_key            NVARCHAR(50),
    cst_firstname      NVARCHAR(50),
    cst_lastname       NVARCHAR(50),
    cst_marital_status NVARCHAR(50),
    cst_gndr           NVARCHAR(50),
    cst_create_date    DATE,
    dwh_create_date    DATETIME2 DEFAULT GETDATE()
);
GO

IF OBJECT_ID('silver.crm_prd_info', 'U') IS NOT NULL DROP TABLE silver.crm_prd_info;
CREATE TABLE silver.crm_prd_info (
    prd_id          INT,
    cat_id          NVARCHAR(50),
    prd_key         NVARCHAR(50),
    prd_nm          NVARCHAR(100),
    prd_cost        INT,
    prd_line        NVARCHAR(50),
    prd_start_dt    DATE,
    prd_end_dt      DATE,
    dwh_create_date DATETIME2 DEFAULT GETDATE()
);
GO

IF OBJECT_ID('silver.crm_sales_details', 'U') IS NOT NULL DROP TABLE silver.crm_sales_details;
CREATE TABLE silver.crm_sales_details (
    sls_ord_num     NVARCHAR(50),
    sls_prd_key     NVARCHAR(50),
    sls_cust_id     INT,
    sls_order_dt    DATE,
    sls_ship_dt     DATE,
    sls_due_dt      DATE,
    sls_sales       INT,
    sls_quantity    INT,
    sls_price       INT,
    dwh_create_date DATETIME2 DEFAULT GETDATE()
);
GO

IF OBJECT_ID('silver.erp_cust_az12', 'U') IS NOT NULL DROP TABLE silver.erp_cust_az12;
CREATE TABLE silver.erp_cust_az12 (
    cid             NVARCHAR(50),
    bdate           DATE,
    gen             NVARCHAR(50),
    dwh_create_date DATETIME2 DEFAULT GETDATE()
);
GO

IF OBJECT_ID('silver.erp_loc_a101', 'U') IS NOT NULL DROP TABLE silver.erp_loc_a101;
CREATE TABLE silver.erp_loc_a101 (
    cid             NVARCHAR(50),
    cntry           NVARCHAR(50),
    dwh_create_date DATETIME2 DEFAULT GETDATE()
);
GO

IF OBJECT_ID('silver.erp_px_cat_g1v2', 'U') IS NOT NULL DROP TABLE silver.erp_px_cat_g1v2;
CREATE TABLE silver.erp_px_cat_g1v2 (
    id              NVARCHAR(50),
    cat             NVARCHAR(50),
    subcat          NVARCHAR(50),
    maintenance     NVARCHAR(50),
    dwh_create_date DATETIME2 DEFAULT GETDATE()
);
GO

-- =============================================================================
-- 4. Gold Layer Tables (Star Schema)
-- =============================================================================
IF OBJECT_ID('gold.fact_sales', 'U') IS NOT NULL DROP TABLE gold.fact_sales;
IF OBJECT_ID('gold.dim_customers', 'U') IS NOT NULL DROP TABLE gold.dim_customers;
IF OBJECT_ID('gold.dim_products', 'U') IS NOT NULL DROP TABLE gold.dim_products;

CREATE TABLE gold.dim_customers (
    customer_key    INT IDENTITY(1,1) PRIMARY KEY,
    customer_id     INT NOT NULL,
    customer_number NVARCHAR(50) NOT NULL,
    first_name      NVARCHAR(50),
    last_name       NVARCHAR(50),
    country         NVARCHAR(50),
    marital_status  NVARCHAR(50),
    gender          NVARCHAR(50),
    birthdate       DATE,
    create_date     DATE
);
GO

CREATE TABLE gold.dim_products (
    product_key    INT IDENTITY(1,1) PRIMARY KEY,
    product_id     INT NOT NULL,
    product_number NVARCHAR(50) NOT NULL,
    product_name   NVARCHAR(100),
    category_id    NVARCHAR(50),
    category       NVARCHAR(50),
    subcategory    NVARCHAR(50),
    maintenance    NVARCHAR(50),
    cost           INT,
    product_line   NVARCHAR(50),
    start_date     DATE
);
GO

CREATE TABLE gold.fact_sales (
    order_number  NVARCHAR(50) NOT NULL,
    product_key   INT NOT NULL FOREIGN KEY REFERENCES gold.dim_products(product_key),
    customer_key  INT NOT NULL FOREIGN KEY REFERENCES gold.dim_customers(customer_key),
    order_date    DATE,
    shipping_date DATE,
    due_date      DATE,
    sales_amount  INT,
    quantity      INT,
    price         INT
);
GO

-- =============================================================================
-- 5. Bulk Insert Seed Templates (Customize path as required)
-- =============================================================================
/*
BULK INSERT bronze.crm_cust_info
FROM '/path/to/datasets/bronze.crm_cust_info.csv'
WITH (FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '\n', TABLOCK);

BULK INSERT bronze.crm_prd_info
FROM '/path/to/datasets/bronze.crm_prd_info.csv'
WITH (FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '\n', TABLOCK);

BULK INSERT bronze.crm_sales_details
FROM '/path/to/datasets/bronze.crm_sales_details.csv'
WITH (FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '\n', TABLOCK);

BULK INSERT bronze.erp_cust_az12
FROM '/path/to/datasets/bronze.erp_cust_az12.csv'
WITH (FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '\n', TABLOCK);

BULK INSERT bronze.erp_loc_a101
FROM '/path/to/datasets/bronze.erp_loc_a101.csv'
WITH (FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '\n', TABLOCK);

BULK INSERT bronze.erp_px_cat_g1v2
FROM '/path/to/datasets/bronze.erp_px_cat_g1v2.csv'
WITH (FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '\n', TABLOCK);
*/
