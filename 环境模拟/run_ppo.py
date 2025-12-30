from stable_baselines3 import PPO
from knitting_env import KnittingEnv
import time

# 1. 加载环境和模型
env = KnittingEnv()
model = PPO.load("ppo_knitting_brain")

print("🤖 加载 PPO 模型，开始接管设备...")

# 2. 开始运行
obs, _ = env.reset()
total_reward = 0

for i in range(50):  # 模拟运行 50 个周期
    # === 关键点：让神经网络预测动作 ===
    # deterministic=True 表示不随机探索了，直接拿最优解
    action, _states = model.predict(obs, deterministic=True)

    # 执行动作
    obs, reward, terminated, truncated, info = env.step(action)
    total_reward += reward

    rpm = obs[0]
    tension = obs[1]
    power = obs[2]

    status = "🔴 断纱" if terminated else "🟢 正常"
    print(
        f"Step {i:02d} | RPM: {rpm:.2f} | 张力: {tension:.2f} | 动作: {action} | {status}")

    if terminated:
        print("❌ 发生断纱，模拟结束")
        break

    time.sleep(0.1)

print(f"最终平均能效得分: {total_reward/50:.2f}")
