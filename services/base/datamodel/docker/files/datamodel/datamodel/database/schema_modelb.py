import graphene
import graphql.execution.base
from graphene import relay
from graphene_sqlalchemy import SQLAlchemyObjectType, SQLAlchemyConnectionField
from .modelB import DataEntityB as DataEntityBModel, Collection as CollectionModel, Link as LinkModel


class DataEntityB(SQLAlchemyObjectType):
    class Meta:
        model = DataEntityBModel
        fields = ("__all__")
        interfaces = (relay.Node, )

class Collection(SQLAlchemyObjectType):
    class Meta:
        model = CollectionModel
        fields = ("__all__")
        interfaces = (relay.Node, )

class Link(SQLAlchemyObjectType):
    class Meta:
        model = LinkModel
        fields = ("__all__")
        interfaces = (relay.Node, )

class Query(graphene.ObjectType):
    node = relay.Node.Field()
    get_dataentityb= graphene.List(DataEntityB)
    def resolve_get_dataentityb(self, info): #, type: str=None):
        query = DataEntityB.get_query(info)  # SQLAlchemy query
        return query.all()