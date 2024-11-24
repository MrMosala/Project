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
    
class File(db.Model,ToDictMixin):
    __bind_key__ = 'operational'
    __tablename__ = 'Files'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_hash = db.Column(db.String(64), nullable=False)  # For duplicate checking
    user_id = db.Column(UNIQUEIDENTIFIER, nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer)  # in bytes
    file_type = db.Column(db.String(50))
    status = db.Column(db.String(50), default='Uploaded')
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('Insights.id'), nullable=False)

    insight = db.relationship('Insight', back_populates='files')
   
    def __repr__(self):
        return f'<File {self.filename}>'
    
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

class Insight(db.Model,ToDictMixin):
    __bind_key__ = 'operational'
    __tablename__ = 'Insights'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UNIQUEIDENTIFIER, nullable=False)  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 

    files = db.relationship('File', back_populates='insight', cascade='all, delete-orphan')
    sales_data = db.relationship('SalesData', back_populates='insight', cascade='all, delete-orphan')
    order_status = db.relationship('OrderStatus', back_populates='insight', cascade='all, delete-orphan')
    sales_over_time = db.relationship('SalesOverTime', back_populates='insight', cascade='all, delete-orphan')
    quantity_price_data = db.relationship('QuantityPriceData', back_populates='insight', cascade='all, delete-orphan')

    item_frequencies = db.relationship('ItemFrequency', back_populates='insight', cascade='all, delete-orphan')
    monthly_sales = db.relationship('MonthlySales', back_populates='insight', cascade='all, delete-orphan')
    customer_frequencies = db.relationship('CustomerFrequency', back_populates='insight', cascade='all, delete-orphan')
    common_item_pairs = db.relationship('CommonItemPairs', back_populates='insight', cascade='all, delete-orphan')
    seasonal_items = db.relationship('SeasonalItems', back_populates='insight', cascade='all, delete-orphan')
    customer_segments = db.relationship('CustomerSegments', back_populates='insight', cascade='all, delete-orphan')
    
    ChatMessage = db.relationship("ChatMessage", back_populates="insight", cascade="all, delete-orphan")
     
    def __repr__(self):
        return f'<Insight {self.id}>'
     
    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': str(self.user_id), 
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'processing_result': self.get_analysis_data(),
            'files': [file.to_dict() for file in self.files] 
        }
    def get_analysis_data(self):
        sales_data = [
            {'PRODUCTLINE': sd.product_line, 'SALES': float(sd.sales)}
            for sd in self.sales_data
        ]
        
        order_status = [
            {'STATUS': os.status_type, 'count': os.status_count}
            for os in self.order_status
        ]
        
        sales_over_time = [
            {'ORDERDATE': sot.order_date.strftime('%Y-%m-%d'), 'SALES': float(sot.daily_sales)}
            for sot in self.sales_over_time
        ]
        
        quantity_vs_price = [
            {'QUANTITYORDERED': qpd.quantity_ordered, 'PRICEEACH': float(qpd.price_each)}
            for qpd in self.quantity_price_data
        ]
        
        item_frequency = {
            if_item.item_description: if_item.frequency
            for if_item in self.item_frequencies
        }
        
        monthly_sales = [
            {'Date': ms.date.strftime('%Y-%m-%d'), 'count': ms.count}
            for ms in self.monthly_sales
        ]
        
        customer_frequency = {
            cf.purchase_frequency: cf.customer_count
            for cf in self.customer_frequencies
        }
        
        common_pairs = {
            cp.item_pair: cp.pair_count
            for cp in self.common_item_pairs
        }
        
        seasonal_items = {
            si.month: si.item_description
            for si in self.seasonal_items
        }
        
        customer_segments = {
            cs.segment: cs.count
            for cs in self.customer_segments
        }

        return {
            'salesData': sales_data,
            'orderStatus': order_status,
            'salesOverTime': sales_over_time,
            'quantityVsPrice': quantity_vs_price,
            'itemFrequency': item_frequency,
            'monthlySales': monthly_sales,
            'customerFrequency': customer_frequency,
            'commonItemPairs': common_pairs,
            'seasonalItems': seasonal_items,
            'customerSegments': customer_segments
        }
   
class ChatMessage(db.Model,ToDictMixin):
    __bind_key__ = 'operational'
    __tablename__ = 'ChatMessage'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('Insights.id'), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    insight = db.relationship('Insight', back_populates='ChatMessage')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'insight_id': str(self.insight_id),
            'user_message': self.user_message,
            'bot_response': self.bot_response,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
        
