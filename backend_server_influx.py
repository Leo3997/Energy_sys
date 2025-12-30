import socket
import json
import threading
import pickle
import numpy as np
import time
from flask import Flask, jsonify, send_file, request, Response
from flask_cors import CORS
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# --- 新增 1: 引入 InfluxDB 库 ---
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
# --- 新增 5: 引入 Flask-SocketIO ---
from flask_socketio import SocketIO, emit
import eventlet

# --- 新增 Imports for Realtime Monitoring ---
import sys
import os
from datetime import datetime
# Ensure we can import from local directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from energy_model.influx_connector import InfluxConnector
from energy_model.optimization import EnergyOptimizer
from energy_model.optimization import EnergyOptimizer
from energy_model.lstm_forecasting import LSTMForecaster
from energy_model.optimization import EnergyOptimizer
from energy_model.mysql_db import MySQLDatabase # [NEW] MySQL Support
from energy_model.settings import settings # [NEW] Settings Support
import pandas as pd
import io
import csv

# --- 新增 2: 远程数据库配置 ---
# 请将下面的 Token 替换为你远程数据库 (115.120.248.123) 上的真实 Token
INFLUX_URL = "http://115.120.248.123:8086"
INFLUX_TOKEN = "dev-admin-token-123456"  
INFLUX_ORG = "dls"                         
INFLUX_BUCKET = "energy_save_data"      

# --- Realtime Monitoring Config (from realtime_monitoring.py) ---
MONITOR_URL = "http://1.94.121.255:8086"
MONITOR_TOKEN = "K-xsdqIdqS0CaEl2cj2nHqGmgXv6A6EjQ7TuZhHd6d15Ns9LqNYsVveX9lJzob7LT-Q0pfylKpiXdDbPEy87JQ=="
MONITOR_BUCKET = "energy"
MONITOR_ORG = "fengtian"
# TARGET_DEVICE 已移至 GLOBAL_STATE['current_device']

# --- MySQL Config ---
MYSQL_HOST = "115.120.248.123"
MYSQL_USER = "root"
MYSQL_PASS = "rootpassword"
MYSQL_DB = "energy"
mysql_db = None # Global instance

# 全局客户端变量
influx_client = None
write_api = None

import requests # Ensure requests is imported
QWEN_API_KEY = os.getenv('QWEN_API_KEY', '')



try:
    from predict_baseline import EnergyBaselinePredictor
except ImportError:
    print("⚠️ 警告: 未找到 predict_baseline.py，基线预测功能将不可用")
    EnergyBaselinePredictor = None

# --- 配置 ---
HOST = '0.0.0.0'    # 建议改为 0.0.0.0 以便允许外部访问
PORT = 8012        
HTTP_PORT = 8011    

# ... (Global State, Price, Injection Config 保持不变) ...
GLOBAL_STATE = {
    "devices": {},  
    "current_device": "energy*1*1",  # 当前监控的设备ID，可动态切换
    "energy_stats": {
        "total_savings_kwh": 0.0,
        "total_savings_elec_cost": 0.0,
        "total_savings_oil_liters": 0.0,
        "total_savings_cost": 0.0,
        "current_total_power": 0.0,
        "baseline_total_power": 0.0
    },
    "monitor_context": {},
    "command_queues": {} # { "device_ip": [ {"action": "...", ...} ] }
}
GLOBAL_STATE['logs'] = []

def add_system_log(event_type, message, details=None, device_ip=None, device_type=None):
    """Add a log entry, emit via WebSocket, and save to MySQL."""
    log_entry = {
        "timestamp": datetime.now().strftime('%H:%M:%S'),
        "event_type": event_type,
        "message": message,
        "details": details or {}
    }
    # Keep last 50 logs
    GLOBAL_STATE['logs'].insert(0, log_entry)
    if len(GLOBAL_STATE['logs']) > 50:
        GLOBAL_STATE['logs'].pop()
    
    socketio.emit('system_log_new', log_entry)

    # [NEW] Save to MySQL
    if mysql_db:
        mysql_db.insert_event(
            device_ip or "SYSTEM", 
            device_type or "SERVER", 
            event_type, 
            message, 
            details
        )

# Constants are now managed by settings.py
# ELECTRICITY_PRICE = 0.5
# OIL_PRICE = 20.0
# ...

PRODUCTION_ORDERS = {
    "127.0.0.1": {
        "diameter": 30,
        "needles": 3200,
        "yarn": "Polyester",
        "structure": "Jacquard",
        "rpm": 25
    }
}

