import json
from uuid import UUID
from datetime import date, datetime
from flask_jwt_extended import get_jwt_identity
from app import db
from flask import current_app, has_request_context
from flask_login import current_user
from logging_config import default_logger as logger
from app.models.audit import AuditEntry

def json_serializer(obj):
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

def serialize_dict(d):
    if d is None:
        return None
    return json.dumps(d, default=json_serializer)

def log_audit(action, table_name, record_id, old_values=None, new_values=None, additional_info=None):
    try:
        if has_request_context():
            user_id = get_jwt_identity()
        else:
            user_id = None  # or any identifier you want to use for system actions
    except Exception:
        user_id = None  # Fallback if JWT is not available
   
    audit_entry = AuditEntry(
        user_id=str(user_id) if user_id else None,
        action=action,
        table_name=table_name,
        record_id=str(record_id),
        old_values=serialize_dict(old_values),
        new_values=serialize_dict(new_values),
        additional_info=serialize_dict(additional_info)
    )
    
    try:
        db.session.add(audit_entry)
        db.session.commit()
        logger.info(f"Audit log created: {audit_entry}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create audit log: {str(e)}")