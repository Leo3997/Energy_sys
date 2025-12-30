import joblib
import numpy as np
import os


class NILMDisaggregator:
    def __init__(self):
        if os.path.exists('nilm_kmeans.pkl'):
            self.model = joblib.load('nilm_kmeans.pkl')
            self.labels_map = joblib.load('nilm_labels.pkl')
            # 将中心点排序，方便后续计算
            self.centers = sorted(self.model.cluster_centers_.flatten())
            self.fan_power_est = self.centers[1]  # 聚类中心里中间那个通常是风机
            print(f"🔍 [NILM] 加载成功. 估算风机功率: {self.fan_power_est:.2f} kW")
        else:
            print("⚠️ 未找到 NILM 模型，请先运行 train_nilm.py")
            self.model = None

    def disassemble(self, total_power):
        """
        输入: 总功率
        输出: {主电机功率, 风机功率, 状态, 是否浪费}
        """
        if not self.model:
            return {}

        # 1. 识别状态
        cluster_idx = self.model.predict([[total_power]])[0]
        # 找到该簇对应的中心值（用于查表确定含义）
        # 注意：KMeans的label是随机的(0,1,2)，我们需要通过中心值大小来找对应的真实含义
        predicted_center = self.model.cluster_centers_[cluster_idx][0]

        # 找到最接近的已知中心
        closest_center_idx = np.argmin(
            np.abs(np.array(self.centers) - predicted_center))
        state = ["OFF", "FAN_ONLY", "RUNNING"][closest_center_idx]

        # 2. 功率分解 (数学减法)
        fan_p = 0.0
        motor_p = 0.0
        is_waste = False

        if state == "OFF":
            fan_p = 0
            motor_p = 0

        elif state == "FAN_ONLY":
            fan_p = total_power  # 此时全是风机
            motor_p = 0
            is_waste = True  # 🚨 只有风机在转，主电机没动 -> 浪费！

        elif state == "RUNNING":
            fan_p = self.fan_power_est  # 假设风机是恒定负载
            motor_p = max(0, total_power - fan_p)  # 剩下的都是主电机

        return {
            "total_kw": round(total_power, 2),
            "main_motor_kw": round(motor_p, 2),
            "fan_kw": round(fan_p, 2),
            "state": state,
            "is_waste": is_waste
        }


# === 测试代码 ===
if __name__ == "__main__":
    nilm = NILMDisaggregator()

    # 模拟场景测试
    test_powers = [0.1, 1.55, 5.2]

    for p in test_powers:
        res = nilm.disassemble(p)
        print(
            f"输入: {p}kW -> 状态:{res['state']} | 电机:{res['main_motor_kw']}kW + 风机:{res['fan_kw']}kW | 浪费警告: {res['is_waste']}")
