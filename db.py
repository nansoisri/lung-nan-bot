import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator

DB_PATH = Path(__file__).resolve().parent / "budget.db"


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                txn_type TEXT NOT NULL CHECK (txn_type IN ('income', 'expense')),
                amount REAL NOT NULL,
                category TEXT,
                note TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def add_transaction(user_id: str, txn_type: str, amount: float, category: str, note: str) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO transactions (user_id, txn_type, amount, category, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, txn_type, amount, category, note, now),
        )
        conn.commit()


def summary_range(user_id: str, start_date: str, end_date: str) -> tuple[float, float, float]:
    with get_conn() as conn:
        income = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) FROM transactions
            WHERE user_id = ? AND txn_type = 'income'
              AND substr(created_at, 1, 10) >= ? AND substr(created_at, 1, 10) <= ?
            """,
            (user_id, start_date, end_date),
        ).fetchone()[0]
        expense = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) FROM transactions
            WHERE user_id = ? AND txn_type = 'expense'
              AND substr(created_at, 1, 10) >= ? AND substr(created_at, 1, 10) <= ?
            """,
            (user_id, start_date, end_date),
        ).fetchone()[0]

    balance = income - expense
    return float(income), float(expense), float(balance)


def summary_today(user_id: str) -> tuple[float, float, float]:
    today = datetime.now().date().isoformat()
    return summary_range(user_id, today, today)


def summary_month(user_id: str) -> tuple[float, float, float]:
    now = datetime.now()
    start = now.replace(day=1).date().isoformat()
    end = now.date().isoformat()
    return summary_range(user_id, start, end)


def financial_health(user_id: str) -> dict[str, float | int | str | None]:
    now = datetime.now()
    start = now.replace(day=1).date().isoformat()
    end = now.date().isoformat()
    income, expense, balance = summary_range(user_id, start, end)

    with get_conn() as conn:
        count = conn.execute(
            """
            SELECT COUNT(*) FROM transactions
            WHERE user_id = ? AND substr(created_at, 1, 10) >= ? AND substr(created_at, 1, 10) <= ?
            """,
            (user_id, start, end),
        ).fetchone()[0]
        top = conn.execute(
            """
            SELECT COALESCE(category, 'ไม่ระบุหมวดหมู่') AS cat, COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE user_id = ? AND txn_type = 'expense'
              AND substr(created_at, 1, 10) >= ? AND substr(created_at, 1, 10) <= ?
            GROUP BY cat
            ORDER BY total DESC
            LIMIT 1
            """,
            (user_id, start, end),
        ).fetchone()

    savings_rate = None
    expense_ratio = None
    if income > 0:
        savings_rate = (balance / income) * 100
        expense_ratio = (expense / income) * 100

    if income <= 0 and expense > 0:
        score = "ต้องระวัง"
        tip = "เดือนนี้ยังไม่พบรายรับ แต่มีรายจ่าย ลองตั้งงบรายจ่ายต่อวัน"
    elif savings_rate is None:
        score = "ยังไม่มีข้อมูลพอ"
        tip = "เริ่มบันทึกรายรับรายจ่ายต่อเนื่องก่อน เพื่อวิเคราะห์ให้แม่นขึ้น"
    elif savings_rate >= 30:
        score = "ดีมาก"
        tip = "รักษาวินัยการออมต่อเนื่องได้เลย"
    elif savings_rate >= 10:
        score = "ดี"
        tip = "ลองลดหมวดรายจ่ายที่สูงสุดลงอีกเล็กน้อยเพื่อเพิ่มเงินออม"
    elif savings_rate >= 0:
        score = "พอใช้"
        tip = "เพิ่มเงินออมอัตโนมัติ 5-10% ของรายรับทุกครั้งที่เงินเข้า"
    else:
        score = "ต้องปรับ"
        tip = "รายจ่ายมากกว่ารายรับ ควรลดค่าใช้จ่ายไม่จำเป็นและตั้งเพดานรายวัน"

    top_category = "ไม่มีข้อมูล"
    top_amount = 0.0
    if top:
        top_category = str(top[0])
        top_amount = float(top[1])

    return {
        "income_month": income,
        "expense_month": expense,
        "balance_month": balance,
        "savings_rate": savings_rate,
        "expense_ratio": expense_ratio,
        "transaction_count_month": int(count),
        "top_expense_category": top_category,
        "top_expense_amount": top_amount,
        "score": score,
        "tip": tip,
    }
