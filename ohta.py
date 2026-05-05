import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import google.generativeai as genai
import base64

# --- 1. ページ設定（最上段に配置） ---
st.set_page_config(
    page_title="レシピ検索アプリ",
    page_icon="logo.png",
    layout="wide"
)

# --- 2. 認証機能 ---
def check_password():
    """パスワードが正しいかチェックする関数"""
    if st.session_state.get("password_correct", False):
        return True

    # ログイン画面の表示
    st.title("🔐 認証が必要です")
    password = st.text_input("パスワードを入力してください", type="password")
    
    if st.button("ログイン"):
        # セキュリティを高める場合は将来的に st.secrets["app_password"] に書き換え
        if password == "20250505": 
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("パスワードが違います")
    return False

# --- 3. メイン処理（認証後に実行される全ロジック） ---
def main_app():
    # --- iPhoneホーム画面用設定 (Base64埋め込み) ---
    def get_image_base64(file_path):
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            return base64.b64encode(data).decode()
        except Exception:
            return None

    img_base64 = get_image_base64("logo.png")

    if img_base64:
        st.markdown(
            f"""
            <head>
                <link rel="apple-touch-icon" href="data:image/png;base64,{img_base64}">
                <meta name="apple-mobile-web-app-title" content="大畑ちつるレシピ">
                <meta name="apple-mobile-web-app-capable" content="yes">
            </head>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown('<link rel="apple-touch-icon" href="logo.png">', unsafe_allow_html=True)

    # --- 画面上の表示 ---
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        st.image("title1.png", use_container_width=True)
        st.caption("日々の献立作りをサポートする、プロの野菜レシピ検索ツールです。")

    # --- 設定 ---
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("GOOGLE_API_KEYが見つかりません。")

    model = genai.GenerativeModel('gemini-3-flash-preview')

    # --- データ読み込み ---
    @st.cache_data
    def load_data(file_path):
        df = pd.read_csv(file_path)
        df = df[df['Post Type'] == 'recipe'].copy()
        def strip_html(html_str):
            if pd.isna(html_str): return ""
            return BeautifulSoup(html_str, "html.parser").get_text(separator=" ").strip()
        df['clean_content'] = df['Content'].apply(strip_html)
        return df

    df = load_data("fa2ac34592382d85a2af03a450f780a4.csv")

    # --- UI ---
    st.sidebar.title("メニュー")
    st.sidebar.markdown("### 🔍 レシピを絞り込む")

    if '季節' in df.columns:
        all_seasons = df['季節'].dropna().unique().tolist()
    else:
        all_seasons = ["春", "夏", "秋", "冬"]

    selected_seasons = st.sidebar.multiselect(
        "季節・旬を選択",
        options=all_seasons,
        default=all_seasons
    )

    filtered_df = df[df['季節'].isin(selected_seasons)]
    mode = st.sidebar.radio("機能を選択", ["過去レシピを検索", "自由な食材から新作を生成"])

    # --- 1. 検索モード ---
    if mode == "過去レシピを検索":
        st.title("🔍 過去レシピ検索")
        q = st.text_input("キーワードを入力（食材や料理名）", placeholder="例：なす 豚肉")
        
        if q:
            keywords = q.split()
            mask = filtered_df['clean_content'].str.contains(keywords[0], na=False, case=False)
            for kw in keywords[1:]:
                mask &= filtered_df['clean_content'].str.contains(kw, na=False, case=False)
            
            results = filtered_df[mask]
            st.write(f"ヒット数: {len(results)}件")
            for _, row in results.head(10).iterrows():
                with st.expander(f"📖 {row['Title']}"):
                    if pd.notna(row['Image URL']):
                        st.image(row['Image URL'].split('|')[0], width=300)
                    st.markdown(f"**[元記事を見る]({row['Permalink']})**")
                    st.write(row['clean_content'])
                    st.divider() 
                    st.caption("コピーして献立メモなどに貼り付けられます ↓")
                    copy_text = f"【{row['Title']}】\n\n{row['clean_content']}\n\n元記事: {row['Permalink']}"
                    st.code(copy_text, language="text")

    # --- 2. 生成モード ---
    else:
        st.title("✨ 自由食材で新作生成")
        st.write("手元にある食材や、使いたい調味料を自由に入力してください。")
        input_text = st.text_area("使いたい食材・条件を入力", placeholder="例：なす、厚揚げ、少しピリ辛にしたい")

        if st.button("大畑ちつるスタイルでレシピを考案"):
            if not input_text:
                st.warning("食材を入力してください。")
            else:
                 # プロンプトの構築

            prompt = f"""

あなたは料理研究家の大畑ちつるです。

あなたの過去のレシピ（野菜中心、彩り、素材を活かす味付け）を理解した上で、新作レシピを提案してください。



【制約事項】

・「大畑ちつる」とフルネームで名乗ること。

・「〜の手法を採用」「〜が特徴です」といったAIによる客観的な解説は禁止します。

・本人がブログで語るような、素材への愛着や食卓の風景を感じる主観的なトーンで書いてください。

・共働き、蒸し炒め、薄口しょうゆ等の要素は、言葉で説明するのではなく、レシピの内容そのもので表現してください。

・鶏がらスープや顆粒出汁は使わず、素材の旨味を「薄口しょうゆ」などで引き出す構成にしてください。



# ユーザーからのリクエスト（食材・条件）

{input_text}
                with st.spinner("大畑ちつるの過去の味付けを分析して考案中..."):
                    try:
                        response = model.generate_content(prompt)
                        answer = response.text
                        st.success("新作レシピ案が完成しました！")
                        st.markdown(answer)
                        st.divider()
                        st.caption("📋 レシピ全文をコピー")
                        st.code(answer, language="text")
                    except Exception as e:
                        st.error(f"生成エラー: {e}")

# --- 4. 実行のトリガー（ここが門番） ---
if check_password():
    main_app()
else:
    st.stop()
