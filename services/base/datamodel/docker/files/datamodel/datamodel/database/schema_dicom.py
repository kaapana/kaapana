# flask_sqlalchemy/schema_dicom.py
import graphene
import graphql.execution.base
from graphene import relay
from graphene_sqlalchemy import SQLAlchemyObjectType, SQLAlchemyConnectionField
from .model import KaapanaNode as KaapanaNodeModel, DataEntity as DataEntityModel
from .model_dicom import DicomPatient as PatientModel, DicomStudy as StudyModel, DicomSeries as SeriesModel
from .model_permission import Access as AccessModel


class DicomPatient(SQLAlchemyObjectType):
    class Meta:
        model = PatientModel
        exclude = ("id",)
        interfaces = (relay.Node, )

class Access(SQLAlchemyObjectType):
    class Meta:
        model = AccessModel
        exclude = ("id",)
        interfaces = (relay.Node, )
    group = graphene.String()


class DicomStudy(SQLAlchemyObjectType):
    #has to be added, to search for (many to many relationships)
    accesses = graphene.List(Access)
    class Meta:
        model = StudyModel
        fields = ("__all__")
        interfaces = (relay.Node, )

class DicomSeries(SQLAlchemyObjectType):
    class Meta:
        model = SeriesModel
        fields = ("__all__")
        interfaces = (relay.Node, )

class Query(graphene.ObjectType):
    node = relay.Node.Field()
    study = graphene.Field(DicomStudy)
    get_studies = graphene.List(DicomStudy, access=graphene.String())
    def resolve_get_studies(self, info: graphql.execution.base.ResolveInfo, access):
        query = DicomStudy.get_query(info)
        study_list = query.join(StudyModel.data_entity, DataEntityModel.accesses).filter(AccessModel.group ==access).all()
        return study_list
