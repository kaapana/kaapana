from flask import Flask, request, redirect, url_for
from flasgger import Swagger, LazyString, LazyJSONEncoder
from app.api.v1 import api_v1

app = Flask(__name__)

# Reverse Proxy fix for swaggerUI
app.json_encoder = LazyJSONEncoder
template = dict(swaggerUiPrefix=LazyString(lambda : request.environ.get('HTTP_X_SCRIPT_NAME', request.environ.get('SCRIPT_NAME', ''))))
swagger = Swagger(app, template=template)

app.register_blueprint(api_v1, url_prefix='/api/v1')

@app.route('/')
def redirect_to_swagger():
    return redirect(url_for('flasgger.apidocs'))


from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)