import socket
import pandas as pd
from datetime import datetime
import subprocess
import time
from os.path import join, abspath, dirname

# === 設定 ===
FILE_NAME = "hospital_status.csv"  # CSVファイルへの相対パス
CSV_PATH = join(abspath(dirname(__file__)), FILE_NAME)
GITHUB_REPO = "https://github.com/yuya-0411/csv_test.git"  # トークン付きURL
UDP_PORT = 8888  # ESP32が送ってくるポート
GIT_PUSH_INTERVAL = 30  # 秒

# タイマ初期化
last_push_time = time.monotonic()

def update_hospital_status(mac, state, power):
    df = pd.read_csv(CSV_PATH)

    now = datetime.now().strftime("%H:%M:%S")
    idx = df.index[df["mac_address"] == mac]

    if not idx.empty:
        i = idx[0]
        df.at[i, "power_supply_health"] = state
        df.at[i, "power_consumption"] = power
        df.at[i, "time"] = now
        df.to_csv(CSV_PATH, index=False)
        print(f"[UPDATE] {df.at[i, 'name']} ({mac}) → {state}, {power}W at {now}")
    else:
        print(f"[WARN] MAC {mac} not found in CSV")

def git_commit_and_push_if_due():
    global last_push_time
    now = time.monotonic()
    if now - last_push_time >= GIT_PUSH_INTERVAL:
        print("[GIT] 30秒経過、CSVをGitHubに反映します...")
        subprocess.run(["git", "add", CSV_PATH])
        subprocess.run(["git", "commit", "-m", "Auto update"], check=False)
        subprocess.run(["git", "push", GITHUB_REPO], check=False)
        last_push_time = now

def listen_udp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    print(f"[INFO] Listening for UDP on port {UDP_PORT}...")

    while True:
        try:
            data, _ = sock.recvfrom(1024)
            text = data.decode().strip()
            print(f"[RECV] {text}")

            mac, state, power = text.split(",")
            if state == "ERROR":
                update_hospital_status(mac, "ERROR", 0.0)
            else:
                update_hospital_status(mac, state, float(power))

            git_commit_and_push_if_due()

        except Exception as e:
            print("[ERROR]", e)

if __name__ == "__main__":
    listen_udp()

