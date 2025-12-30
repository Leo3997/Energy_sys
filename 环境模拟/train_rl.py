import numpy as np
import pickle
from env_sim import OilEnvironment

# Q-Table: 10种电流状态 x 10种温度状态 x 2种动作(喷/不喷)
q_table = np.zeros((10, 10, 2))

# 超参数
epsilon = 0.9   # 探索率 (前期多瞎试，后期多利用)
alpha = 0.1     # 学习率
gamma = 0.9     # 折扣因子 (看重长远利益)
EPISODES = 5000

env = OilEnvironment()

print("🚀 开始强化学习训练...")

for episode in range(EPISODES):
    state = env.reset()  # state is (current_idx, temp_idx)
    done = False

    # 随着训练进行，减少瞎试的概率 (Epsilon Decay)
    if epsilon > 0.1:
        epsilon -= 0.0002

    while not done:
        # 1. 选择动作 (Epsilon-Greedy)
        if np.random.uniform(0, 1) < epsilon:
            action = np.random.choice([0, 1])  # 探索：随机试
        else:
            action = np.argmax(q_table[state[0], state[1]])  # 利用：选目前最好的

        # 2. 与环境交互
        next_state, reward, done = env.step(action)

        # 3. 更新 Q-Table (贝尔曼方程)
        # Q(S,A) = Q(S,A) + alpha * [R + gamma * max(Q(S',a)) - Q(S,A)]
        old_value = q_table[state[0], state[1], action]
        next_max = np.max(q_table[next_state[0], next_state[1]])

        new_value = old_value + alpha * (reward + gamma * next_max - old_value)
        q_table[state[0], state[1], action] = new_value

        state = next_state

    if episode % 500 == 0:
        print(f"Episode {episode}: 剩余 Epsilon {epsilon:.3f}")

# 保存训练好的大脑
with open("q_brain.pkl", "wb") as f:
    pickle.dump(q_table, f)

print("✅ 训练完成！模型已保存为 q_brain.pkl")
# 打印一部分策略看看
print("\n--- 策略预览 (部分) ---")
print("当电流很高(Idx=8), 温度很高(Idx=8)时 ->",
      "喷油" if np.argmax(q_table[8, 8]) == 1 else "不喷")
print("当电流正常(Idx=1), 温度正常(Idx=1)时 ->",
      "喷油" if np.argmax(q_table[1, 1]) == 1 else "不喷")
