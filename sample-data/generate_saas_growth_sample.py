from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path


SEED = 20260518
TARGET_ROWS_BEFORE_DUPLICATES = 2375
DUPLICATE_ROWS = 25
OUTPUT_PATH = Path(__file__).with_name("saas_growth_sample.csv")


CHANNELS = [
    "Organic Search",
    "Referral",
    "Paid Search",
    "Paid Social",
    "Partner",
    "Content",
]
REGIONS = ["North America", "Europe", "APAC", "Latin America", "Middle East & Africa"]
COMPANY_SIZES = ["SMB", "Mid-Market", "Enterprise"]
PLANS = ["Starter", "Growth", "Business", "Enterprise"]


def main() -> None:
    random.seed(SEED)
    rows: list[dict[str, str]] = []
    customer_number = 1

    monthly_targets = _monthly_targets()
    for month_index, monthly_count in enumerate(monthly_targets):
        month_start = _add_months(date(2024, 1, 1), month_index)
        for _ in range(monthly_count):
            rows.append(_make_customer_row(customer_number, month_index, month_start))
            customer_number += 1

    rows = rows[:TARGET_ROWS_BEFORE_DUPLICATES]
    _inject_outliers(rows)

    duplicate_source_indexes = random.sample(range(150, len(rows) - 150), DUPLICATE_ROWS)
    for index in duplicate_source_indexes:
        rows.append(dict(rows[index]))

    rows.sort(key=lambda row: (row["date"], row["customer_id"]))
    _write_csv(rows)


def _monthly_targets() -> list[int]:
    counts: list[int] = []
    for month_index in range(24):
        trend = 51 + month_index * 3
        seasonal = 8 if month_index % 12 in {0, 1, 8, 9} else 0
        year_two_push = 13 if month_index >= 12 else 0
        paid_campaign_push = 16 if month_index >= 16 else 0
        final_month_adjustment = 7 if month_index == 23 else 0
        counts.append(
            trend
            + seasonal
            + year_two_push
            + paid_campaign_push
            + final_month_adjustment
        )
    return counts


def _make_customer_row(customer_number: int, month_index: int, month_start: date) -> dict[str, str]:
    channel = _weighted_choice(_channel_weights(month_index))
    company_size = _company_size(channel)
    plan = _plan(company_size, channel)
    region = _region(company_size, channel)
    signup_source = _signup_source(channel)
    discount = _discount(channel, plan, month_index)
    sales_cycle_days = _sales_cycle_days(company_size, channel, plan)
    usage_score = _usage_score(channel, company_size, plan, discount, month_index)
    support_tickets = _support_tickets(usage_score, company_size, channel)
    churned = _churned(usage_score, support_tickets, channel, plan, discount, month_index)
    if churned:
        support_tickets = min(38, support_tickets + random.randint(1, 5))
    nps_score = _nps_score(usage_score, support_tickets, channel, churned)
    monthly_revenue = _monthly_revenue(plan, company_size, channel, region, discount, month_index)

    row = {
        "date": _random_day_in_month(month_start).isoformat(),
        "customer_id": f"CUST-{customer_number:05d}",
        "company_size": company_size,
        "region": region,
        "acquisition_channel": channel,
        "plan": plan,
        "monthly_revenue": _money(monthly_revenue),
        "product_usage_score": _number(usage_score, 1),
        "support_tickets": str(support_tickets),
        "churned": "1.0" if churned else "0.0",
        "signup_source": signup_source,
        "sales_cycle_days": str(sales_cycle_days),
        "discount_percentage": _number(discount, 1),
        "nps_score": str(nps_score),
    }
    _apply_missing_values(row, channel, plan)
    return row


def _channel_weights(month_index: int) -> list[tuple[str, float]]:
    paid_ramp = min(1.0, max(0.0, (month_index - 8) / 15))
    return [
        ("Organic Search", 0.28 - 0.08 * paid_ramp),
        ("Referral", 0.23 - 0.07 * paid_ramp),
        ("Paid Search", 0.17 + 0.12 * paid_ramp),
        ("Paid Social", 0.09 + 0.12 * paid_ramp),
        ("Partner", 0.16 - 0.02 * paid_ramp),
        ("Content", 0.07 - 0.01 * paid_ramp),
    ]


