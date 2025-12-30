import numpy as np
import pickle
from env_tension_sim import TensionEnvironment

# Q-Table: 10种纱线状态 x 10种张力状态 x 2种动作
q_table = np.zeros((10, 10, 2))

# 参数
epsilon = 0.9
alpha = 0.1
gamma = 0.95
EPISODES = 5000

env = TensionEnvironment()

print("🧵 [张力优化] 开始 RL 训练...")

for episode in range(EPISODES):
    state = env.reset()
    done = False

    # 衰减探索率
    if epsilon > 0.05:
        epsilon -= 0.0002

    while not done:
        # 1. 选动作
        if np.random.uniform(0, 1) < epsilon:
            action = np.random.choice([0, 1])
        else:
            action = np.argmax(q_table[state[0], state[1]])

        # 2. 交互
        next_state, reward, done = env.step(action)

        # 3. 学习 (贝尔曼方程)
        old_val = q_table[state[0], state[1], action]
        next_max = np.max(q_table[next_state[0], next_state[1]])
        new_val = old_val + alpha * (reward + gamma * next_max - old_val)
        q_table[state[0], state[1], action] = new_val

        state = next_state

# 保存模型
with open("tension_q_brain.pkl", "wb") as f:
    pickle.dump(q_table, f)

print("✅ 模型已保存为 tension_q_brain.pkl")

# --- 验证一下 AI 学到了什么 ---
print("\n--- AI 策略预览 ---")
# 看看纱线充足(状态9)且张力正常(状态0)时，它怎么选
act_normal = np.argmax(q_table[9, 0])
print(f"纱线充足(100%), 张力低 -> {'🔴 必须换筒' if act_normal==1 else '🟢 继续运行'}")

# 看看纱线快没了(状态1)且张力极高(状态8)时，它怎么选
act_danger = np.argmax(q_table[1, 8])
print(f"纱线告急(10%), 张力高 -> {'🔴 必须换筒' if act_danger==1 else '🟢 继续运行'}")
