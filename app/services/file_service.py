import hashlib
import os
from datetime import datetime, date
from sqlalchemy import Date, cast
from app import db
from app.models.operational import CommonItemPairs, CustomerFrequency, CustomerSegments, File, Insight, ItemFrequency, MonthlySales, OrderStatus, QuantityPriceData, SalesData, SalesOverTime, SeasonalItems
import pandas as pd
from collections import Counter
from itertools import combinations  

from app.services.audit_service import log_audit
from logging_config import default_logger as logger

# Custom exceptions
class FileProcessingError(Exception):
    pass

class DataValidationError(Exception):
    pass

def create_insight(user_id): 
    try:
        insight = Insight(
            user_id=user_id, 
        )
        db.session.add(insight)
        db.session.commit()
        
        log_audit(
            action='create',
            table_name='Insights',
            record_id=insight.id,
            new_values=insight.to_dict()
        )
        
        logger.info(f"Created new insight: {insight.id} for user: {user_id}")
        return insight
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create insight for user {user_id}: {str(e)}")
        raise FileProcessingError(f"Failed to create insight: {str(e)}")

def add_file_to_insight(insight_id, filename, file_path, user_id, file_size, file_type, file_hash):
    try:
        existing_file = File.query.filter_by(file_hash=file_hash, user_id=user_id, insight_id=insight_id).first()
        if existing_file:
            logger.info(f"File already exists: {filename} for insight: {insight_id}")
            return existing_file, True  # File already exists

        file_record = File(
            filename=filename,
            file_path=file_path,
            file_hash=file_hash,
            user_id=user_id,
            file_size=file_size,
            file_type=file_type,
            insight_id=insight_id
        )
        db.session.add(file_record)
        db.session.commit()
        
        log_audit(
            action='create',
            table_name='Files',
            record_id=file_record.id,
            new_values=file_record.to_dict()
        )
        
        logger.info(f"Added new file: {filename} to insight: {insight_id}")
        return file_record, False  # New file added
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to add file {filename} to insight {insight_id}: {str(e)}")
        raise FileProcessingError(f"Failed to add file to insight: {str(e)}")
 
def get_file_hash(file_path):
    BUF_SIZE = 65536  # read in 64kb chunks
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(BUF_SIZE)
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()
    except IOError as e:
        raise FileProcessingError(f"Failed to read file for hashing: {str(e)}")

def save_file(file, filename, upload_folder):
    try:
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        return file_path
    except Exception as e:
        raise FileProcessingError(f"Failed to save file: {str(e)}")

def get_file_size(file_path):
    try:
        return os.path.getsize(file_path)
    except OSError as e:
        raise FileProcessingError(f"Failed to get file size: {str(e)}")

def get_file_type(filename):
    return os.path.splitext(filename)[1]

def get_all_insights(user_id):
    return Insight.query.filter_by(user_id=user_id).order_by(Insight.created_at.desc()).all()

def get_existing_insight(user_id,date): 
    return Insight.query.filter(
        Insight.user_id == user_id, 
        cast(Insight.created_at, Date) == date 
    ).first()

def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def process_files(file_id, insight_id): 
    try:
        file_upload = File.query.get(file_id)
        if not file_upload:
            logger.error(f"File with ID {file_id} not found")
            raise FileProcessingError(f"File with ID {file_id} not found")

        logger.info(f"Processing file: {file_upload.filename} for insight: {insight_id}")
        df = pd.read_csv(file_upload.file_path, encoding='ISO-8859-1')
        
        file_type = identify_file_type(df)
        logger.info(f"Identified file type: {file_type}")
        if file_type == 'sales':
            process_sales_data(df, file_id, insight_id)
        elif file_type == 'market_basket':
            process_market_basket_data(df, file_id,insight_id)
        else:
            logger.error(f"Unknown file type for {file_upload.filename}")
            raise DataValidationError(f'Unknown file type for {file_upload.filename}')
        
        # Update file status after processing
        old_file_values = file_upload.to_dict()
        file_upload.status = 'Processed'
        db.session.commit()
        
        log_audit(
            action='update',
            table_name='Files',
            record_id=file_upload.id,
            old_values=old_file_values,
            new_values=file_upload.to_dict()
        )
        
    except pd.errors.EmptyDataError:
        logger.error("The file is empty or contains no data")
        raise DataValidationError("The file is empty or contains no data")
    except pd.errors.ParserError:
        logger.error("Error parsing the CSV file. Please check the file format")
        raise DataValidationError("Error parsing the CSV file. Please check the file format")
    except Exception as e:
        logger.error(f"An unexpected error occurred while processing file {file_id}: {str(e)}")
        raise FileProcessingError(f"An unexpected error occurred: {str(e)}")

def identify_file_type(df):
    if 'ORDERDATE' in df.columns and 'SALES' in df.columns:
        return 'sales'
    elif 'Date' in df.columns and 'itemDescription' in df.columns:
        return 'market_basket'
    else:
        return 'unknown'

