import socket
import json
import time
import random
import numpy as np

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8012  # 注意：连接同一个端口


class KnittingMachineSim:
    def __init__(self):
        self.tension = 3.0
        self.yarn_remain = 1.0
        self.power = 3.2
        self.is_running = True # [NEW] Persistent State

    def update(self, fix_signal=False, stop_signal=False, start_signal=False):
        # 1. Update State
        if stop_signal:
            self.is_running = False
            print("\033[91m>>> [张力机] 停止运行 (Persistent)\033[0m")
        if start_signal:
            self.is_running = True
            self.power = 3.2
            self.tension = 3.0
            print("\033[92m>>> [张力机] 恢复运行\033[0m")

        # 2. Logic based on State
        if not self.is_running:
            self.power = 0.0
            self.tension = 0.0
            return

        if fix_signal:
            print("\033[96m>>> [张力机] 执行自动换筒操作...\033[0m")
            self.yarn_remain = 1.0
            self.tension = 3.0
            time.sleep(1)  # 模拟换筒时间
            return

        # 模拟纱线消耗 (3小时耗尽: 1.0 / (3*3600) ≈ 0.0000925 -> 0.0001)
        self.yarn_remain = max(0, self.yarn_remain - 0.0001)

        base_tension = 3.0
        if self.yarn_remain < 0.20:
            spike = (0.20 - self.yarn_remain) * 40
            self.tension = base_tension + spike + np.random.normal(0, 0.2)
        else:
            self.tension = base_tension + np.random.normal(0, 0.1)

        tension_penalty = max(0, (self.tension - 3.0) * 0.2)
        self.power = 3.2 + tension_penalty

    def get_data(self):
        return {
            "device_type": "TENSION_BOT",  # <--- 身份标识
            "tension": round(self.tension, 2),
            "yarn_pct": round(self.yarn_remain * 100, 1),
            "power": round(self.power, 2)
        }


def start_device():
    machine = KnittingMachineSim()
    while True:
        try:
            print(f"🔄 [张力设备] 正在连接中心 {SERVER_HOST}:{SERVER_PORT}...")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((SERVER_HOST, SERVER_PORT))
                print(f"✅ [张力设备] 已连接!")

                while True:
                    data = machine.get_data()
                    s.sendall(json.dumps(data).encode('utf-8'))

                    resp = json.loads(s.recv(1024).decode('utf-8'))
                    action = resp.get("action", "MONITOR")

                    # --- 修改开始 ---
                    if not machine.is_running:
                        print(f"\033[90m[张力机] ⛔ 已停机 (待机中) | 纱余:{data['yarn_pct']}% | 等待指令...\033[0m")
                    else:
                        color = "\033[91m" if action == "OPTIMIZE_TENSION" else "\033[0m"
                        print(f"[张力机] 纱余:{data['yarn_pct']}% | 张力:{data['tension']}g | {color}指令:{action}\033[0m")
                    # --- 修改结束 ---

                    machine.update(fix_signal=(action == "OPTIMIZE_TENSION"), stop_signal=(action == "STOP"), start_signal=(action == "START"))
                    time.sleep(1)

        except Exception as e:
            print(f"⚠️ 连接断开或失败: {e}")
            print("   -> 3秒后重连...")
            time.sleep(3)


if __name__ == "__main__":
    start_device()
