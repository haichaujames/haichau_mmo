import hashlib
import os
import time
from datetime import datetime, timedelta, timezone

import base58
import ecdsa
import requests

# ==============================
# CONFIG
# ==============================
TELEGRAM_BOT_TOKEN = "8384293861:AAGhGg6rOmRzVeOOelWlllP0wX1jaJPVBqs"
TELEGRAM_CHAT_ID = "907113056"
BALANCE_THRESHOLD = 0.001  # BTC
BATCH_SIZE = 200
LOOP_DELAY = 5  # giây giữa mỗi batch
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


# ✅ Check balance cho nhiều địa chỉ 1 lần
def get_balances(address_list):
  try:
    addresses_str = "|".join(address_list)
    url = f"https://blockchain.info/balance?active={addresses_str}"
    r = requests.get(url, timeout=20)
    data = r.json()
    balances = {}
    for addr in address_list:
      if addr in data:
        balances[addr] = data[addr]['final_balance'] / 1e8
      else:
        balances[addr] = 0.0
    return balances
  except Exception as e:
    print("Error get_balances:", e)
    return dict.fromkeys(address_list, 0.0)


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
Balance (Uncompressed): {balance_uncompressed} BTC
-------------------------------------------------------------------------------------------------------

WIF (compressed): {wif_compressed}
Address (compressed): {addr_compressed}
Balance (Compressed): {balance_compressed} BTC
=======================================================================================================
"""


def main():
  # 🔹 Khi bắt đầu chương trình -> gửi tin nhắn báo hiệu
  gmt7 = timezone(timedelta(hours=7))
  now = datetime.now(gmt7)
  time_str = now.strftime("%H:%M:%S")
  date_str = now.strftime("%d/%m/%Y")
  start_msg = f"""==========================================================
{time_str} <=> {date_str}
Chương trình bắt đầu chạy 
=========================================================="""
  send_telegram(start_msg)

  while True:
    batch_private_keys = [os.urandom(32) for _ in range(BATCH_SIZE)]
    addresses_info = []

    # Tạo địa chỉ từ private key
    for pk_bytes in batch_private_keys:
      pk_hex = pk_bytes.hex()
      wif_uncompressed = private_key_to_wif(pk_bytes, compressed=False)
      wif_compressed = private_key_to_wif(pk_bytes, compressed=True)
      pub_uncompressed = private_to_public(pk_bytes, compressed=False)
      pub_compressed = private_to_public(pk_bytes, compressed=True)
      addr_uncompressed = pubkey_to_address(pub_uncompressed)
      addr_compressed = pubkey_to_address(pub_compressed)

      addresses_info.append({
          'private_key_hex': pk_hex,
          'wif_uncompressed': wif_uncompressed,
          'addr_uncompressed': addr_uncompressed,
          'wif_compressed': wif_compressed,
          'addr_compressed': addr_compressed
      })

    # Lấy balance cho toàn bộ batch cùng lúc
    all_addresses = []
    for info in addresses_info:
      all_addresses.append(info['addr_uncompressed'])
      all_addresses.append(info['addr_compressed'])

    balances = get_balances(all_addresses)

    # Gán balance vào từng địa chỉ và xuất kết quả
    for info in addresses_info:
      balance_uncompressed = balances.get(info['addr_uncompressed'], 0.0)
      balance_compressed = balances.get(info['addr_compressed'], 0.0)

      output_text = format_output(info['private_key_hex'],
                                  info['wif_uncompressed'],
                                  info['addr_uncompressed'],
                                  balance_uncompressed, info['wif_compressed'],
                                  info['addr_compressed'], balance_compressed)

      #print(output_text)

      if balance_uncompressed > BALANCE_THRESHOLD or balance_compressed > BALANCE_THRESHOLD:
        send_telegram(output_text)

    # Delay giữa các batch
    time.sleep(LOOP_DELAY)


if __name__ == "__main__":
  main()
