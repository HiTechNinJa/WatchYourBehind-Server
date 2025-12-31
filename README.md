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

### 0. 设备列表查询 (GET /api/v1/devices)

**目的**: 获取所有已注册设备的MAC地址和基本状态

**响应**:
```json
{
  "code": 200,
  "data": [
    {
      "device_mac": "AA:BB:CC:DD:EE:FF",
      "online_status": true,
      "firmware_ver": "V2.04.23101915",
      "last_heartbeat": "2025-12-31T12:00:00Z",
      "active_viewers": 2
    }
  ]
}
```

**功能**: 前端可调用此API获取可用设备MAC，然后用于其他查询

### 前端设备发现流程

为简化用户操作，前端应实现自动设备发现：

1. **页面初始化**: 自动调用 `GET /api/v1/devices` 获取设备列表
2. **设备选择**: 自动选择第一个在线设备，或显示选择器
3. **后续调用**: 使用选中的MAC调用其他API

**前端示例代码**:
```javascript
// 自动获取设备MAC
fetch('/api/v1/devices')
  .then(res => res.json())
  .then(result => {
    if (result.code === 200 && result.data.length > 0) {
      const onlineDevices = result.data.filter(d => d.online_status);
      if (onlineDevices.length > 0) {
        const mac = onlineDevices[0].device_mac;
        // 使用MAC调用其他API
        loadDeviceData(mac);
      }
    }
  });
```

这样用户无需手动输入MAC，前端自动处理。

### 1. 数据上报接口 (POST /api/v1/device/sync)

**目的**: ESP32设备上报雷达检测到的目标数据

**请求体**:
```json
{
  "device_mac": "AA:BB:CC:DD:EE:FF",
  "targets": [
    {"x":100,"y":200,"speed":10,"resolution":360},
    {"x":300,"y":400,"speed":20,"resolution":360}
  ],
  "batch_id": "batch_20231231120000"
}
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "next_interval": 1000,
    "server_time": 1715000000,
    "pending_cmd": {
      "command_id": 1,
      "command_type": "SET_MODE",
      "payload": {"mode": "single"}
    }
  }
}
```

**功能**:
- 自动过滤无效目标（x/y/speed/resolution全为0）
- 实时推送数据到WebSocket客户端
- 检查并返回待执行指令

### 2. 设备状态接口 (GET /api/v1/device/status)

**目的**: 获取设备在线状态、固件版本等信息

**参数**:
- `device_mac` (必需): 设备MAC地址

**响应**:
```json
{
  "code": 200,
  "data": {
    "device_mac": "AA:BB:CC:DD:EE:FF",
    "online_status": true,
    "firmware_ver": "V2.04.23101915",
    "track_mode": "multi",
    "bluetooth_state": false,
    "zone_config": [{"x1":0,"y1":0,"x2":1000,"y2":1000}],
    "active_viewers": 2,
    "last_heartbeat": "2025-12-31T12:00:00Z"
  }
}
```

**错误响应**:
```json
{"code": 404, "message": "Device not found"}
```

### 3. 历史轨迹接口 (GET /api/v1/radar/history)

**目的**: 获取历史雷达数据，用于轨迹重放和热力图

**参数**:
- `device_mac` (必需): 设备MAC地址
- `start_time` (必需): 开始时间 (ISO格式，如 2024-01-01T00:00:00)
- `end_time` (必需): 结束时间 (ISO格式)

**响应**:
```json
{
  "code": 200,
  "data": [
    {
      "target_id": 1,
      "pos_x": 100,
      "pos_y": 200,
      "speed": 10,
      "resolution": 360,
      "created_at": "2025-12-31T12:00:00.000Z"
    }
  ]
}
```

### 4. 守卫事件接口 (GET /api/v1/guard/events)

**目的**: 获取入侵报警的历史记录

**参数**:
- `device_mac` (必需): 设备MAC地址
- `start_time` (可选): 开始时间
- `end_time` (可选): 结束时间

**响应**:
```json
{
  "code": 200,
  "data": [
    {
      "event_id": 1,
      "device_mac": "AA:BB:CC:DD:EE:FF",
      "zone_id": 1,
      "start_time": "2025-12-31T12:00:00Z",
      "end_time": "2025-12-31T12:05:00Z",
      "duration": 300,
      "max_speed": 50,
      "snapshot_points": [{"x":100,"y":200}]
    }
  ]
}
```

### 5. 指令下发接口 (POST /api/v1/device/command)

**目的**: 向设备下发控制指令

**请求体**:
```json
{
  "device_mac": "AA:BB:CC:DD:EE:FF",
  "command_type": "SET_MODE",
  "payload": {"mode": "single"}
}
```

**支持的指令类型**:
- `REBOOT`: 重启设备
- `SET_MODE`: 设置跟踪模式 (single/multi)
- `SET_ZONE`: 设置预警区域

**响应**:
```json
{
  "code": 200,
  "message": "Command queued successfully",
  "command_id": 123
}
```

### 6. 实时数据流 (WebSocket /ws/radar/live)

**目的**: 获取10Hz实时雷达数据推送

**连接URL**: `ws://your-server:5000/ws/radar/live?mac=AA:BB:CC:DD:EE:FF`

**服务器推送消息**:
```json
{
  "type": "radar_data",
  "device_mac": "AA:BB:CC:DD:EE:FF",
  "targets": [
    {"x":100,"y":200,"speed":10,"resolution":360}
  ],
  "timestamp": 1640995200.000
}
```

**功能**:
- 连接时自动增加设备活跃观看者计数
- 断开时减少计数
- 支持多客户端同时观看

## 开发日志
- 2025-12-31：优化数据入库逻辑，后端自动过滤x/y全为0的无效目标，不再写入数据库，并在日志中记录过滤情况，防止冗余数据
- 2025-12-31：根据前端设计文档更新API规划，添加设备状态、历史回溯、守卫事件、指令下发和WebSocket实时流接口