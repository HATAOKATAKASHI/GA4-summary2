import os
from datetime import date, timedelta
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
import google.generativeai as genai

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
        
    genai.configure(api_key=api_key)
    
    prompt = f"""
    あなたは高級輸入車（ポルシェ、マセラティ、BMW、ランドローバー等）を扱う販売店「Dutton ONE」の専属Webマーケターです。
    以下のGoogle Analytics（GA4）レポートは、先月1ヶ月間のWebサイトのセッションおよびコンバージョンデータです。
    このデータを分析し、以下の2点を簡潔に提案してください。結論ファーストで出力してください。
    
    1. 最も伸びている、あるいは重要なチャネル（参照元）とその理由
    2. CVR（コンバージョン率）を最大化するための次月のアクションプランを3つ
    
    【GA4データ】
    {csv_data}
    """
    
    try:
        # まずは賢い上位モデル（1.5-pro）で試行
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        response = model.generate_content(prompt)
    except Exception as e:
        # 万が一見つからない場合は、100%動く安定版（gemini-pro）に自動で切り替え
        print("上位モデルでエラーが発生したため、安定版モデル(gemini-pro)に切り替えて分析します。")
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        
    # GitHubのIssue投稿用にMarkdownファイルを作成
    with open("issue_body.md", "w", encoding="utf-8") as f:
        f.write(response.text)

if __name__ == "__main__":
    print("GA4からデータを取得中...")
    csv_data = get_ga4_report()
    print("Geminiでデータを分析中...")
    analyze_with_gemini(csv_data)
    print("分析完了！issue_body.md を作成しました。")
