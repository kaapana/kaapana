from pydantic import BaseModel, validator, root_validator
from typing import List, Optional, Any
import sys





class SchemaModelConverter:
    def dicom_hierarchy(self):
        Patient = 0
        Study = 1
        Series = 2
        Other = 3

    @staticmethod
    # todo make more generic, this is really specifc!
    def get_linkage(model_class_type, model_type):
        members = model_class_type.schema()["properties"]
        sources = list()
        for member, value in members.items():
            reference = str()
            if '$ref' in value:
                reference = value['$ref']
            elif 'items' in value and '$ref' in value['items']:
                reference = value['items']['$ref']

            if reference:
                try:
                    rev_value = reference.split('/')[-1]
                    getattr(sys.modules[__name__], rev_value)
                    sources.append(rev_value)
                except:
                    print("not a class reference")
        linker = list()
        for source in sources:
            link = {
                'source': source,
                'target_type': model_type
            }
            linker.append(link)
        return linker

    @staticmethod
    def map_type(pytype: Any):
        if pytype == 'string':
            return str
        return pytype

    @staticmethod
    def resolver(model_type, meta_json):
        meta_model = meta_json[model_type]
        type_class = getattr(sys.modules[__name__], model_type)
        # type_class = eval(model_type)
        conversion = type_class(**meta_model)
        return conversion

    @staticmethod
    def mapper(json_dict: dict, model_type: str) -> dict:
        meta = dict()
        try:
            model_class_type = getattr(sys.modules[__name__], model_type)
        except:
            print("modelclass not in pydantic model")
            json_dict['links'] = [{'target': DEFAULT_LINKER_TARGET,
                                   'source_type': model_type}]
            return json_dict
        members = model_class_type.schema()["properties"]

        model_class_dict = dict.fromkeys(members.keys())
        for key in json_dict:
            found = False
            for member, value in members.items():
                if member == key:
                    pydantic_type = SchemaModelConverter.map_type(value['type'])
                    model_class_dict[key] = pydantic_type(json_dict[key])
                    found = True
                    break
                # TODO: converter from call member to (dicom) key
                # elif converter(member) == key:
            if not found:
                meta[key] = json_dict[key]
        found_dict = dict()
        for key, value in model_class_dict.items():
            if value:
                found_dict[key] = value
            # todo else: create mapper
        meta[model_type] = model_class_type.parse_obj(found_dict).dict()
        meta["links"] = SchemaModelConverter.get_linkage(model_class_type, model_type)
        return meta



def set_id_value(values, field_value):
    value_requested = values.get(field_value)
    values["id"] = value_requested
    return values


def set_id(field_value) -> classmethod:
    return root_validator(allow_reuse=True)(lambda cls, values: set_id_value(values, field_value))

DEFAULT_LINKER_TARGET = "Series"
class Series(BaseModel):
    id: str = "set_by_UID"
    dicomuid: str = "Undefined"
    SeriesInstanceUID: str = "Undefined"
    Modality: str = "Unknown"
    BodyPartExamined: str = 'Unknown'
    SeriesTime: Optional[str]
    SeriesDate: Optional[str]
    instances: Optional[List[str]]
    _validate_id = set_id('SeriesInstanceUID')


#
class Study(BaseModel):
    id: str = "set_by_UID"
    StudyInstanceUID: str = "Undefined"
    dicomuid: str = "Undefined"
    series: Optional[List[Series]]
    _validate_id = set_id('StudyInstanceUID')


class Patient(BaseModel):
    id: str = "set_by_UID"
    first_name: str = "Hans"
    last_name: str = "Mustermann"
    PatientName: str = "Hans^Mustermann"
    PatientID: str = "PatientID"
    PatientSex: str = "O"
    PatientBirthDate: str = "15000101"
    studies: Optional[List[Study]]
    _validate_id = set_id('PatientID')
