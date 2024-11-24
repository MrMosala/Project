from datetime import datetime
import os
from uuid import UUID
from logging_config import default_logger as logger
from sqlalchemy import Date, cast, func
from app.models.operational import Insight
from app.models.archive import ArchivedInsight
from app.services.file_service import (
    create_insight, add_file_to_insight, get_existing_insight, get_file_hash, 
    get_file_size, get_file_type, process_files, save_file, get_all_insights,
    FileProcessingError, DataValidationError
)
from . import file_bp
from flask import Blueprint, current_app, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest, NotFound, InternalServerError
from app.services.auth_service import get_user_subscription

ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@file_bp.route('/')
def hello_world():
    return jsonify({"message": "Hello, World!"})

@file_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    if 'files' not in request.files:
        raise BadRequest("No file part in the request")
    
    files = request.files.getlist('files')
    if not files or all(file.filename == '' for file in files):
        raise BadRequest("No selected files")
       
    insight_id = request.form.get('insight_id', None) 


    should_create_insight = request.form.get('create_insight', 'false').lower() == 'true'
     
    current_user_id = get_jwt_identity()
    
    try: 
        if should_create_insight:
            print("should_create_insight")
            subscription = get_user_subscription(current_user_id)
            subscription_type = subscription.PlanName if subscription else None

            def get_insight_limit(subscription_type):
                if subscription_type == 'Basic':
                    return 2
                elif subscription_type == 'Pro':
                    return 5
                elif subscription_type == 'Enterprise':
                    return 10
                else:
                    return 1
        
            insight_limit = get_insight_limit(subscription)
            today = datetime.utcnow().date()
            insights_today = Insight.query.filter( Insight.user_id == current_user_id, cast(Insight.created_at, Date) == today).count()
            if insights_today >= insight_limit:
                raise BadRequest(f"Insight limit reached for today. Your plan allows {insight_limit} insights per day.")
            else:
                insight = create_insight(current_user_id)
        elif insight_id: 
            insight = Insight.query.get(insight_id)
        else: 
            today = datetime.utcnow().date()
            insight = get_existing_insight(current_user_id, today)
            if not insight:
                insight = create_insight(current_user_id)
        
        file_results = []
        print(insight)
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = save_file(file, filename, current_app.config['UPLOAD_FOLDER'])
                file_size = get_file_size(file_path)
                file_type = get_file_type(filename)
                file_hash = get_file_hash(file_path)
                
                file_record, is_duplicate = add_file_to_insight(
                    insight.id, filename, file_path, current_user_id, file_size, file_type, file_hash
                )

                if is_duplicate:
                    file_results.append({
                        "filename": filename,
                        "status": "duplicate",
                        "message": "File already exists and was not uploaded."
                    })
                else:
                    file_results.append({
                        "filename": filename,
                        "status": "uploaded",
                        "message": "File successfully uploaded and added to the insight."
                    })
            else:
                file_results.append({
                    "filename": file.filename,
                    "status": "error",
                    "message": "Invalid file type."
                })
        
         
        return jsonify({
            'message': 'Files processed',
            'insight_id': str(insight.id),
            'file_results': file_results
        }), 200
    except FileProcessingError as e:
        logger.error(f"File processing error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e: 
        logger.error(f"Unexpected error in file upload: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred during file upload'}), 500

@file_bp.route('/insight/<uuid:insight_id>', methods=['GET'])
@jwt_required()
def get_insight(insight_id):
    current_user_id = get_jwt_identity()
    insight = Insight.query.get(insight_id)
    
    if not insight:
        raise NotFound("Insight not found")
    if str(insight.user_id) != str(current_user_id): 
        raise BadRequest("You don't have permission to access this insight")
 
    return jsonify(insight.to_dict()), 200

@file_bp.route('/insights', methods=['GET'])
@jwt_required()
def get_insights():
    try:
        current_user_id = get_jwt_identity()
        insights = get_all_insights(current_user_id)
        return jsonify([ insight.to_dict() for insight in insights]), 200
    except Exception as e:
        logger.error(f"Error fetching insights: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching insights'}), 500
    
@file_bp.route('/insights/today', methods=['GET'])
@jwt_required()
def get_todays_insights():
    current_user_id = get_jwt_identity()
    today = datetime.utcnow().date()
    print("today", today)
    insights = Insight.query.filter(
        Insight.user_id == current_user_id,
        cast(Insight.created_at, Date) == today
    ).order_by(Insight.created_at.desc()).first()
    
    if not insights:
        raise NotFound("No insights found for today")
    
    insight = Insight.query.get(insights.id)
     
    return jsonify(insight.to_dict()), 200

@file_bp.route('/insights/previous', methods=['GET'])
@jwt_required()
def get_previous_insights():
    current_user_id = get_jwt_identity()
    today = datetime.utcnow()
    
    insights = Insight.query.filter(
        Insight.user_id == current_user_id,
        cast(Insight.created_at, Date)  < today
    ).order_by(Insight.created_at.desc()).all()
    
    return jsonify([insight.to_dict() for insight in insights]), 200

@file_bp.route('/insights/archived', methods=['GET'])
@jwt_required()
def get_archived_insights():
    current_user_id = get_jwt_identity()
    
    try:
        archived_insights = ArchivedInsight.query.filter(
            ArchivedInsight.user_id == current_user_id, 
        ).order_by(ArchivedInsight.created_at.desc()).all()
          
        return jsonify([insight.to_dict() for insight in archived_insights]), 200
    except Exception as e:
        logger.error(f"Error fetching archived insights: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching archived insights'}), 500

@file_bp.route('/insights/unarchive/<string:insight_id>', methods=['POST'])
@jwt_required()
def unarchive_insight(insight_id):
    current_user_id = get_jwt_identity()
    
    try:
        from app.services.archive_service import unarchive_insight as unarchive_insight_service
        
        new_insight = unarchive_insight_service(insight_id)
        
        if not new_insight:
            return jsonify({"error": "Failed to unarchive insight"}), 400
        
        return jsonify({"message": "Insight unarchived successfully", "new_insight_id": str(new_insight.id)}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Error unarchiving insight: {str(e)}")
        return jsonify({'error': 'An error occurred while unarchiving the insight'}), 500

@file_bp.route('/insights/archived/<string:insight_id>', methods=['GET'])
@jwt_required()
def get_archived_insight(insight_id):
    current_user_id = get_jwt_identity()
    
    try:
        archived_insight = ArchivedInsight.query.filter_by(
            id=insight_id,
            user_id=current_user_id
        ).first()
        
        if not archived_insight:
            return jsonify({"error": "Archived insight not found"}), 404
        
        return jsonify(archived_insight.to_dict()), 200
    except Exception as e: 
        logger.error(f"Error fetching archived insight: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching the archived insight'}), 500


@file_bp.route('/process', methods=['POST'])
@jwt_required()
def process_file():
    file_id = request.json.get('file_id')
    insight_id = request.json.get('insight_id')
     
    if not file_id:
        raise BadRequest("No file ID provided")
    if not insight_id:
        raise BadRequest("No insight ID provided")
    
    try: 
        process_files(file_id, insight_id)
        return jsonify({"message": "File processed successfully"}), 200
    except FileProcessingError as e:
        logger.error(f"File processing error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except DataValidationError as e:
        logger.error(f"Data validation error: {str(e)}")
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        logger.error(f"Unexpected error in process_file: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@file_bp.errorhandler(BadRequest)
@file_bp.errorhandler(NotFound)
@file_bp.errorhandler(InternalServerError)
def handle_error(error):
    response = jsonify({"error": str(error)})
    response.status_code = error.code if hasattr(error, 'code') else 500
    return response