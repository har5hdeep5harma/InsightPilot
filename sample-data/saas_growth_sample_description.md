# SaaS Growth Sample Dataset

File: `saas_growth_sample.csv`

This synthetic dataset represents 2,400 SaaS customer records from January 2024 through December 2025. It is designed for demonstrating InsightPilot's deterministic profiling, chart recommendations, evidence-backed insights, and report generation.

## Business Context

The fictional company sells a B2B SaaS product across four plans:

- Starter
- Growth
- Business
- Enterprise

Customers arrive through organic, referral, paid, partner, and content channels. The company grew top-line monthly revenue during 2025, but the growth was not uniformly healthy.

## Encoded Patterns

- Revenue trends upward over time as customer volume grows.
- Paid Search and Paid Social become a larger share of acquisition in the second half of 2025.
- Paid acquisition contributes more revenue later in the period, but those customers have lower usage, higher support burden, higher discounts, weaker NPS, and higher churn.
- Enterprise customers create substantial revenue concentration by plan.
- North America creates substantial revenue concentration by region.
- Product usage score is negatively associated with churn.
- Support tickets are positively associated with churn.
- High discounts are more common in paid channels.
- Enterprise and partner-led customers have longer sales cycles.

## Data Quality Features

The file intentionally includes realistic data quality issues:

- 25 exact duplicate rows.
- Missing values in `nps_score`, `sales_cycle_days`, `discount_percentage`, `support_tickets`, `product_usage_score`, and `signup_source`.
- Monthly revenue outliers from large enterprise contracts.
- Support ticket outliers from distressed customers.
- High discount outliers in paid acquisition channels.

## Columns

- `date`: customer signup or observation date.
- `customer_id`: customer identifier.
- `company_size`: SMB, Mid-Market, or Enterprise.
- `region`: customer region.
- `acquisition_channel`: acquisition source group.
- `plan`: purchased SaaS plan.
- `monthly_revenue`: monthly recurring revenue associated with the customer.
- `product_usage_score`: 0-100 engagement score.
- `support_tickets`: number of support tickets in the observation period.
- `churned`: numeric churn flag, `1.0` for churned and `0.0` for retained.
- `signup_source`: more granular source label.
- `sales_cycle_days`: days from lead creation to purchase.
- `discount_percentage`: discount applied to the account.
- `nps_score`: customer NPS score.

## Current Dataset Facts

- Rows: 2,400
- Columns: 14
- Exact duplicate rows: 25
- Total monthly revenue represented: 11,724,714.13
- Enterprise plan revenue share: 78.1%
- North America revenue share: 53.8%
- Product usage to churn correlation: -0.318
- Support tickets to churn correlation: 0.501
- January 2024 monthly revenue: 359,725.52
- December 2025 monthly revenue: 775,039.71
- Revenue change from January 2024 to December 2025: 115.5%

The dataset is deterministic. Re-run `python sample-data/generate_saas_growth_sample.py` from the repository root to regenerate the same CSV.
