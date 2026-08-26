/*
===============================================================================
Logistics & Shipping Operations Analysis
===============================================================================
Purpose:
    - To analyze delivery lead times, on-time shipment rates, and fulfillment delays.
    - To identify operational bottlenecks across categories and destination countries.
===============================================================================
*/

-- 1. Overall Delivery & On-Time Performance KPIs
SELECT
    COUNT(*) AS total_shipments,
    SUM(CASE WHEN shipping_date <= due_date THEN 1 ELSE 0 END) AS on_time_shipments,
    SUM(CASE WHEN shipping_date > due_date THEN 1 ELSE 0 END) AS late_shipments,
    ROUND(100.0 * SUM(CASE WHEN shipping_date <= due_date THEN 1 ELSE 0 END) / COUNT(*), 2) AS on_time_rate_pct,
    AVG(DATEDIFF(day, order_date, shipping_date)) AS avg_days_to_ship,
    MAX(DATEDIFF(day, order_date, shipping_date)) AS max_days_to_ship
FROM gold.fact_sales
WHERE order_date IS NOT NULL AND shipping_date IS NOT NULL;

-- 2. Shipping Turnaround & On-Time Rate by Product Category
SELECT
    p.category,
    COUNT(f.order_number) AS total_orders,
    AVG(DATEDIFF(day, f.order_date, f.shipping_date)) AS avg_ship_days,
    SUM(CASE WHEN f.shipping_date <= f.due_date THEN 1 ELSE 0 END) AS on_time_orders,
    ROUND(100.0 * SUM(CASE WHEN f.shipping_date <= f.due_date THEN 1 ELSE 0 END) / COUNT(*), 2) AS on_time_pct
FROM gold.fact_sales f
LEFT JOIN gold.dim_products p ON f.product_key = p.product_key
WHERE f.order_date IS NOT NULL AND f.shipping_date IS NOT NULL
GROUP BY p.category
ORDER BY on_time_pct DESC;

-- 3. Fulfillment Performance by Destination Country
SELECT
    c.country,
    COUNT(f.order_number) AS total_orders,
    AVG(DATEDIFF(day, f.order_date, f.shipping_date)) AS avg_ship_days,
    SUM(CASE WHEN f.shipping_date > f.due_date THEN 1 ELSE 0 END) AS delayed_orders,
    ROUND(100.0 * SUM(CASE WHEN f.shipping_date <= f.due_date THEN 1 ELSE 0 END) / COUNT(*), 2) AS on_time_pct
FROM gold.fact_sales f
LEFT JOIN gold.dim_customers c ON f.customer_key = c.customer_key
WHERE f.order_date IS NOT NULL AND f.shipping_date IS NOT NULL
GROUP BY c.country
ORDER BY total_orders DESC;
