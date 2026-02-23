import base64
import hashlib
import hmac
import json
import os

import requests
from dotenv import load_dotenv
from flask import Flask, abort, request

from db import add_transaction, financial_health, init_db, summary_month, summary_today
from parser import parse_transactions

load_dotenv()

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

if not LINE_CHANNEL_SECRET or not LINE_CHANNEL_ACCESS_TOKEN:
    raise RuntimeError("Please set LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN in .env")

app = Flask(__name__)
init_db()


def verify_signature(body: str, signature: str) -> bool:
    mac = hmac.new(LINE_CHANNEL_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def reply_message(reply_token: str, text: str) -> None:
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}],
    }
    requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)


def welcome_message() -> str:
    return (
        "สวัสดีครับ ผมลุงน่าน ผู้ช่วยบันทึกรายรับรายจ่าย\n"
        "เริ่มใช้งานได้ทันที แค่พิมพ์ยอดเงินในแชต\n\n"
        "ตัวอย่าง:\n"
        "- จ่ายค่าข้าว 65\n"
        "- รับเงินเดือน 25000\n"
        "- ข้าว 50, กาแฟ 45, เดินทาง 30\n\n"
        "คำสั่งสำคัญ:\n"
        "- สรุปวันนี้\n"
        "- สรุปเดือนนี้\n"
        "- สุขภาพการเงินของฉัน"
    )


def handle_text_message(user_id: str, text: str) -> str:
    normalized = text.strip().lower()

    if normalized in {"สรุป", "สรุปวันนี้", "summary"}:
        income, expense, balance = summary_today(user_id)
        return (
            "สรุปวันนี้ของลุงน่าน\n"
            f"- รายรับ: {income:,.2f} บาท\n"
            f"- รายจ่าย: {expense:,.2f} บาท\n"
            f"- คงเหลือ: {balance:,.2f} บาท"
        )

    if normalized in {"สรุปเดือนนี้", "summary month", "เดือนนี้"}:
        income, expense, balance = summary_month(user_id)
        return (
            "สรุปเดือนนี้ของลุงน่าน\n"
            f"- รายรับ: {income:,.2f} บาท\n"
            f"- รายจ่าย: {expense:,.2f} บาท\n"
            f"- คงเหลือ: {balance:,.2f} บาท"
        )

    if normalized in {"สุขภาพการเงินของฉัน", "สุขภาพการเงิน", "financial health"}:
        health = financial_health(user_id)
        savings_rate = health["savings_rate"]
        expense_ratio = health["expense_ratio"]
        savings_text = f"{savings_rate:,.2f}%" if isinstance(savings_rate, float) else "คำนวณไม่ได้"
        expense_text = f"{expense_ratio:,.2f}%" if isinstance(expense_ratio, float) else "คำนวณไม่ได้"
        return (
            "สุขภาพการเงินของฉัน (เดือนนี้)\n"
            f"- สถานะ: {health['score']}\n"
            f"- รายรับ: {health['income_month']:,.2f} บาท\n"
            f"- รายจ่าย: {health['expense_month']:,.2f} บาท\n"
            f"- คงเหลือ: {health['balance_month']:,.2f} บาท\n"
            f"- สัดส่วนรายจ่ายต่อรายรับ: {expense_text}\n"
            f"- อัตราเงินออม: {savings_text}\n"
            f"- หมวดจ่ายสูงสุด: {health['top_expense_category']} ({health['top_expense_amount']:,.2f} บาท)\n"
            f"- จำนวนรายการเดือนนี้: {health['transaction_count_month']}\n"
            f"- คำแนะนำ: {health['tip']}"
        )

    parsed_items = parse_transactions(text)
    if not parsed_items:
        return (
            "ลุงน่านอ่านยอดเงินไม่เจอ\n"
            "ลองพิมพ์แบบนี้:\n"
            "- จ่ายค่าข้าว 65\n"
            "- รับเงินเดือน 25000\n"
            "- +500 ค่าขายของ\n"
            "- ข้าว 50, กาแฟ 45, เดินทาง 30\n"
            "- สรุปวันนี้\n"
            "- สรุปเดือนนี้\n"
            "- สุขภาพการเงินของฉัน"
        )

    for parsed in parsed_items:
        add_transaction(
            user_id=user_id,
            txn_type=parsed.txn_type,
            amount=parsed.amount,
            category=parsed.category,
            note=parsed.note,
        )

    total_income = sum(item.amount for item in parsed_items if item.txn_type == "income")
    total_expense = sum(item.amount for item in parsed_items if item.txn_type == "expense")
    net_amount = total_income - total_expense

    if len(parsed_items) == 1:
        parsed = parsed_items[0]
        thai_type = "รายรับ" if parsed.txn_type == "income" else "รายจ่าย"
        return (
            "บันทึกแล้ว\n"
            f"- ประเภท: {thai_type}\n"
            f"- หมวดหมู่: {parsed.category}\n"
            f"- จำนวน: {parsed.amount:,.2f} บาท\n"
            f"- รวมข้อความนี้: รับ {total_income:,.2f} | จ่าย {total_expense:,.2f} | สุทธิ {net_amount:,.2f}"
        )

    lines = [f"บันทึกแล้ว {len(parsed_items)} รายการ"]
    for idx, item in enumerate(parsed_items, start=1):
        thai_type = "รับ" if item.txn_type == "income" else "จ่าย"
        lines.append(f"{idx}) {thai_type} {item.amount:,.2f} บาท ({item.category})")
    lines.append(f"รวมข้อความนี้: รับ {total_income:,.2f} | จ่าย {total_expense:,.2f} | สุทธิ {net_amount:,.2f}")
    return "\n".join(lines)


@app.post("/webhook")
def webhook() -> tuple[str, int]:
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    if not verify_signature(body, signature):
        abort(400)

    payload = request.get_json(silent=True) or {}
    events = payload.get("events", [])

    for event in events:
        event_type = event.get("type")
        reply_token = event.get("replyToken")

        if event_type == "follow":
            if reply_token:
                reply_message(reply_token, welcome_message())
            continue

        if event_type != "message":
            continue

        message = event.get("message", {})
        if message.get("type") != "text":
            continue

        user_id = event.get("source", {}).get("userId", "anonymous")
        text = message.get("text", "")
        reply_text = handle_text_message(user_id, text)
        if reply_token:
            reply_message(reply_token, reply_text)

    return "OK", 200


@app.get("/")
def health() -> tuple[str, int]:
    return "Lung Nan Budget Bot is running", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
