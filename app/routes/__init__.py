from flask import Blueprint

main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
file_bp = Blueprint('file', __name__) 
chatbot_bp = Blueprint('chatbot', __name__)

from . import main_routes
from . import auth_routes
from . import file_routes
from . import chatbot_routes