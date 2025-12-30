import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
import joblib
import matplotlib.pyplot as plt

# === 1. 模拟采集一周的功率数据 ===


def generate_power_profile(n_points=1000):
    np.random.seed(42)

    # 定义设备额定功率 (模拟真实物理世界)
    power_fan = 1.5      # 吸风风机 (恒定)
    power_motor_base = 3.5  # 主电机 (基础)

    data = []

    for _ in range(n_points):
        # 随机模拟工厂的状态
        rand = np.random.uniform(0, 1)

        main_motor = 0
        suction_fan = 0
        state_label = "OFF"

        if rand < 0.3:
            # 状态A: 全关 (午休/下班)
            pass

        elif rand < 0.5:
            # 状态B: 只有风机 (比如刚开机还没跑，或者跑完忘关) -> 浪费时刻！
            suction_fan = power_fan + np.random.normal(0, 0.05)
            state_label = "FAN_ONLY"

        else:
            # 状态C: 正常生产 (风机必须开，电机也开)
            suction_fan = power_fan + np.random.normal(0, 0.05)
            # 电机功率会波动
            main_motor = power_motor_base + np.random.normal(0, 0.3)
            state_label = "RUNNING"

        total_power = main_motor + suction_fan
        data.append([total_power, state_label])

    return pd.DataFrame(data, columns=['total_power', 'label'])

# === 2. 训练模型 (无监督学习) ===


def train_nilm_model():
    print("📊 生成模拟功率流数据...")
    df = generate_power_profile(2000)

    # 我们只用 'total_power' 这一列来训练，模拟只有一个总电表的情况
    X = df[['total_power']]

    # 使用 K-Means 聚类，假设有 3 个主要状态中心 (关机, 仅风机, 全开)
    # AI 会自动找到这三个中心点在哪里
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    kmeans.fit(X)

    # 获取聚类中心
    centers = kmeans.cluster_centers_.flatten()
    print(f"🧠 模型识别到的功率中心: {sorted(np.round(centers, 2))} kW")

    # 自动标记：哪个中心对应哪个状态？
    # 最小的是关机，中间的是风机，最大的是全开
    sorted_idx = np.argsort(centers)
    state_map = {
        sorted_idx[0]: "OFF",
        sorted_idx[1]: "FAN_ONLY",  # 这是一个关键的“浪费”特征
        sorted_idx[2]: "RUNNING"
    }

    # 保存模型
    joblib.dump(kmeans, 'nilm_kmeans.pkl')
    joblib.dump(state_map, 'nilm_labels.pkl')
    print("✅ NILM 分解模型已保存")


if __name__ == "__main__":
    train_nilm_model()
