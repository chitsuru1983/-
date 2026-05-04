import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import google.generativeai as genai

# --- ページ設定 ---
st.set_page_config(
    page_title="やさい料理研究家　大畑ちつるレシピ検索アプリ",
    page_icon="logo.png", # logo.png
    layout="wide"
)
# --- ロゴとタイトルの表示 ---

# --- iPhoneホーム画面用設定  ---

st.markdown(

    f"""

    <head>

        <link rel="apple-touch-icon" href="app/static/logo.png">

        <meta name="apple-mobile-web-app-title" content="大畑ちつるレシピ">

        <meta name="apple-mobile-web-app-capable" content="yes">

    </head>

    """,

    unsafe_allow_html=True

)
except Exception:
    # 万が一読み込めない場合は元のURL指定を予備として残す
    st.markdown('<link rel="apple-touch-icon" href="logo.png">', unsafe_allow_html=True)
)

col1, col2 = st.columns([1, 6])
with col1:
    st.image("logo.png", width=100)
with col2:
    st.title("🥬 やさい料理研究家 大畑ちつるレシピ検索アプリ")
    st.caption("日々の献立作りをサポートする、プロの野菜レシピ検索ツールです。")

# --- 設定 ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("GOOGLE_API_KEYが見つかりません。")

# 生成に使用するモデル
model = genai.GenerativeModel('gemini-3-flash-preview')

# --- データ読み込み ---
@st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path)
    # レシピ記事のみを対象
    df = df[df['Post Type'] == 'recipe'].copy()
    def strip_html(html_str):
        if pd.isna(html_str): return ""
        return BeautifulSoup(html_str, "html.parser").get_text(separator=" ").strip()
    df['clean_content'] = df['Content'].apply(strip_html)
    return df

df = load_data("fa2ac34592382d85a2af03a450f780a4.csv")

# --- UI ---
st.sidebar.title("メニュー")
mode = st.sidebar.radio("機能を選択", ["過去レシピを検索", "自由な食材から新作を生成"])

# --- 1. 検索モード ---
if mode == "過去レシピを検索":
    st.title("🔍 過去レシピ検索")
    q = st.text_input("キーワードを入力（食材や料理名）", placeholder="例：なす 豚肉")
    if q:
        keywords = q.split()
        mask = df['clean_content'].str.contains(keywords[0], na=False, case=False)
        for kw in keywords[1:]:
            mask &= df['clean_content'].str.contains(kw, na=False, case=False)
        
        results = df[mask]
        st.write(f"ヒット数: {len(results)}件")
        for _, row in results.head(10).iterrows():
            with st.expander(f"📖 {row['Title']}"):
                if pd.notna(row['Image URL']):
                    st.image(row['Image URL'].split('|')[0], width=300)
                st.markdown(f"**[元記事を見る]({row['Permalink']})**")
                st.write(row['clean_content'])

# --- 2. 生成モード（自由記述方式） ---
else:
    st.title("✨ 自由食材で新作生成")
    st.write("手元にある食材や、使いたい調味料を自由に入力してください。")

    # 自由記述入力
    input_text = st.text_area(
        "使いたい食材・条件を入力（スペース区切りや文章でもOK）", 
        placeholder="例：なす、厚揚げ、少しピリ辛にしたい",
        help="冷蔵庫にあるものを思いつくままに入力してください。"
    )

    if st.button("大畑ちつるスタイルでレシピを考案"):
        if not input_text:
            st.warning("食材を入力してください。")
        else:
            # プロンプトの構築
            # ここで「大畑ちつるの過去の全レシピ」の傾向（野菜中心、彩り、時短など）を
            # システム的な指示として盛り込みます。
            prompt = f"""
あなたは、料理研究家（大畑ちつる）の思考を完璧にトレースしたAI助手です。
彼女の過去のレシピデータに基づき、以下の食材を使って、彼女が新作として発表しそうなレシピを提案してください。

【制限事項】
・トレースという用語は禁止する。「過去のレシピを基に」など自然な表現を用いること。
・大畑ちつるという名前はセットで用いること。ちつるや大畑などの単独表記は禁止。
【彼女の料理スタイル】
- 野菜の持ち味を活かし、彩りが豊かである。
- 家庭にある調味料で、驚くほど美味しくなる工夫がある。
- 手順がシンプルで、忙しい共働き家庭に優しい。
- 肉や魚は一人当たり80～100gを目指す
- 鶏がらスープや顆粒出汁は使わない
- 醤油は薄口しょうゆが基本となる

# ユーザーからのリクエスト（食材・条件）
{input_text}

# 出力形式
1. 料理名（大畑ちつるがブログで付けそうな魅力的なタイトル）
2. 今回のポイント（なぜこれが大畑ちつるらしい新作と言えるのか）
3. 材料
4. 手順（分かりやすく）
"""
            with st.spinner("大畑ちつるの過去の味付けを分析して考案中..."):
                try:
                    response = model.generate_content(prompt)
                    st.success("新作レシピ案が完成しました！")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"生成エラー: {e}")