# ... (LubricationAI_RL, TensionAI_RL 类保持不变) ...
class LubricationAI_RL:
    def __init__(self):
        self.load_model()
        self.cooldown = 0
        self.inject_count = 0 
        
    def load_model(self):
        self.model_path = "q_brain.pkl"
        self.last_mtime = 0
        try:
            if os.path.exists(self.model_path):
                self.last_mtime = os.path.getmtime(self.model_path)
                with open(self.model_path, "rb") as f:
                    self.q_table = pickle.load(f)
                print("🧠 [LubAI] Model Loaded/Reloaded")
            else:
                self.q_table = None
        except:
             self.q_table = None

    def check_reload(self):
        if os.path.exists(self.model_path):
            mtime = os.path.getmtime(self.model_path)
            if mtime > self.last_mtime:
                print("🔄 [LubAI] Detecting model change, reloading...")
                self.load_model()

    # ... (analyze 方法保持不变) ...
    def analyze(self, data):
        self.check_reload() # [NEW] Check before analyze
        # (为了节省篇幅，这里省略中间代码，请保持原样)
        if self.cooldown > 0:
            self.cooldown -= 1
            return None
        curr = data.get('current_a', 10.0)
        temp = data.get('temperature_c', 40.0)
        if temp > 55.0 or curr > 13.0:
             self.cooldown = 5
             self.inject_count += 1
             return {"action": "INJECT", "msg": "🔥 强制保护"}
        if self.q_table is not None:
            curr_idx = int(min(9, max(0, (curr - 9.0) * 2)))
            temp_idx = int(min(9, max(0, (temp - 25.0) / 5)))
            if np.argmax(self.q_table[curr_idx, temp_idx]) == 1:
                self.cooldown = 5
                self.inject_count += 1
                return {"action": "INJECT", "msg": "🧠 RL决策喷油"}
        return {"action": "MONITOR", "msg": "Running"}

    def force_cooldown(self, steps):
        self.cooldown = max(self.cooldown, steps)

class TensionAI_RL:
    def __init__(self):
        self.load_model()
        self.optimize_count = 0

    def load_model(self):
        self.model_path = "tension_q_brain.pkl"
        self.last_mtime = 0
        try:
            if os.path.exists(self.model_path):
                self.last_mtime = os.path.getmtime(self.model_path)
                with open(self.model_path, "rb") as f:
                    self.q_table = pickle.load(f)
                print("🧠 [TensionAI] Model Loaded/Reloaded")
            else:
                self.q_table = None
        except:
             self.q_table = None

    def check_reload(self):
        if os.path.exists(self.model_path):
            mtime = os.path.getmtime(self.model_path)
            if mtime > self.last_mtime:
                print("🔄 [TensionAI] Detecting model change, reloading...")
                self.load_model()

    # ... (analyze 方法保持不变) ...
    def analyze(self, data):
        self.check_reload()
        # (保持原样)
        tension = data.get('tension', 3.0)
        yarn_pct = data.get('yarn_pct', 100.0)
        yarn_idx = int((yarn_pct / 100.0) * 10)
        yarn_idx = max(0, min(9, yarn_idx))
        tension_idx = int(min(9, max(0, tension - 3.0)))
        if self.q_table is not None:
            if np.argmax(self.q_table[yarn_idx, tension_idx]) == 1:
                self.optimize_count += 1
                return {"action": "OPTIMIZE_TENSION", "msg": "⚡ RL优化张力"}
        return {"action": "MONITOR", "msg": "Optimal"}

# === Flask Server 保持不变 ===
app = Flask(__name__)
# 允许前端访问这些敏感 Header
CORS(app, expose_headers=["Content-Disposition", "Content-Length"])
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

