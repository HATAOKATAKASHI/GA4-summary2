import os
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google import genai

def get_ga4_report():
    property_id = os.environ.get("GA4_PROPERTY_ID")
    if not property_id:
        raise ValueError("GA4_PROPERTY_ID environment variable not set")

    client = BetaAnalyticsDataClient()

    # 【変更箇所】「先月」ではなく、「過去90日間〜今日まで」の広い範囲でデータを取得します
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
        date_ranges=[DateRange(start_date="90daysAgo", end_date="today")],
    )
    response = client.run_report(request)

    # AIに読み込ませるためのCSVテキストを作成
    csv_data = "sessionSourceMedium,deviceCategory,sessions,engagementRate,conversions\n"
    for row in response.rows:
        dims = [d.value for d in row.dimension_values]
        mets = [m.value for m in row.metric_values]
        csv_data += ",".join(dims + mets) + "\n"
        
    return csv_data

def analyze_with_gemini(csv_data):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
        
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    あなたは高級輸入車（ポルシェ、マセラティ、BMW、ランドローバー等）を扱う販売店「Dutton ONE」の専属Webマーケターです。
    以下のGoogle Analytics（GA4）レポートは、過去90日間のWebサイトのセッションおよびコンバージョンデータです。
    このデータを分析し、以下の2点を簡潔に提案してください。結論ファーストで出力してください。
    
    1. 最も伸びている、あるいは重要なチャネル（参照元）とその理由
    2. CVR（コンバージョン率）を最大化するための次月のアクションプランを3つ
    
    【GA4データ】
    {csv_data}
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
        
    with open("issue_body.md", "w", encoding="utf-8") as f:
        f.write(response.text)

if __name__ == "__main__":
    print("GA4からデータを取得中...")
    csv_data = get_ga4_report()
    print("Geminiでデータを分析中...")
    analyze_with_gemini(csv_data)
    print("分析完了！issue_body.md を作成しました。")
