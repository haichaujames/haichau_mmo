import os
import time
import random
import requests
import datetime
import bitcoin

# Lấy biến môi trường
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message: str):
    """Gởi tin nhắn Telegram"""
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception:
            pass

def get_balance(address: str):
    """Fake balance check (bạn thay bằng API ElectrumX hoặc blockchain explorer)"""
    # Ở đây mình giả lập cho dễ test
    return {"confirmed_BTC": round(random.random() * 0.002, 8), "unconfirmed_BTC": 0.0}

def format_wallet_info(private_key_hex, wif_uncompressed, addr_uncompressed, balance_uncompressed,
                       wif_compressed, addr_compressed, balance_compressed):
    return f"""-------------------------------------------------------------------------------------------------------
Private key (hex): {private_key_hex}
-------------------------------------------------------------------------------------------------------

WIF (uncompressed): {wif_uncompressed}
Address (uncompressed): {addr_uncompressed}
Balance (Uncompressed): Số dư có sẵn_BTC': {balance_uncompressed['confirmed_BTC']}, số dư chưa có sẵn_BTC': {balance_uncompressed['unconfirmed_BTC']}
-------------------------------------------------------------------------------------------------------

WIF (compressed): {wif_compressed}
Address (compressed): {addr_compressed}
Balance (Compressed): Số dư có sẵn_BTC': {balance_compressed['confirmed_BTC']}, số dư chưa có sẵn_BTC': {balance_compressed['unconfirmed_BTC']}
"""

def main_loop():
    """Vòng lặp chính"""
    # Gởi tin nhắn khi start
    now = datetime.datetime.now().strftime("%H:%M:%S <=> %d/%m/%Y")
    send_telegram_message(f"""==========================================================
{now}
Chương trình bắt đầu chạy 
==========================================================""")

    while True:
        # Sinh private key ngẫu nhiên
        private_key_hex = os.urandom(32).hex()

        # Sinh WIF và địa chỉ
        wif_uncompressed = bitcoin.encode_privkey(private_key_hex, 'wif')
        wif_compressed = bitcoin.encode_privkey(private_key_hex + "01", 'wif')

        addr_uncompressed = bitcoin.privkey_to_address(private_key_hex)
        addr_compressed = bitcoin.privkey_to_address(private_key_hex + "01")

        # Check balance
        balance_uncompressed = get_balance(addr_uncompressed)
        balance_compressed = get_balance(addr_compressed)

        # Nếu có số dư > 0.001 BTC thì gởi Telegram
        if balance_uncompressed["confirmed_BTC"] > 0.001 or balance_compressed["confirmed_BTC"] > 0.001:
            msg = format_wallet_info(
                private_key_hex,
                wif_uncompressed, addr_uncompressed, balance_uncompressed,
                wif_compressed, addr_compressed, balance_compressed
            )
            send_telegram_message(msg)

        time.sleep(1)  # tránh spam CPU

if __name__ == "__main__":
    main_loop()
