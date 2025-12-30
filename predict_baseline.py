import pandas as pd
import joblib
import numpy as np


class EnergyBaselinePredictor:
    def __init__(self):
        try:
            self.model = joblib.load('energy_baseline_model.pkl')
            self.model_columns = joblib.load('model_columns.pkl')  # 加载训练时的列结构
            print("🧠 基线模型加载成功")
        except:
            print("⚠️ 模型文件缺失，请先运行训练脚本")

    def predict_baseline(self, diameter, needles, yarn, structure, rpm):
        # 1. 构造原始数据 Frame
        input_data = pd.DataFrame([{
            'diameter': diameter,
            'needles': needles,
            'yarn': yarn,
            'structure': structure,
            'rpm': rpm
        }])

        # 2. 进行同样的 One-Hot 编码
        input_encoded = pd.get_dummies(
            input_data, columns=['yarn', 'structure'])

        # 3. 对齐列 (核心步骤)
        # 因为输入只有一行 'Nylon'，get_dummies 不会生成 'yarn_Polyester' 列，
        # 但模型需要看到所有列（即便是0）。所以我们要补齐缺失的列。
        for col in self.model_columns:
            if col not in input_encoded.columns:
                input_encoded[col] = 0

        # 确保列顺序一致
        input_encoded = input_encoded[self.model_columns]

        # 4. 预测
        baseline_power = self.model.predict(input_encoded)[0]
        return round(baseline_power, 2)


# === 测试场景 ===
if __name__ == "__main__":
    predictor = EnergyBaselinePredictor()

    # 场景 A: 小机器做简单的平纹
    p1 = predictor.predict_baseline(
        diameter=14, needles=1800, yarn='Spandex', structure='Plain', rpm=20)
    print(f"场景A (14寸/平纹) 标准功耗: {p1} kW")

    # 场景 B: 大机器做复杂的提花 (理应更高)
    p2 = predictor.predict_baseline(
        diameter=34, needles=4000, yarn='Polyester', structure='Jacquard', rpm=20)
    print(f"场景B (34寸/提花) 标准功耗: {p2} kW")

    # === 实际应用逻辑 ===
    real_time_power = 6.8  # 假设传感器读数
    diff = real_time_power - p2
    percentage = (diff / p2) * 100

    print(f"\n当前实际功耗: {real_time_power} kW")
    print(f"偏差值: {diff:.2f} kW ({percentage:.1f}%)")

    if percentage > 15:  # 设定阈值：超过基线 15% 报警
        print("🚨 异常报警：当前能耗远超该款式的理论基线！可能存在机械故障。")
    else:
        print("✅ 能耗正常 (处于该款式的合理波动范围内)")
