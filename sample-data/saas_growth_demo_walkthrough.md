# Demo Walkthrough: SaaS Growth Sample

Use `saas_growth_sample.csv` to demonstrate InsightPilot end to end.

## 1. Upload

Start the backend and frontend, then open:

```text
http://localhost:3000/studio
```

Upload:

```text
sample-data/saas_growth_sample.csv
```

Expected upload result:

- 2,400 rows
- 14 columns
- Preview rows with real SaaS customer fields

## 2. Dataset Profile

Open Dataset Profile after upload.

Look for:

- `date` detected as datetime.
- `monthly_revenue`, `product_usage_score`, `support_tickets`, `churned`, `sales_cycle_days`, `discount_percentage`, and `nps_score` detected as numeric metrics.
- `company_size`, `region`, `acquisition_channel`, `plan`, and `signup_source` detected as dimensions.
- `customer_id` detected as ID-like.
- Duplicate rows reported.
- Missing value warnings for NPS, sales cycle, discounts, support tickets, usage score, and signup source.

## 3. Chart Gallery

Generate recommended charts.

Useful exhibits should include:

- Revenue over time.
- Revenue by plan.
- Revenue by region or acquisition channel.
- Distribution of monthly revenue.
- Scatter plots involving revenue, usage, tickets, churn, discount, or sales cycle when supported.
- Correlation heatmap across numeric metrics.

Use the include/exclude controls to keep exhibits that support the memo story.

## 4. Insight Board

Open the Insight Board and inspect evidence drawers.

Strong briefing angles:

- Revenue increased over time.
- Revenue is concentrated in Enterprise accounts.
- Revenue is concentrated in North America.
- Paid acquisition segments have lower usage and higher churn.
- Support ticket volume is associated with churn.
- Monthly revenue and support tickets contain outliers.
- Missing NPS and sales cycle values should be treated as data quality caveats.

The hidden story to look for:

```text
Paid acquisition scaled revenue, especially in the second half of 2025, but brought lower-quality customers with lower usage, more support tickets, higher discounts, lower NPS, and higher churn.
```

## 5. Report Preview

Generate the executive report.

The report should read like an analyst memo, not a dashboard export. It should:

- Summarize growth.
- Flag concentration risks.
- Separate acquisition volume from customer quality.
- Include data quality notes.
- Preserve evidence references.
- Avoid claims that are not backed by computed values.

## 6. Export

Use HTML export as the primary demo export.

PDF export is optional. If local PDF dependencies are not installed, the product should show a clear `PDF_EXPORT_UNAVAILABLE` response rather than pretending the PDF was generated.
