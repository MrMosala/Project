from app import db
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
import uuid
from datetime import datetime

class AuditEntry(db.Model):
    __bind_key__ = 'audit'  # Assuming you'll use a separate database for auditing
    __tablename__ = 'audit_entries'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(UNIQUEIDENTIFIER, nullable=True)  # Nullable for system actions
    action = db.Column(db.String(50), nullable=False)
    table_name = db.Column(db.String(50), nullable=False)
    record_id = db.Column(UNIQUEIDENTIFIER, nullable=False)
    old_values = db.Column(db.JSON, nullable=True)
    new_values = db.Column(db.JSON, nullable=True)
    additional_info = db.Column(db.JSON, nullable=True)

    def __repr__(self):
        return f'<AuditEntry {self.id}: {self.action} on {self.table_name}>'

    def to_dict(self):
        return {
            'id': str(self.id),
            'timestamp': self.timestamp.isoformat(),
            'user_id': str(self.user_id) if self.user_id else None,
            'action': self.action,
            'table_name': self.table_name,
            'record_id': str(self.record_id),
            'old_values': self.old_values,
            'new_values': self.new_values,
            'additional_info': self.additional_info
        }