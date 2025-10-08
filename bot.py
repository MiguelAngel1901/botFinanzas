import os
import re
import io
import datetime
import pytesseract
import cv2
import numpy as np
import pandas as pd
from telegram import Update, Bot
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext
import json
from google.oauth2.service_account import Credentials
import gspread

if 'G_CREDENTIALS_JSON' in os.environ:
    creds_json = json.loads(os.environ['G_CREDENTIALS_JSON'])
    creds = Credentials.from_service_account_info(creds_json)
else:
    creds = Credentials.from_service_account_file("credentials.json")

gc = gspread.authorize(creds)
G_SHEET_NAME = "Finanzas"
TELEGRAM_TOKEN = "7830595885:AAFg3OFdmWc_M3jAAC4QNGfxFOgi_1FfUKs"
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

IMG_DIR = "comprobantes_img"
os.makedirs(IMG_DIR, exist_ok=True)

def preprocess_image_bytes(image_bytes):
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3,3), 0)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return th

amount_re = re.compile(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))') 
date_re = re.compile(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})') 

def extract_fields(text):
    text_low = text.lower()
    amount = None
    for m in amount_re.findall(text):
        candidate = m.replace(' ', '').replace('.', '').replace(',', '.')
        try:
            val = float(candidate)
            if val > 0.01:
                amount = val
                break
        except:
            continue

    date = None
    dmatch = date_re.search(text)
    if dmatch:
        date = dmatch.group(1)

    ttype = "desconocido"
    if "transfer" in text_low or "transferencia" in text_low:
        ttype = "transferencia"
    elif "retir" in text_low or "cajero" in text_low:
        ttype = "retiro"
    elif "pago" in text_low or "pos" in text_low or "tarjeta" in text_low:
        ttype = "pago"

    return {"amount": amount, "date": date, "type": ttype, "raw": text[:120]}

def gsheets_client():
    scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(G_CREDENTIALS_JSON, scope)
    client = gspread.authorize(creds)
    return client

def append_row_to_sheets(row):
    client = gsheets_client()
    try:
        sheet = client.open(G_SHEET_NAME).sheet1
    except Exception as e:
        sh = client.create(G_SHEET_NAME)
        sh.share('tu-email@example.com', perm_type='user', role='owner')  # comparte a tu cuenta si es necesario
        sheet = sh.sheet1
    sheet.append_row(row)

def handle_photo(update: Update, context: CallbackContext):
    user = update.message.from_user
    photo = update.message.photo[-1]
    bio = io.BytesIO()
    photo.get_file().download(out=bio)
    bio.seek(0)
    img_bytes = bio.read()

    fname = f"{IMG_DIR}/{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{user.id}.jpg"
    with open(fname, "wb") as f:
        f.write(img_bytes)

    img_proc = preprocess_image_bytes(img_bytes)
    text = pytesseract.image_to_string(img_proc, lang='spa+eng')  # spa+eng por si viene mezcla
    fields = extract_fields(text)

    now = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')
    row = [now, fields.get("date"), fields.get("amount"), fields.get("type"), fields.get("raw"), fname]
    try:
        append_row_to_sheets(row)
        update.message.reply_text(f"Guardado ✅\nMonto: {fields.get('amount')}\nTipo: {fields.get('type')}\nFecha detección: {fields.get('date')}")
    except Exception as e:
        update.message.reply_text(f"Error guardando: {e}")

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))
    updater.start_polling()
    print("Bot corriendo...")
    updater.idle()

if __name__ == "__main__":

    main()
