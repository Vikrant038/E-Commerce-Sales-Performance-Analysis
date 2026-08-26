/*
===============================================================================
Cumulative Analysis
===============================================================================
Purpose:
    - To calculate running totals or moving averages for key metrics.
    - To track performance over time cumulatively.
    - Useful for growth analysis or identifying long-term trends.
===============================================================================
*/

-- Calculate the total sales per month 
-- and the running total of sales over time 
SELECT
	order_month,
	monthly_sales,
	SUM(monthly_sales) OVER (ORDER BY order_month) AS running_total_sales,
	AVG(monthly_sales) OVER (ORDER BY order_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS moving_avg_3m_sales
FROM
(
    SELECT 
        DATETRUNC(month, order_date) AS order_month,
        SUM(sales_amount) AS monthly_sales,
        AVG(CAST(price AS FLOAT)) AS avg_unit_price
    FROM gold.fact_sales
    WHERE order_date IS NOT NULL
    GROUP BY DATETRUNC(month, order_date)
) t
ORDER BY order_month;
