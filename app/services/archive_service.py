from datetime import datetime, timedelta
from sqlalchemy import Date, cast
from app import db
from app.services.audit_service import log_audit
from logging_config import default_logger as logger
from app.models.archive import (
    ArchivedChatMessage, ArchivedFile, ArchivedInsight, ArchivedOrderStatus, ArchivedQuantityPriceData, 
    ArchivedSalesData, ArchivedSalesOverTime, ArchivedItemFrequency, ArchivedMonthlySales, 
    ArchivedCustomerFrequency, ArchivedCommonItemPairs, ArchivedSeasonalItems, ArchivedCustomerSegments
)
from app.models.operational import ChatMessage, CommonItemPairs, CustomerFrequency, CustomerSegments, File, Insight, ItemFrequency, MonthlySales, OrderStatus, QuantityPriceData, SalesData, SalesOverTime, SeasonalItems

def archive_old_data():
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=3)
  
        old_insights = Insight.query.filter(cast(Insight.created_at, Date) < cutoff_date).all()
        
        for insight in old_insights:
            archived_insight = ArchivedInsight(
                id=insight.id,
                user_id=insight.user_id, 
                created_at=insight.created_at,
                updated_at=insight.updated_at, 
            )
            
             # Archive files
            for file in insight.files:
                archived_file = ArchivedFile(
                    id=file.id,
                    filename=file.filename,
                    file_path=file.file_path,
                    file_hash=file.file_hash,
                    user_id=file.user_id,
                    upload_date=file.upload_date,
                    file_size=file.file_size,
                    file_type=file.file_type,
                    status=file.status,
                    insight_id=file.insight_id
                )
                archived_insight.files.append(archived_file)
                log_audit('archive', 'Files', file.id, old_values=file.to_dict(), new_values=archived_file.to_dict())
            
            # Archive sales data
            for sales_data in insight.sales_data:
                archived_sales_data = ArchivedSalesData(
                    id=sales_data.id,
                    product_line=sales_data.product_line,
                    sales=sales_data.sales,
                    insight_id=sales_data.insight_id
                )
                archived_insight.sales_data.append(archived_sales_data)
                log_audit('archive', 'SalesData', sales_data.id, old_values=sales_data.to_dict(), new_values=archived_sales_data.to_dict())
            
            # Archive order status
            for order_status in insight.order_status:
                archived_order_status = ArchivedOrderStatus(
                    id=order_status.id,
                    status_type=order_status.status_type,
                    status_count=order_status.status_count,
                    insight_id=order_status.insight_id
                )
                archived_insight.order_status.append(archived_order_status)
                log_audit('archive', 'OrderStatus', order_status.id, old_values=order_status.to_dict(), new_values=archived_order_status.to_dict())
            
            # Archive sales over time
            for sales_over_time in insight.sales_over_time:
                archived_sales_over_time = ArchivedSalesOverTime(
                    id=sales_over_time.id,
                    order_date=sales_over_time.order_date,
                    daily_sales=sales_over_time.daily_sales,
                    insight_id=sales_over_time.insight_id
                )
                archived_insight.sales_over_time.append(archived_sales_over_time)
                log_audit('archive', 'SalesOverTime', sales_over_time.id, old_values=sales_over_time.to_dict(), new_values=archived_sales_over_time.to_dict())
            
            # Archive quantity price data
            for quantity_price_data in insight.quantity_price_data:
                archived_quantity_price_data = ArchivedQuantityPriceData(
                    id=quantity_price_data.id,
                    quantity_ordered=quantity_price_data.quantity_ordered,
                    price_each=quantity_price_data.price_each,
                    insight_id=quantity_price_data.insight_id
                )
                archived_insight.quantity_price_data.append(archived_quantity_price_data)
                log_audit('archive', 'QuantityPriceData', quantity_price_data.id, old_values=quantity_price_data.to_dict(), new_values=archived_quantity_price_data.to_dict())
            

            # Archive item frequencies
            for item_frequency in insight.item_frequencies:
                archived_item_frequency = ArchivedItemFrequency(
                    id=item_frequency.id,
                    item_description=item_frequency.item_description,
                    frequency=item_frequency.frequency,
                    insight_id=item_frequency.insight_id
                )
                archived_insight.item_frequencies.append(archived_item_frequency)
                log_audit('archive', 'ItemFrequency', item_frequency.id, old_values=item_frequency.to_dict(), new_values=archived_item_frequency.to_dict())

            # Archive monthly sales
            for monthly_sale in insight.monthly_sales:
                archived_monthly_sale = ArchivedMonthlySales(
                    id=monthly_sale.id,
                    date=monthly_sale.date,
                    count=monthly_sale.count,
                    insight_id=monthly_sale.insight_id
                )
                archived_insight.monthly_sales.append(archived_monthly_sale)
                log_audit('archive', 'MonthlySales', monthly_sale.id, old_values=monthly_sale.to_dict(), new_values=archived_monthly_sale.to_dict())

            # Archive customer frequencies
            for customer_frequency in insight.customer_frequencies:
                archived_customer_frequency = ArchivedCustomerFrequency(
                    id=customer_frequency.id,
                    purchase_frequency=customer_frequency.purchase_frequency,
                    customer_count=customer_frequency.customer_count,
                    insight_id=customer_frequency.insight_id
                )
                archived_insight.customer_frequencies.append(archived_customer_frequency)
                log_audit('archive', 'CustomerFrequency', customer_frequency.id, old_values=customer_frequency.to_dict(), new_values=archived_customer_frequency.to_dict())

            # Archive common item pairs
            for common_item_pair in insight.common_item_pairs:
                archived_common_item_pair = ArchivedCommonItemPairs(
                    id=common_item_pair.id,
                    item_pair=common_item_pair.item_pair,
                    pair_count=common_item_pair.pair_count,
                    insight_id=common_item_pair.insight_id
                )
                archived_insight.common_item_pairs.append(archived_common_item_pair)
                log_audit('archive', 'CommonItemPairs', common_item_pair.id, old_values=common_item_pair.to_dict(), new_values=archived_common_item_pair.to_dict())

            # Archive seasonal items
            for seasonal_item in insight.seasonal_items:
                archived_seasonal_item = ArchivedSeasonalItems(
                    id=seasonal_item.id,
                    month=seasonal_item.month,
                    item_description=seasonal_item.item_description,
                    insight_id=seasonal_item.insight_id
                )
                archived_insight.seasonal_items.append(archived_seasonal_item)
                log_audit('archive', 'SeasonalItems', seasonal_item.id, old_values=seasonal_item.to_dict(), new_values=archived_seasonal_item.to_dict())

            # Archive customer segments
            for customer_segment in insight.customer_segments:
                archived_customer_segment = ArchivedCustomerSegments(
                    id=customer_segment.id,
                    segment=customer_segment.segment,
                    count=customer_segment.count,
                    insight_id=customer_segment.insight_id
                )
                archived_insight.customer_segments.append(archived_customer_segment)
                log_audit('archive', 'CustomerSegments', customer_segment.id, old_values=customer_segment.to_dict(), new_values=archived_customer_segment.to_dict())
           
            # Archive chat messages
            for chat_message in insight.ChatMessage:
                archived_chat_message = ArchivedChatMessage(
                    id=chat_message.id,
                    insight_id=chat_message.insight_id,
                    user_message=chat_message.user_message,
                    bot_response=chat_message.bot_response,
                    timestamp=chat_message.timestamp
                )
                archived_insight.ArchivedChatMessage.append(archived_chat_message)
                log_audit('archive', 'ChatMessage', chat_message.id, old_values=chat_message.to_dict(), new_values=archived_chat_message.to_dict())
                
            db.session.add(archived_insight)
            db.session.delete(insight)
            
            # Log audit for the insight itself
            log_audit('archive', 'Insights', insight.id, old_values=insight.to_dict(), new_values=archived_insight.to_dict())
        
        
        db.session.commit()
        
        logger.info(f"Successfully archived {len(old_insights)} insights and their related data.")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error occurred during archiving process: {str(e)}")
        raise


