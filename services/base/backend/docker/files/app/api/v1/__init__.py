from flask import Blueprint

api_v1 = Blueprint("api_v1", __name__)

from . import colors_sample_api
from . import data_example
from . import heartbeat
from . import minio_apis
from . import helm_apis
from . import monitoring
from . import users
