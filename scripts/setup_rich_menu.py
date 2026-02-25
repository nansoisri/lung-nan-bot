import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

RICH_MENU_NAME = "lung-nan-main-menu"
DEFAULT_IMAGE_PATH = Path(__file__).resolve().parent.parent / "assets" / "richmenu.png"


def build_rich_menu_payload() -> dict:
    return {
        "size": {"width": 2500, "height": 843},
        "selected": True,
        "name": RICH_MENU_NAME,
        "chatBarText": "เมนูลุงน่าน",
        "areas": [
            {
                "bounds": {"x": 0, "y": 0, "width": 833, "height": 843},
                "action": {"type": "message", "text": "สรุปวันนี้"},
            },
            {
                "bounds": {"x": 833, "y": 0, "width": 834, "height": 843},
                "action": {"type": "message", "text": "สรุปเดือนนี้"},
            },
            {
                "bounds": {"x": 1667, "y": 0, "width": 833, "height": 843},
                "action": {"type": "message", "text": "สุขภาพการเงินของฉัน"},
            },
        ],
    }


def line_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def check_response(res: requests.Response, action: str) -> None:
    if res.status_code >= 400:
        raise RuntimeError(f"{action} failed [{res.status_code}]: {res.text}")


def get_existing_rich_menus(token: str) -> list[dict]:
    res = requests.get(
        "https://api.line.me/v2/bot/richmenu/list",
        headers=line_headers(token),
        timeout=20,
    )
    check_response(res, "list rich menus")
    data = res.json()
    return data.get("richmenus", [])


def delete_rich_menu(token: str, rich_menu_id: str) -> None:
    res = requests.delete(
        f"https://api.line.me/v2/bot/richmenu/{rich_menu_id}",
        headers=line_headers(token),
        timeout=20,
    )
    check_response(res, f"delete rich menu {rich_menu_id}")


def create_rich_menu(token: str) -> str:
    payload = build_rich_menu_payload()
    res = requests.post(
        "https://api.line.me/v2/bot/richmenu",
        headers={**line_headers(token), "Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=20,
    )
    check_response(res, "create rich menu")
    return res.json()["richMenuId"]


def upload_rich_menu_image(token: str, rich_menu_id: str, image_path: Path) -> None:
    content_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    with image_path.open("rb") as fp:
        res = requests.post(
            f"https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content",
            headers={**line_headers(token), "Content-Type": content_type},
            data=fp.read(),
            timeout=30,
        )
    check_response(res, "upload rich menu image")


def set_default_rich_menu(token: str, rich_menu_id: str) -> None:
    res = requests.post(
        f"https://api.line.me/v2/bot/user/all/richmenu/{rich_menu_id}",
        headers=line_headers(token),
        timeout=20,
    )
    check_response(res, "set default rich menu")


def main() -> int:
    load_dotenv()

    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    if not token:
        print("LINE_CHANNEL_ACCESS_TOKEN not found in environment/.env")
        return 1

    image_arg = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_IMAGE_PATH)
    image_path = Path(image_arg).expanduser().resolve()
    if not image_path.exists():
        print("Rich menu image not found:", image_path)
        print("Please provide PNG/JPG image size 2500x843, then run:")
        print("python scripts/setup_rich_menu.py /path/to/richmenu.png")
        return 1

    if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        print("Unsupported image type. Use .png, .jpg or .jpeg")
        return 1

    existing = get_existing_rich_menus(token)
    for menu in existing:
        if menu.get("name") == RICH_MENU_NAME:
            rich_menu_id = menu.get("richMenuId")
            if rich_menu_id:
                delete_rich_menu(token, rich_menu_id)

    rich_menu_id = create_rich_menu(token)
    upload_rich_menu_image(token, rich_menu_id, image_path)
    set_default_rich_menu(token, rich_menu_id)

    print("Rich menu created and set as default")
    print("richMenuId:", rich_menu_id)
    print("name:", RICH_MENU_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
