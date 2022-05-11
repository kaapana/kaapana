import strawberry
from .pydantic_model import Patient as PatientModel, Study as StudyModel, Series as SeriesModel
from .base import session
from .modelB import DataEntityB
from .pydantic_model import SchemaModelConverter
from typing import List

@strawberry.experimental.pydantic.type(model=SeriesModel, all_fields=True)
class Series:
    pass

@strawberry.experimental.pydantic.type(model=StudyModel, all_fields=True)
class Study:
    pass
@strawberry.experimental.pydantic.type(model=PatientModel, all_fields=True)
class Patient:
    pass


@strawberry.type
class Query:
    @strawberry.field
    def get_patient(self, name: str) -> List[Patient]:
        type_request = 'Patient'
        patient_entities = session().query(DataEntityB).filter(
            DataEntityB.meta[type_request]['PatientName'].astext.like('%{0}%'.format(name))).all()
        # fetch actual PersonModels here
        patient_list = list()
        for patient in patient_entities:
            meta = patient.meta
            patient = SchemaModelConverter.resolver(type_request, meta)
            #TODO: get links
            # linker = SchemaModelConverter.get_linkage(PatientModel.schema()["properties"], type_request)
            # linked_entities = list()
            # for link in linker:
            #     if 'source'
            patient_list.append(patient)
        return patient_list



schema = strawberry.Schema(query=Query)



