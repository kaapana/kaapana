from flask import Blueprint

api_v1 = Blueprint("api_v1", __name__)

from . import heartbeat
from . import minio
from . import extensions
from . import monitoring
from . import users
