import numpy as np
import random


class TensionEnvironment:
    def __init__(self):
        self.reset()

    def reset(self):
        self.yarn_remain = 1.0  # 100% 纱线
        self.tension = 3.0
        self.power = 3.2
        self.steps = 0
        return self.get_state()

    def get_state(self):
        # 状态离散化 (Discretization)
        # 我们关注两个指标：
        # 1. 纱线剩余量 (分10个等级) -> AI 会学到纱线少的时候危险
        # 2. 当前张力 (分10个等级) -> AI 会学到张力高费电

        yarn_idx = int(self.yarn_remain * 10)  # 0.95 -> 9, 0.15 -> 1
        yarn_idx = max(0, min(9, yarn_idx))

        # 张力范围假设 3.0 ~ 13.0
        tension_idx = int(min(9, max(0, self.tension - 3.0)))

        return (yarn_idx, tension_idx)

    def step(self, action):
        # Action: 0=Monitor, 1=Optimize
        self.steps += 1

        action_cost = 0
        if action == 1:
            # 执行优化的代价
            # 假设每次换筒/复位相当于消耗了 5.0 单位的"虚拟能量" (停机损失)
            # 如果把这个值调大，AI就会更"懒"，直到迫不得已才换
            action_cost = 5.0

            # 状态重置
            self.yarn_remain = 1.0
            self.tension = 3.0

        # === 物理模拟 (复用你的设备代码逻辑) ===
        if action == 0:
            self.yarn_remain = max(0, self.yarn_remain - 0.02)

            base_tension = 3.0
            if self.yarn_remain < 0.20:
                spike = (0.20 - self.yarn_remain) * 40
                self.tension = base_tension + spike + np.random.normal(0, 0.2)
            else:
                self.tension = base_tension + np.random.normal(0, 0.1)

        # 计算功耗
        tension_penalty = max(0, (self.tension - 3.0) * 0.2)
        self.power = 3.2 + tension_penalty

        # === 奖励函数 (Reward Function) ===
        # 目标：总成本最低
        # 成本 = (额外的电费) + (操作动作的成本)
        # 这里的 2.0 是电费权重，意味着每多用1W电，惩罚2分
        electricity_cost = (self.power - 3.2) * 2.0

        reward = -electricity_cost - action_cost

        # 结束条件
        done = False
        if self.steps >= 500:  # 训练一个回合最多500步
            done = True

        return self.get_state(), reward, done
