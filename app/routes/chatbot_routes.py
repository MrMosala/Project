from flask import jsonify, request
import logging
from uuid import UUID

from app.models.operational import Insight
from app.services.chatbot_service import ChatbotService
from . import chatbot_bp

# Initialize logger
logger = logging.getLogger(__name__)

def is_valid_uuid(uuid_to_test, version=4):
    try:
        uuid_obj = UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test

@chatbot_bp.route('/chatbot/<uuid:insight_id>', methods=['POST'])
def chatbot_query(insight_id):
    data = request.json
    if not data or 'query' not in data:
        return jsonify({'error': 'No query provided'}), 400

    if not is_valid_uuid(str(insight_id)):
        return jsonify({'error': 'Invalid insight_id'}), 400

    chatbot_service = ChatbotService()
    try:
        response = chatbot_service.process_query(str(insight_id), data['query'])
        return jsonify({'response': response}), 200
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return jsonify({'error': str(e)}), 500

@chatbot_bp.route('/chatbot/<uuid:insight_id>/history', methods=['GET'])
def get_chat_history(insight_id):
    if not is_valid_uuid(str(insight_id)):
        return jsonify({'error': 'Invalid insight_id'}), 400

    insight = Insight.query.get(insight_id)
    if not insight:
        return jsonify({'error': 'Insight not found'}), 404

    ChatMessage = insight.ChatMessage if insight.ChatMessage else []
    chat_history = [
        {
            'user_message': msg.user_message,
            'bot_response': msg.bot_response,
            'timestamp': msg.timestamp.isoformat()
        }
        for msg in ChatMessage
    ]

    return jsonify({'chat_history': chat_history}), 200