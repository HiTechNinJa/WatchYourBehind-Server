from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, RadarTrackingLog, DeviceShadow, GuardEvent, PendingCommand
from flask_socketio import SocketIO, emit, join_room, leave_room
import config
from datetime import datetime, timedelta
import eventlet

app = Flask(__name__)
CORS(app)
app.config.from_object('config')
db.init_app(app)

# 初始化SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

with app.app_context():
    db.create_all()

@app.route('/api/v1/device/sync', methods=['POST'])
def device_sync():
    data = request.get_json()
    targets = data.get('targets', [])
    batch_id = data.get('batch_id', 'batch_' + datetime.now().strftime('%Y%m%d%H%M%S'))
    device_mac = data.get('device_mac', 'unknown')
    now = datetime.now()
    filtered_count = 0
    for i, t in enumerate(targets):
        x = t.get('x', 0)
        y = t.get('y', 0)
        speed = t.get('speed', 0)
        resolution = t.get('resolution', 0)
        if x == 0 and y == 0 and speed == 0 and resolution == 0:
            print(f"[SYNC][{now}] 过滤掉无效目标: device_mac={device_mac}, batch_id={batch_id}, target_id={i+1}, x=0, y=0, speed=0, resolution=0")
            filtered_count += 1
            continue
        log = RadarTrackingLog(
            device_mac=device_mac,
            batch_id=batch_id,
            target_id=i+1,
            pos_x=x,
            pos_y=y,
            speed=t.get('speed', 0),
            resolution=t.get('resolution', 0),
            created_at=now
        )
        db.session.add(log)
    db.session.commit()
    
    # 检查是否有待执行指令
    pending_cmd = PendingCommand.query.filter_by(
        device_mac=device_mac, 
        status='PENDING'
    ).order_by(PendingCommand.created_at.asc()).first()
    
    if pending_cmd:
        pending_cmd.status = 'SENT'
        db.session.commit()
        pending_cmd_data = {
            "command_type": pending_cmd.command_type,
            "payload": pending_cmd.payload,
            "command_id": pending_cmd.id
        }
    else:
        pending_cmd_data = None
    
    # WebSocket广播数据
    socketio.emit('radar_data', {
        'device_mac': device_mac,
        'targets': targets,
        'timestamp': now.timestamp()
    }, room=device_mac)
    
    print(f"[SYNC][{now}] device_mac={device_mac}, batch_id={batch_id}, 有效目标数={len(targets)-filtered_count}, 过滤无效目标数={filtered_count}")
    resp = {
        "code": 200,
        "data": {
            "next_interval": 1000,
            "server_time": int(now.timestamp()),
            "pending_cmd": pending_cmd_data
        }
    }
    return jsonify(resp)

@app.route('/api/v1/devices', methods=['GET'])
def device_list():
    devices = DeviceShadow.query.all()
    device_list = []
    for device in devices:
        # 判断在线状态
        is_online = False
        if device.last_heartbeat:
            time_diff = datetime.now() - device.last_heartbeat
            is_online = time_diff.total_seconds() < 300  # 5分钟
        
        device_list.append({
            "device_mac": device.device_mac,
            "online_status": is_online,
            "firmware_ver": device.firmware_ver or "unknown",
            "last_heartbeat": device.last_heartbeat.isoformat() + 'Z' if device.last_heartbeat else None,
            "active_viewers": device.active_viewers
        })
    
    return jsonify({
        "code": 200,
        "data": device_list
    })
    
    shadow = DeviceShadow.query.filter_by(device_mac=device_mac).first()
    if not shadow:
        return jsonify({"code": 404, "message": "Device not found"}), 404
    
    # 判断在线状态（5分钟内有心跳）
    is_online = False
    if shadow.last_heartbeat:
        time_diff = datetime.now() - shadow.last_heartbeat
        is_online = time_diff.total_seconds() < 300  # 5分钟
    
    data = {
        "device_mac": shadow.device_mac,
        "online_status": is_online,
        "firmware_ver": shadow.firmware_ver,
        "track_mode": shadow.track_mode,
        "bluetooth_state": shadow.bluetooth_state,
        "zone_config": shadow.zone_config,
        "active_viewers": shadow.active_viewers or 0,
        "last_heartbeat": shadow.last_heartbeat.isoformat() + 'Z' if shadow.last_heartbeat else None
    }
    return jsonify({"code": 200, "data": data})

