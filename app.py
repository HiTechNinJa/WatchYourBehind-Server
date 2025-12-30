from flask import Flask, request, jsonify
from models import db, RadarTrackingLog, DeviceShadow, GuardEvent, PendingCommand
import config
from datetime import datetime

app = Flask(__name__)
app.config.from_object('config')
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/api/v1/device/sync', methods=['POST'])
def device_sync():
    data = request.get_json()
    targets = data.get('targets', [])
    batch_id = data.get('batch_id', 'batch_' + datetime.now().strftime('%Y%m%d%H%M%S'))
    device_mac = data.get('device_mac', 'unknown')
    now = datetime.now()
    for i, t in enumerate(targets):
        log = RadarTrackingLog(
            device_mac=device_mac,
            batch_id=batch_id,
            target_id=i+1,
            pos_x=t.get('x', 0),
            pos_y=t.get('y', 0),
            speed=t.get('speed', 0),
            resolution=t.get('resolution', 0),
            created_at=now
        )
        db.session.add(log)
    db.session.commit()
    resp = {
        "code": 200,
        "data": {
            "next_interval": 1000,
            "server_time": int(now.timestamp()),
            "pending_cmd": None
        }
    }
    return jsonify(resp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
