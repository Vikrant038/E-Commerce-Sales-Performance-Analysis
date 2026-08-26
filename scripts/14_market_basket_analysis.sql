/*
===============================================================================
Market Basket & Cross-Selling Affinity Analysis
===============================================================================
Purpose:
    - To identify frequent item co-occurrences within multi-item customer orders.
    - To discover attach-rate and cross-selling opportunities (e.g. Bikes -> Accessories).
===============================================================================
*/

-- 1. Co-Purchased Subcategory Combinations (Cross-Selling Pairs)
WITH order_subcategories AS (
    SELECT DISTINCT
        f.order_number,
        p.subcategory,
        p.category
    FROM gold.fact_sales f
    JOIN gold.dim_products p ON f.product_key = p.product_key
    WHERE f.order_date IS NOT NULL
)
SELECT TOP 15
    a.subcategory AS primary_item,
    b.subcategory AS attached_item,
    COUNT(*) AS times_bought_together,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(DISTINCT order_number) FROM order_subcategories WHERE subcategory = a.subcategory), 2) AS attach_rate_pct
FROM order_subcategories a
JOIN order_subcategories b
    ON a.order_number = b.order_number
    AND a.subcategory < b.subcategory  -- Prevent duplicate symmetrical pairs
GROUP BY a.subcategory, b.subcategory
ORDER BY times_bought_together DESC;

-- 2. Multi-Item Order Penetration by Year
WITH order_item_counts AS (
    SELECT
        YEAR(order_date) AS order_year,
        order_number,
        COUNT(DISTINCT product_key) AS unique_items_in_order,
        SUM(quantity) AS total_units_in_order
    FROM gold.fact_sales
    WHERE order_date IS NOT NULL
    GROUP BY YEAR(order_date), order_number
)
SELECT
    order_year,
    COUNT(order_number) AS total_orders,
    SUM(CASE WHEN unique_items_in_order > 1 THEN 1 ELSE 0 END) AS multi_item_orders,
    ROUND(100.0 * SUM(CASE WHEN unique_items_in_order > 1 THEN 1 ELSE 0 END) / COUNT(order_number), 2) AS multi_item_order_pct,
    ROUND(AVG(CAST(total_units_in_order AS FLOAT)), 2) AS avg_units_per_order
FROM order_item_counts
GROUP BY order_year
ORDER BY order_year;
