# Expected Insights: SaaS Growth Sample

These are the kinds of insights InsightPilot should be able to surface from `saas_growth_sample.csv`. Exact wording may vary because the backend ranks deterministic insights by evidence strength, but the claims below are encoded in the data and can be verified from the CSV.

## Revenue Growth

Monthly revenue rises over the dataset period.

- January 2024 revenue: 359,725.52
- December 2025 revenue: 775,039.71
- Change: 115.5%
- Evidence columns: `date`, `monthly_revenue`

Expected report angle: revenue is growing, but the source and quality of that growth should be reviewed before treating it as durable.

## Revenue Concentration By Plan

Enterprise accounts dominate revenue.

- Enterprise revenue share: 78.1%
- Business revenue share: 17.3%
- Growth revenue share: 4.0%
- Starter revenue share: 0.6%
- Evidence columns: `plan`, `monthly_revenue`

Expected report angle: the business depends heavily on enterprise revenue, so segment retention and large-account concentration deserve attention.

## Revenue Concentration By Region

North America contributes the majority of revenue.

- North America revenue share: 53.8%
- Europe revenue share: 25.3%
- APAC revenue share: 14.3%
- Evidence columns: `region`, `monthly_revenue`

Expected report angle: geographic concentration may be acceptable, but expansion planning should compare quality and retention across smaller regions.

## Hidden Story: Paid Growth Quality Risk

Paid acquisition expands in the second half of 2025 and brings revenue growth, but customer quality is weaker.

2024 paid acquisition:

- Paid row share: 28.5%
- Paid revenue share: 12.6%
- Paid churn rate: 25.0%
- Non-paid churn rate: 7.5%
- Paid average usage score: 57.9
- Non-paid average usage score: 79.1

Second half of 2025 paid acquisition:

- Paid row share: 40.7%
- Paid revenue share: 23.8%
- Paid churn rate: 38.0%
- Non-paid churn rate: 10.0%
- Paid average usage score: 54.5
- Non-paid average usage score: 78.1

Evidence columns: `date`, `acquisition_channel`, `monthly_revenue`, `product_usage_score`, `support_tickets`, `discount_percentage`, `churned`, `nps_score`

Expected report angle: paid channels helped scale acquisition and revenue, but they brought lower-usage customers with materially higher churn.

## Usage And Churn Relationship

Lower product usage is associated with churn.

- Correlation between `product_usage_score` and `churned`: -0.318
- Paid Social average usage score: 51.01
- Paid Social churn rate: 41%
- Referral average usage score: 81.75
- Referral churn rate: 8%

Expected report angle: activation and product adoption are likely important health indicators.

## Support Burden And Churn Relationship

Higher support ticket volume is associated with churn.

- Correlation between `support_tickets` and `churned`: 0.501
- Paid Social average support tickets: 5.46
- Paid Search average support tickets: 4.73
- Referral average support tickets: 2.20
- Organic Search average support tickets: 2.19

Expected report angle: support burden may be a risk signal, especially in paid acquisition cohorts.

## Data Quality Notes

The dataset contains realistic issues that should appear in profiling or quality notes.

- Exact duplicate rows: 25
- Missing `nps_score`: 286 rows
- Missing `sales_cycle_days`: 243 rows
- Missing `discount_percentage`: 121 rows
- Missing `support_tickets`: 80 rows
- Missing `product_usage_score`: 54 rows
- Missing `signup_source`: 39 rows

Expected report angle: analysis using NPS, sales cycle, discount, support tickets, usage, or signup source should mention reduced sample size.

## Outliers

The dataset includes intentional outliers.

- Monthly revenue values above 50,000: 12 rows
- Support ticket values of 30 or higher: 14 rows
- Discount values of 50% or higher: 10 rows

Expected report angle: averages can be distorted; inspect outlier records before making segment-level claims.
