from flask import Flask, request, redirect, url_for
from flasgger import Swagger, LazyString, LazyJSONEncoder
from datamodel.Datamodel import KaapanaDatamodel
from datamodel.DatamodelB import KaapanaDatamodelB
app = Flask(__name__)

DM = KaapanaDatamodelB()
DM.setup_db(app)