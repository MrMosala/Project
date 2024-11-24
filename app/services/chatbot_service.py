from typing import Dict, Any, List, Tuple
from app.models.operational import ChatMessage, Insight
from app import db
from sqlalchemy.orm import Session
import re
from datetime import datetime
from collections import defaultdict
import numpy as np
from scipy import stats

class ChatbotService:
    def __init__(self):
        self.intents = {
            'monthly_sales_trend': r'monthly sales trend|sales trend by month|overall sales trends?|monthly revenue patterns?|trend of sales for (?:this|last|current|previous) month|monthly income trend|monthly sales analysis|how have monthly sales changed',
            'sales_over_time': r'sales over time|sales trends?|revenue over time|long-term sales trends?|how have sales changed over time|sales performance over time|sales history|sales evolution|trend of sales over the year',
            'customer_segments_distribution': r'customer segments? distribution|proportion of customers by segment|customer segmentation|breakdown of customer types|customer demographics?|customer categories distribution|customer types analysis|customer groups breakdown|distribution of customers by groups|segments of customers|how are our customer segments distributed',
            'top_items_by_frequency': r'top (?:\d+ )?items by frequency|most (?:frequently|commonly) purchased items|top selling items|best-selling products|items that sell the most|most popular products|frequently bought products|best selling categories|products purchased the most|what products sell the most|which are the top-selling products',
            'customer_purchase_frequency_distribution': r'customer purchase frequency(?: distribution)?|distribution of customers by purchase frequency|how often customers (?:buy|purchase)|buying frequency|repeat customer frequency|customer repeat purchases?|customer buying habits|customer purchase cycles|how many times customers buy|average purchase frequency|customers\' buying pattern|what\'s the frequency of customer purchases',
            'quantity_vs_price_relationship': r'quantity vs\.? price( relationship)?|relationship between quantity and price|price-quantity correlation|how price affects quantity ordered|relationship of price to quantity|price sensitivity vs quantity|impact of price on quantity|quantity ordered in relation to price|effect of price on sales volume',
            'product_line_performance': r'product line performance|sales by product line|product category performance|product sales comparison by line|how are product lines performing?|performance of different product categories|compare product line sales|product lines sales analysis',
            'order_status_distribution': r'order status distribution|proportion of orders by status|breakdown of order statuses|status of current orders|what\'s the distribution of order statuses?|order processing status breakdown|order fulfillment status|order statuses overview',
            #'greetings': r'hi|hello|hey|greetings|good (morning|afternoon|evening)|how are you?|what\'s up|what can you do?|introduce yourself|start conversation|help me with my data'
         }
    def process_query(self, insight_id: str, query: str) -> str:
        insight = Insight.query.get(insight_id)
        if not insight:
            return "I'm sorry, I couldn't find the data for this insight."

        intent = self.identify_intent(query)
        response = self.generate_response(intent, insight, query)

        chat_message = ChatMessage(
            insight_id=insight.id,
            user_message=query,
            bot_response=response
        )
        db.session.add(chat_message)
        db.session.commit()

        return response

    def identify_intent(self, query: str) -> str:
        for intent, pattern in self.intents.items():
            if re.search(pattern, query, re.IGNORECASE):
                return intent
        return 'unknown'

    def generate_response(self, intent: str, insight: Insight, query: str) -> str:
        analysis_data = insight.get_analysis_data()
        
        response_functions = {
            'monthly_sales_trend': self.monthly_sales_trend_response,
            'sales_over_time': self.sales_over_time_response,
            'customer_segments_distribution': self.customer_segments_distribution_response,
            'top_items_by_frequency': self.top_items_by_frequency_response,
            'customer_purchase_frequency_distribution': self.customer_purchase_frequency_distribution_response,
            'quantity_vs_price_relationship': self.quantity_vs_price_relationship_response,
            'product_line_performance': self.product_line_performance_response,
            'order_status_distribution': self.order_status_distribution_response,
            'greetings': self.greetings_response
        }

        if intent in response_functions:
            return response_functions[intent](analysis_data, query)
        
        return self.unknown_intent_response(query)
   
    def monthly_sales_trend_response(self, data: Dict[str, Any], query: str) -> str:
        monthly_sales_data = data.get('monthlySales', [])
        if not monthly_sales_data:
            return "I'm sorry, I don't have enough data to provide a summary of the monthly sales trend."

        sales_counts = [item['count'] for item in monthly_sales_data]
        total_sales = sum(sales_counts)
        avg_monthly_sales = total_sales / len(monthly_sales_data)

        max_sales_month = max(monthly_sales_data, key=lambda x: x['count'])
        min_sales_month = min(monthly_sales_data, key=lambda x: x['count'])

        if len(monthly_sales_data) >= 2:
            first_month_sales = monthly_sales_data[0]['count']
            last_month_sales = monthly_sales_data[-1]['count']
            sales_growth_percentage = ((last_month_sales - first_month_sales) / first_month_sales) * 100
        else:
            sales_growth_percentage = None

        response = "Monthly Sales Trend Analysis:\n\n"

        response += f"1. Overall Trend: "
        if sales_growth_percentage is not None:
            if sales_growth_percentage > 5:
                response += f"Strong growth ({sales_growth_percentage:.1f}% increase)\n"
            elif sales_growth_percentage > 0:
                response += f"Slight growth ({sales_growth_percentage:.1f}% increase)\n"
            elif sales_growth_percentage < -5:
                response += f"Significant decline ({abs(sales_growth_percentage):.1f}% decrease)\n"
            elif sales_growth_percentage < 0:
                response += f"Slight decline ({abs(sales_growth_percentage):.1f}% decrease)\n"
            else:
                response += "Stable sales (no significant change)\n"
        else:
            response += "Insufficient data for trend analysis\n"

        response += f"2. Peak Performance: {max_sales_month['Date']} ({max_sales_month['count']:,} sales)\n"
        response += f"3. Lowest Performance: {min_sales_month['Date']} ({min_sales_month['count']:,} sales)\n"

        seasonality = self.detect_seasonality(sales_counts)
        response += f"4. Seasonality: {seasonality}\n"

        response += "5. Recent Trend: "
        if len(monthly_sales_data) >= 3:
            latest_months = monthly_sales_data[-3:]
            latest_sales = [item['count'] for item in latest_months]
            if all(latest_sales[i] < latest_sales[i+1] for i in range(len(latest_sales)-1)):
                response += "Upward trajectory in the last 3 months\n"
            elif all(latest_sales[i] > latest_sales[i+1] for i in range(len(latest_sales)-1)):
                response += "Downward trajectory in the last 3 months\n"
            else:
                response += "Fluctuating sales in the last 3 months\n"
        else:
            response += "Insufficient data for recent trend analysis\n"

        response += "\nInsights and Recommendations:\n"
        response += f"- The average monthly sales is {avg_monthly_sales:,.0f}. Months below this might need attention.\n"
        response += f"- Focus on replicating strategies from {max_sales_month['Date']} in other months.\n"
        response += f"- Investigate factors contributing to low sales in {min_sales_month['Date']} to prevent future dips.\n"
        if seasonality != "No clear seasonality detected":
            response += "- Plan inventory and marketing campaigns according to the observed seasonality.\n"
        response += "- Continue monitoring the recent sales trend to adapt strategies promptly.\n"

        return response

    def detect_seasonality(self, sales_data):
        if len(sales_data) < 12:
            return "Insufficient data to detect seasonality"
        
        # Simple seasonality detection - compare same month across years
        yearly_diffs = [abs(sales_data[i] - sales_data[i-12]) for i in range(12, len(sales_data))]
        avg_yearly_diff = sum(yearly_diffs) / len(yearly_diffs)
        
        if avg_yearly_diff < 0.1 * sum(sales_data) / len(sales_data):
            return "Strong seasonal pattern detected"
        elif avg_yearly_diff < 0.2 * sum(sales_data) / len(sales_data):
            return "Moderate seasonal pattern detected"
        else:
            return "No clear seasonality detected"
   
    def sales_over_time_response(self, data: Dict[str, Any], query: str) -> str:
        sales_data = data.get('salesOverTime', [])
        if not sales_data:
            return "I'm sorry, I don't have the sales over time data at the moment."

        total_sales = sum(item['SALES'] for item in sales_data)
        avg_sales = total_sales / len(sales_data)
        max_sales = max(sales_data, key=lambda x: x['SALES'])
        min_sales = min(sales_data, key=lambda x: x['SALES'])

        # Calculate overall trend
        first_sales = sales_data[0]['SALES']
        last_sales = sales_data[-1]['SALES']
        overall_trend = (last_sales - first_sales) / first_sales * 100

        response = "Sales Over Time Analysis:\n\n"
        response += f"1. Total Sales: ${total_sales:,.2f}\n"
        response += f"2. Average Daily Sales: ${avg_sales:,.2f}\n"
        response += f"3. Peak Performance: {max_sales['ORDERDATE']} (${max_sales['SALES']:,.2f})\n"
        response += f"4. Lowest Performance: {min_sales['ORDERDATE']} (${min_sales['SALES']:,.2f})\n"

        response += "5. Overall Trend: "
        if overall_trend > 10:
            response += f"Strong upward trend ({overall_trend:.1f}% increase)\n"
        elif overall_trend > 0:
            response += f"Slight upward trend ({overall_trend:.1f}% increase)\n"
        elif overall_trend < -10:
            response += f"Strong downward trend ({abs(overall_trend):.1f}% decrease)\n"
        elif overall_trend < 0:
            response += f"Slight downward trend ({abs(overall_trend):.1f}% decrease)\n"
        else:
            response += "Stable sales (no significant change)\n"

        # Analyze recent trend
        if len(sales_data) >= 7:
            recent_sales = [item['SALES'] for item in sales_data[-7:]]
            recent_trend = sum(recent_sales) / 7
            response += "6. Recent Trend (Last 7 days): "
            if recent_trend > avg_sales * 1.1:
                response += "Significantly above average\n"
            elif recent_trend > avg_sales:
                response += "Above average\n"
            elif recent_trend < avg_sales * 0.9:
                response += "Significantly below average\n"
            elif recent_trend < avg_sales:
                response += "Below average\n"
            else:
                response += "In line with overall average\n"
        else:
            response += "6. Recent Trend: Insufficient data for recent trend analysis\n"

        response += "\nInsights and Recommendations:\n"
        response += f"- The sales variability (difference between highest and lowest sales) is ${max_sales['SALES'] - min_sales['SALES']:,.2f}. "
        response += "High variability might indicate inconsistent performance or seasonal effects.\n"
        response += f"- Investigate factors contributing to peak sales on {max_sales['ORDERDATE']} for potential replication.\n"
        response += f"- Analyze reasons for low sales on {min_sales['ORDERDATE']} to prevent future dips.\n"
        if overall_trend < 0:
            response += "- Develop strategies to reverse the overall downward trend in sales.\n"
        elif overall_trend > 0:
            response += "- Capitalize on the positive trend by reinforcing successful sales strategies.\n"
        response += "- Continue monitoring recent trends to quickly adapt to changes in sales patterns.\n"

        return response
    
    def customer_segments_distribution_response(self, data: Dict[str, Any], query: str) -> str:
        segments_data = data.get('customerSegments', {})
        if not segments_data:
            return "I'm sorry, I don't have the customer segments distribution data at the moment."

        total_customers = sum(segments_data.values())
        sorted_segments = sorted(segments_data.items(), key=lambda x: x[1], reverse=True)

        response = "Customer Segmentation Analysis:\n\n"

        # Top and bottom segments
        response += f"1. Dominant Segment: {sorted_segments[0][0]} ({sorted_segments[0][1]} customers, {sorted_segments[0][1]/total_customers*100:.1f}%)\n"
        response += f"2. Smallest Segment: {sorted_segments[-1][0]} ({sorted_segments[-1][1]} customers, {sorted_segments[-1][1]/total_customers*100:.1f}%)\n"

        # Segment diversity
        response += f"3. Total Segments: {len(segments_data)}\n"

        # High-value segments
        high_value_segments = [seg for seg in sorted_segments if 'high' in seg[0].lower()]
        high_value_customers = sum(count for _, count in high_value_segments)
        response += f"4. High-Value Segments: {len(high_value_segments)} segments, {high_value_customers/total_customers*100:.1f}% of customers\n"

        # Segment concentration
        top_two_percentage = (sorted_segments[0][1] + sorted_segments[1][1]) / total_customers * 100
        response += f"5. Concentration: Top 2 segments represent {top_two_percentage:.1f}% of customers\n"

        response += "\nInsights and Recommendations:\n"
        
        if top_two_percentage > 70:
            response += "- High concentration in top segments. Consider strategies to grow smaller segments.\n"
        else:
            response += "- Relatively balanced distribution. Tailor strategies for each segment's needs.\n"
        
        if high_value_customers/total_customers < 0.2:
            response += "- Low proportion of high-value customers. Implement programs to upgrade customers to higher segments.\n"
        else:
            response += "- Significant high-value customer base. Focus on retention and expanding their share of wallet.\n"
        
        if len(segments_data) > 5:
            response += "- Large number of segments. Consider consolidating for more focused strategies.\n"
        elif len(segments_data) < 3:
            response += "- Few segments. Explore opportunities for more granular segmentation.\n"
        
        response += f"- Develop targeted marketing and service strategies for the dominant {sorted_segments[0][0]} segment.\n"
        response += f"- Investigate the {sorted_segments[-1][0]} segment to understand its unique characteristics and growth potential.\n"

        return response

    def top_items_by_frequency_response(self, data: Dict[str, Any], query: str) -> str:
        item_frequency_data = data.get('itemFrequency', {})
        if not item_frequency_data:
            return "I'm sorry, I don't have enough data to provide insights on the top items by frequency."

        sorted_items = sorted(item_frequency_data.items(), key=lambda x: x[1], reverse=True)
        top_items = sorted_items[:5]
        total_frequency = sum(item_frequency_data.values())

        response = "Top Items Analysis:\n\n"

        # Top 5 items
        response += "1. Top 5 Most Frequently Purchased Items:\n"
        for i, (item, frequency) in enumerate(top_items, 1):
            percentage = (frequency / total_frequency) * 100
            response += f"   {i}. {item}: {frequency} purchases ({percentage:.1f}% of total)\n"

        # Concentration of top items
        top_5_frequency = sum(freq for _, freq in top_items)
        top_5_percentage = (top_5_frequency / total_frequency) * 100
        response += f"\n2. Top 5 Items Concentration: {top_5_percentage:.1f}% of total purchases\n"

        # Diversity of product mix
        unique_items = len(item_frequency_data)
        response += f"3. Product Diversity: {unique_items} unique items\n"

        # Long tail analysis
        long_tail_items = len([item for item, freq in sorted_items if freq < total_frequency * 0.01])
        long_tail_percentage = (long_tail_items / unique_items) * 100
        response += f"4. Long Tail: {long_tail_percentage:.1f}% of items account for < 1% of purchases each\n"

        # Purchase frequency drop-off
        if len(sorted_items) > 5:
            drop_off = (top_items[-1][1] - sorted_items[5][1]) / top_items[-1][1] * 100
            response += f"5. Top 5 Drop-off: {drop_off:.1f}% decrease to 6th most frequent item\n"

        response += "\nInsights and Recommendations:\n"

        if top_5_percentage > 50:
            response += "- High concentration in top items. Ensure sufficient stock and prominent placement.\n"
        else:
            response += "- Diverse purchasing patterns. Consider bundling strategies for less popular items.\n"

        if long_tail_percentage > 70:
            response += "- Large 'long tail' of infrequently purchased items. Review inventory of slow-moving products.\n"
        
        if drop_off > 30:
            response += "- Significant drop-off after top items. Focus marketing efforts on top performers.\n"
        else:
            response += "- Gradual frequency decrease. Balanced approach to product promotion recommended.\n"

        response += f"- Analyze characteristics of top-selling item '{top_items[0][0]}' for insights into customer preferences.\n"
        response += "- Regular review of this analysis can inform inventory management and marketing strategies.\n"

        return response

    def customer_purchase_frequency_distribution_response(self, data: Dict[str, Any], query: str) -> str:
        frequency_data = data.get('customerFrequency', {})
        if not frequency_data:
            return "I'm sorry, I don't have the customer purchase frequency distribution data at the moment."

        total_customers = sum(frequency_data.values())
        sorted_frequency = sorted(frequency_data.items(), key=lambda x: int(x[0]))

        response = "Customer Purchase Frequency Analysis:\n\n"

        # Most common purchase frequency
        most_common = max(frequency_data.items(), key=lambda x: x[1])
        response += f"1. Most Common Frequency: {most_common[0]} purchases ({most_common[1]} customers, {most_common[1]/total_customers*100:.1f}%)\n"

        # Average purchase frequency
        avg_frequency = sum(int(freq) * count for freq, count in frequency_data.items()) / total_customers
        response += f"2. Average Purchase Frequency: {avg_frequency:.2f} purchases\n"

        # Customer loyalty breakdown
        low_freq = sum(count for freq, count in frequency_data.items() if int(freq) <= 2)
        med_freq = sum(count for freq, count in frequency_data.items() if 2 < int(freq) <= 5)
        high_freq = sum(count for freq, count in frequency_data.items() if int(freq) > 5)
        response += f"3. Customer Loyalty: Low (1-2): {low_freq/total_customers*100:.1f}%, Medium (3-5): {med_freq/total_customers*100:.1f}%, High (6+): {high_freq/total_customers*100:.1f}%\n"

        # Frequency range
        min_freq, max_freq = int(sorted_frequency[0][0]), int(sorted_frequency[-1][0])
        response += f"4. Frequency Range: {min_freq} to {max_freq} purchases\n"

        # Repeat customer rate
        repeat_rate = (total_customers - frequency_data.get('1', 0)) / total_customers * 100
        response += f"5. Repeat Customer Rate: {repeat_rate:.1f}%\n"

        response += "\nInsights and Recommendations:\n"

        if repeat_rate < 50:
            response += "- Low repeat customer rate. Focus on customer retention strategies.\n"
        else:
            response += "- Strong repeat customer base. Implement loyalty programs to further increase retention.\n"

        if high_freq/total_customers < 0.2:
            response += "- Small proportion of high-frequency customers. Develop strategies to increase purchase frequency.\n"
        else:
            response += "- Significant high-frequency customer base. Analyze and replicate success factors.\n"

        if avg_frequency < 3:
            response += "- Low average purchase frequency. Investigate barriers to repeat purchases.\n"
        elif avg_frequency > 5:
            response += "- High average purchase frequency. Ensure stock levels meet demand and consider bulk purchase incentives.\n"

        response += f"- Tailor marketing strategies for different frequency segments (e.g., reactivation for low, upselling for medium, retention for high).\n"
        response += "- Regularly analyze this distribution to track the effectiveness of customer engagement initiatives.\n"

        return response
     
    def quantity_vs_price_relationship_response(self, data: Dict[str, Any], query: str) -> str:
        quantity_price_data = data.get('quantityVsPrice', [])
        if not quantity_price_data:
            return "I'm sorry, I don't have the quantity vs price relationship data at the moment."

        total_items = len(quantity_price_data)
        prices = [item['PRICEEACH'] for item in quantity_price_data]
        quantities = [item['QUANTITYORDERED'] for item in quantity_price_data]

        avg_price = np.mean(prices)
        avg_quantity = np.mean(quantities)
        median_price = np.median(prices)
        median_quantity = np.median(quantities)

        correlation, _ = stats.pearsonr(prices, quantities)

        response = "Quantity vs Price Relationship Analysis:\n\n"

        response += f"1. Sample Size: {total_items} items\n"
        response += f"2. Average Price: ${avg_price:.2f} (Median: ${median_price:.2f})\n"
        response += f"3. Average Quantity: {avg_quantity:.2f} (Median: {median_quantity:.2f})\n"
        response += f"4. Price-Quantity Correlation: {correlation:.2f}\n"

        # Price elasticity of demand (simple calculation)
        high_price = np.percentile(prices, 75)
        low_price = np.percentile(prices, 25)
        high_quantity = np.mean([q for p, q in zip(prices, quantities) if p >= high_price])
        low_quantity = np.mean([q for p, q in zip(prices, quantities) if p <= low_price])
        
        elasticity = ((high_quantity - low_quantity) / low_quantity) / ((high_price - low_price) / low_price)
        response += f"5. Estimated Price Elasticity: {abs(elasticity):.2f}\n"

        response += "\nInsights and Recommendations:\n"

        if correlation < -0.5:
            response += "- Strong negative relationship: Higher prices are associated with lower quantities ordered.\n"
            response += "- Consider promotional pricing or volume discounts to increase sales.\n"
        elif correlation > 0.5:
            response += "- Strong positive relationship: Higher prices are associated with higher quantities ordered.\n"
            response += "- This unusual pattern might indicate luxury goods or bundled products. Investigate further.\n"
        else:
            response += "- Weak price-quantity relationship: Other factors may be more influential in determining order quantities.\n"
            response += "- Focus on non-price factors (e.g., quality, marketing) to influence sales.\n"

        if abs(elasticity) > 1:
            response += f"- Demand is elastic (elasticity > 1). Price changes have a significant impact on quantity demanded.\n"
            response += "- Be cautious with price increases; consider strategies to reduce price sensitivity.\n"
        else:
            response += f"- Demand is inelastic (elasticity < 1). Quantity demanded is less sensitive to price changes.\n"
            response += "- There may be opportunity to optimize pricing for revenue without significantly impacting demand.\n"

        if median_price < avg_price:
            response += "- Price distribution is right-skewed. A few high-priced items are pulling up the average.\n"
            response += "- Analyze these high-priced items separately to understand their impact on overall sales.\n"

        if median_quantity < avg_quantity:
            response += "- Quantity distribution is right-skewed. There are some large-volume orders influencing the average.\n"
            response += "- Consider strategies to encourage more large-volume orders across the customer base.\n"

        response += "\nNote: This analysis provides general insights. For more accurate pricing strategies, consider additional factors such as product categories, customer segments, and market conditions."

        return response

    def product_line_performance_response(self, data: Dict[str, Any], query: str) -> str:
        sales_data = data.get('salesData', [])
        if not sales_data:
            return "I'm sorry, I don't have the product line performance data at the moment."

        total_sales = sum(item['SALES'] for item in sales_data)
        sorted_data = sorted(sales_data, key=lambda x: x['SALES'], reverse=True)

        response = "Product Line Performance Analysis:\n\n"

        # Top and bottom performers
        response += f"1. Top Performer: {sorted_data[0]['PRODUCTLINE']} (${sorted_data[0]['SALES']:,.2f}, {sorted_data[0]['SALES']/total_sales*100:.1f}% of total)\n"
        response += f"2. Bottom Performer: {sorted_data[-1]['PRODUCTLINE']} (${sorted_data[-1]['SALES']:,.2f}, {sorted_data[-1]['SALES']/total_sales*100:.1f}% of total)\n"

        # Sales concentration
        top_two_sales = sorted_data[0]['SALES'] + sorted_data[1]['SALES']
        response += f"3. Top 2 Product Lines: {top_two_sales/total_sales*100:.1f}% of total sales\n"

        # Performance spread
        performance_spread = sorted_data[0]['SALES'] / sorted_data[-1]['SALES']
        response += f"4. Performance Spread: Top performer outsells bottom by {performance_spread:.1f}x\n"

        # Average product line sales
        avg_sales = total_sales / len(sales_data)
        response += f"5. Average Product Line Sales: ${avg_sales:,.2f}\n"

        response += "\nDetailed Product Line Breakdown:\n"
        for item in sorted_data:
            percentage = (item['SALES'] / total_sales) * 100
            performance = "Above Average" if item['SALES'] > avg_sales else "Below Average"
            response += f"- {item['PRODUCTLINE']}: ${item['SALES']:,.2f} ({percentage:.1f}%, {performance})\n"

        response += "\nInsights and Recommendations:\n"

        if top_two_sales / total_sales > 0.7:
            response += "- High concentration in top product lines. Consider diversifying to reduce risk.\n"
        else:
            response += "- Balanced sales across product lines. Continue to monitor and optimize each line.\n"

        if performance_spread > 10:
            response += f"- Large performance gap. Investigate reasons for {sorted_data[-1]['PRODUCTLINE']}'s underperformance.\n"
        else:
            response += "- Relatively even performance across lines. Focus on incremental improvements.\n"

        above_avg = sum(1 for item in sales_data if item['SALES'] > avg_sales)
        if above_avg <= len(sales_data) / 3:
            response += "- Few product lines performing above average. Consider reallocating resources to top performers.\n"
        elif above_avg >= 2 * len(sales_data) / 3:
            response += "- Most product lines performing well. Look for opportunities to further capitalize on strengths.\n"

        response += f"- Analyze success factors of {sorted_data[0]['PRODUCTLINE']} for potential application to other lines.\n"
        response += f"- Develop targeted strategies to improve {sorted_data[-1]['PRODUCTLINE']} performance or consider phasing out.\n"
        response += "- Regularly review this analysis to track changes in product line performance and adjust strategies accordingly.\n"

        return response

    def order_status_distribution_response(self, data: Dict[str, Any], query: str) -> str:
        status_data = data.get('orderStatus', [])
        if not status_data:
            return "I'm sorry, I don't have the order status distribution data at the moment."

        total_orders = sum(item['count'] for item in status_data)
        sorted_data = sorted(status_data, key=lambda x: x['count'], reverse=True)

        response = "Order Status Distribution Analysis:\n\n"

        # Most common status
        response += f"1. Most Common Status: {sorted_data[0]['STATUS']} ({sorted_data[0]['count']} orders, {sorted_data[0]['count']/total_orders*100:.1f}%)\n"

        # Least common status
        response += f"2. Least Common Status: {sorted_data[-1]['STATUS']} ({sorted_data[-1]['count']} orders, {sorted_data[-1]['count']/total_orders*100:.1f}%)\n"

        # Completed orders (assuming 'Shipped' or 'Delivered' indicates completion)
        completed_statuses = ['Shipped', 'Delivered']
        completed_orders = sum(item['count'] for item in status_data if item['STATUS'] in completed_statuses)
        completion_rate = completed_orders / total_orders * 100
        response += f"3. Order Completion Rate: {completion_rate:.1f}%\n"

        # Problematic orders (assuming 'Cancelled', 'Disputed', or 'On Hold' are problematic)
        problematic_statuses = ['Cancelled', 'Disputed', 'On Hold']
        problematic_orders = sum(item['count'] for item in status_data if item['STATUS'] in problematic_statuses)
        problem_rate = problematic_orders / total_orders * 100
        response += f"4. Problematic Order Rate: {problem_rate:.1f}%\n"

        # In-process orders (assuming 'In Process' or 'Pending' are in-process)
        in_process_statuses = ['In Process', 'Pending']
        in_process_orders = sum(item['count'] for item in status_data if item['STATUS'] in in_process_statuses)
        in_process_rate = in_process_orders / total_orders * 100
        response += f"5. In-Process Order Rate: {in_process_rate:.1f}%\n"

        response += "\nDetailed Status Breakdown:\n"
        for item in sorted_data:
            percentage = (item['count'] / total_orders) * 100
            response += f"- {item['STATUS']}: {item['count']} orders ({percentage:.1f}%)\n"

        response += "\nInsights and Recommendations:\n"

        if completion_rate < 80:
            response += "- Low order completion rate. Investigate bottlenecks in the order fulfillment process.\n"
        else:
            response += "- Healthy order completion rate. Continue to optimize the fulfillment process.\n"

        if problem_rate > 10:
            response += "- High rate of problematic orders. Analyze reasons for cancellations, disputes, and holds.\n"
        else:
            response += "- Acceptable rate of problematic orders. Monitor closely to maintain or improve.\n"

        if in_process_rate > 30:
            response += "- Large proportion of in-process orders. Check for delays in order processing.\n"
        elif in_process_rate < 10:
            response += "- Low in-process rate. Ensure this doesn't indicate understocking or fulfillment issues.\n"

        most_common_status = sorted_data[0]['STATUS']
        if most_common_status not in completed_statuses:
            response += f"- Most common status is '{most_common_status}'. Focus on moving these orders to completion.\n"

        response += "- Regularly review this distribution to identify trends and improve order processing efficiency.\n"
        response += "- Consider implementing customer communication strategies for orders in problematic statuses.\n"
        response += "- Use this data to forecast resource needs in different stages of the order fulfillment process.\n"

        return response

    def greetings_response(self, data: Dict[str, Any], query: str) -> str:
        return (
            "Hello! I'm here to help you analyze your business data. "
            "What would you like to know about? I can provide insights on sales trends, "
            "customer behavior, product performance, and more. Just ask!"
        )

    def unknown_intent_response(self, query: str) -> str:
        return (
            "I apologize, but I'm not sure I understood your query. To help you best, "
            "I can provide insights on the following topics:\n\n"
            "1. Sales Analysis:\n"
            "   - Monthly sales trends\n"
            "   - Product line performance\n"
            "   - Top selling items\n\n"
            "2. Customer Insights:\n"
            "   - Customer segmentation\n"
            "   - Purchase frequency distribution\n\n"
            "3. Product Analysis:\n"
            "   - Quantity vs price relationship\n\n"
            "4. Order Management:\n"
            "   - Order status distribution\n\n"
            "Could you please rephrase your question or choose one of these topics? "
            "For example, you could ask:\n"
            "- What are our monthly sales trends?\n"
            "- What's our customer purchase frequency distribution?\n"
            "- Can you explain the relationship between quantity and price?\n"
            "- What are our monthly sales trends?\n"
            "- What's the current order status distribution?\n\n" 
            "I'm here to provide detailed analysis and actionable insights based on your sales data!"
        
        )