def unarchive_insight(archived_insight_id):
    try:
        archived_insight = ArchivedInsight.query.get(archived_insight_id)
        if not archived_insight:
            logger.error(f"Archived insight with ID {archived_insight_id} not found")
            raise ValueError(f"Archived insight with ID {archived_insight_id} not found")

        # Create a new Insight
        new_insight = Insight(
            id=archived_insight.id,
            user_id=archived_insight.user_id,
            created_at=archived_insight.created_at,
            updated_at=datetime.utcnow(),
          
        )

        # Unarchive files
        for archived_file in archived_insight.files:
            new_file = File(
                id=archived_file.id,
                filename=archived_file.filename,
                file_path=archived_file.file_path,
                file_hash=archived_file.file_hash,
                user_id=archived_file.user_id,
                upload_date=archived_file.upload_date,
                file_size=archived_file.file_size,
                file_type=archived_file.file_type,
                status=archived_file.status,
                insight_id=new_insight.id
            )
            new_insight.files.append(new_file)
            db.session.delete(archived_file)
            log_audit('unarchive', 'Files', new_file.id, old_values=archived_file.to_dict(), new_values=new_file.to_dict())

        # Unarchive sales data
        for archived_sales_data in archived_insight.sales_data:
            new_sales_data = SalesData(
                id=archived_sales_data.id,
                product_line=archived_sales_data.product_line,
                sales=archived_sales_data.sales,
                insight_id=new_insight.id
            )
            new_insight.sales_data.append(new_sales_data)
            db.session.delete(archived_sales_data)
            log_audit('unarchive', 'SalesData', new_sales_data.id, old_values=archived_sales_data.to_dict(), new_values=new_sales_data.to_dict())

        # Unarchive order status
        for archived_order_status in archived_insight.order_status:
            new_order_status = OrderStatus(
                id=archived_order_status.id,
                status_type=archived_order_status.status_type,
                status_count=archived_order_status.status_count,
                insight_id=new_insight.id
            )
            new_insight.order_status.append(new_order_status)
            db.session.delete(archived_order_status)
            log_audit('unarchive', 'OrderStatus', new_order_status.id, old_values=archived_order_status.to_dict(), new_values=new_order_status.to_dict())

        # Unarchive sales over time
        for archived_sales_over_time in archived_insight.sales_over_time:
            new_sales_over_time = SalesOverTime(
                id=archived_sales_over_time.id,
                order_date=archived_sales_over_time.order_date,
                daily_sales=archived_sales_over_time.daily_sales,
                insight_id=new_insight.id
            )
            new_insight.sales_over_time.append(new_sales_over_time)
            db.session.delete(archived_sales_over_time)
            log_audit('unarchive', 'SalesOverTime', new_sales_over_time.id, old_values=archived_sales_over_time.to_dict(), new_values=new_sales_over_time.to_dict())

        # Unarchive quantity price data
        for archived_quantity_price_data in archived_insight.quantity_price_data:
            new_quantity_price_data = QuantityPriceData(
                id=archived_quantity_price_data.id,
                quantity_ordered=archived_quantity_price_data.quantity_ordered,
                price_each=archived_quantity_price_data.price_each,
                insight_id=new_insight.id
            )
            new_insight.quantity_price_data.append(new_quantity_price_data)
            db.session.delete(archived_quantity_price_data)
            log_audit('unarchive', 'QuantityPriceData', new_quantity_price_data.id, old_values=archived_quantity_price_data.to_dict(), new_values=new_quantity_price_data.to_dict())

        # Unarchive item frequencies
        for archived_item_frequency in archived_insight.item_frequencies:
            new_item_frequency = ItemFrequency(
                id=archived_item_frequency.id,
                item_description=archived_item_frequency.item_description,
                frequency=archived_item_frequency.frequency,
                insight_id=new_insight.id
            )
            new_insight.item_frequencies.append(new_item_frequency)
            db.session.delete(archived_item_frequency)
            log_audit('unarchive', 'ItemFrequency', new_item_frequency.id, old_values=archived_item_frequency.to_dict(), new_values=new_item_frequency.to_dict())

        # Unarchive monthly sales
        for archived_monthly_sales in archived_insight.monthly_sales:
            new_monthly_sales = MonthlySales( 
                id=archived_monthly_sales.id,
                date=archived_monthly_sales.date,
                count=archived_monthly_sales.count,
                insight_id=new_insight.id
            )
            new_insight.monthly_sales.append(new_monthly_sales)
            db.session.delete(archived_monthly_sales)
            log_audit('unarchive', 'MonthlySales', new_monthly_sales.id, old_values=archived_monthly_sales.to_dict(), new_values=new_monthly_sales.to_dict())

        # Unarchive customer frequencies
        for archived_customer_frequency in archived_insight.customer_frequencies:
            new_customer_frequency = CustomerFrequency(
                id=archived_customer_frequency.id,
                purchase_frequency=archived_customer_frequency.purchase_frequency,
                customer_count=archived_customer_frequency.customer_count,
                insight_id=new_insight.id
            )
            new_insight.customer_frequencies.append(new_customer_frequency)
            db.session.delete(archived_customer_frequency)
            log_audit('unarchive', 'CustomerFrequency', new_customer_frequency.id, old_values=archived_customer_frequency.to_dict(), new_values=new_customer_frequency.to_dict())

        # Unarchive common item pairs
        for archived_common_item_pair in archived_insight.common_item_pairs:
            new_common_item_pair = CommonItemPairs(
                id=archived_common_item_pair.id,
                item_pair=archived_common_item_pair.item_pair,
                pair_count=archived_common_item_pair.pair_count,
                insight_id=new_insight.id
            )
            new_insight.common_item_pairs.append(new_common_item_pair)
            db.session.delete(archived_common_item_pair)
            log_audit('unarchive', 'CommonItemPairs', new_common_item_pair.id, old_values=archived_common_item_pair.to_dict(), new_values=new_common_item_pair.to_dict())

        # Unarchive seasonal items
        for archived_seasonal_item in archived_insight.seasonal_items:
            new_seasonal_item = SeasonalItems(
                id=archived_seasonal_item.id,
                month=archived_seasonal_item.month,
                item_description=archived_seasonal_item.item_description,
                insight_id=new_insight.id
            )
            new_insight.seasonal_items.append(new_seasonal_item)
            db.session.delete(archived_seasonal_item)
            log_audit('unarchive', 'SeasonalItems', new_seasonal_item.id, old_values=archived_seasonal_item.to_dict(), new_values=new_seasonal_item.to_dict())

        # Unarchive customer segments
        for archived_customer_segment in archived_insight.customer_segments:
            new_customer_segment = CustomerSegments(
                id=archived_customer_segment.id,
                segment=archived_customer_segment.segment,
                count=archived_customer_segment.count,
                insight_id=new_insight.id
            )
            new_insight.customer_segments.append(new_customer_segment)
            db.session.delete(archived_customer_segment)
            log_audit('unarchive', 'CustomerSegments', new_customer_segment.id, old_values=archived_customer_segment.to_dict(), new_values=new_customer_segment.to_dict())

        # Unarchive chat messages
        for archived_chat_message in archived_insight.ArchivedChatMessage:
            new_chat_message = ChatMessage(
                id=archived_chat_message.id,
                insight_id=archived_chat_message.insight_id,
                user_message=archived_chat_message.user_message,
                bot_response=archived_chat_message.bot_response,
                timestamp=archived_chat_message.timestamp
            )
            new_insight.ChatMessage.append(new_chat_message)
            db.session.delete(archived_chat_message)
            log_audit('unarchive', 'ChatMessage', new_chat_message.id, old_values=archived_chat_message.to_dict(), new_values=new_chat_message.to_dict())

        db.session.add(new_insight)
        db.session.delete(archived_insight)
        db.session.commit()

        log_audit('unarchive', 'Insights', new_insight.id, old_values=archived_insight.to_dict(), new_values=new_insight.to_dict())
        logger.info(f"Successfully unarchived insight with ID {archived_insight_id}")

        return new_insight

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error occurred during unarchiving process: {str(e)}")
        raise