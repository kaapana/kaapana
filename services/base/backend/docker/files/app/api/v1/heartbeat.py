from flask import jsonify
from . import api_v1
from datetime import datetime

@api_v1.route('/heartbeat')
def beat():
    """Returns the current server time, can be used to check if 
    ---
    responses:
      200:
        description: A list of colors (may be filtered by palette)
        schema:
          $ref: '#/definitions/Palette'
        examples:
          time: '2021-02-01 11:12:13'
    """
    return jsonify({"time": datetime.now().isoformat()})