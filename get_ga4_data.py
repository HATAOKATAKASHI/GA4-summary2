import os
import csv
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)

def get_ga4_report():
    """Fetches a report from Google Analytics 4 Data API."""
    property_id = os.environ.get("GA4_PROPERTY_ID")
    if not property_id:
        raise ValueError("GA4_PROPERTY_ID environment variable not set")

    client = BetaAnalyticsDataClient()

    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="date"),
            Dimension(name="country"),
            Dimension(name="browser"),
        ],
        metrics=[
            Metric(name="activeUsers"),
            Metric(name="newUsers"),
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="engagementRate"),
        ],
        date_ranges=[DateRange(start_date="yesterday", end_date="yesterday")],
    )
    response = client.run_report(request)

    with open("report.csv", "w", newline="") as f:
        writer = csv.writer(f)
        # Write header
        header = [h.name for h in response.dimension_headers] + [h.name for h in response.metric_headers]
        writer.writerow(header)

        # Write rows
        for row in response.rows:
            writer.writerow(
                [d.value for d in row.dimension_values] + [m.value for m in row.metric_values]
            )

if __name__ == "__main__":
    get_ga4_report()