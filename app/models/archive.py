from flask_sqlalchemy import SQLAlchemy 
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
import uuid
from datetime import datetime
from app import db

class ToDictMixin:
    def to_dict(self):
        def serialize(value):
            if isinstance(value, UNIQUEIDENTIFIER):
                return str(value)
            return value
        
        return {column.name: serialize(getattr(self, column.name)) for column in self.__table__.columns}
    
class ArchivedInsight(db.Model,ToDictMixin):
    __bind_key__ = 'archive'
    __tablename__ = 'ArchivedInsights'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True)
    user_id = db.Column(UNIQUEIDENTIFIER, nullable=False) 
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime) 
    archived_at = db.Column(db.DateTime, default=datetime.utcnow)

    files = db.relationship('ArchivedFile', back_populates='insight', cascade='all, delete-orphan')
    sales_data = db.relationship('ArchivedSalesData', back_populates='insight', cascade='all, delete-orphan')
    order_status = db.relationship('ArchivedOrderStatus', back_populates='insight', cascade='all, delete-orphan')
    sales_over_time = db.relationship('ArchivedSalesOverTime', back_populates='insight', cascade='all, delete-orphan')
    quantity_price_data = db.relationship('ArchivedQuantityPriceData', back_populates='insight', cascade='all, delete-orphan')

    item_frequencies = db.relationship('ArchivedItemFrequency', back_populates='insight', cascade='all, delete-orphan')
    monthly_sales = db.relationship('ArchivedMonthlySales', back_populates='insight', cascade='all, delete-orphan')
    customer_frequencies = db.relationship('ArchivedCustomerFrequency', back_populates='insight', cascade='all, delete-orphan')
    common_item_pairs = db.relationship('ArchivedCommonItemPairs', back_populates='insight', cascade='all, delete-orphan')
    seasonal_items = db.relationship('ArchivedSeasonalItems', back_populates='insight', cascade='all, delete-orphan')
    customer_segments = db.relationship('ArchivedCustomerSegments', back_populates='insight', cascade='all, delete-orphan')

    ChatMessage = db.relationship("ArchivedChatMessage", back_populates="insight", cascade="all, delete-orphan")
     
    # Update the get_analysis_data method
    def get_analysis_data(self):
        analysis_data = {
            'salesData': [
                {'PRODUCTLINE': sd.product_line, 'SALES': float(sd.sales)}
                for sd in self.sales_data
            ],
            'orderStatus': [
                {'STATUS': os.status_type, 'count': os.status_count}
                for os in self.order_status
            ],
            'salesOverTime': [
                {'ORDERDATE': sot.order_date.strftime('%Y-%m-%d'), 'SALES': float(sot.daily_sales)}
                for sot in self.sales_over_time
            ],
            'quantityVsPrice': [
                {'QUANTITYORDERED': qpd.quantity_ordered, 'PRICEEACH': float(qpd.price_each)}
                for qpd in self.quantity_price_data
            ],
            'itemFrequency': {
                if_item.item_description: if_item.frequency
                for if_item in self.item_frequencies
            },
            'monthlySales': [
                {'Date': ms.date.strftime('%Y-%m-%d'), 'count': ms.count}
                for ms in self.monthly_sales
            ],
            'customerFrequency': {
                cf.purchase_frequency: cf.customer_count
                for cf in self.customer_frequencies
            },
            'commonItemPairs': {
                cp.item_pair: cp.pair_count
                for cp in self.common_item_pairs
            },
            'seasonalItems': {
                si.month: si.item_description
                for si in self.seasonal_items
            },
            'customerSegments': {
                cs.segment: cs.count
                for cs in self.customer_segments
            }
        }
        return analysis_data
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': str(self.user_id), 
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'processing_result': self.get_analysis_data(),
            'files': [file.to_dict() for file in self.files] 
        }
        
class ArchivedFile(db.Model,ToDictMixin):
    __bind_key__ = 'archive'
    __tablename__ = 'ArchivedFiles'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_hash = db.Column(db.String(64), nullable=False)
    user_id = db.Column(UNIQUEIDENTIFIER, nullable=False)
    upload_date = db.Column(db.DateTime)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(50))
    status = db.Column(db.String(50))
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('ArchivedInsights.id'), nullable=False)

    insight = db.relationship('ArchivedInsight', back_populates='files')
    
    def to_dict(self):
        return {   
            'id': str(self.id),
            'filename': self.filename,
            'file_path': self.file_path,
            'file_hash': self.file_hash,
            'user_id': str(self.user_id),
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'status': self.status,
            'insight_id': str(self.insight_id)
        }

