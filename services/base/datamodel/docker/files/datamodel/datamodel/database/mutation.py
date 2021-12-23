import graphene
import graphql
from .model_dicom import DicomStudy as StudyModel
from .schema_dicom import DicomStudy as StudySchema
from ..AccessData import AccessData
from ..Database import DatabaseImporter, Database

class AddAccess(graphene.Mutation):
    class Arguments:
        access_group = graphene.String()
        study_uid = graphene.String()

    ok = graphene.Boolean()

    def mutate(root, info: graphql.execution.base.ResolveInfo, study_uid: str, access_group: str):
        query = StudySchema.get_query(info)
        study = query.filter(StudyModel.study_uid == study_uid).first()
        keycloak_group= AccessData.GetKeycloakGroupModels(access_group)
        DatabaseImporter.add_access(data_entity=study.data_entity,
                                    keycloak_group=keycloak_group)
        Database.commit_to_db()
        ok = True
        return AddAccess(ok=ok)


class RemoveAccess(graphene.Mutation):
    class Arguments:
        access_group = graphene.String()
        study_uid = graphene.String()

    ok = graphene.Boolean()

    def mutate(root, info: graphql.execution.base.ResolveInfo, study_uid: str, access_group: str):
        query = StudySchema.get_query(info)
        study = query.filter(StudyModel.study_uid == study_uid).first()
        keycloak_group= AccessData.GetKeycloakGroupModels(access_group)
        ok = DatabaseImporter.remove_access(study.data_entity, keycloak_group)
        Database.commit_to_db()
        return AddAccess(ok=ok)


class MyMutation(graphene.ObjectType):
    add_access = AddAccess.Field()
    remove_access  = RemoveAccess.Field()