@app.route('/api/v1/radar/history', methods=['GET'])
def radar_history():
    device_mac = request.args.get('device_mac')
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')
    
    if not device_mac:
        return jsonify({"code": 400, "message": "device_mac is required"}), 400
    
    # 解析时间参数
    try:
        if start_time_str:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        else:
            start_time = datetime.now() - timedelta(hours=1)  # 默认1小时前
        
        if end_time_str:
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        else:
            end_time = datetime.now()
    except ValueError:
        return jsonify({"code": 400, "message": "Invalid time format"}), 400
    
    # 查询历史数据
    logs = RadarTrackingLog.query.filter(
        RadarTrackingLog.device_mac == device_mac,
        RadarTrackingLog.created_at.between(start_time, end_time)
    ).order_by(RadarTrackingLog.created_at.asc()).all()
    
    data = []
    for log in logs:
        data.append({
            "target_id": log.target_id,
            "pos_x": log.pos_x,
            "pos_y": log.pos_y,
            "speed": log.speed,
            "resolution": log.resolution,
            "created_at": log.created_at.isoformat() + 'Z'
        })
    
    return jsonify({"code": 200, "data": data})

@app.route('/api/v1/guard/events', methods=['GET'])
def guard_events():
    device_mac = request.args.get('device_mac')
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')
    
    if not device_mac:
        return jsonify({"code": 400, "message": "device_mac is required"}), 400
    
    # 解析时间参数，默认7天
    try:
        if start_time_str:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        else:
            start_time = datetime.now() - timedelta(days=7)
        
        if end_time_str:
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        else:
            end_time = datetime.now()
    except ValueError:
        return jsonify({"code": 400, "message": "Invalid time format"}), 400
    
    # 查询守卫事件
    events = GuardEvent.query.filter(
        GuardEvent.device_mac == device_mac,
        GuardEvent.start_time >= start_time,
        GuardEvent.end_time <= end_time
    ).order_by(GuardEvent.start_time.desc()).all()
    
    data = []
    for event in events:
        data.append({
            "event_id": event.event_id,
            "device_mac": event.device_mac,
            "zone_id": event.zone_id,
            "start_time": event.start_time.isoformat() + 'Z',
            "end_time": event.end_time.isoformat() + 'Z',
            "duration": event.duration,
            "max_speed": event.max_speed,
            "snapshot_points": event.snapshot_points
        })
    
    return jsonify({"code": 200, "data": data})

@app.route('/api/v1/device/command', methods=['POST'])
def device_command():
    data = request.get_json()
    device_mac = data.get('device_mac')
    command_type = data.get('command_type')
    payload = data.get('payload', {})
    
    if not device_mac or not command_type:
        return jsonify({"code": 400, "message": "device_mac and command_type are required"}), 400
    
    # 验证command_type
    valid_commands = ['REBOOT', 'SET_MODE', 'SET_ZONE']
    if command_type not in valid_commands:
        return jsonify({"code": 400, "message": f"Invalid command_type. Valid: {valid_commands}"}), 400
    
    # 创建指令
    command = PendingCommand(
        device_mac=device_mac,
        command_type=command_type,
        payload=payload,
        status='PENDING',
        created_at=datetime.now()
    )
    db.session.add(command)
    db.session.commit()
    
    return jsonify({
        "code": 200,
        "message": "Command queued successfully",
        "command_id": command.id
    })

# WebSocket事件处理
@socketio.on('connect')
def handle_connect():
    device_mac = request.args.get('mac')
    if device_mac:
        join_room(device_mac)
        # 增加活跃观察者计数
        shadow = DeviceShadow.query.filter_by(device_mac=device_mac).first()
        if shadow:
            shadow.active_viewers = (shadow.active_viewers or 0) + 1
            db.session.commit()
        print(f"[WS] Client connected to room: {device_mac}")

@socketio.on('disconnect')
def handle_disconnect():
    device_mac = request.args.get('mac')
    if device_mac:
        leave_room(device_mac)
        # 减少活跃观察者计数
        shadow = DeviceShadow.query.filter_by(device_mac=device_mac).first()
        if shadow and shadow.active_viewers and shadow.active_viewers > 0:
            shadow.active_viewers -= 1
            db.session.commit()
        print(f"[WS] Client disconnected from room: {device_mac}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
