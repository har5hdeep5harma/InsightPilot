# InsightPilot Analytics Rules

Deterministic analytics rules will be documented here as they are implemented.

Every implemented rule must define:

- Inputs
- Thresholds
- Evidence fields
- Failure/skip conditions
- Related chart behavior

## Implemented Profiling Rules

The dataset profiler is deterministic and runs from the persisted parsed dataset artifact.

### Type Detection

- Numeric: values parse as numeric with at least 90% confidence.
- Boolean: non-empty values are mostly true/false-like values.
- Datetime: values parse as datetime with at least 85% confidence.
- Categorical: low-cardinality values with no stronger numeric/datetime/text signal.
- Text: long free-form strings or high-cardinality strings that do not look like IDs.
- Unknown: empty or insufficient signal.

### Role Detection

- Metric: numeric column with meaningful variation.
- Dimension: low-cardinality categorical or boolean column.
- Datetime: parseable datetime column.
- ID: ID-like column names or long sequential mostly unique numeric identifiers.
- Text: free-form text columns.
- Ignored: mostly missing or unprofileable columns.

### Warnings

- `HIGH_MISSINGNESS`
- `MOSTLY_MISSING_COLUMN`
- `CONSTANT_COLUMN`
- `POSSIBLE_ID_COLUMN`
- `HIGH_CARDINALITY`
- `DUPLICATE_ROWS`
- `SUSPICIOUS_DATE_PARSING`
- `NUMERIC_STORED_AS_TEXT`
- `SKEWED_DISTRIBUTION`

### Quality Score

The quality score starts at 100 and applies deterministic penalties for:

- dataset-level missing cells
- duplicate rows
- profile warnings

The final score is clamped from 0 to 100.

## Implemented Chart Recommendation Rules

The chart recommender runs from the persisted parsed dataset artifact and `DatasetProfile`.

### General Constraints

- Limit initial recommendations to at most 8 charts.
- Do not recommend charts for ID columns.
- Do not emit chart specs without directly renderable `chart_data`.
- Skip constant, mostly missing, or insufficient-variation columns.
- Use top-N aggregation for categorical charts.
- Prefer business-relevant metrics such as revenue, sales, profit, amount, cost, units, and quantity.
- Prefer business-relevant dimensions such as region, category, product, segment, market, and channel.

### Rules

- Time series line chart: at least one datetime column and one numeric metric.
- Bar chart: categorical dimension plus numeric metric; categories sorted by aggregate value and capped to top values.
- Horizontal concentration chart: categorical dimension with a meaningful top-category share, using metric aggregate or record count.
- Histogram: numeric metric with enough variation.
- Scatter plot: two numeric metrics with meaningful variation.
- Correlation heatmap: at least three numeric metrics.
- Box plot: one manageable categorical dimension and one numeric metric.
- Stacked bar chart: two manageable categorical dimensions and one numeric metric.

The recommender is deterministic and does not use an LLM.

## Implemented Insight Rules

The insight generator runs from the persisted parsed dataset artifact, `DatasetProfile`, and generated chart specs. It does not use an LLM.

### General Constraints

- Every insight must include a structured `evidence` object.
- Evidence must include the calculation, relevant columns, values or comparison values, and row counts where relevant.
- Weak signals are skipped.
- Output is capped at 12 insights.
- ID columns are not used as business metrics or dimensions.
- Recommendations use careful language and avoid unsupported causal claims.

### Rules

- Dataset quality: duplicate rows, substantial missingness, and low quality score.
- Trend: datetime plus numeric metric, comparing first period to last period with percentage change and direction.
- Top category and concentration: categorical dimension plus metric, grouped by sum or count with share of total.
- Outlier: IQR rule for numeric metrics.
- Correlation: strongest positive and negative Pearson correlations above absolute threshold 0.65.
- Distribution: skew, high relative variance, or concentration around zero.
- Missing data risk: important columns with missingness that may affect downstream charts or comparisons.
- Segment difference: highest versus lowest category-level mean, emitted only above a material ratio threshold.

## Implemented Executive Memo Rules

The executive memo generator uses deterministic templates by default. It may only use values from:

- dataset metadata
- dataset profile
- chart specs
- deterministic insights
- evidence objects

Generated sections:

- title
- dataset overview
- executive summary
- key findings
- risks
- opportunities
- recommended actions
- data quality notes
- charts included by ID
- evidence appendix

The generator avoids unsupported business claims and includes evidence references in key findings. Optional AI narrative polishing is disabled by default. When `ENABLE_AI_NARRATIVE=true` and a provider key is configured, the AI layer receives only structured deterministic report facts, must return JSON, and is rejected if it changes list lengths or introduces unsupported numeric values. Any provider error or validation failure falls back to the deterministic report.
