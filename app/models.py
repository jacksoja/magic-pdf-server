from app.extensions import db
from datetime import datetime
import pytz


class ConversionTask(db.Model):
    uid = db.Column(db.String(32), primary_key=True)
    filename = db.Column(db.String(255))
    upload_time = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Shanghai')))
    status = db.Column(db.String(20), default='pending')
    progress = db.Column(db.Integer, default=0)  # 新增进度字段
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Shanghai')))
