#!/usr/bin/env python3
import hashlib
import json
import pydicom
from pydicom._dicom_dict import DicomDictionary
from dataclasses import dataclass
from typing import List, Iterable
import os

@dataclass
class DICOMModuleClass:
    name: str
    id: str
    description: str
    linkToStandard: str

@dataclass
class CIODClass:
    name: str
    id: str
    description: str
    linkToStandard: str

@dataclass
class CIOD2Module:
    ciodId: str
    moduleId: str
    usage: str
    conditionalStatement: str
    informationEntity: str



@dataclass
class Module2Attribute:
    moduleId: str
    # TODO there are modules with same id but different paths
    path: str
    tag: str
    type: str
    linkToStandard: str
    description: str
    externalReferences: list



@dataclass
class SOP:
    name: str
    id: str
    ciod: str


@dataclass
class DICOMModule:
    clazz: DICOMModuleClass
    tags: List[pydicom.tag.Tag]
    missing: List[pydicom.tag.Tag]
    informationEntity: str




class Extractor:
    def load_cls(self, constructor, path: str):
        with open(path) as fp:
            unparsed = json.load(fp)
            return [constructor(**x) for x in unparsed]

    def read_modules(self, ds) -> Iterable[DICOMModule]:
        if "SOPClassUID" not in ds:
            raise Exception("SOPClassUID not in dataset")
        sop = ds["SOPClassUID"].value
        if sop not in self.sops:
            raise Exception(f"Unkonwn SOPClassUID: {sop}")
        ciod = self.name2ciods[self.sops[sop].ciod]
        print(f"Identified ciod {ciod}")

        for module in self.ciod2module_index[ciod.id]:
            missing = []
            found = []
            for attribute in self.module2attributes_index[module.moduleId]:
                try:
                    tag = pydicom.tag.Tag("".join(attribute.tag[1:-1].split(',')))
                    if tag in found:
                        print(attribute)
                        continue
                except ValueError as e:
                    # TODO move this to parsing of dicom stadnart, maybe realted to path issue and xxx are placeholder
                    print(e)
                # TODO duplicates
                if tag in ds:
                    found.append(tag)
                else:
                    # print(attribute.description)
                    missing.append(tag)
            if not found:
                print("Module is empty")
                continue
            if missing:
                pass
                # TODO find out what attributes are allowed to be absend
                # print(f"Incomplete Module, missing tags {missing}")
            else:
                print("Complete Module")
            yield DICOMModule(
                clazz=module,
                tags=found,
                missing=missing,
                informationEntity=module.informationEntity
            )

    def __init__(self):
        dirname = os.path.dirname(__file__)
        #self.modules = {x.id: x
        #                for x in self.load_cls(DICOMModuleClass,
        #                                       os.path.join(dirname, "./dicom-standard/standard/modules.json"))}
        #self.ciods = {x.id: x for x in self.load_cls(CIODClass, os.path.join(dirname, "./dicom-standard/standard/ciods.json"))}
        self.name2ciods = {x.name: x for x in self.load_cls(CIODClass, os.path.join(dirname, "./dicom-standard/standard/ciods.json"))}
        ciod2module = self.load_cls(CIOD2Module, os.path.join(dirname, "./dicom-standard/standard/ciod_to_modules.json"))
        self.ciod2module_index = {}
        for x in ciod2module:
            if x.ciodId in self.ciod2module_index:
                self.ciod2module_index[x.ciodId].append(x)
            else:
                self.ciod2module_index[x.ciodId] = [x]
        module2attributes = self.load_cls(Module2Attribute, os.path.join(dirname, "./dicom-standard/standard/module_to_attributes.json"))
        self.module2attributes_index = {}
        for x in module2attributes:
            if x.moduleId in self.module2attributes_index:
                self.module2attributes_index[x.moduleId].append(x)
            else:
                self.module2attributes_index[x.moduleId] = [x]
        self.sops = {x.id: x for x in self.load_cls(SOP, os.path.join(dirname, "./dicom-standard/standard/sops.json"))}
        # sanity checks
        for x in self.sops.values():
            assert x.ciod in self.name2ciods

    def get_modules(self, dcm_file_path):
        with open(dcm_file_path, 'rb') as infile:
            ds = pydicom.dcmread(infile)
        modules = list(self.read_modules(ds))
        covered_tags = set()
        for module in modules:
            for tag in module.tags:
                covered_tags.add(tag)
        uncovered_tags = set(ds.keys()) - covered_tags
        if not uncovered_tags:
            print("All covered")
        else:
            for tag in uncovered_tags:
                try:
                    print(DicomDictionary[tag])
                except:
                    print(tag)
                    print("Tag was not found in DicomDictionnary")

        informationEntity_index = {}
        for x in modules:
            if x.informationEntity in informationEntity_index:
                informationEntity_index[x.informationEntity].append(x)
            else:
                informationEntity_index[x.informationEntity] = [x]

        objects = []
        for name, modules in informationEntity_index.items():
            print(name)
            obj = {
                "type": name
            }
            for m in modules:
                print(f"\t{m.clazz.moduleId}")
                for t in m.tags:
                    if t == "PixelData":
                        continue
                    print(f"\t\t{DicomDictionary[t][4]}-{t}={ds[t].value}")
                    obj[DicomDictionary[t][4]] = ds[t].value
            objects.append(self.dict_hash(obj))

        # Add uncovered tags
        extra_obj = {}
        for t in uncovered_tags:
                try:
                    extra_obj[DicomDictionary[t][4]] = ds[t].value
                except:
                    print("tag not possible")
        extra_obj["type"] = "extra"
        objects.append(self.dict_hash(extra_obj))

        return objects #json.dumps(objects, indent=2, cls=ComplexEncoder)


    #todo: maybe not stable, but valid for tests...
    # https://www.doc.ic.ac.uk/~nuric/coding/how-to-hash-a-dictionary-in-python.html
    # https://stackoverflow.com/questions/5884066/hashing-a-dictionary
    def dict_hash(self, objects: dict) -> str:

        json_dict = json.dumps(objects, indent=2, cls=ComplexEncoder).encode("utf-8")
        """MD5 hash of a dictionary."""
        dhash = hashlib.md5()
        # We need to sort arguments so {'a': 1, 'b': 2} is
        # the same as {'b': 2, 'a': 1}

        dhash.update(json_dict)
        dict_with_complex_encoder = json.loads(json_dict)
        dict_with_complex_encoder['hash_id'] = dhash.hexdigest()
        return dict_with_complex_encoder

class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj,pydicom.valuerep.PersonName):
            return str(obj)
        elif isinstance(obj, pydicom.sequence.Sequence):
            return [x for x in obj]
        elif isinstance(obj, pydicom.multival.MultiValue):
            return [x for x in obj]
        elif isinstance(obj, pydicom.Dataset):
            return {key: val for key,val in obj.items()}
        elif isinstance(obj, pydicom.dataelem.DataElement):
            return obj.to_json()
        else:
            return json.JSONEncoder.default(self, obj)

# List of information entities
#print(set([x.informationEntity for x in ciod2module]))