def _company_size(channel: str) -> str:
    if channel == "Partner":
        return _weighted_choice([("SMB", 0.12), ("Mid-Market", 0.43), ("Enterprise", 0.45)])
    if channel == "Referral":
        return _weighted_choice([("SMB", 0.32), ("Mid-Market", 0.45), ("Enterprise", 0.23)])
    if channel == "Paid Social":
        return _weighted_choice([("SMB", 0.70), ("Mid-Market", 0.24), ("Enterprise", 0.06)])
    if channel == "Paid Search":
        return _weighted_choice([("SMB", 0.49), ("Mid-Market", 0.38), ("Enterprise", 0.13)])
    return _weighted_choice([("SMB", 0.48), ("Mid-Market", 0.36), ("Enterprise", 0.16)])


def _plan(company_size: str, channel: str) -> str:
    if company_size == "Enterprise":
        return _weighted_choice([("Business", 0.34), ("Enterprise", 0.66)])
    if company_size == "Mid-Market":
        return _weighted_choice([("Growth", 0.36), ("Business", 0.51), ("Enterprise", 0.13)])
    if channel == "Paid Social":
        return _weighted_choice([("Starter", 0.58), ("Growth", 0.35), ("Business", 0.07)])
    return _weighted_choice([("Starter", 0.46), ("Growth", 0.43), ("Business", 0.11)])


def _region(company_size: str, channel: str) -> str:
    weights = {
        "North America": 0.45,
        "Europe": 0.25,
        "APAC": 0.18,
        "Latin America": 0.08,
        "Middle East & Africa": 0.04,
    }
    if company_size == "Enterprise":
        weights["North America"] += 0.07
        weights["Europe"] += 0.03
        weights["Latin America"] -= 0.04
        weights["Middle East & Africa"] -= 0.02
    if channel == "Partner":
        weights["Europe"] += 0.04
        weights["APAC"] += 0.03
        weights["North America"] -= 0.07
    return _weighted_choice(list(weights.items()))


def _signup_source(channel: str) -> str:
    sources = {
        "Organic Search": [("Website SEO", 0.76), ("Blog", 0.18), ("Marketplace", 0.06)],
        "Referral": [("Customer Referral", 0.82), ("Founder Network", 0.18)],
        "Paid Search": [("Google Ads", 0.78), ("Bing Ads", 0.12), ("Retargeting", 0.10)],
        "Paid Social": [("LinkedIn Ads", 0.54), ("Meta Ads", 0.36), ("Retargeting", 0.10)],
        "Partner": [("Solutions Partner", 0.68), ("Reseller", 0.32)],
        "Content": [("Webinar", 0.46), ("Whitepaper", 0.34), ("Newsletter", 0.20)],
    }
    return _weighted_choice(sources[channel])


def _discount(channel: str, plan: str, month_index: int) -> float:
    base = {
        "Organic Search": 4,
        "Referral": 3,
        "Paid Search": 13,
        "Paid Social": 18,
        "Partner": 8,
        "Content": 6,
    }[channel]
    if plan == "Enterprise":
        base += 5
    if month_index >= 16 and channel in {"Paid Search", "Paid Social"}:
        base += 6
    return _clamp(random.gauss(base, 5), 0, 45)


def _sales_cycle_days(company_size: str, channel: str, plan: str) -> int:
    base = {"SMB": 13, "Mid-Market": 34, "Enterprise": 78}[company_size]
    if channel in {"Paid Search", "Paid Social"} and plan in {"Starter", "Growth"}:
        base -= 7
    if channel == "Partner":
        base += 16
    if plan == "Enterprise":
        base += 22
    return max(1, round(random.gauss(base, max(4, base * 0.22))))


def _usage_score(
    channel: str,
    company_size: str,
    plan: str,
    discount: float,
    month_index: int,
) -> float:
    base = 72
    base += {"SMB": -5, "Mid-Market": 2, "Enterprise": 7}[company_size]
    base += {"Starter": -5, "Growth": 0, "Business": 4, "Enterprise": 7}[plan]
    base += {
        "Organic Search": 3,
        "Referral": 8,
        "Paid Search": -9,
        "Paid Social": -14,
        "Partner": 5,
        "Content": 2,
    }[channel]
    if month_index >= 16 and channel in {"Paid Search", "Paid Social"}:
        base -= 4
    base -= max(0, discount - 20) * 0.35
    return _clamp(random.gauss(base, 12), 4, 99)


def _support_tickets(usage_score: float, company_size: str, channel: str) -> int:
    base = 0.9 + max(0, 78 - usage_score) / 14
    base += {"SMB": 0.0, "Mid-Market": 0.7, "Enterprise": 1.4}[company_size]
    if channel in {"Paid Search", "Paid Social"}:
        base += 0.6
    return max(0, round(random.gauss(base, 1.6)))


