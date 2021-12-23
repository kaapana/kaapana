# flask_sqlalchemy/schema_dicom.py
import graphene
import graphql.execution.base
from graphene import relay
from graphene_sqlalchemy import SQLAlchemyObjectType, SQLAlchemyConnectionField
from .model import KaapanaNode as KaapanaNodeModel, DataEntity as DataEntityModel
from .model_dicom import DicomPatient as PatientModel, DicomStudy as StudyModel, DicomSeries as SeriesModel
from .model_permission import Access as AccessModel
from .model_raw import Dataset as DatasetModel, File as FileModel, Experiment as ExperimentModel
from .schema_dicom import Query as DicomQuery
class KaapanaNode(SQLAlchemyObjectType):
    class Meta:
        model = KaapanaNodeModel
        interfaces = (relay.Node, )

class DataEntity(SQLAlchemyObjectType):
    class Meta:
        model = DataEntityModel
        interfaces = (relay.Node, )

class Dataset(SQLAlchemyObjectType):
    class Meta:
        model = DatasetModel
        interfaces = (relay.Node, )

class File(SQLAlchemyObjectType):
    class Meta:
        model = FileModel
        interfaces = (relay.Node, )

class Expermiment(SQLAlchemyObjectType):
    class Meta:
        model = ExperimentModel
        interfaces = (relay.Node, )

class Query(DicomQuery, graphene.ObjectType):
    get_access = graphene.List(DataEntity, access=graphene.String())
    def resolve_get_access(self, info: graphql.execution.base.ResolveInfo, access):
        query = DataEntity.get_query(info)
        data_entity = query.join(DataEntityModel.accesses).filter(
            AccessModel.group == access).all()

        return data_entity

from .mutation import MyMutation
schema = graphene.Schema(query=Query, mutation=MyMutation)



