/*
===============================================================================
Performance Analysis (Year-over-Year, Month-over-Month)
===============================================================================
Purpose:
    - To measure the performance of products, customers, or regions over time.
    - For benchmarking and identifying high-performing entities.
    - To track yearly trends and growth.
===============================================================================
*/

/* Analyze the yearly performance of products by comparing their sales 
to both the average sales performance of the product and the true previous calendar year's sales */
WITH all_years AS (
    SELECT DISTINCT YEAR(order_date) AS order_year
    FROM gold.fact_sales
    WHERE order_date IS NOT NULL
),
all_products AS (
    SELECT DISTINCT product_key, product_name
    FROM gold.dim_products
),
product_year_matrix AS (
    SELECT 
        y.order_year,
        p.product_name,
        p.product_key
    FROM all_years y
    CROSS JOIN all_products p
),
yearly_product_sales AS (
    SELECT
        m.order_year,
        m.product_name,
        ISNULL(SUM(f.sales_amount), 0) AS current_sales
    FROM product_year_matrix m
    LEFT JOIN gold.fact_sales f
        ON m.product_key = f.product_key
        AND m.order_year = YEAR(f.order_date)
    GROUP BY 
        m.order_year,
        m.product_name
)
SELECT
    order_year,
    product_name,
    current_sales,
    AVG(current_sales) OVER (PARTITION BY product_name) AS avg_sales,
    current_sales - AVG(current_sales) OVER (PARTITION BY product_name) AS diff_avg,
    CASE 
        WHEN current_sales - AVG(current_sales) OVER (PARTITION BY product_name) > 0 THEN 'Above Avg'
        WHEN current_sales - AVG(current_sales) OVER (PARTITION BY product_name) < 0 THEN 'Below Avg'
        ELSE 'Avg'
    END AS avg_change,
    -- Year-over-Year Analysis
    LAG(current_sales) OVER (PARTITION BY product_name ORDER BY order_year) AS py_sales,
    current_sales - LAG(current_sales) OVER (PARTITION BY product_name ORDER BY order_year) AS diff_py,
    CASE 
        WHEN LAG(current_sales) OVER (PARTITION BY product_name ORDER BY order_year) IS NULL THEN 'New / No Prior Year'
        WHEN current_sales - LAG(current_sales) OVER (PARTITION BY product_name ORDER BY order_year) > 0 THEN 'Increase'
        WHEN current_sales - LAG(current_sales) OVER (PARTITION BY product_name ORDER BY order_year) < 0 THEN 'Decrease'
        ELSE 'No Change'
    END AS py_change
FROM yearly_product_sales
WHERE current_sales > 0 OR LAG(current_sales) OVER (PARTITION BY product_name ORDER BY order_year) > 0
ORDER BY product_name, order_year;
