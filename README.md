# 得鹿山能耗优化中心

一个基于机器学习和实时监控的智能能耗优化系统，用于监控和优化工业设备的能耗。

## 项目概述

本项目是一个综合性的能耗监控与优化系统，包含实时数据采集、机器学习预测、智能控制和可视化展示等功能。系统通过模拟工业设备（如润滑机、张力机等）的运行状态，收集能耗数据，并使用强化学习和LSTM模型进行能耗优化。

## 核心功能

- **实时监控**：通过Socket连接实时监控设备状态
- **数据采集**：使用InfluxDB存储设备运行数据
- **能耗预测**：使用LSTM模型预测未来能耗
- **智能优化**：基于强化学习的能耗优化算法
- **可视化界面**：Web Dashboard展示实时数据和优化结果
- **设备控制**：远程控制设备开关和参数调节

## 系统架构

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Dashboard     │◄──►│  Backend Server  │◄──►│  Device Simulators │
│   (Web UI)      │    │ (Flask + SocketIO)│    │ (Oil/Tension)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   InfluxDB         │
                    │   (Data Storage)   │
                    └────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  ML Models         │
                    │  (LSTM/Q-Learning) │
                    └────────────────────┘
```

## 主要组件

### 1. 后端服务 (backend_server_influx.py)
- 基于Flask和SocketIO的Web服务器
- 提供REST API和WebSocket接口
- 连接远程InfluxDB数据库
- 集成LSTM预测模型和强化学习优化算法

### 2. 设备模拟器
- **device_sender_oil.py**：模拟润滑油设备
- **device_tension.py**：模拟张力设备
- 通过Socket向后端发送模拟数据

### 3. 数据库
- InfluxDB：时序数据存储
- MySQL：配置和设置数据存储

### 4. 机器学习模型
- LSTM：能耗预测模型
- Q-Learning：能耗优化算法
- 基于强化学习的智能决策系统

### 5. 监控脚本
- `monitor_energy_services.sh`：监控服务运行状态
- `start_energy_services.sh`：启动所有服务

## 技术栈

### 后端技术
- Python 3.10+
- Flask + Flask-SocketIO
- InfluxDB Client
- MySQL Connector

### 机器学习
- Scikit-learn
- PyTorch
- Stable-Baselines3
- NumPy, Pandas

### 前端技术
- HTML5/CSS3
- JavaScript
- SocketIO Client
- Chart.js (图表展示)

## 安装与部署

### 1. 环境准备
```bash
# 克隆项目
git clone <repository-url>
cd energy

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量
```bash
# 编辑 .env 文件
cp .env.example .env
# 配置数据库连接和其他参数
```

### 3. 启动服务
```bash
# 启动所有服务
./start_energy_services.sh

# 或单独启动
python backend_server_influx.py
python device_sender_oil.py
python device_tension.py
```

### 4. 访问系统
- Web Dashboard: http://localhost:8011
- API文档: http://localhost:8011/api/

## 项目文件结构

```
energy/
├── backend_server_influx.py     # 主后端服务
├── device_sender_oil.py         # 润滑设备模拟器
├── device_tension.py            # 张力设备模拟器
├── dashboard.html               # 前端界面
├── monitor_energy_services.sh   # 服务监控脚本
├── start_energy_services.sh     # 服务启动脚本
├── requirements.txt             # 依赖包列表
├── energy_model/               # 机器学习模型模块
│   ├── influx_connector.py     # InfluxDB连接器
│   ├── optimization.py         # 优化算法
│   ├── lstm_forecasting.py     # LSTM预测模型
│   └── mysql_db.py             # MySQL数据库接口
├── train_learning.py           # 训练学习脚本
├── config.json                 # 配置文件
└── README.md                   # 项目说明
```

## API 接口

### 设备管理
- `GET /api/devices/list` - 获取设备列表
- `POST /api/devices/switch/:device_id` - 控制设备开关
- `GET /api/history` - 获取历史数据

### 数据查询
- `GET /api/data/current` - 获取当前数据
- `GET /api/data/forecast` - 获取预测数据
- `GET /api/settings` - 获取系统设置

## 机器学习模型

### LSTM 预测模型
- 使用历史能耗数据训练
- 预测未来能耗趋势
- 支持多变量时间序列预测

### Q-Learning 优化算法
- 基于强化学习的能耗优化
- 实时调整设备参数以降低能耗
- 平衡生产效率和能耗

## 监控与日志

- 服务日志：`backend.log`, `oil_sender.log`, `tension_sender.log`
- 监控日志：`monitor.log`, `service_monitor.log`
- 实时监控：通过Web界面查看设备状态和能耗数据

## 部署配置

### 环境变量配置 (.env)
```
INFLUX_URL=http://115.120.248.123:8086
INFLUX_TOKEN=your_token_here
INFLUX_ORG=dls
INFLUX_BUCKET=energy_save_data
MYSQL_HOST=localhost
MYSQL_USER=user
MYSQL_PASSWORD=password
```

## 开发与维护

### 服务管理
```bash
# 启动服务
./start_energy_services.sh

# 监控服务
./monitor_energy_services.sh

# 查看日志
tail -f backend.log
```

### 数据库管理
- InfluxDB用于存储时序数据
- MySQL用于存储配置和设置
- 定期备份重要数据

## 注意事项

1. 确保InfluxDB和MySQL服务正常运行
2. 检查网络连接以确保远程数据库访问
3. 定期监控服务日志以发现潜在问题
4. 保持机器学习模型的更新以提高预测准确性

## 贡献

欢迎提交Issue和Pull Request来改进项目。

## 许可证

[请根据实际情况填写许可证信息]
