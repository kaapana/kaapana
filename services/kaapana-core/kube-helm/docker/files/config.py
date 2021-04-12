import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = os.environ['SECRET_KEY']
    APPLICATION_ROOT = os.environ['APPLICATION_ROOT']
    NAMESPACE = 'default'
    HELM_EXTENSIONS_CACHE="/root/charts/extensions"
    HELM_COLLECTIONS_CACHE="/root/charts/collections"
    HELM_HELPERS_CACHE="/root/charts/helpers"
    REGISTRY_URL = os.environ['REGISTRY_URL']