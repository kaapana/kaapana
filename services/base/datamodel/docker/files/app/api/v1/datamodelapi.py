from flask import jsonify, request, abort, Response, current_app as app

from . import api_v1
import logging



@api_v1.route('/import_dicom/', methods=['POST'])
def import_dicom():
    content = request.json
    logging.info(content)
    upload = app.datamodel.import_dicom(content)
    if 0 == upload:
        return Response("{'response':'success'}", status=200, mimetype='application/json')
    return Response("{'response':'error'}", status=200, mimetype='application/json')
