# ลุงน่าน Budgeting LINE Bot

บอทแชตไลน์สำหรับบันทึกรายรับ-รายจ่าย โดยพิมพ์ข้อความธรรมดา แล้วระบบจะแยกเป็นรายการรายรับ/รายจ่ายให้อัตโนมัติ

## ความสามารถหลัก
- รับข้อความจาก LINE ผ่าน webhook
- แยกประเภท `รายรับ` / `รายจ่าย` จากข้อความไทย
- ดึงจำนวนเงินจากข้อความ เช่น `จ่ายค่าข้าว 65`
- รวมยอดรายรับ/รายจ่ายจากแต่ละข้อความให้อัตโนมัติ
- บันทึกลง SQLite (`budget.db`)
- ดูสรุปวันนี้ด้วยคำสั่ง `สรุปวันนี้`
- ดูสรุปเดือนนี้ด้วยคำสั่ง `สรุปเดือนนี้`
- วิเคราะห์สุขภาพการเงินด้วยคำสั่ง `สุขภาพการเงินของฉัน`
- ตรวจสอบหมวดหมู่ได้ด้วยคำสั่ง `ตรวจสอบหมวดหมู่`
- เพิ่มหมวดหมู่เองได้ด้วยคำสั่ง `เพิ่มหมวดหมู่ <ชื่อ> = <คีย์เวิร์ด,...>`
- ลบหมวดหมู่ที่เพิ่มเองได้ด้วยคำสั่ง `ลบหมวดหมู่ <ชื่อ>`

## ตัวอย่างข้อความที่บอทเข้าใจ
- `จ่ายค่าข้าว 65`
- `ซื้อกาแฟ 55`
- `รับเงินเดือน 25000`
- `+500 ค่าขายของ`
- `ข้าว 50, กาแฟ 45, เดินทาง 30`
- `รายรับ ฟรีแลนซ์ 1200, ขายของ 300`
- `รับ 500, จ่ายค่ารถ 80`
- `สรุปวันนี้`
- `สรุปเดือนนี้`
- `สุขภาพการเงินของฉัน`
- `ตรวจสอบหมวดหมู่`
- `เพิ่มหมวดหมู่ ค่าเดินทางพิเศษ = taxi, grab, bts`
- `ลบหมวดหมู่ ค่าเดินทางพิเศษ`

## ติดตั้ง
```bash
cd lung-nan-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

กรอกค่าใน `.env`
- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`

## รันในเครื่อง
```bash
python app.py
```

Server จะรันที่ `http://localhost:8000`

## เชื่อมกับ LINE
1. ไปที่ [LINE Developers](https://developers.line.biz/)
2. สร้าง Messaging API Channel
3. ตั้งค่า Webhook URL เป็น
   - `https://<your-public-domain>/webhook`
4. เปิด `Use webhook`
5. นำ `Channel secret` และ `Channel access token` มาใส่ `.env`

> ทดสอบ local สามารถใช้ ngrok เช่น `ngrok http 8000` แล้วนำ HTTPS URL ไปใส่ webhook

## Deploy บน Render
1. Push โค้ดไป GitHub
2. ใน Render เลือก `New +` -> `Blueprint` แล้วเลือก repo นี้ (ใช้ `render.yaml`)
3. ตั้งค่า Environment Variables ใน Render:
   - `LINE_CHANNEL_SECRET`
   - `LINE_CHANNEL_ACCESS_TOKEN`
4. Deploy แล้วนำโดเมนที่ได้ไปตั้ง LINE Webhook URL:
   - `https://<your-render-domain>/webhook`

หมายเหตุ:
- โปรเจกต์นี้ตั้ง `startCommand` เป็น `gunicorn app:app`
- บน Render Free ใช้ `BUDGET_DB_PATH=/opt/render/project/src/budget.db` (ข้อมูลไม่ถาวรถ้า instance รีสตาร์ท)
- ถ้าต้องการข้อมูลถาวร ให้ย้ายไป PostgreSQL หรืออัปเกรดแผนที่รองรับ disk

## โครงสร้างไฟล์
- `app.py` จัดการ webhook และตอบกลับ LINE
- `parser.py` แยกประเภทรายรับ/รายจ่าย + ดึงจำนวนเงิน
- `db.py` บันทึกและสรุปข้อมูลใน SQLite

## หมายเหตุ
ตัว parser ตั้งใจให้เรียบง่ายและใช้งานได้เร็ว หากต้องการแยกประโยคซับซ้อนกว่านี้ (หลายรายการใน 1 ข้อความ หรือหมวดหมู่ละเอียด) สามารถต่อยอดกฎใน `parser.py` ได้ทันที
