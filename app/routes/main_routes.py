from . import main_bp
from flask import jsonify

@main_bp.route('/')
def hello_world():
    return jsonify({"message": "Hello, World!"})

@main_bp.route('/api/v1/example')
def example_endpoint():
    return jsonify({"data": "This is an example endpoint"})