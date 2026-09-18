# Streamlit BI Starter

StreamlitでBIダッシュボードを構築する学習用プロジェクトです。

## 技術スタック

- Python 3.11+ / uv（パッケージ管理）
- Streamlit（ダッシュボード）
- Pandas（データ処理）/ Plotly（可視化）

## プロジェクト構造

- `Home.py`: アプリのエントリーポイント
- `pages/`: 追加ページはこのディレクトリにPythonファイルとして作成する
- `sample_data/`: 分析対象のCSVデータ。スキーマの詳細はREADME.mdを参照

## よく使うコマンド

- 依存関係のインストール: `uv sync`
- ライブラリの追加: `uv add <package>`
- アプリの起動: `streamlit run Home.py`

## ルール

- データを読み込む処理には`@st.cache_data`を付ける
- グラフはPlotlyで作成し、`st.plotly_chart(fig, use_container_width=True)`で表示する
- 認証情報・APIキーはコードに書かず、`st.secrets`（`.streamlit/secrets.toml`）から読み込む
- 分析コードを書く前に、実際のCSVを読んでデータ構造を確認する
