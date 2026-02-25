import re
from dataclasses import dataclass


@dataclass
class ParsedTransaction:
    txn_type: str
    amount: float
    category: str
    note: str


INCOME_KEYWORDS = [
    "รายรับ",
    "รับ",
    "ได้เงิน",
    "เงินเข้า",
    "ขายได้",
    "โบนัส",
    "เงินเดือน",
]

EXPENSE_KEYWORDS = [
    "รายจ่าย",
    "จ่าย",
    "ซื้อ",
    "โอน",
    "ค่า",
    "ผ่อน",
    "เติม",
]

CATEGORY_MAP = {
    "อาหาร": [
        "ข้าว",
        "กาแฟ",
        "อาหาร",
        "ของกิน",
        "ชานม",
        "หมูกระทะ",
        "ก๋วยเตี๋ยว",
        "ชาบู",
        "บุฟเฟต์",
        "กิน",
        "คาเฟ่",
        "อาหารกลางวัน",
        "อาหารเย็น",
    ],
    "เดินทาง": [
        "เดินทาง",
        "ค่ารถ",
        "ค่าแท็กซี่",
        "แท็กซี่",
        "taxi",
        "grab",
        "bolt",
        "lineman",
        "มอไซ",
        "วิน",
        "รถเมล์",
        "รถไฟ",
        "bts",
        "mrt",
        "น้ำมัน",
        "เติมน้ำมัน",
        "ทางด่วน",
        "ค่าทางด่วน",
        "ค่าจอดรถ",
        "ที่จอดรถ",
    ],
    "บ้าน": [
        "ค่าเช่า",
        "ค่าไฟ",
        "ค่าน้ำ",
        "ไฟ",
        "น้ำ",
        "เน็ต",
        "อินเทอร์เน็ต",
        "ค่าโทร",
        "ค่าโทรศัพท์",
        "ค่าไฟฟ้า",
        "ค่าบ้าน",
    ],
    "ช้อปปิ้ง": [
        "เสื้อ",
        "รองเท้า",
        "ช้อป",
        "shopping",
        "ของใช้",
        "เครื่องสำอาง",
        "กระเป๋า",
        "ของแต่งบ้าน",
        "ช้อปปิ้ง",
    ],
    "สุขภาพ": ["หมอ", "ยา", "โรงพยาบาล", "สุขภาพ", "คลินิก", "ฟิตเนส", "ประกันสุขภาพ"],
    "รายได้เสริม": ["ฟรีแลนซ์", "ขาย", "คอมมิชชั่น"],
}

AMOUNT_PATTERN = re.compile(r"(\d[\d,]*(?:\.\d+)?)")
SPLIT_PATTERN = re.compile(r"(?:\n|,|;| และ | กับ )")


def parse_amount(text: str) -> float | None:
    match = AMOUNT_PATTERN.search(text)
    if not match:
        return None

    raw = match.group(1).replace(",", "")
    try:
        amount = float(raw)
    except ValueError:
        return None

    if amount <= 0:
        return None

    return amount


def type_hint(text: str) -> str | None:
    lowered = text.lower()
    has_income = any(keyword in lowered for keyword in INCOME_KEYWORDS)
    has_expense = any(keyword in lowered for keyword in EXPENSE_KEYWORDS)

    if lowered.strip().startswith("+"):
        return "income"
    if lowered.strip().startswith("-"):
        return "expense"

    if has_income and has_expense:
        return None
    if has_income:
        return "income"
    if has_expense:
        return "expense"

    return None


def detect_type(text: str, fallback_type: str = "expense") -> str:
    return type_hint(text) or fallback_type


def detect_category(text: str, txn_type: str, category_map: dict[str, list[str]] | None = None) -> str:
    active_map = category_map or CATEGORY_MAP
    lowered = text.lower()
    compact = lowered.replace(" ", "")
    for category, keywords in active_map.items():
        if any(keyword.lower() in lowered or keyword.lower().replace(" ", "") in compact for keyword in keywords):
            return category

    return "รายรับทั่วไป" if txn_type == "income" else "รายจ่ายทั่วไป"


def clean_note(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:120]


def split_entries(text: str) -> list[str]:
    normalized = text.replace("，", ",")
    parts = [part.strip(" -•\t") for part in SPLIT_PATTERN.split(normalized)]
    return [part for part in parts if part]


def infer_global_type(text: str) -> str | None:
    entries = split_entries(text)
    hints = [hint for entry in entries if (hint := type_hint(entry)) is not None]
    unique_hints = set(hints)

    if len(unique_hints) == 1:
        return hints[0]

    if len(unique_hints) > 1:
        return None

    return type_hint(text)


def parse_single_transaction(
    text: str, fallback_type: str | None = None, category_map: dict[str, list[str]] | None = None
) -> ParsedTransaction | None:
    amount = parse_amount(text)
    if amount is None:
        return None

    txn_type = detect_type(text, fallback_type or "expense")
    category = detect_category(text, txn_type, category_map=category_map)
    note = clean_note(text)

    return ParsedTransaction(txn_type=txn_type, amount=amount, category=category, note=note)


def parse_transactions(text: str, category_map: dict[str, list[str]] | None = None) -> list[ParsedTransaction]:
    entries = split_entries(text)
    if not entries:
        return []

    global_type = infer_global_type(text)
    parsed_list: list[ParsedTransaction] = []

    for entry in entries:
        entry_fallback = global_type if type_hint(entry) is None else None
        parsed = parse_single_transaction(entry, fallback_type=entry_fallback, category_map=category_map)
        if parsed is not None:
            parsed_list.append(parsed)

    if parsed_list:
        return parsed_list

    single = parse_single_transaction(text, category_map=category_map)
    return [single] if single else []


def parse_transaction(text: str, category_map: dict[str, list[str]] | None = None) -> ParsedTransaction | None:
    parsed = parse_transactions(text, category_map=category_map)
    if not parsed:
        return None
    return parsed[0]
