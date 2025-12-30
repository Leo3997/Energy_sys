import socket
import json
import time
import random
from datetime import datetime

# 连接配置
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8012


class DevicePhysics:
    def __init__(self):
        self.lubrication = 1.0
        self.temperature = 25.0
        self.current = 10.0
        self.friction = 1.0
        self.is_running = True # [NEW] Persistent State
        
        # 1.0 = 演示模式 (极快)
        # 0.1 = 慢速模式 (更真实，变化缓慢)
        self.time_scale = 0.1
        
    def update(self, inject_signal=False, stop_signal=False, start_signal=False):
        # 1. Update State Flags
        if stop_signal:
            self.is_running = False
            print("\033[91m>>> [润滑机] 停止运行 (Persistent)\033[0m")
        if start_signal:
            self.is_running = True
            self.current = 10.0
            self.friction = 1.0
            self.lubrication = 1.0
            print("\033[92m>>> [润滑机] 恢复运行\033[0m")

        # 2. Logic based on State
        if not self.is_running:
            self.current = 0.0
            self.friction = 0.0
            # Cool down
            dt = self.time_scale
            heat_out = (self.temperature - 25.0) * 0.2
            self.temperature -= heat_out * dt
            return

        # 3. Normal Operation
        # 如果收到注油信号，恢复状态
        if inject_signal:
            self.lubrication = min(1.0, self.lubrication + 0.4)
            self.temperature -= (0.2 * self.time_scale)
        # 自然衰减与摩擦逻辑
        base_decay = 0.0005 # 原来是 0.005，缩小10倍
        decay = base_decay * random.uniform(0.8, 1.5)
        # 如果当前在运行(有电流)，衰减才发生
        if self.current > 1.0: 
            self.lubrication = max(0.05, self.lubrication - decay)

        # 2. 摩擦力计算 (不变)
        self.friction = 1.0 + (1.0 - self.lubrication) ** 2 * 3.0
        #电流计算
        base_current = 10.0
        self.current = (base_current * self.friction) + random.uniform(-0.1, 0.1)
        #3.热量计算 (Modified for 13A -> 55C target, fast response)
        # Ratio of coefficients (2.0 / 0.2 = 10) determines equilibrium temp.
        # Magnitude (2.0, 0.2) determines speed.
        heat_in = (self.current - 10.0) * 2.0 
        heat_out = (self.temperature - 25.0) * 0.2
        # 应用时间缩放
        dt = self.time_scale # 模拟的时间步长
        self.temperature += (heat_in - heat_out) * dt + random.uniform(-0.01, 0.01)

    def get_data(self):
        return {
            "device_type": "LUBRICATION_BOT",  # <--- 身份标识
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "current_a": round(self.current, 2),
            "temperature_c": round(self.temperature, 2)
        }


def start_device():
    device = DevicePhysics()
    while True:
        try:
            print(f"🔄 [润滑设备] 正在连接中心 {SERVER_HOST}:{SERVER_PORT}...")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((SERVER_HOST, SERVER_PORT))
                print(f"✅ [润滑设备] 已连接!")

                while True:
                    data = device.get_data()
                    s.sendall(json.dumps(data).encode('utf-8'))

                    # 接收指令
                    resp = json.loads(s.recv(1024).decode('utf-8'))
                    action = resp.get("action", "MONITOR")
                    # --- 修改开始: 优化显示逻辑 ---
                    if not device.is_running:
                        # 停机状态：打印灰色或红色提示，且不刷屏太快
                        print(f"\033[90m[润滑机] ⛔ 已停机 (待机中) | 温度:{data['temperature_c']}C | 等待指令...\033[0m")
                    else:
                        # 运行状态：正常打印绿色/白色
                        status_color = "\033[92m" if action == "INJECT" else "\033[0m"
                        print(f"[润滑机] 电流:{data['current_a']}A | 温度:{data['temperature_c']}C | {status_color}指令:{action}\033[0m")

                    # 执行闭环
                    device.update(inject_signal=(action == "INJECT"), stop_signal=(action == "STOP"), start_signal=(action == "START"))
                    time.sleep(1)

        except Exception as e:
            print(f"⚠️ 连接断开或失败: {e}")
            print("   -> 3秒后重连...")
            time.sleep(3)


if __name__ == "__main__":
    start_device()