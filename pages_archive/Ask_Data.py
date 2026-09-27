import re

import anthropic
import streamlit as st

st.set_page_config(page_title="データに質問する (Text-to-SQL)", page_icon="💬", layout="wide")

st.title("データに質問する（Text-to-SQL）")
st.caption(
    "自然言語の質問からClaude（claude-sonnet-5）がSQLを生成し、"
    "`data/analytics.db`に対して実行します。安全のため、SELECT文のみ・最大100行までの結果表示に制限しています。"
)

MODEL = "claude-sonnet-5"

# 生成SQLの安全性チェックで拒否するキーワード（SELECT/WITH以外の副作用を持つ文を防ぐ）
FORBIDDEN_KEYWORDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "REPLACE",
    "ATTACH",
    "DETACH",
    "TRUNCATE",
    "PRAGMA",
    "VACUUM",
    "GRANT",
    "REVOKE",
    "EXEC",
]

MAX_ROWS = 100

SCHEMA_NOTES = """
補足（列の意味）:
- orders.status の値: Complete / Shipped / Processing / Cancelled / Returned
  （Cancelled=取引未成立のキャンセル、Returned=返品。実質的な売上を集計する場合は通常この2つを除外する）
- orders.category の値: Electronics / Apparel / Home & Kitchen / Beauty / Sports / Books / Toys
- orders.payment_method の値: credit_card / paypal / bank_transfer / mobile_payment
- orders.sale_price = unit_price × quantity × (1 - discount_rate)（実際の販売金額。売上集計にはこの列を使う）
- orders.user_id は users.id と対応する（JOINする場合は orders.user_id = users.id）
- users.traffic_source の値: Search / Organic / Email / Ads / Social / Referral
- users.gender の値: M / F
""".strip()

SYSTEM_PROMPT_TEMPLATE = """あなたはSQLite用のSQL生成アシスタントです。
以下のテーブルスキーマに対して、ユーザーの自然言語の質問（日本語）に答えるための単一のSQL文を生成してください。

{schema}

ルール:
- SQLiteの構文に従うこと
- SELECT文（WITH句によるCTEも可）のみを出力すること。INSERT/UPDATE/DELETE/DROP/ALTER/PRAGMAなど、
  データやスキーマを変更する文や副作用のある文は絶対に出力しないこと
- 複数のSQL文をセミコロンで区切って出力しないこと
- 出力は実行可能なSQL文のみとし、説明文やMarkdownのコードブロック（```）を付けないこと
"""


@st.cache_data(ttl=3600)
def build_schema_description(_conn) -> str:
    """data/analytics.dbのorders・usersテーブルの実際の列情報からスキーマ説明文を作る。"""
    lines = []
    for table in ["orders", "users"]:
        columns = _conn.query(f"PRAGMA table_info({table})", ttl=3600)
        lines.append(f"テーブル: {table}")
        for _, col in columns.iterrows():
            lines.append(f"  - {col['name']} ({col['type']})")
        lines.append("")
    return "\n".join(lines).strip() + "\n\n" + SCHEMA_NOTES


def extract_sql(raw_text: str) -> str:
    """Claudeの応答からSQL本体だけを取り出す。

    説明文なしでSQLのみが返る想定だが、Claudeが説明文やMarkdownのコードフェンス付きで
    返した場合にも対応できるよう、フェンス内のSQLを優先的に抽出する。
    """
    text = raw_text.strip()
    fence_match = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    return text


def validate_select_only(sql: str) -> str:
    """SELECT（またはWITH句によるCTE）以外のSQLを拒否する。問題なければ整形済みSQLを返す。"""
    stripped = sql.strip().rstrip(";").strip()
    if not stripped:
        raise ValueError("SQLが生成されませんでした。")
    if ";" in stripped:
        raise ValueError("安全のため、複数のSQL文はまとめて実行できません。")

    first_word = stripped.split(None, 1)[0].upper()
    if first_word not in ("SELECT", "WITH"):
        raise ValueError("安全のため、SELECT文以外のSQLは実行できません。")

    upper_sql = stripped.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper_sql):
            raise ValueError(f"安全のため、'{keyword}' を含むSQLは実行できません。")

    return stripped


def generate_sql(question: str, schema: str) -> str:
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "st.secrets['ANTHROPIC_API_KEY'] が設定されていません。"
            ".streamlit/secrets.toml を確認してください。"
        )
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT_TEMPLATE.format(schema=schema),
        messages=[{"role": "user", "content": question}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


conn = st.connection("local_db", type="sql")
schema_description = build_schema_description(conn)

with st.expander("データベースのスキーマ情報（Claudeに渡している内容）"):
    st.code(schema_description, language="text")

question = st.text_input(
    "質問を入力してください",
    placeholder="例: カテゴリ別の売上ランキングを教えて",
)
run_clicked = st.button("分析する", type="primary")

if run_clicked:
    if not question.strip():
        st.warning("質問を入力してください。")
        st.stop()

    with st.spinner("SQLを生成しています..."):
        try:
            raw_sql = generate_sql(question, schema_description)
        except Exception as e:
            st.error(f"SQLの生成中にエラーが発生しました: {e}")
            st.stop()

    sql = extract_sql(raw_sql)

    st.subheader("生成されたSQL")
    try:
        validated_sql = validate_select_only(sql)
    except ValueError as e:
        st.code(sql or "(空の応答)", language="sql")
        st.error(str(e))
        st.stop()

    st.code(validated_sql, language="sql")

    st.subheader("実行結果")
    try:
        result = conn.query(validated_sql, ttl=0)
    except Exception as e:
        st.error(f"SQLの実行中にエラーが発生しました: {e}")
        st.stop()

    if len(result) > MAX_ROWS:
        st.caption(f"結果が{len(result):,}行あったため、先頭{MAX_ROWS}行のみ表示しています。")
        result = result.head(MAX_ROWS)

    st.dataframe(result, use_container_width=True)
