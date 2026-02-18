import os
import csv
from datetime import date, timedelta
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)

def get_last_month_dates():
    today = date.today()
    first_day_this_month = today.replace(day=1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    first_day_last_month = last_day_last_month.replace(day=1)
    return first_day_last_month.strftime("%Y-%m-%d"), last_day_last_month.strftime("%Y-%m-%d")

def get_ga4_report():
    property_id = os.environ.get("GA4_PROPERTY_ID")
    if not property_id:
        raise ValueError("GA4_PROPERTY_ID environment variable not set")

    client = BetaAnalyticsDataClient()
    start_date, end_date = get_last_month_dates()

    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="sessionSourceMedium"),
            Dimension(name="deviceCategory"),
        ],
        metrics=[
            Metric(name="sessions"),
            Metric(name="engagementRate"),
            Metric(name="conversions"),
        ],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )
    response = client.run_report(request)

    with open("report.csv", "w", newline="") as f:
        writer = csv.writer(f)
        header = [h.name for h in response.dimension_headers] + [h.name for h in response.metric_headers]
        writer.writerow(header)
        for row in response.rows:
            writer.writerow([d.value for d in row.dimension_values] + [m.value for m in row.metric_values])

if __name__ == "__main__":
    get_ga4_report()
