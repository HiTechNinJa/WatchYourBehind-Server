# WatchYourBehind-Server API 实现规划 (server-TODO.md)

## 概述

当前后端仅实现了 `/api/v1/device/sync` (POST) 接口。根据前端设计文档和数据库设计，需要实现以下5个API以支持完整可视化功能：

1. **实时流**: `/ws/radar/live?mac={id}` (WebSocket)
2. **历史回溯**: `/api/v1/radar/history` (GET)
3. **守卫日志**: `/api/v1/guard/events` (GET)
4. **设备状态**: `/api/v1/device/status` (GET)
5. **下发指令**: `/api/v1/device/command` (POST)

## 技术栈更新

### 新增依赖 (requirements.txt)
```
flask-socketio==5.3.6
eventlet==0.33.3  # 或 gevent==23.9.1
```

### Flask应用修改
```python
from flask_socketio import SocketIO, emit
import eventlet

# 修改app.py启动方式
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
```

## API详细设计

### 1. 设备状态API (/api/v1/device/status)

**目的**: 获取ESP32固件版本、MAC、最后心跳时间及在线状态

**方法**: GET

**参数**:
- `device_mac` (query string): 设备MAC地址

**数据库查询**:
```sql
SELECT * FROM device_shadow WHERE device_mac = ?
```

**响应格式**:
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
    "active_viewers": 0,
    "last_heartbeat": "2025-12-31T12:00:00Z"
  }
}
```

**实现逻辑**:
- 查询DeviceShadow表
- 如果无记录，返回默认值或404
- 在线状态基于last_heartbeat判断（例如5分钟内）

### 2. 历史回溯API (/api/v1/radar/history)

**目的**: 获取历史轨迹点，用于轨迹重放和热力图

**方法**: GET

**参数**:
- `device_mac` (query string): 设备MAC
- `start_time` (query string): 开始时间 (ISO格式)
- `end_time` (query string): 结束时间 (ISO格式)

**数据库查询**:
```sql
SELECT target_id, pos_x, pos_y, speed, resolution, created_at
FROM radar_tracking_logs
WHERE device_mac = ? AND created_at BETWEEN ? AND ?
ORDER BY created_at ASC
```

**响应格式**:
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

**实现逻辑**:
- 利用idx_mac_time索引加速查询
- 支持分页（可选添加limit/offset参数）
- 时间格式转换：datetime to ISO string

### 3. 守卫日志API (/api/v1/guard/events)

**目的**: 获取入侵报警的历史列表与坐标节点

**方法**: GET

**参数**:
- `device_mac` (query string): 设备MAC
- `start_time` (query string, optional): 开始时间
- `end_time` (query string, optional): 结束时间

**数据库查询**:
```sql
SELECT * FROM guard_events
WHERE device_mac = ? AND start_time >= ? AND end_time <= ?
ORDER BY start_time DESC
```

**响应格式**:
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

**实现逻辑**:
- 默认查询最近7天数据
- 支持时间范围过滤
- snapshot_points用于前端缩略图展示

### 4. 下发指令API (/api/v1/device/command)

**目的**: 存储待执行指令（重启、切模式、设预警区）

**方法**: POST

**请求体**:
```json
{
  "device_mac": "AA:BB:CC:DD:EE:FF",
  "command_type": "SET_MODE",
  "payload": {"mode": "single"}
}
```

**数据库操作**:
```sql
INSERT INTO pending_commands (device_mac, command_type, payload, status, created_at)
VALUES (?, ?, ?, 'PENDING', NOW())
```

**响应格式**:
```json
{
  "code": 200,
  "message": "Command queued successfully",
  "command_id": 123
}
```

**实现逻辑**:
- 验证command_type有效性 (REBOOT, SET_MODE, SET_ZONE等)
- payload根据command_type验证格式
- ESP32在sync时检查pending_commands并执行

### 5. 实时流WebSocket (/ws/radar/live)

**目的**: 获取10Hz实时坐标推送

**协议**: WebSocket

**连接URL**: `/ws/radar/live?mac=AA:BB:CC:DD:EE:FF`

**消息格式** (服务器推送):
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

**实现逻辑**:
- 连接时增加DeviceShadow.active_viewers计数
- 断开时减少计数
- 当有新sync数据时，通过WebSocket广播给所有连接的客户端
- 支持多客户端同时观看

## 实现步骤

1. **更新依赖和启动方式**
   - 添加flask-socketio和eventlet
   - 修改app.py使用socketio.run()

2. **实现REST API**
   - 按顺序实现4个GET/POST API
   - 添加参数验证和错误处理

3. **实现WebSocket**
   - 添加连接/断开事件处理
   - 修改device_sync函数，推送数据到WebSocket

4. **测试和优化**
   - 单元测试各API
   - 性能测试（尤其是历史查询）
   - 添加日志记录

## 注意事项

- **数据一致性**: 确保WebSocket推送的数据与sync API一致
- **性能优化**: 历史查询可能返回大量数据，考虑分页
- **安全**: 添加MAC地址验证，防止越权访问
- **错误处理**: 统一的错误响应格式
- **时间处理**: 使用UTC时间，ISO格式字符串</content>
<parameter name="filePath">h:\Code\WatchYourBehind-Server\server-TODO.md