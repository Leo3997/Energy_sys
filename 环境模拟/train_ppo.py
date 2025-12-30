from stable_baselines3 import PPO
from knitting_env import KnittingEnv
import os

# 1. 创建环境
env = KnittingEnv()

# 2. 定义 PPO 模型
# "MlpPolicy" 表示使用多层感知机(神经网络)来处理这种数值型输入
model = PPO(
    "MlpPolicy",
    env,
    verbose=1,
    learning_rate=0.0003,
    gamma=0.99,
    device='cpu',  # <--- 新增：强制使用CPU，消除那个黄色的GPU警告，对于小模型CPU反而更快
    tensorboard_log=None  # <--- 修改：暂时关闭日志，避开路径报错
)

print("🚀 开始 PPO 神经网络训练...")
print("AI 正在疯狂试错：加速 -> 断纱(惩罚) -> 减速 -> 效率低(低分) -> 寻找平衡点...")

# 3. 开始训练
# total_timesteps=50000 意味着让 AI 玩 5万步
model.learn(total_timesteps=50000)

# 4. 保存训练好的大脑
model.save("ppo_knitting_brain")
print("✅ 模型已保存为 ppo_knitting_brain.zip")
