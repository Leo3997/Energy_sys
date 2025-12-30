import random
import numpy as np


class OilEnvironment:
    def __init__(self):
        self.reset()

    def reset(self):
        # 初始状态
        self.lubrication = 1.0
        self.temperature = 40.0
        self.current = 10.0
        self.friction = 1.0
        self.health = 100.0  # <--- 新增：生命值
        self.steps = 0
        return self.get_state()

    def get_state(self):
        # 为了让 Q-Learning 表格更小，我们将连续数值"离散化" (分桶)
        # 电流: 10.0~15.0 -> 映射为 0~9 的整数
        # 温度: 25.0~75.0 -> 映射为 0~9 的整数
        curr_idx = int(min(9, max(0, (self.current - 9.0) * 2)))
        temp_idx = int(min(9, max(0, (self.temperature - 25.0) / 5)))
        return (curr_idx, temp_idx)

    def step(self, action):
        """
        Action: 0 = 不喷, 1 = 喷油
        返回: next_state, reward, done
        """
        self.steps += 1

        # 1. 执行动作
        inject_cost = 0
        if action == 1:
            self.lubrication = min(1.0, self.lubrication + 0.6)  # 喷油恢复润滑
            self.temperature -= 2.0
            inject_cost = 2.0  # <--- 代价 A: 喷油要花钱 (比如2块钱)

        # 2. 物理演变 (照搬之前的逻辑)
        decay = 0.01 * random.uniform(0.8, 1.2)
        self.lubrication = max(0.05, self.lubrication - decay)
        self.friction = 1.0 + (1.0 - self.lubrication) ** 3 * 5.0  # 摩擦恶化更快一点

        base_current = 10.0
        self.current = (base_current * self.friction) + \
            random.uniform(-0.1, 0.1)

        heat_in = (self.current - 10.0) * 1.5
        heat_out = (self.temperature - 25.0) * 0.1
        self.temperature += (heat_in - heat_out)

        # 3. 计算磨损 (Health Damage)
        # 如果摩擦过大或温度过高，健康值下降
        damage = 0
        if self.friction > 1.5 or self.temperature > 55:
            damage = (self.friction - 1.0) * 10  # 磨损速度
            self.health -= damage

        # 4. 计算奖励 (Reward)
        # 奖励 = -(喷油成本) - (设备磨损成本 * 权重)
        # 我们希望这个值越大越好 (即扣分越少越好)
        reward = -inject_cost - (damage * 5.0)

        # 5. 判断结束
        done = False
        if self.health <= 0:
            reward = -1000  # 惩罚：机器挂了，巨额扣分
            done = True
        if self.steps >= 1000:  # 或者运行时间到了
            done = True

        return self.get_state(), reward, done