class SalesData(db.Model,ToDictMixin):
    __bind_key__ = 'operational'
    __tablename__ = 'SalesData'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('Insights.id'), nullable=False)
    product_line = db.Column(db.String(100), nullable=False)
    sales = db.Column(db.Numeric(18, 2), nullable=False)

    insight = db.relationship('Insight', back_populates='sales_data')

    def to_dict(self):
        return {
            'id': str(self.id),
            'insight_id': str(self.insight_id),
            'product_line': self.product_line,
            'sales': float(self.sales)
        }

class OrderStatus(db.Model,ToDictMixin):
    __bind_key__ = 'operational'
    __tablename__ = 'OrderStatus'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('Insights.id'), nullable=False)
    status_type = db.Column(db.String(50), nullable=False)
    status_count = db.Column(db.Integer, nullable=False)

    insight = db.relationship('Insight', back_populates='order_status')

    def to_dict(self):
        return {
            'id': str(self.id),
            'insight_id': str(self.insight_id),
            'status_type': self.status_type,
            'status_count': self.status_count
        }

class SalesOverTime(db.Model,ToDictMixin):
    __bind_key__ = 'operational'
    __tablename__ = 'SalesOverTime'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('Insights.id'), nullable=False)
    order_date = db.Column(db.Date, nullable=False)
    daily_sales = db.Column(db.Numeric(18, 2), nullable=False)

    insight = db.relationship('Insight', back_populates='sales_over_time')

    def to_dict(self):
        return {
            'id': str(self.id),
            'insight_id': str(self.insight_id),
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'daily_sales': float(self.daily_sales)
        }

class QuantityPriceData(db.Model,ToDictMixin):
    __bind_key__ = 'operational'
    __tablename__ = 'QuantityPriceData'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('Insights.id'), nullable=False)
    quantity_ordered = db.Column(db.Integer, nullable=False)
    price_each = db.Column(db.Numeric(18, 2), nullable=False)

    insight = db.relationship('Insight', back_populates='quantity_price_data')

    def to_dict(self):
        return {
            'id': str(self.id),
            'insight_id': str(self.insight_id),
            'quantity_ordered': self.quantity_ordered,
            'price_each': float(self.price_each)
        }
        
class ItemFrequency(db.Model,ToDictMixin):
    __bind_key__ = 'operational'
    __tablename__ = 'ItemFrequency'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('Insights.id'), nullable=False)
    item_description = db.Column(db.String(255), nullable=False)
    frequency = db.Column(db.Integer, nullable=False)

    insight = db.relationship('Insight', back_populates='item_frequencies')

class MonthlySales(db.Model,ToDictMixin):
    __bind_key__ = 'operational'
    __tablename__ = 'MonthlySales'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('Insights.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    count = db.Column(db.Integer, nullable=False)

    insight = db.relationship('Insight', back_populates='monthly_sales')

class CustomerFrequency(db.Model,ToDictMixin):
    __bind_key__ = 'operational'
    __tablename__ = 'CustomerFrequency'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('Insights.id'), nullable=False)
    purchase_frequency = db.Column(db.Integer, nullable=False)
    customer_count = db.Column(db.Integer, nullable=False)

    insight = db.relationship('Insight', back_populates='customer_frequencies')

class CommonItemPairs(db.Model,ToDictMixin):
    __bind_key__ = 'operational'
    __tablename__ = 'CommonItemPairs'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('Insights.id'), nullable=False)
    item_pair = db.Column(db.String(510), nullable=False)  # 255 * 2 for two item descriptions
    pair_count = db.Column(db.Integer, nullable=False)

    insight = db.relationship('Insight', back_populates='common_item_pairs')

class SeasonalItems(db.Model,ToDictMixin):
    __bind_key__ = 'operational'
    __tablename__ = 'SeasonalItems'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('Insights.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    item_description = db.Column(db.String(255), nullable=False)

    insight = db.relationship('Insight', back_populates='seasonal_items')

class CustomerSegments(db.Model,ToDictMixin):
    __bind_key__ = 'operational'
    __tablename__ = 'CustomerSegments'

    id = db.Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    insight_id = db.Column(UNIQUEIDENTIFIER, db.ForeignKey('Insights.id'), nullable=False)
    segment = db.Column(db.String(50), nullable=False)
    count = db.Column(db.Integer, nullable=False)

    insight = db.relationship('Insight', back_populates='customer_segments')