class ArchivedSalesData(db.Model,ToDictMixin):
    __bind_key__ = 'archive'
    __tablename__ = 'ArchivedSalesData'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('ArchivedInsights.id'), nullable=False)
    product_line = db.Column(db.String(100), nullable=False)
    sales = db.Column(db.Numeric(18, 2), nullable=False)

    insight = db.relationship('ArchivedInsight', back_populates='sales_data')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'insight_id': str(self.insight_id),
            'product_line': self.product_line,
            'sales': float(self.sales)
        }

class ArchivedOrderStatus(db.Model,ToDictMixin):
    __bind_key__ = 'archive'
    __tablename__ = 'ArchivedOrderStatus'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('ArchivedInsights.id'), nullable=False)
    status_type = db.Column(db.String(50), nullable=False)
    status_count = db.Column(db.Integer, nullable=False)

    insight = db.relationship('ArchivedInsight', back_populates='order_status')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'insight_id': str(self.insight_id),
            'status_type': self.status_type,
            'status_count': self.status_count
        }

class ArchivedSalesOverTime(db.Model,ToDictMixin):
    __bind_key__ = 'archive'
    __tablename__ = 'ArchivedSalesOverTime'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('ArchivedInsights.id'), nullable=False)
    order_date = db.Column(db.Date, nullable=False)
    daily_sales = db.Column(db.Numeric(18, 2), nullable=False)

    insight = db.relationship('ArchivedInsight', back_populates='sales_over_time')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'insight_id': str(self.insight_id),
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'daily_sales': float(self.daily_sales)
        }

class ArchivedQuantityPriceData(db.Model,ToDictMixin):
    __bind_key__ = 'archive'
    __tablename__ = 'ArchivedQuantityPriceData'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('ArchivedInsights.id'), nullable=False)
    quantity_ordered = db.Column(db.Integer, nullable=False)
    price_each = db.Column(db.Numeric(18, 2), nullable=False)

    insight = db.relationship('ArchivedInsight', back_populates='quantity_price_data')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'insight_id': str(self.insight_id),
            'quantity_ordered': self.quantity_ordered,
            'price_each': float(self.price_each)
        }
   
class ArchivedItemFrequency(db.Model,ToDictMixin):
    __bind_key__ = 'archive'
    __tablename__ = 'ArchivedItemFrequency'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('ArchivedInsights.id'), nullable=False)
    item_description = db.Column(db.String(255), nullable=False)
    frequency = db.Column(db.Integer, nullable=False)

    insight = db.relationship('ArchivedInsight', back_populates='item_frequencies')

class ArchivedMonthlySales(db.Model,ToDictMixin):
    __bind_key__ = 'archive'
    __tablename__ = 'ArchivedMonthlySales'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('ArchivedInsights.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    count = db.Column(db.Integer, nullable=False)

    insight = db.relationship('ArchivedInsight', back_populates='monthly_sales')

class ArchivedCustomerFrequency(db.Model,ToDictMixin):
    __bind_key__ = 'archive'
    __tablename__ = 'ArchivedCustomerFrequency'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('ArchivedInsights.id'), nullable=False)
    purchase_frequency = db.Column(db.Integer, nullable=False)
    customer_count = db.Column(db.Integer, nullable=False)

    insight = db.relationship('ArchivedInsight', back_populates='customer_frequencies')

class ArchivedCommonItemPairs(db.Model,ToDictMixin):
    __bind_key__ = 'archive'
    __tablename__ = 'ArchivedCommonItemPairs'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('ArchivedInsights.id'), nullable=False)
    item_pair = db.Column(db.String(510), nullable=False)
    pair_count = db.Column(db.Integer, nullable=False)

    insight = db.relationship('ArchivedInsight', back_populates='common_item_pairs')

class ArchivedSeasonalItems(db.Model,ToDictMixin):
    __bind_key__ = 'archive'
    __tablename__ = 'ArchivedSeasonalItems'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('ArchivedInsights.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    item_description = db.Column(db.String(255), nullable=False)

    insight = db.relationship('ArchivedInsight', back_populates='seasonal_items')

class ArchivedCustomerSegments(db.Model,ToDictMixin):
    __bind_key__ = 'archive'
    __tablename__ = 'ArchivedCustomerSegments'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('ArchivedInsights.id'), nullable=False)
    segment = db.Column(db.String(50), nullable=False)
    count = db.Column(db.Integer, nullable=False)

    insight = db.relationship('ArchivedInsight', back_populates='customer_segments')

class ArchivedChatMessage(db.Model,ToDictMixin):
    __bind_key__ = 'archive'
    __tablename__ = 'ArchivedChatMessage'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('ArchivedInsights.id'), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    insight = db.relationship('ArchivedInsight', back_populates='ChatMessage')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'insight_id': str(self.insight_id),
            'user_message': self.user_message,
            'bot_response': self.bot_response,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
     