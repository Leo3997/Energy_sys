import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import joblib

# === 1. 模拟历史生产数据 (实际场景中，这是从你的数据库读取的 CSV) ===


def generate_mock_data(n_samples=1000):
    np.random.seed(42)

    data = []
    yarns = ['Nylon', 'Spandex', 'Polyester']     # 锦纶, 氨纶, 涤纶
    structures = ['Plain', 'Rib', 'Jacquard']     # 平纹, 罗纹, 提花

    for _ in range(n_samples):
        # 随机生成工艺参数
        diameter = np.random.choice([14, 28, 30, 34])
        needles = int(diameter * np.random.uniform(20, 30) * 3)  # 估算针数
        yarn = np.random.choice(yarns)
        struct = np.random.choice(structures)
        rpm = np.random.uniform(15, 30)  # 建议加入转速

        # --- 模拟物理规律 (生成 Label: Power) ---
        # 基础功率
        base_power = 2.0
        # 筒径越大、针数越多，功率越大
        hw_factor = (diameter / 14.0) * (needles / 2000.0)
        # 纱线摩擦系数: 涤纶 > 锦纶 > 氨纶 (假设)
        yarn_factor = {'Polyester': 1.2, 'Nylon': 1.1, 'Spandex': 1.0}[yarn]
        # 结构复杂度: 提花 > 罗纹 > 平纹
        struct_factor = {'Jacquard': 1.5, 'Rib': 1.2, 'Plain': 1.0}[struct]
        # 速度影响: 功率与速度大致成正比
        speed_factor = rpm / 20.0

        # 最终功率 = 基础 * 硬件 * 纱线 * 结构 * 速度 + 随机波动(噪声)
        power = base_power * hw_factor * yarn_factor * struct_factor * speed_factor
        power += np.random.normal(0, 0.2)  # 添加一点现实世界的噪声

        data.append([diameter, needles, yarn, struct, rpm, round(power, 2)])

    df = pd.DataFrame(
        data, columns=['diameter', 'needles', 'yarn', 'structure', 'rpm', 'power'])
    return df

# === 2. 训练模型 ===


def train_model():
    print("📊 正在生成并加载训练数据...")
    df = generate_mock_data(2000)

    # 特征预处理：One-Hot 编码
    # 将 yarn 和 structure 转换为数值列 (例如 yarn_Nylon, structure_Rib)
    df_encoded = pd.get_dummies(df, columns=['yarn', 'structure'])

    # 定义特征 (X) 和 目标 (y)
    X = df_encoded.drop('power', axis=1)
    y = df_encoded['power']

    # 保存列名，这非常重要！预测时输入数据的列顺序必须和训练时完全一致
    feature_columns = X.columns.tolist()
    joblib.dump(feature_columns, 'model_columns.pkl')

    # 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42)

    # 初始化随机森林回归器
    model = RandomForestRegressor(n_estimators=100, random_state=42)

    print("🚀 开始训练基线模型...")
    model.fit(X_train, y_train)

    # 评估
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    print(f"✅ 训练完成！平均预测误差 (MAE): {mae:.3f} kW")
    print(f"   (意味着模型预测的基线值与理论值平均只差 {mae*1000:.1f} 瓦)")

    # 保存模型
    joblib.dump(model, 'energy_baseline_model.pkl')
    print("💾 模型已保存为 energy_baseline_model.pkl")


if __name__ == "__main__":
    train_model()