def _churned(
    usage_score: float,
    support_tickets: int,
    channel: str,
    plan: str,
    discount: float,
    month_index: int,
) -> bool:
    probability = 0.05
    probability += max(0, 62 - usage_score) * 0.009
    probability += support_tickets * 0.018
    probability += {"Paid Search": 0.055, "Paid Social": 0.085}.get(channel, 0)
    probability += {"Starter": 0.035, "Growth": 0.015, "Business": -0.005, "Enterprise": -0.025}[plan]
    probability += max(0, discount - 20) * 0.004
    if month_index >= 16 and channel in {"Paid Search", "Paid Social"}:
        probability += 0.045
    return random.random() < _clamp(probability, 0.01, 0.62)


def _nps_score(usage_score: float, support_tickets: int, channel: str, churned: bool) -> int:
    score = usage_score * 1.35 - 46
    score -= support_tickets * 3.8
    if channel in {"Paid Search", "Paid Social"}:
        score -= 8
    if churned:
        score -= 18
    return round(_clamp(random.gauss(score, 12), -100, 100))


def _monthly_revenue(
    plan: str,
    company_size: str,
    channel: str,
    region: str,
    discount: float,
    month_index: int,
) -> float:
    plan_ranges = {
        "Starter": (79, 249),
        "Growth": (320, 950),
        "Business": (1200, 3900),
        "Enterprise": (7200, 26000),
    }
    low, high = plan_ranges[plan]
    base = random.uniform(low, high)
    base *= {"SMB": 0.92, "Mid-Market": 1.08, "Enterprise": 1.22}[company_size]
    base *= {"North America": 1.12, "Europe": 1.03, "APAC": 0.88, "Latin America": 0.74, "Middle East & Africa": 0.82}[region]
    if channel == "Partner":
        base *= 1.1
    base *= 1 + month_index * 0.006
    return max(0, base * (1 - discount / 100))


def _apply_missing_values(row: dict[str, str], channel: str, plan: str) -> None:
    if random.random() < 0.13:
        row["nps_score"] = ""
    if random.random() < 0.08 or (plan == "Starter" and random.random() < 0.04):
        row["sales_cycle_days"] = ""
    if random.random() < 0.05:
        row["discount_percentage"] = ""
    if random.random() < 0.035:
        row["support_tickets"] = ""
    if random.random() < 0.025:
        row["product_usage_score"] = ""
    if channel in {"Paid Search", "Paid Social"} and random.random() < 0.045:
        row["signup_source"] = ""


def _inject_outliers(rows: list[dict[str, str]]) -> None:
    enterprise_rows = [row for row in rows if row["plan"] == "Enterprise" and row["region"] == "North America"]
    for row in random.sample(enterprise_rows, 12):
        row["monthly_revenue"] = _money(random.uniform(52000, 118000))
        row["discount_percentage"] = _number(random.uniform(18, 32), 1)

    risky_rows = [
        row
        for row in rows
        if row["acquisition_channel"] in {"Paid Search", "Paid Social"}
        and row["product_usage_score"]
    ]
    for row in random.sample(risky_rows, 14):
        row["support_tickets"] = str(random.randint(31, 58))
        row["product_usage_score"] = _number(random.uniform(8, 34), 1)
        row["churned"] = "1.0"
        row["nps_score"] = str(random.randint(-84, -22))

    paid_rows = [row for row in rows if row["acquisition_channel"] in {"Paid Search", "Paid Social"}]
    for row in random.sample(paid_rows, 10):
        row["discount_percentage"] = _number(random.uniform(55, 72), 1)


def _write_csv(rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "date",
        "customer_id",
        "company_size",
        "region",
        "acquisition_channel",
        "plan",
        "monthly_revenue",
        "product_usage_score",
        "support_tickets",
        "churned",
        "signup_source",
        "sales_cycle_days",
        "discount_percentage",
        "nps_score",
    ]
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _weighted_choice(weighted_items: list[tuple[str, float]]) -> str:
    total = sum(weight for _, weight in weighted_items)
    pick = random.random() * total
    current = 0.0
    for item, weight in weighted_items:
        current += weight
        if pick <= current:
            return item
    return weighted_items[-1][0]


def _random_day_in_month(month_start: date) -> date:
    next_month = _add_months(month_start, 1)
    days = (next_month - month_start).days
    return month_start + timedelta(days=random.randrange(days))


def _add_months(value: date, months: int) -> date:
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    return date(year, month, 1)


def _money(value: float) -> str:
    return f"{value:.2f}"


def _number(value: float, digits: int) -> str:
    return f"{value:.{digits}f}"


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


if __name__ == "__main__":
    main()
