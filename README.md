# WatchYourBehind-Server

后端基于 Flask，支持设备数据上报、自动建表、MySQL远程连接。

## 项目结构
```
。
WatchYourBehind-Server/
├── app.py
├── models.py
├── config.py
├── requirements.txt
└── README.md
```

## 快速启动
1. 安装依赖
   ```
   pip install -r requirements.txt
   ```
2. 进入目录激活虚拟环境
    ```
   cd WatchYourBehind-Server && source venv/bin/activate  # Linux/Mac
   ```   
2. 配置数据库连接（编辑 config.py）
3. 启动服务
   ```
   python app.py
   ```
4. 一键启动
    ```
    cd WatchYourBehind-Server && source venv/bin/activate && python app.py
    ```
## 主要文件说明
- app.py：主入口，API路由
- models.py：数据库模型
- config.py：数据库连接配置
- requirements.txt：依赖列表

## API 示例
- POST /api/v1/device/sync
  - 设备数据上报接口
  - 请求体示例：
    ```json
    {
      "device_mac": "AA:BB:CC:DD:EE:FF",
      "targets": [
        {"x":100,"y":200,"speed":10,"resolution":360},
        {"x":300,"y":400,"speed":20,"resolution":360}
      ]
    }
    ```
  - 响应示例：
    ```json
    {
      "code": 200,
      "data": {
        "next_interval": 1000,
        "server_time": 1715000000,
        "pending_cmd": null
      }
    }
    ```

- GET /api/v1/device/status
  - 获取设备状态信息
  - 参数：device_mac (查询字符串)
  - 响应示例：
    ```json
    {
      "code": 200,
      "data": {
        "device_mac": "AA:BB:CC:DD:EE:FF",
        "online_status": true,
        "firmware_ver": "1.0.0",
        "track_mode": "multi",
        "bluetooth_state": false,
        "last_heartbeat": "2025-12-31T12:00:00Z"
      }
    }
    ```

- GET /api/v1/radar/history
  - 获取历史轨迹数据
  - 参数：device_mac, start_time, end_time (查询字符串)
  - 响应示例：
    ```json
    {
      "code": 200,
      "data": [
        {
          "target_id": 1,
          "pos_x": 100,
          "pos_y": 200,
          "speed": 10,
          "created_at": "2025-12-31T12:00:00Z"
        }
      ]
    }
    ```

- GET /api/v1/guard/events
  - 获取守卫事件日志
  - 参数：device_mac, start_time, end_time (查询字符串)
  - 响应示例：
    ```json
    {
      "code": 200,
      "data": [
        {
          "event_id": 1,
          "zone_id": 1,
          "start_time": "2025-12-31T12:00:00Z",
          "end_time": "2025-12-31T12:05:00Z",
          "duration": 300,
          "max_speed": 50
        }
      ]
    }
    ```

- POST /api/v1/device/command
  - 下发设备指令
  - 请求体示例：
    ```json
    {
      "device_mac": "AA:BB:CC:DD:EE:FF",
      "command_type": "SET_MODE",
      "payload": {"mode": "single"}
    }
    ```
  - 响应示例：
    ```json
    {
      "code": 200,
      "message": "Command queued successfully"
    }
    ```

- WS /ws/radar/live?mac={id}
  - WebSocket实时数据流
  - 消息格式：同 /api/v1/device/sync 的 targets 数组

## 开发日志
- 2025-12-31：优化数据入库逻辑，后端自动过滤x/y全为0的无效目标，不再写入数据库，并在日志中记录过滤情况，防止冗余数据
- 2025-12-31：根据前端设计文档更新API规划，添加设备状态、历史回溯、守卫事件、指令下发和WebSocket实时流接口