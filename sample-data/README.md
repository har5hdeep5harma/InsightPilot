# Sample Data

`sample_retail_sales.csv` is a small synthetic retail dataset for smoke testing the InsightPilot MVP.

`saas_growth_sample.csv` is the primary recruiter-grade demo dataset. It contains 2,400 synthetic SaaS customer records with realistic growth, segment differences, missing values, duplicates, outliers, churn relationships, and a hidden paid-acquisition quality story.

Supporting SaaS demo files:

- `generate_saas_growth_sample.py`: deterministic generator for the CSV.
- `saas_growth_sample_description.md`: dataset context, columns, and current facts.
- `saas_growth_expected_insights.md`: expected evidence-backed insight themes.
- `saas_growth_demo_walkthrough.md`: end-to-end demo flow through InsightPilot.

Generated reports and uploaded files should be written to ignored runtime folders:

```text
sample-data/uploads/
sample-data/exports/
```
