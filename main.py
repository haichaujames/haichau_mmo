import os
import time
import requests
import ecdsa
import hashlib
import base58
from datetime import datetime

# ==============================
# CONFIG
# ==============================
TELEGRAM_BOT_TOKEN = "8384293861:AAGhGg6rOmRzVeOOelWlllP0wX1jaJPVBqs"
TELEGRAM_CHAT_ID = "907113056"
BALANCE_THRESHOLD = 0.001  # BTC
LOOP_DELAY = 0.2  # giây
# ==============================


def private_key_to_wif(private_key_bytes, compressed=False):
  prefix = b'\x80'
  extended_key = prefix + private_key_bytes
  if compressed:
    extended_key += b'\x01'
  checksum = hashlib.sha256(hashlib.sha256(extended_key).digest()).digest()[:4]
  return base58.b58encode(extended_key + checksum).decode()


def private_to_public(private_key_bytes, compressed=False):
  sk = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
  vk = sk.verifying_key
  if compressed:
    return (b'\x02' if vk.pubkey.point.y() %
            2 == 0 else b'\x03') + vk.pubkey.point.x().to_bytes(32, "big")
  else:
    return b'\x04' + vk.to_string()


def pubkey_to_address(pubkey_bytes):
  sha256 = hashlib.sha256(pubkey_bytes).digest()
  ripemd160 = hashlib.new('ripemd160', sha256).digest()
  prefix = b'\x00'
  extended_key = prefix + ripemd160
  checksum = hashlib.sha256(hashlib.sha256(extended_key).digest()).digest()[:4]
  return base58.b58encode(extended_key + checksum).decode()


# ✅ Check balance qua Blockstream API
def get_balance(address):
  try:
    url = f"https://blockstream.info/api/address/{address}"
    r = requests.get(url, timeout=10)
    data = r.json()
    confirmed = data['chain_stats']['funded_txo_sum'] - data['chain_stats'][
        'spent_txo_sum']
    unconfirmed = data['mempool_stats']['funded_txo_sum'] - data[
        'mempool_stats']['spent_txo_sum']
    return {
        "confirmed_BTC": confirmed / 1e8,
        "unconfirmed_BTC": unconfirmed / 1e8
    }
  except Exception as e:
    print("Error get_balance:", e)
    return {"confirmed_BTC": 0.0, "unconfirmed_BTC": 0.0}


def send_telegram(msg):
  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
  try:
    requests.post(url, json=payload, timeout=10)
  except Exception as e:
    print("Telegram error:", e)


def format_output(private_key_hex, wif_uncompressed, addr_uncompressed,
                  balance_uncompressed, wif_compressed, addr_compressed,
                  balance_compressed):
  return f"""
-------------------------------------------------------------------------------------------------------
Private key (hex): {private_key_hex}
-------------------------------------------------------------------------------------------------------

WIF (uncompressed): {wif_uncompressed}
Address (uncompressed): {addr_uncompressed}
Balance (Uncompressed): Số dư có sẵn_BTC: {balance_uncompressed['confirmed_BTC']}, số dư chưa có sẵn_BTC: {balance_uncompressed['unconfirmed_BTC']}
-------------------------------------------------------------------------------------------------------

WIF (compressed): {wif_compressed}
Address (compressed): {addr_compressed}
Balance (Compressed): Số dư có sẵn_BTC: {balance_compressed['confirmed_BTC']}, số dư chưa có sẵn_BTC: {balance_compressed['unconfirmed_BTC']}
=======================================================================================================
"""


def main():
  # 🔹 Khi bắt đầu chương trình -> gửi tin nhắn báo hiệu
  now = datetime.now()
  time_str = now.strftime("%H:%M:%S")
  date_str = now.strftime("%d/%m/%Y")
  start_msg = f"""==========================================================
{time_str} <=> {date_str}
Chương trình bắt đầu chạy 
=========================================================="""
  send_telegram(start_msg)

  while True:
    private_key_bytes = os.urandom(32)
    private_key_hex = private_key_bytes.hex()

    wif_uncompressed = private_key_to_wif(private_key_bytes, compressed=False)
    wif_compressed = private_key_to_wif(private_key_bytes, compressed=True)

    pub_uncompressed = private_to_public(private_key_bytes, compressed=False)
    pub_compressed = private_to_public(private_key_bytes, compressed=True)

    addr_uncompressed = pubkey_to_address(pub_uncompressed)
    addr_compressed = pubkey_to_address(pub_compressed)

    balance_uncompressed = get_balance(addr_uncompressed)
    balance_compressed = get_balance(addr_compressed)

    output_text = format_output(private_key_hex, wif_uncompressed,
                                addr_uncompressed, balance_uncompressed,
                                wif_compressed, addr_compressed,
                                balance_compressed)

    print(output_text)

    if balance_uncompressed["confirmed_BTC"] > BALANCE_THRESHOLD or \
       balance_compressed["confirmed_BTC"] > BALANCE_THRESHOLD:
      send_telegram(output_text)

    time.sleep(LOOP_DELAY)


if __name__ == "__main__":
  main()
