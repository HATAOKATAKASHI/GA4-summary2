import os
from datetime import date, timedelta
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
    OrderBy,
)
from google import genai
from google.genai import types # AIに検索機能を持たせるための追加パーツ

def get_month_ranges():
    today = date.today()
    # 先月
    first_day_this_month = today.replace(day=1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    first_day_last_month = last_day_last_month.replace(day=1)
    
    # 前月（比較用）
    last_day_prev_month = first_day_last_month - timedelta(days=1)
    first_day_prev_month = last_day_prev_month.replace(day=1)
    
    return (
        first_day_last_month.strftime("%Y-%m-%d"), last_day_last_month.strftime("%Y-%m-%d"),
        first_day_prev_month.strftime("%Y-%m-%d"), last_day_prev_month.strftime("%Y-%m-%d")
    )

def fetch_ga4_data():
    property_id = os.environ.get("GA4_PROPERTY_ID")
    if not property_id:
        raise ValueError("GA4_PROPERTY_ID environment variable not set")
        
    client = BetaAnalyticsDataClient()
    start_last, end_last, start_prev, end_prev = get_month_ranges()

    # 1. KPIの取得 (先月と前月)
    def get_kpi(start, end):
        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=start, end_date=end)],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="newUsers"),
                Metric(name="screenPageViews"),
                Metric(name="engagedSessions"),
                Metric(name="averageSessionDuration"),
                Metric(name="engagementRate"),
                Metric(name="conversions"),
            ]
        )
        response = client.run_report(request)
        if response.rows:
            return [float(m.value) for m in response.rows[0].metric_values]
        return [0] * 8

    kpi_last = get_kpi(start_last, end_last)
    kpi_prev = get_kpi(start_prev, end_prev)

    # 前月比の計算関数
    def calc_mom(last, prev):
        if prev == 0:
            return "前月データなし"
        return f"{(last / prev) * 100:.1f}%"

    metrics_names = [
        "セッション数", "総ユーザー数", "新規ユーザー数", "ページ表示回数", 
        "エンゲージのあったセッション数", "平均エンゲージメント時間(秒)", 
        "エンゲージメント率", "キーイベント数(CV)"
    ]
    
    last_month_num = int(start_last.split("-")[1])
    prev_month_num = int(start_prev.split("-")[1])
    
    kpi_text = f"【先月（{last_month_num}月） vs 前月（{prev_month_num}月） KPI比較】\n"
    
    for i, name in enumerate(metrics_names):
        val_last = kpi_last[i]
        val_prev = kpi_prev[i]
        mom = calc_mom(val_last, val_prev)
        
        if name == "エンゲージメント率":
            kpi_text += f"- {name}: {val_last*100:.1f}% (前月比: {mom})\n"
        elif name == "平均エンゲージメント時間(秒)":
            kpi_text += f"- {name}: {val_last:.1f}秒 (前月比: {mom})\n"
        else:
            kpi_text += f"- {name}: {int(val_last)} (前月比: {mom})\n"

    # 2. ランディングページTOP5
    request_lp = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start_last, end_date=end_last)],
        dimensions=[Dimension(name="landingPagePlusQueryString")],
        metrics=[Metric(name="sessions")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=5
    )
    res_lp = client.run_report(request_lp)
    lp_text = "\n【ランディングページ TOP 5】\n"
    for i, row in enumerate(res_lp.rows):
        lp_text += f"{i+1}. {row.dimension_values[0].value} ({row.metric_values[0].value} セッション)\n"

    # 3. 参照元/メディアTOP5
    request_sm = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start_last, end_date=end_last)],
        dimensions=[Dimension(name="sessionSourceMedium")],
        metrics=[Metric(name="sessions")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=5
    )
    res_sm = client.run_report(request_sm)
    sm_text = "\n【参照元／メディア TOP 5】\n"
    for i, row in enumerate(res_sm.rows):
        sm_text += f"{i+1}. {row.dimension_values[0].value} ({row.metric_values[0].value} セッション)\n"

    return kpi_text + lp_text + sm_text

def analyze_with_gemini(data_text):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
        
    client = genai.Client(api_key=api_key)
    
    # ---------------------------------------------------------
    # ↓ ご要望の高度な分析・施策提案プロンプトに差し替えました ↓
    # ---------------------------------------------------------
    prompt = f"""
    あなたは、GA4に精通した大変優秀なマーケターです。
    以下のGoogle Analytics（GA4）データは、先月と前月のWebサイトの実績です。
    このデータを元に、月次レポートを作成してください。

    【出力の絶対ルール】
    1. 挨拶や自己紹介（「Webマーケターの〇〇です」など）は一切書かないでください。最初の文字から直接レポートの内容（見出し等）を書き始めてください。
    2. 提供した【KPI比較】【TOP5】のデータは、マークダウンで見やすい表やリスト形式にして、レポートの冒頭に必ずすべて記載してください。見出しはそのまま使用してください。
    3. そのデータの後に、プロの視点で以下の3点の分析・提案を記載してください。
       - 分析と結論の抽出：「先月対比で最も変動が大きかった指標」と、そこから読み取れる「ビジネス的な結論」を１つ抽出してください。
       - 施策への落とし込み：上記の分析結果に基づき、「CVRを最大化する」ために、次月のSNS施策として最も有効なアクションプランを1つ提案してください。
       - 異常値の発見：上記のデータ内で、特にセッション数が急激に伸びている、または落ち込んでいるチャネル（参照元）を特定し、Web検索機能を使ってその原因となり得る外部要因（例：ニュース、業界のトレンド、競合の動きなど）を調査して考察してください。

    【GA4データ】
    {data_text}
    """
    
    # ---------------------------------------------------------
    # ↓ Geminiに「Google検索」を使用する権限を与えました ↓
    # ---------------------------------------------------------
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}],  # ここで検索機能をONにしています！
        )
    )
        
    with open("issue_body.md", "w", encoding="utf-8") as f:
        f.write(response.text)

if __name__ == "__main__":
    print("GA4からデータを取得中...")
    data_text = fetch_ga4_data()
    print("Geminiでデータを分析中...")
    analyze_with_gemini(data_text)
    print("分析完了！issue_body.md を作成しました。")
