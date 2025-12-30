from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.mysql import TINYINT, SMALLINT, BIGINT, VARCHAR, DATETIME, JSON, ENUM

db = SQLAlchemy()

class RadarTrackingLog(db.Model):
    __tablename__ = 'radar_tracking_logs'
    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    device_mac = db.Column(VARCHAR(17), index=True)
    batch_id = db.Column(VARCHAR(32))
    target_id = db.Column(TINYINT)
    pos_x = db.Column(SMALLINT)
    pos_y = db.Column(SMALLINT)
    speed = db.Column(SMALLINT)
    resolution = db.Column(SMALLINT)
    created_at = db.Column(DATETIME(fsp=3), index=True)
    __table_args__ = (
        db.Index('idx_mac_time', 'device_mac', 'created_at'),
    )

class DeviceShadow(db.Model):
    __tablename__ = 'device_shadow'
    device_mac = db.Column(VARCHAR(17), primary_key=True)
    online_status = db.Column(db.Boolean)
    firmware_ver = db.Column(VARCHAR(50))
    track_mode = db.Column(ENUM('single', 'multi'))
    bluetooth_state = db.Column(db.Boolean)
    zone_config = db.Column(JSON)
    active_viewers = db.Column(db.Integer)
    last_heartbeat = db.Column(DATETIME)

class GuardEvent(db.Model):
    __tablename__ = 'guard_events'
    event_id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    device_mac = db.Column(VARCHAR(17))
    zone_id = db.Column(TINYINT)
    start_time = db.Column(DATETIME)
    end_time = db.Column(DATETIME)
    duration = db.Column(db.Integer)
    max_speed = db.Column(SMALLINT)
    snapshot_points = db.Column(JSON)

class PendingCommand(db.Model):
    __tablename__ = 'pending_commands'
    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    device_mac = db.Column(VARCHAR(17), index=True)
    command_type = db.Column(VARCHAR(20))
    payload = db.Column(JSON)
    status = db.Column(ENUM('PENDING', 'SENT', 'EXECUTED'), index=True)
    created_at = db.Column(DATETIME)
    __table_args__ = (
        db.Index('idx_mac_status', 'device_mac', 'status'),
    )