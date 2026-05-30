from enum import StrEnum

from pydantic import AliasChoices, Field

from app.models.common import ApiModel, NonEmptyStr


class ChartType(StrEnum):
    bar = "bar"
    horizontal_bar = "horizontal_bar"
    line = "line"
    time_series_line = "line"
    scatter = "scatter"
    histogram = "histogram"
    correlation_heatmap = "correlation_heatmap"
    heatmap = "correlation_heatmap"
    box_plot = "box_plot"
    stacked_bar = "stacked_bar"


class Aggregation(StrEnum):
    sum = "sum"
    mean = "mean"
    median = "median"
    count = "count"
    none = "none"


class ChartSpec(ApiModel):
    id: NonEmptyStr
    dataset_id: NonEmptyStr
    title: NonEmptyStr
    chart_type: ChartType
    x_column: str | None = None
    y_column: str | None = None
    group_by: str | None = None
    description: NonEmptyStr
    reasoning: NonEmptyStr
    priority: int = Field(ge=1, le=100)
    chart_data: list[dict[str, object]] = Field(
        default_factory=list,
        validation_alias=AliasChoices("chart_data", "data"),
    )