@app.route('/')
def index(): return send_file('dashboard.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """提供静态文件（PNG、CSS等）"""
    if filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico', '.css', '.js')):
        return send_file(filename)
    return "Not Found", 404

@app.route('/api/status')
def get_status(): return jsonify(GLOBAL_STATE)

@app.route('/api/control', methods=['POST'])
def manual_control():
    try:
        data = request.json
        client_ip = data.get('ip')
        action = data.get('action')
        password = data.get('password') # [NEW] Auth Check

        if not client_ip or not action:
            return jsonify({"error": "Missing params"}), 400
        
        # Simple Hardcoded Auth
        if password != "admin123":
             print(f"🔒 [Security] Unauthorized control attempt from {client_ip} for {action}")
             return jsonify({"error": "Unauthorized"}), 401

        # Push to Queue
        device_type = data.get('type')
        queue_key = f"{client_ip}_{device_type}" if device_type else client_ip
        
        if queue_key not in GLOBAL_STATE['command_queues']:
            GLOBAL_STATE['command_queues'][queue_key] = []
        
        cmd = {"action": action, "params": data.get('params', {})}
        GLOBAL_STATE['command_queues'][queue_key].append(cmd)
        
        # Log
        add_system_log("MANUAL_CONTROL", f"User dispatched {action} to {client_ip}")
        
        return jsonify({"status": "queued", "target": client_ip, "action": action})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/devices/list')
def get_device_list():
    """
    获取设备列表：
    1. 尝试从远程 MONITOR 库查询真实设备。
    2. 合并当前内存中已连接的模拟设备 (GLOBAL_STATE)。
    """
    devices = set() # 使用集合去重

    # --- 步骤 A: 查询远程 InfluxDB (MONITOR_URL) ---
    try:
        if MONITOR_TOKEN:
            # 注意：这里我们加上 try-except，防止远程连不上导致整个接口报错，
            # 从而导致连本地设备都显示不出来。
            try:
                client = InfluxDBClient(url=MONITOR_URL, token=MONITOR_TOKEN, org=MONITOR_ORG)
                query_api = client.query_api()
                
                # 查询远程数据库的 gateWayId 标签（实际字段名）
                query = f'import "influxdata/influxdb/schema"\n schema.tagValues(bucket: "{MONITOR_BUCKET}", tag: "gateWayId")'
                
                tables = query_api.query(query)
                for table in tables:
                    for record in table.records:
                        val = record.get_value()
                        if val: devices.add(val)
                client.close()
                print(f"🌍 [Device List] Found {len(devices)} remote devices.")
            except Exception as remote_e:
                print(f"⚠️ [Device List] 远程库查询失败 (非致命): {remote_e}")
    except Exception as e:
        print(f"⚠️ [Device List] 远程连接初始化错误: {e}")

    # --- 步骤 B: 合并本地模拟设备 (关键修复) ---
    # 即使远程查不到，这里也能保证显示你正在运行的 Python 模拟器
    try:
        local_count = 0
        for device_key, device_info in GLOBAL_STATE['devices'].items():
            # device_key 格式通常是 "IP_TYPE" 或直接是 IP
            # 我们优先提取 device_info 里的 'ip'，如果没有则解析 key
            ip = device_info.get('ip')
            if not ip:
                ip = device_key.split('_')[0] # 尝试从 key 提取 IP
            
            if ip:
                devices.add(ip)
                local_count += 1
        print(f"💻 [Device List] Added {local_count} local simulation devices.")
    except Exception as local_e:
        print(f"❌ [Device List] 本地合并错误: {local_e}")

    # --- 步骤 C: 格式化返回 ---
    final_list = list(devices)
    final_list.sort()
    
    # 如果列表为空，返回一个友好的错误提示，而不是空列表，方便前端调试
    if not final_list:
        print("⚠️ [Device List] No devices found in either Remote DB or Local Memory.")
    
    return jsonify(final_list)

@app.route('/api/devices/switch/<path:device_id>', methods=['POST'])
def switch_device(device_id):
    """切换当前监控的设备，并立即刷新数据"""
    GLOBAL_STATE['current_device'] = device_id
    add_system_log("DEVICE_SWITCH", f"已切换监控设备至 {device_id}")
    print(f"🔄 [Device Switch] Now monitoring: {device_id}")
    
    # === 立即查询并推送数据 ===
    try:
        connector = InfluxConnector(MONITOR_URL, MONITOR_TOKEN, MONITOR_ORG, MONITOR_BUCKET)
        df = connector.query_recent_data(minutes=10, device_id=device_id)
        connector.close()
        
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            
            # 提取电压电流功率
            volts = 0
            if all(c in df.columns for c in ['ua', 'ub', 'uc']):
                volts = df[['ua', 'ub', 'uc']].iloc[-1].mean()
            
            amps = 0
            if all(c in df.columns for c in ['ia', 'ib', 'ic']):
                amps = df[['ia', 'ib', 'ic']].iloc[-1].mean()
            
            power_kw = 0
            if 'pt' in df.columns:
                power_kw = float(latest.get('pt', 0)) / 1000.0
            elif 'demand' in df.columns:
                power_kw = float(latest.get('demand', 0)) / 1000.0
            
            pf = float(latest.get('pft', 0))
            if pf > 1.0:
                pf = pf / 1000.0
            
            baseline_kw = power_kw * 1.15 if power_kw > 0.1 else None
            
            payload = {
                "power_kw": round(power_kw, 2),
                "baseline_kw": round(baseline_kw, 2) if baseline_kw else None,
                "voltage": round(volts, 1),
                "current": round(amps, 1),
                "pf": round(pf, 2),
                "idle_hours": 0,
                "forecast_peak_kw": None,
                "alerts": [{"msg": f"✅ 已切换至 {device_id}", "level": "NOTICE", "confidence": "高"}],
                "timestamp": datetime.now().strftime('%H:%M:%S')
            }
            
            socketio.emit('grid_monitor_update', payload)
            print(f"📡 [Immediate Push] Data sent for {device_id}")
            
    except Exception as e:
        print(f"⚠️ [Device Switch] Immediate query failed: {e}")
    
    return jsonify({"status": "ok", "device": device_id})

@app.route('/api/history')
def get_history():
    """获取过去1小时的聚合数据 (Device A + Device B)"""
    if not influx_client:
        return jsonify({"error": "InfluxDB not connected"}), 500

    query_api = influx_client.query_api()
    # 查询 Device A (current) 和 Device B (power)
    # 简单起见，从 "sensor_metrics" bucket 取最近 1h
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r["_measurement"] == "sensor_metrics")
      |> filter(fn: (r) => r["_field"] == "power_kw" or r["_field"] == "current_a")
      |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
      |> yield(name: "mean")
    '''
    try:
        tables = query_api.query(query, org=INFLUX_ORG)
        history_data = []
        for table in tables:
            for record in table.records:
                # 简单聚合：把所有设备的 metric 都丢进去展示趋势
                history_data.append({
                    "time": record.get_time().isoformat(),
                    "value": record.get_value(),
                    "field": record.get_field()
                })
        return jsonify(history_data)
    except Exception as e:
        print(f"Query Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'GET':
        return jsonify(settings.config)
    elif request.method == 'POST':
        data = request.json
        settings.update(data)
        return jsonify({"status": "updated", "config": settings.config})

@app.route('/api/control', methods=['POST'])
def handle_control():
    """
    接收前端手动指令
    Input: { "ip": "127.0.0.1", "action": "INJECT", "params": {} }
    """
    try:
        data = request.json
        target_ip = data.get('ip')
        action = data.get('action')
        params = data.get('params', {})
        
        if not target_ip or not action:
            return jsonify({"error": "Missing 'ip' or 'action'"}), 400
            
        # Initialize queue if not exists
        if target_ip not in GLOBAL_STATE['command_queues']:
            GLOBAL_STATE['command_queues'][target_ip] = []
            
        cmd = {"action": action, **params, "timestamp": time.time()}
        GLOBAL_STATE['command_queues'][target_ip].append(cmd)
        
        print(f"🎮 [Manual Control] Queued for {target_ip}: {action}")
        add_system_log("人工指令", f"已下发指令 {action} 到设备 {target_ip}", details=cmd)
        
        return jsonify({"status": "queued", "queue_length": len(GLOBAL_STATE['command_queues'][target_ip])})
        
    except Exception as e:
        print(f"Control Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/export/events')
def export_events():
    if not mysql_db:
        return jsonify({"error": "Database not connected"}), 500
    
    events = mysql_db.fetch_events(limit=5000)
    if not events:
        return "No events found", 404
    
    import traceback
    try:
        # Convert to Excel
        print("📊 [Export] Fetching events...")
        df = pd.DataFrame(events)
        print(f"📊 [Export] DataFrame created: {len(df)} rows")
        
        # Reorder/Rename columns if needed
        if not df.empty:
            # Ensure correct column order/names
            cols = ['id', 'event_time', 'device_ip', 'device_type', 'action_type', 'message', 'details_json']
            # Filter only existing columns
            cols = [c for c in cols if c in df.columns]
            df = df[cols]
            
            # Ensure datetime is timezone-naive to avoid Excel errors
            if 'event_time' in df.columns:
                df['event_time'] = df['event_time'].astype(str)

        output = io.BytesIO()
        print("📊 [Export] Writing to CSV...")
        # export to csv with utf-8-sig (BOM) for Excel compatibility
        df.to_csv(output, index=False, encoding='utf-8-sig')
        
        output.seek(0)
        print("✅ [Export] Done.")
        
       # 1. 获取文件精确大小 (Bytes)
        file_size = output.getbuffer().nbytes

        # 2. 生成响应对象，但不直接 return
        response = send_file(
            output,
            as_attachment=True,
            download_name='events_report.csv',
            mimetype='text/csv'
        )

        # 3. 显式添加 Content-Length 头
        # 这也是下载工具判断进度的关键
        response.headers["Content-Length"] = file_size
        
        # 4. 显式添加 Content-Disposition (双重保险)
        # 防止 Flask 版本兼容问题导致 download_name 失效
        response.headers["Content-Disposition"] = "attachment; filename=events_report.csv"

        # 5. 添加 CORS 暴露头 (防止前端 JS 拿不到文件名)
        response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"

        return response
    except Exception as e:
        print(f"❌ Export Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def start_http_server():
    print(f"🌍 [Web API] 启动 (SocketIO port {HTTP_PORT})")
    socketio.run(app, host='0.0.0.0', port=HTTP_PORT, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)

# --- 新增 3: 初始化远程数据库连接与 Bucket ---
def init_influxdb():
    global influx_client, write_api
    print(f"☁️ 正在连接远程数据库: {INFLUX_URL} ...")
    
    try:
        influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        
        # 1. 检查并创建 Bucket
        buckets_api = influx_client.buckets_api()
        existing_bucket = buckets_api.find_bucket_by_name(INFLUX_BUCKET)
        
        if existing_bucket:
            print(f"✅ 远程 Bucket '{INFLUX_BUCKET}' 已存在。")
        else:
            print(f"📦 远程 Bucket '{INFLUX_BUCKET}' 不存在，正在创建...")
            buckets_api.create_bucket(bucket_name=INFLUX_BUCKET, org=INFLUX_ORG)
            print(f"✅ Bucket '{INFLUX_BUCKET}' 创建成功！")

        # 2. 初始化写入 API (使用异步批量写入，防止阻塞 socket 线程)
        write_api = influx_client.write_api(write_options=WriteOptions(batch_size=1, flush_interval=1000))
        print("🚀 InfluxDB 写入通道已就绪")
        
    except Exception as e:
        print(f"❌ 远程数据库连接失败: {e}")
        print("   -> 请检查 IP 是否通畅，端口 8086 是否开放，Token 是否正确。")
        influx_client = None
        write_api = None

# Retry Helper
last_influx_retry = 0
def get_influx_writer():
    global write_api, last_influx_retry
    if write_api: 
        return write_api
    
    # Check cooldown (e.g., 30s)
    if time.time() - last_influx_retry < 30:
        return None
        
    last_influx_retry = time.time()
    print("🔄 [System] 尝试重连 InfluxDB...")
    init_influxdb()
    return write_api

# === Realtime Monitoring Loop ===
def run_monitoring_loop():
    print(f"🔍 [Monitoring] Connecting to Monitor DB at {MONITOR_URL}...")
    connector = InfluxConnector(MONITOR_URL, MONITOR_TOKEN, MONITOR_ORG, MONITOR_BUCKET)
    
    print("🧠 [Monitoring] Loading Forecasting Model (LSTM)...")
    try:
        forecaster = LSTMForecaster()
    except Exception as e:
        print(f"⚠️ [Monitoring] Model load failed: {e}")
        forecaster = None

    # --- Initialize Baseline Predictor ---
    baseline_predictor = None
    if EnergyBaselinePredictor:
        try:
            baseline_predictor = EnergyBaselinePredictor()
            print("🧠 [Monitoring] Baseline Predictor Loaded")
        except Exception as e:
            print(f"⚠️ [Monitoring] Baseline Predictor init failed: {e}")

    print("✅ [Monitoring] Loop Started (60s interval)")
    
    while True:
        try:
            # 1. Fetch Data
            # Fetch last 24 hours (1440 min) to ensure accurate daily idle stats
            current_device = GLOBAL_STATE.get('current_device', 'energy*1*1')
            df = connector.query_recent_data(minutes=1440, device_id=current_device)
            
            if df is not None and not df.empty:
                # 2. Prepare Data
                df_kw = df.copy()
                if 'pt' in df_kw.columns:
                    df_kw['pt'] = df_kw['pt'] / 1000.0
                if 'demand' in df_kw.columns:
                    df_kw['demand'] = df_kw['demand'] / 1000.0

                # 3. Analyze
                optimizer = EnergyOptimizer(df_kw)
                idle_stats = optimizer.detect_idle_state(duration_minutes=15, resample_interval_minutes=1) 
                balance_stats = optimizer.analyze_phase_balance()
                pf_stats = optimizer.analyze_power_factor()
                
                # 4. Extract Metrics
                current_power_kw = 0
                if 'pt' in df_kw.columns: current_power_kw = df_kw['pt'].iloc[-1]
                elif 'demand' in df_kw.columns: current_power_kw = df_kw['demand'].iloc[-1]

                volts = 0
                if all(c in df.columns for c in ['ua', 'ub', 'uc']):
                    volts = df[['ua', 'ub', 'uc']].iloc[-1].mean()
                
                amps = 0
                if all(c in df.columns for c in ['ia', 'ib', 'ic']):
                    amps = df[['ia', 'ib', 'ic']].iloc[-1].mean()
                
                pf = 0
                if 'pft' in df.columns:
                    pf = df['pft'].iloc[-1]
                    if pf > 1.0: pf = pf / 1000.0

                # 5. Forecast
                pred_peak_kw = None
                if forecaster:
                    try:
                        pred_peak_watts = forecaster.predict_next_peak(df)
                        if pred_peak_watts is not None:
                            pred_peak_kw = pred_peak_watts / 1000.0
                    except Exception as e:
                        print(f"Forecast error: {e}")
                
                # 5.1 Calculate Dynamic Baseline
                baseline_kw = None
                
                # [MODIFIED] Strategy Change: User requested Baseline = 115% of Current Power
                # Previous ML-based approach:
                # if baseline_predictor:
                #     order = PRODUCTION_ORDERS.get("127.0.0.1", {})
                #     if order:
                #         try:
                #             baseline_kw = baseline_predictor.predict_baseline(...)
                #         except Exception as e: ...
                
                if current_power_kw > 0.1: # Only calculate if there is power
                     baseline_kw = current_power_kw * 1.15

                # 6. Build Alerts & Tips (Structured)
                alerts = []
                
                # A. Power Anomaly
                # DingTalk Config
                DINGTALK_WEBHOOK = os.getenv('DINGTALK_WEBHOOK', '') # User to provide in .env

                def send_dingtalk_alert(msg):
                    if not DINGTALK_WEBHOOK: return
                    try:
                        requests.post(DINGTALK_WEBHOOK, json={
                            "msgtype": "text",
                            "text": {"content": f"🚨 [得鹿山能源警报] {msg}"}
                        }, timeout=2)
                    except: pass

                if baseline_kw and current_power_kw > baseline_kw:
                    ratio = current_power_kw / baseline_kw
                    if ratio > 1.2:
                        msg = f"🔥 能耗严重超标: {current_power_kw:.1f}kW (>120%)"
                        alerts.append({"msg": msg, "level": "CRITICAL", "confidence": "高"})
                        send_dingtalk_alert(msg) # [NEW] Webhook
                    elif ratio > 1.1:
                        alerts.append({"msg": f"⚠️ 能耗偏高: {current_power_kw:.1f}kW (>110%)", "level": "WARNING", "confidence": "中"})
                
                # B. Voltage Balance
                unbal = balance_stats.get('max_unbalance_percent', 0)
                if unbal > 25:
                     alerts.append({"msg": f"⚡ 三相严重不平: {unbal:.1f}%", "level": "CRITICAL", "confidence": "高"})
                elif unbal > 15:
                     alerts.append({"msg": f"⚠️ 三相不平衡: {unbal:.1f}%", "level": "WARNING", "confidence": "中"})

                # C. Power Factor
                avg_pf = pf_stats.get('avg_pf', 1.0)
                if avg_pf < 0.85:
                    alerts.append({"msg": f"📉 功率因数过低: {avg_pf:.2f}", "level": "WARNING", "confidence": "高"})
                elif avg_pf < 0.90:
                    alerts.append({"msg": f"ℹ️ 功率因数需优化: {avg_pf:.2f}", "level": "NOTICE", "confidence": "低"})

                # D. Idle Detection
                idle_hrs = idle_stats.get('total_idle_hours', 0)
                if idle_hrs > 1.0:
                    alerts.append({"msg": f"💤 长时间空转: {idle_hrs:.1f}h", "level": "WARNING", "confidence": "高"})
                elif idle_hrs > 0.2:
                    alerts.append({"msg": f"ℹ️ 识别到间歇空转: {idle_hrs*60:.0f}min", "level": "NOTICE", "confidence": "中"})

                # E. Optimization Tips (If no critical alerts)
                if not any(a['level'] == 'CRITICAL' for a in alerts):
                     if baseline_kw and current_power_kw <= baseline_kw * 1.05:
                         alerts.insert(0, {"msg": "✅ 机器能耗未超越基线模型，能耗正常", "level": "NOTICE", "confidence": "高"})
                     if avg_pf > 0.95:
                         alerts.append({"msg": "✅ 功率因数优异，无需补偿", "level": "NOTICE", "confidence": "高"})
                     if unbal < 5:
                         alerts.append({"msg": "✅ 三相平衡良好", "level": "NOTICE", "confidence": "高"})

                # 7. Broadcast
                payload = {
                    "power_kw": round(current_power_kw, 2),
                    "baseline_kw": baseline_kw,
                    "voltage": round(volts, 1),
                    "current": round(amps, 1),
                    "pf": round(pf, 2),
                    "idle_hours": round(idle_stats.get('total_idle_hours', 0), 2),
                    "forecast_peak_kw": round(pred_peak_kw, 2) if pred_peak_kw else None,
                    "alerts": alerts,
                    "timestamp": datetime.now().strftime('%H:%M:%S')
                }
                
                # Cache for AI
                GLOBAL_STATE['monitor_context'] = payload

                # print(f"📡 [Monitor] Emitting update: {payload}")
                socketio.emit('grid_monitor_update', payload)

        except Exception as e:
            print(f"❌ [Monitor] Error: {e}")

        time.sleep(60)


# === 服务器主逻辑 ===
def handle_client(conn, addr):
    client_ip = addr[0]
    print(f"🔗 新设备: {client_ip}")

    lub_ai = LubricationAI_RL()
    ten_ai = TensionAI_RL()
    
    # ... (基线初始化保持不变) ...
    baseline_power = 3.5 

    try:
        with conn:
            last_calc_time = time.time()
            while True:
                data = conn.recv(1024)
                if not data: break
                try:
                    sensor_data = json.loads(data.decode('utf-8'))
                except: continue

                d_type = sensor_data.get("device_type", "UNKNOWN")
                

                # --- 新增 4: 将数据写入远程 InfluxDB (Safe & Lazy) ---
                writer = get_influx_writer()
                if writer:
                    try:
                        # 创建数据点
                        p = Point("sensor_metrics") \
                            .tag("device_ip", client_ip) \
                            .tag("device_type", d_type)
                        
                        # 根据设备类型添加 Field
                        if d_type == "LUBRICATION_BOT":
                            p.field("current_a", float(sensor_data.get('current_a', 0)))
                            p.field("temperature_c", float(sensor_data.get('temperature_c', 0)))
                        elif d_type == "TENSION_BOT":
                            p.field("tension_g", float(sensor_data.get('tension', 0)))
                            p.field("yarn_pct", float(sensor_data.get('yarn_pct', 0)))
                            p.field("power_kw", float(sensor_data.get('power', 0)))
                        
                        # 写入
                        writer.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
                    except Exception as ie:
                        print(f"⚠️ 写入失败: {ie}")
                        # If write fails, reset writer to force reconnect next time?
                        # write_api = None # Maybe too aggressive
                        pass

                # ... (原有的 GLOBAL_STATE 更新逻辑 保持不变) ...
                device_key = f"{client_ip}_{d_type}"
                GLOBAL_STATE['devices'][device_key] = {
                    "ip": client_ip, # [FIX] Add IP for frontend
                    "type": d_type,
                    "data": sensor_data,
                    "last_seen": time.time(),
                    "stats": {"inject_count": lub_ai.inject_count, "optimize_count": ten_ai.optimize_count}
                }
                # ... (原有的 U6da6滑/张力 业务逻辑 保持不变) ...

                # ... (原有的 润滑/张力 业务逻辑 保持不变) ...
                
                # === 分支 1: 润滑机器人 ===
                if d_type == "LUBRICATION_BOT":
                    # --- 1. 获取机器运行状态 ---
                    curr_amp = sensor_data.get('current_a', 0.0)
                    # 设定一个阈值，比如 1.0A，低于此值认为机器待机/停车
                    is_running = curr_amp > 1.0 

                    # --- 2. 计算时间差 ---
                    now = time.time()
                    dt_seconds = (now - last_calc_time)
                    last_calc_time = now 
                    
                    # --- 3. 修正后的基线消耗计算 ---
                    # 【修改点】：只有当机器在运转时，才计算基线的理论消耗
                    # 如果机器停了，老机器也不喷油，所以没有产生“节油”
                    if is_running:
                        baseline_rate = settings.get('INJECT_VOLUME_LTERS') / settings.get('BASELINE_INJECT_INTERVAL')
                        period_baseline_usage = baseline_rate * dt_seconds
                    else:
                        period_baseline_usage = 0.0

                    saved_oil = period_baseline_usage

                    # --- 4. 执行决策 (人工优先) ---
                    # Check for manual command
                    manual_cmd = None
                    # Use device_key (ip_type) which solves collision
                    if device_key in GLOBAL_STATE['command_queues'] and GLOBAL_STATE['command_queues'][device_key]:
                         manual_cmd = GLOBAL_STATE['command_queues'][device_key].pop(0)
                         print(f"🎮 [Override] 润滑机 {device_key} 执行人工指令: {manual_cmd['action']}")
                    
                    # FALLBACK: Try IP only (legacy or generic broadcast)
                    elif client_ip in GLOBAL_STATE['command_queues'] and GLOBAL_STATE['command_queues'][client_ip]:
                         manual_cmd = GLOBAL_STATE['command_queues'][client_ip].pop(0)
                         print(f"🎮 [Override] 润滑机 {client_ip} 执行广播指令: {manual_cmd['action']}")

                    if manual_cmd:
                        result = manual_cmd
                        # Ensure msg exists
                        if 'msg' not in result: result['msg'] = f"Manual Control: {manual_cmd['action']}"
                    else:
                        # 即使停车也可以让AI分析（为了监控温度），但通常AI也会返回MONITOR
                        result = lub_ai.analyze(sensor_data)
                    
                    if result:
                        response = result
                        if result["action"] == "INJECT":
                            # 如果 RL 决定喷油，则扣除节省量 (即实际消耗了)
                            saved_oil -= settings.get('AI_INJECT_VOLUME')
                            # 【可选】可以在这里强制增加一个物理冷却，防止AI连续误判
                            lub_ai.force_cooldown(5) # 例如强制冷却10分钟
                            print(f"[润滑 {addr}] {result['msg']}")
                            
                            # Log Event
                            is_manual = (manual_cmd is not None)
                            add_system_log(
                                "人工喷油" if is_manual else "自动喷油", 
                                "收到人工强制注油指令" if is_manual else "检测到温度和电流升高，超过强化学习最优基线，自动执行喷油操作",
                                {"current": f"{curr_amp:.2f}A", "temp": f"{sensor_data.get('temperature_c',0):.1f}°C"},
                                device_ip=client_ip,
                                device_type=d_type
                            )
                    
                    # --- 5. 更新全局统计 ---
                    GLOBAL_STATE['energy_stats']['total_savings_oil_liters'] += saved_oil
                    GLOBAL_STATE['energy_stats']['total_savings_cost'] += (saved_oil * settings.get('OIL_PRICE'))


                # === 分支 2: 张力机器人 (集成基线 + RL) ===
                elif d_type == "TENSION_BOT":
                    current_power = sensor_data.get('power', 0)
                    
                    # [MODIFIED] Dynamic Baseline for Savings Calculation
                    # Ensure baseline is always relavtive to current usage for demo purposes
                    if current_power > 0.1:
                        baseline_power = current_power * 1.15
                    else:
                        baseline_power = 0.0

                    # --- 成本计算逻辑 (累计节能) ---
                    if baseline_power:
                        now = time.time()
                        dt_hours = (now - last_calc_time) / 3600.0
                        last_calc_time = now
                        
                        # 只有当实际功耗小于基线时，才算作"节能"
                        # 如果实际功耗大于基线，说明可能存在浪费或故障，这里暂不扣减收益，只累计正向收益
                        saved_power = max(0, baseline_power - current_power)
                        saved_kwh = saved_power * dt_hours
                        saved_cost = saved_kwh * settings.get('ELECTRICITY_PRICE')
                        
                        GLOBAL_STATE['energy_stats']['total_savings_kwh'] += saved_kwh
                        GLOBAL_STATE['energy_stats']['total_savings_elec_cost'] += saved_cost
                        GLOBAL_STATE['energy_stats']['total_savings_cost'] += saved_cost
                        GLOBAL_STATE['energy_stats']['current_total_power'] = current_power # 简化：只显示当前的
                        GLOBAL_STATE['energy_stats']['baseline_total_power'] = baseline_power

                    # --- 步骤 A: 基线异常检测 (Rule-based Safety) ---
                    # 如果计算出了基线，先检查是否严重超标
                    is_serious_fault = False
                    if baseline_power:
                        diff_pct = (
                            (current_power - baseline_power) / baseline_power) * 100
                        # 阈值：如果超标 20%，这肯定不是张力问题，而是机器卡死或坏了
                        if diff_pct > 20:
                            is_serious_fault = True
                            response = {
                                "action": "ALARM_STOP",
                                "msg": f"🚨 [严重异常] 实测{current_power}kW 远超基线{baseline_power}kW (+{diff_pct:.1f}%)"
                            }
                            print(
                                f"\033[91m[张力 {addr}] {response['msg']}\033[0m")

                    # --- 步骤 B: RL 节能优化 ---
                    # 只有在没有严重故障时，才让 RL 介入微调
                    if not is_serious_fault:
                        # Check for manual command
                        manual_cmd = None
                        # Use device_key (ip_type) which solves collision
                        if device_key in GLOBAL_STATE['command_queues'] and GLOBAL_STATE['command_queues'][device_key]:
                             manual_cmd = GLOBAL_STATE['command_queues'][device_key].pop(0)
                        elif client_ip in GLOBAL_STATE['command_queues'] and GLOBAL_STATE['command_queues'][client_ip]:
                             manual_cmd = GLOBAL_STATE['command_queues'][client_ip].pop(0)
                        
                        if manual_cmd:
                            result = manual_cmd
                            if 'msg' not in result: result['msg'] = f"Manual: {manual_cmd['action']}"
                        else:
                            result = ten_ai.analyze(sensor_data)
                            
                        response = result

                        # 为了演示，我们将基线信息附加到 Monitor 消息里
                        if response["action"] == "MONITOR" and baseline_power:
                            diff_pct = (
                                (current_power - baseline_power) / baseline_power) * 100
                            response["msg"] += f" (偏差 {diff_pct:.1f}%)"

                        if result["action"] == "OPTIMIZE_TENSION":
                            print(f"[张力 {addr}] {result['msg']}")
                            # Log Event for specific tension conditions (simulation)
                            if sensor_data.get('tension', 0) > 10: # Example threshold
                                 add_system_log(
                                    "更换线盘",
                                    "检测到电流线盘张力升高，已通知维护人员及时更换线盘",
                                    {"tension": f"{sensor_data.get('tension',0):.1f}g", "current": f"{current_power:.2f}kW"},
                                    device_ip=client_ip,
                                    device_type=d_type
                                )
                    # 如果有严重故障，response已经设置为ALARM_STOP，无需额外操作
                    # 如果有严重故障，response已经设置为ALARM_STOP，无需额外操作

                else:
                    response = {"action": "ERROR", "msg": "Unknown Device"}

                # --- [FIX] 在AI决策后更新设备状态并推送，确保 action 字段正确 ---
                # 将 action 合并到 sensor_data 中
                sensor_data['action'] = response.get('action', 'MONITOR')
                
                # 更新全局状态
                GLOBAL_STATE['devices'][device_key] = {
                    "ip": client_ip,
                    "type": d_type,
                    "data": sensor_data,
                    "last_seen": time.time(),
                    "stats": {"inject_count": lub_ai.inject_count, "optimize_count": ten_ai.optimize_count}
                }
                
                # WebSocket 推送
                socketio.emit('device_update', GLOBAL_STATE['devices'][device_key])
                socketio.emit('stats_update', GLOBAL_STATE['energy_stats'])

                conn.sendall(json.dumps(response).encode('utf-8'))

    except Exception as e:
        print(f"❌ 连接断开 {addr}: {e}")
    finally:
        device_key = f"{client_ip}_{d_type}" if 'd_type' in locals() else client_ip
        if device_key in GLOBAL_STATE['devices']:
            del GLOBAL_STATE['devices'][device_key]

@app.route('/api/ask_ai', methods=['POST'])
def ask_ai():
    try:
        data = request.json
        user_question = data.get('question', '')
        
        # 1. Gather Context
        stats = GLOBAL_STATE.get('energy_stats', {})
        total_kwh = stats.get('total_savings_kwh', 0)
        total_money = stats.get('total_savings_cost', 0)
        
        # Get Monitor Data
        mon_ctx = GLOBAL_STATE.get('monitor_context', {})
        alerts = mon_ctx.get('alerts', [])
        idle_hours = mon_ctx.get('idle_hours', 0)
        curr_pwr = mon_ctx.get('power_kw', stats.get('current_total_power', 0))
        perf = mon_ctx.get('pf', 0)
        
        alerts_str = ", ".join(alerts) if alerts else "None"

        context_str = f"""
        System Status:
        - Total Energy Saved: {total_kwh:.2f} kWh
        - Total Money Saved: {total_money:.2f} CNY
        - Current Actual Power: {curr_pwr:.2f} kW
        - Power Factor: {perf}
        - Idle Hours (24h): {idle_hours} h
        - Active Alerts: {alerts_str}
        """
        
        # 2. Call Qwen API
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {QWEN_API_KEY}"
        }
        body = {
            "model": "qwen-turbo",
            "input": {
                "messages": [
                    {"role": "system", "content": "You are an intelligent energy optimization assistant for a textile factory. Answer concisely based on the system status provided."},
                    {"role": "user", "content": f"Context: {context_str}\n\nQuestion: {user_question}"}
                ]
            }
        }
        
        response = requests.post(url, headers=headers, json=body)
        res_json = response.json()
        
        if response.status_code == 200 and 'output' in res_json:
            ai_text = res_json['output']['text']
            return jsonify({"answer": ai_text})
        else:
            print(f"Qwen Error: {res_json}")
            return jsonify({"answer": "Sorry, I could not connect to the AI service right now."}), 500
            
    except Exception as e:
        print(f"AI Error: {e}")
        return jsonify({"answer": f"Error: {str(e)}"}), 500

@socketio.on('connect')
def handle_connect():
    # Emit history logs
    # Send logs in reverse order (oldest first) so frontend can just append? 
    # Or send list and let frontend handle it. Sending list is standard.
    socketio.emit('system_log_history', GLOBAL_STATE['logs'])

def start_server():
    # 启动前初始化数据库
    init_influxdb() 
    
    print(f"✅ 服务启动 (RL + Remote DB)")
    
    # 启动 Monitor 线程
    monitor_thread = threading.Thread(target=run_monitoring_loop)
    monitor_thread.daemon = True
    monitor_thread.start()

    http_thread = threading.Thread(target=start_http_server)
    http_thread.daemon = True
    http_thread.start()
    
    # [NEW] Init MySQL
    global mysql_db
    mysql_db = MySQLDatabase(MYSQL_HOST, MYSQL_USER, MYSQL_PASS, MYSQL_DB)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    server.settimeout(1.0)
    
    print(f"📡 TCP 监听: {HOST}:{PORT}")
    try:
        while True:
            try:
                conn, addr = server.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr))
                thread.daemon = True
                thread.start()
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        print("停止服务...")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()