def process_sales_data(df, file_id, insight_id):
    try:
        df['ORDERDATE'] = pd.to_datetime(df['ORDERDATE'], errors='coerce')
        
        sales_data = df.groupby('PRODUCTLINE')['SALES'].sum().nlargest(10).reset_index().to_dict('records')
        order_status = df['STATUS'].value_counts().reset_index().to_dict('records')
        sales_over_time = df.resample('ME', on='ORDERDATE')['SALES'].sum().reset_index()
        sales_over_time['ORDERDATE'] = sales_over_time['ORDERDATE'].dt.strftime('%Y-%m-%d')
        sales_over_time = sales_over_time.to_dict('records')
        quantity_vs_price = df[['QUANTITYORDERED', 'PRICEEACH']].sample(n=min(1000, len(df))).to_dict('records')

        processed_data = {
            'salesData': sales_data,
            'orderStatus': order_status,
            'salesOverTime': sales_over_time,
            'quantityVsPrice': quantity_vs_price
        }
         
        
        file_upload = File.query.get(file_id)
        insert_sales_analysis(insight_id, processed_data)
        if file_upload: 
            old_file = file_upload
            file_upload.status = 'Processed'
            db.session.commit()
            
            
            log_audit(
            action='create',
            table_name='File',
            record_id=file_upload.id,
            old_values=old_file.to_dict(),
            new_values=file_upload.to_dict()    )
        
    except Exception as e:
        raise DataValidationError(f"Error processing sales data: {str(e)}")

def process_market_basket_data(df, file_id,insight_id):
    try:
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
        item_frequency = df['itemDescription'].value_counts().head(10).to_dict()
        monthly_sales = df.resample('M').size().reset_index(name='count')
        monthly_sales['Date'] = monthly_sales['Date'].dt.strftime('%Y-%m-%d')
        monthly_sales = monthly_sales.to_dict('records')
        customer_frequency = df['Member_number'].value_counts().value_counts().sort_index().head(5).to_dict()

        def get_item_pairs(x):
            return list(combinations(set(x), 2))

        item_pairs = df.groupby('Member_number')['itemDescription'].apply(get_item_pairs)
        pair_counts = Counter([pair for pairs in item_pairs for pair in pairs])
        common_pairs = {f"{pair[0]} & {pair[1]}": count for pair, count in sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)[:10]}

        df['Month'] = df.index.month
        seasonal_items = df.groupby('Month')['itemDescription'].apply(lambda x: x.value_counts().index[0]).to_dict()

        purchase_frequency = df.groupby('Member_number').size()
        segments = pd.cut(purchase_frequency, bins=[0, 2, 5, 10, float('inf')], 
                            labels=['Low', 'Medium', 'High', 'Very High'])
        customer_segments = segments.value_counts().to_dict()

        processed_data = {
            'itemFrequency': item_frequency,
            'monthlySales': monthly_sales,
            'customerFrequency': customer_frequency,
            'commonItemPairs': common_pairs,
            'seasonalItems': seasonal_items,
            'customerSegments': customer_segments
        }

        # Get the file and associated insight
        file_upload = File.query.get(file_id)
        insert_market_analysis(insight_id,processed_data)
        if not file_upload:
            raise FileProcessingError(f"File with ID {file_id} not found")
        
        insight = file_upload.insight
        if not insight:
            raise FileProcessingError(f"No insight associated with file ID {file_id}")
 

        # Update file status after processing
        old_file_values = file_upload.to_dict()
        file_upload.status = 'Processed'
        db.session.commit()
        
        log_audit(
            action='update',
            table_name='Files',
            record_id=file_upload.id,
            old_values=old_file_values,
            new_values=file_upload.to_dict()
        )

        logger.info(f"Successfully processed market basket data for file {file_id}")

    except Exception as e:
        logger.error(f"Error processing market basket data for file {file_id}: {str(e)}")
        raise DataValidationError(f"Error processing market basket data: {str(e)}")
    
