import anthropic
import streamlit as st

st.set_page_config(page_title="データ分析を依頼する (Text-to-Python)", page_icon="🧪", layout="wide")

st.title("データ分析を依頼する（Text-to-Python）")
st.caption(
    "自然言語で分析を依頼すると、Claude（claude-sonnet-5）がPythonコードを書いて実行し、"
    "グラフと要点のまとめを返します。"
)

MODEL = "claude-sonnet-5"
CSV_PATH = "sample_data/orders.csv"
MAX_TURNS = 8  # pause_turnで継続する場合の上限（無限ループ防止）

TOOLS = [{"type": "code_execution_20260521", "name": "code_execution"}]

SYSTEM_PROMPT = """あなたはECサイトの注文データを分析するデータアナリストです。
添付されたorders.csv（注文データ）を使って、ユーザーの依頼に応じた分析を行ってください。

ルール:
- 分析には pandas と matplotlib を使うこと
- 分析コードは.pyファイルに書いてから実行すること
- 売上は sale_price 列の合計として扱い、status が "Cancelled"（キャンセル）と
  "Returned"（返品）の注文は売上の集計から除外すること
- グラフを作成する場合はPNG形式で $OUTPUT_DIR に保存すること
- 最後に、分析結果の要点を日本語で2〜3文にまとめて回答すること
"""


@st.cache_resource
def get_client() -> anthropic.Anthropic:
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "st.secrets['ANTHROPIC_API_KEY'] が設定されていません。"
            ".streamlit/secrets.toml を確認してください。"
        )
    return anthropic.Anthropic(api_key=api_key)


@st.cache_resource
def upload_orders_csv(_client: anthropic.Anthropic) -> str:
    """sample_data/orders.csvをFiles APIにアップロードし、file_idを返す（プロセス内で1回だけ実行）。"""
    with open(CSV_PATH, "rb") as f:
        file_metadata = _client.files.upload(file=("orders.csv", f, "text/csv"))
    return file_metadata.id


def run_analysis(client: anthropic.Anthropic, file_id: str, question: str) -> list:
    """質問を送り、pause_turnであれば応答をそのまま送り返して続きを実行させる。

    戻り値は、全ターンのcontentブロックを発生順に連結したリスト。
    """
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "container_upload", "file_id": file_id},
                {"type": "text", "text": question},
            ],
        }
    ]

    all_blocks = []
    container_id = None

    for _ in range(MAX_TURNS):
        create_kwargs = dict(
            model=MODEL,
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        if container_id:
            create_kwargs["container"] = container_id

        response = client.messages.create(**create_kwargs)
        all_blocks.extend(response.content)

        if response.container:
            container_id = response.container.id

        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue

        break

    return all_blocks


def extract_code_from_tool_use(block):
    """server_tool_useブロックから、表示すべきPythonコード(パス, コード)を取り出す。"""
    if block.name == "text_editor_code_execution" and block.input.get("command") == "create":
        return block.input.get("path", "script.py"), block.input.get("file_text", "")
    if block.name == "code_execution":
        code = block.input.get("code")
        if code:
            return "REPL", code
    return None


def extract_output_file_ids(block) -> list:
    """code_execution/bash_code_executionの実行結果ブロックから出力ファイルのfile_idを取り出す。"""
    file_ids = []
    content = getattr(block, "content", None)
    inner_items = getattr(content, "content", None) if content is not None else None
    if isinstance(inner_items, list):
        for item in inner_items:
            file_id = getattr(item, "file_id", None)
            if file_id:
                file_ids.append(file_id)
    return file_ids


def render_blocks(client: anthropic.Anthropic, blocks: list) -> None:
    for block in blocks:
        if block.type == "text":
            st.write(block.text)
        elif block.type == "server_tool_use":
            code_info = extract_code_from_tool_use(block)
            if code_info:
                path, code = code_info
                with st.expander(f"Claudeが作成したコード: {path}"):
                    st.code(code, language="python")
        elif block.type in ("code_execution_tool_result", "bash_code_execution_tool_result"):
            for file_id in extract_output_file_ids(block):
                try:
                    metadata = client.files.retrieve_metadata(file_id)
                    if metadata.mime_type.startswith("image/"):
                        image_bytes = client.files.download(file_id).read()
                        st.image(image_bytes)
                except Exception as e:
                    st.error(f"グラフの取得中にエラーが発生しました: {e}")


question = st.text_input(
    "分析依頼を入力してください",
    placeholder="例: 月別の売上推移をグラフにして",
)
run_clicked = st.button("分析を実行", type="primary")

if run_clicked:
    if not question.strip():
        st.warning("分析依頼を入力してください。")
        st.stop()

    try:
        client = get_client()
        file_id = upload_orders_csv(client)
    except RuntimeError as e:
        st.error(str(e))
        st.stop()
    except FileNotFoundError as e:
        st.error(f"データファイルの読み込みに失敗しました: {e}")
        st.stop()

    try:
        with st.spinner("Claudeが分析コードを書いて実行しています..."):
            blocks = run_analysis(client, file_id, question)
    except anthropic.APIError as e:
        st.error(f"Claude APIの呼び出し中にエラーが発生しました: {e}")
        st.stop()

    render_blocks(client, blocks)
