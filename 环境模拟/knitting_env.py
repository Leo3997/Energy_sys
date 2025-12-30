import gymnasium as gym
from gymnasium import spaces
import numpy as np
import random


class KnittingEnv(gym.Env):
    """
    符合 OpenAI Gym 标准的针织机环境
    """

    def __init__(self):
        super(KnittingEnv, self).__init__()

        # === 1. 定义动作空间 (Action Space) ===
        # AI 可以输出两个连续的值：
        #   [0]: 转速调整量 (Delta RPM), 范围 [-1.0, +1.0]
        #   [1]: 张力调整量 (Delta Tension), 范围 [-0.2, +0.2]
        self.action_space = spaces.Box(
            low=np.array([-1.0, -0.2], dtype=np.float32),
            high=np.array([1.0, 0.2], dtype=np.float32),
            shape=(2,),
            dtype=np.float32
        )

        # === 2. 定义观察空间 (Observation Space) ===
        # AI 能看到的数据 (State)：[当前转速, 当前张力, 当前功率]
        # 我们定义这些值的理论最大/最小值范围
        self.observation_space = spaces.Box(
            low=np.array([0.0, 0.0, 0.0], dtype=np.float32),
            high=np.array([150.0, 10.0, 20.0], dtype=np.float32),
            shape=(3,),
            dtype=np.float32
        )

        # 初始化内部状态
        self.state = None
        self.rpm = 80.0
        self.tension = 3.0
        self.steps_left = 100  # 每个回合限制步数

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        # 每一局开始，随机化初始状态，增加训练难度，让 AI 适应性更强
        self.rpm = 80.0 + random.uniform(-5, 5)
        self.tension = 3.0 + random.uniform(-0.5, 0.5)
        self.steps_left = 100

        # 返回初始状态
        power = self._calculate_power()
        self.state = np.array(
            [self.rpm, self.tension, power], dtype=np.float32)
        return self.state, {}

    def step(self, action):
        self.steps_left -= 1

        d_rpm = action[0]
        d_tension = action[1]

        self.rpm = np.clip(self.rpm + d_rpm, 60.0, 100.0)
        self.tension = np.clip(self.tension + d_tension, 1.0, 5.0)

        power = self._calculate_power()
        is_break = self._check_breakage()

        reward = 0
        if is_break:
            # 1. 降低惩罚力度，让它敢于尝试
            reward = -20.0
        else:
            efficiency = self.rpm / (power + 1e-5)

          # === 修改点：强力的高速补贴 ===
            # (RPM - 60) * 0.5
            # 如果跑 60转，补贴 0 分
            # 如果跑 76转，补贴 8 分！(这比能效分本身还高，诱惑巨大)
            speed_bonus = max(0, (self.rpm - 60.0) * 0.5)

            reward = efficiency + speed_bonus

            smoothness_penalty = (abs(d_rpm) + abs(d_tension)) * 0.1
            reward -= smoothness_penalty

        self.state = np.array(
            [self.rpm, self.tension, power], dtype=np.float32)

        terminated = False
        truncated = False

        if is_break:
            terminated = True
        if self.steps_left <= 0:
            truncated = True

        return self.state, reward, terminated, truncated, {}

    def _calculate_power(self):
        # 模拟物理公式：转速越快越费电，张力越大阻力越大
        return 2.0 + (self.rpm / 20.0) + (self.tension * 0.2) + random.uniform(-0.05, 0.05)

    def _check_breakage(self):
        # 模拟物理公式：75转是最佳点，超过后断纱率指数上升
        risk_rpm = max(0, (self.rpm - 75.0) * 0.2)
        prob_break = 0.0001 + (risk_rpm ** 4)  # 三次方，风险剧增
        return random.random() < prob_break