def insert_sales_analysis(insight_id, data):
    try:
        insight = Insight.query.get(insight_id)
        if not insight:
            logger.error(f"No Insight found with id {insight_id}")
            raise ValueError(f"No Insight found with id {insight_id}")

        logger.info(f"Inserting sales analysis for insight {insight_id}")
        
        old_insight_values = insight.to_dict()
        
        for item in data['salesData']:
            sales_data = SalesData(
                insight_id=insight_id,
                product_line=item['PRODUCTLINE'],
                sales=item['SALES']
            )
            db.session.add(sales_data)
            db.session.flush()
            log_audit(
                action='create',
                table_name='SalesData',
                record_id=sales_data.id,
                new_values=sales_data.to_dict()
            )

        for item in data['orderStatus']:
            order_status = OrderStatus(
                insight_id=insight_id,
                status_type=item['STATUS'],
                status_count=item['count']
            )
            db.session.add(order_status)
            db.session.flush()
            log_audit(
                action='create',
                table_name='OrderStatus',
                record_id=order_status.id,
                new_values=order_status.to_dict()
            )

        for item in data['salesOverTime']:
            sales_over_time = SalesOverTime(
                insight_id=insight_id,
                order_date=datetime.strptime(item['ORDERDATE'], '%Y-%m-%d').date(),
                daily_sales=item['SALES']
            )
            db.session.add(sales_over_time)
            db.session.flush()
            log_audit(
                action='create',
                table_name='SalesOverTime',
                record_id=sales_over_time.id,
                new_values=sales_over_time.to_dict()
            )

        for item in data['quantityVsPrice']:
            quantity_price_data = QuantityPriceData(
                insight_id=insight_id,
                quantity_ordered=item['QUANTITYORDERED'],
                price_each=item['PRICEEACH']
            )
            db.session.add(quantity_price_data)
            db.session.flush()
            log_audit(
                action='create',
                table_name='QuantityPriceData',
                record_id=quantity_price_data.id,
                new_values=quantity_price_data.to_dict()
            )
 
        insight.updated_at = datetime.utcnow()

        db.session.commit()
         
        log_audit(
            action='update',
            table_name='Insights',
            record_id=insight.id,
            old_values=old_insight_values,
            new_values=insight.to_dict()
        )
        
        logger.info(f"Successfully inserted sales analysis for insight {insight_id}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to insert sales analysis for insight {insight_id}: {str(e)}")
        raise FileProcessingError(f"Failed to insert sales analysis: {str(e)}")
    
def insert_market_analysis(insight_id, data):
    try:
        insight = Insight.query.get(insight_id)
        if not insight:
            logger.error(f"No Insight found with id {insight_id}")
            raise ValueError(f"No Insight found with id {insight_id}")

        logger.info(f"Inserting market analysis for insight {insight_id}")
        
        old_insight_values = insight.to_dict()
        
        # Insert ItemFrequency
        for item, frequency in data['itemFrequency'].items():
            item_freq = ItemFrequency(
                insight_id=insight_id,
                item_description=item,
                frequency=frequency
            )
            db.session.add(item_freq)
            db.session.flush()
            log_audit(
                action='create',
                table_name='ItemFrequency',
                record_id=item_freq.id,
                new_values=item_freq.to_dict()
            )

        # Insert MonthlySales
        for item in data['monthlySales']:
            monthly_sale = MonthlySales(
                insight_id=insight_id,
                date=datetime.strptime(item['Date'], '%Y-%m-%d').date(),
                count=item['count']
            )
            db.session.add(monthly_sale)
            db.session.flush()
            log_audit(
                action='create',
                table_name='MonthlySales',
                record_id=monthly_sale.id,
                new_values=monthly_sale.to_dict()
            )

        # Insert CustomerFrequency
        for purchase_frequency, customer_count in data['customerFrequency'].items():
            customer_freq = CustomerFrequency(
                insight_id=insight_id,
                purchase_frequency=int(purchase_frequency),
                customer_count=customer_count
            )
            db.session.add(customer_freq)
            db.session.flush()
            log_audit(
                action='create',
                table_name='CustomerFrequency',
                record_id=customer_freq.id,
                new_values=customer_freq.to_dict()
            )

        # Insert CommonItemPairs
        for pair, count in data['commonItemPairs'].items():
            common_pair = CommonItemPairs(
                insight_id=insight_id,
                item_pair=pair,
                pair_count=count
            )
            db.session.add(common_pair)
            db.session.flush()
            log_audit(
                action='create',
                table_name='CommonItemPairs',
                record_id=common_pair.id,
                new_values=common_pair.to_dict()
            )

        # Insert SeasonalItems
        for month, item in data['seasonalItems'].items():
            seasonal_item = SeasonalItems(
                insight_id=insight_id,
                month=int(month),
                item_description=item
            )
            db.session.add(seasonal_item)
            db.session.flush()
            log_audit(
                action='create',
                table_name='SeasonalItems',
                record_id=seasonal_item.id,
                new_values=seasonal_item.to_dict()
            )

        # Insert CustomerSegments
        for segment, count in data['customerSegments'].items():
            customer_segment = CustomerSegments(
                insight_id=insight_id,
                segment=segment,
                count=count
            )
            db.session.add(customer_segment)
            db.session.flush()
            log_audit(
                action='create',
                table_name='CustomerSegments',
                record_id=customer_segment.id,
                new_values=customer_segment.to_dict()
            )
 
        insight.updated_at = datetime.utcnow()

        db.session.commit()
         
        log_audit(
            action='update',
            table_name='Insights',
            record_id=insight.id,
            old_values=old_insight_values,
            new_values=insight.to_dict()
        )
        
        logger.info(f"Successfully inserted market analysis for insight {insight_id}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to insert market analysis for insight {insight_id}: {str(e)}")
        raise FileProcessingError(f"Failed to insert market analysis: {str(e)}")