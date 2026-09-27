# Streamlit BI Starter

StreamlitでBIダッシュボード構築を学ぶためのスターターテンプレートです。AIコーディングエージェント（Claude Code / Codex）と組み合わせて使うことを想定しています。

## セットアップ

GitHub Codespacesで開くと、`.devcontainer`の設定により依存関係が自動でインストールされます。

ローカルで動かす場合:

```bash
uv sync
uv run streamlit run Home.py
```

## プロジェクト構成

```
.
├── Home.py              # アプリのエントリーポイント
├── pages/               # 追加ページを配置するディレクトリ
├── sample_data/         # サンプルデータ（ECサイトの注文・ユーザーデータ）
│   ├── orders.csv
│   └── users.csv
├── .streamlit/
│   └── secrets.toml.example  # 接続情報・APIキーの設定雛形
├── pyproject.toml       # 依存関係の定義（uvで管理）
├── CLAUDE.md            # Claude Code向けのプロジェクト説明
└── AGENTS.md            # Codex向けのプロジェクト説明
```

## 接続情報・APIキーの設定

データベース接続やAPIキーが必要になったら、雛形をコピーして設定します。

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

`.streamlit/secrets.toml`は`.gitignore`に含まれており、Gitにはコミットされません。認証情報は必ずこのファイル（またはデプロイ先のシークレット管理機能）で管理してください。

## データセット

架空のECサイトのサンプルデータです。

### sample_data/orders.csv（注文データ、800件）

| 列名           | 型       | 説明                                                                                    |
| -------------- | -------- | --------------------------------------------------------------------------------------- |
| order_id       | int      | 注文ID                                                                                  |
| user_id        | int      | 注文したユーザーのID（users.csvのidに対応）                                             |
| product_id     | int      | 商品ID                                                                                  |
| product_name   | str      | 商品名（例: Wireless Earbuds）                                                          |
| category       | str      | 商品カテゴリ（Electronics / Apparel / Home & Kitchen / Beauty / Sports / Books / Toys） |
| quantity       | int      | 購入数量                                                                                |
| unit_price     | float    | 商品単価（USD）                                                                         |
| discount_rate  | float    | 割引率（0.0 / 0.1 / 0.2）                                                               |
| sale_price     | float    | 販売価格 = unit_price × quantity × (1 - discount_rate)                                  |
| status         | str      | 注文ステータス（Complete / Shipped / Processing / Cancelled / Returned）                |
| payment_method | str      | 支払い方法（credit_card / paypal / bank_transfer / mobile_payment）                     |
| created_at     | datetime | 注文日時（2025-01〜2026-06）                                                            |
| shipped_at     | datetime | 出荷日時（未出荷の場合は空）                                                            |

### sample_data/users.csv（ユーザーデータ、150件）

| 列名           | 型   | 説明                                                                            |
| -------------- | ---- | ------------------------------------------------------------------------------- |
| id             | int  | ユーザーID                                                                      |
| age            | int  | 年齢                                                                            |
| gender         | str  | 性別（M / F）                                                                   |
| country        | str  | 居住国（United States / Japan / United Kingdom / Germany / Canada / Australia） |
| state          | str  | 州・都道府県                                                                    |
| traffic_source | str  | 流入元（Search / Organic / Email / Ads / Social / Referral）                    |
| created_at     | date | 会員登録日                                                                      |

## 使用技術

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) - パッケージマネージャー
- [Streamlit](https://streamlit.io/) - ダッシュボードフレームワーク
- [Pandas](https://pandas.pydata.org/) - データ処理
- [Plotly](https://plotly.com/python/) - インタラクティブな可視化

## データの定義

- 売上: sale_priceの合計。statusが"Cancelled"と"Returned"の注文は除外する
- 注文数・販売数量も、特に指示がない限り同じ条件で除外する
- ユーザーの属性（国・年齢・性別・流入元）は、orders.user_id と users.id で結合して取得する