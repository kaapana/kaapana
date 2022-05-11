import requests
from fastapi import Depends, FastAPI, Request
from datamodel import DM
from datamodel.database.schema import schema
from strawberry.fastapi import GraphQLRouter
from .routers import importer

app = FastAPI()
DM.init_db()

app.include_router(importer.router)

graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")


