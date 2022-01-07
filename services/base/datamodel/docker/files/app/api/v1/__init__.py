from flask import Blueprint

api_v1 = Blueprint("api_v1", __name__)

from . import datamodelapi