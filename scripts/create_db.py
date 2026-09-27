import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"
DB_PATH = BASE_DIR / "data" / "analytics.db"


def main():
    orders = pd.read_csv(
        SAMPLE_DATA_DIR / "orders.csv", parse_dates=["created_at", "shipped_at"]
    )
    users = pd.read_csv(SAMPLE_DATA_DIR / "users.csv", parse_dates=["created_at"])

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        orders.to_sql("orders", conn, if_exists="replace", index=False)
        users.to_sql("users", conn, if_exists="replace", index=False)

    print(f"orders: {len(orders):,}行, users: {len(users):,}行 を {DB_PATH} に保存しました。")


if __name__ == "__main__":
    main()
