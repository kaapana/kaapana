#!/usr/bin/env python3
import json
import pydicom
from pydicom._dicom_dict import DicomDictionary
from dataclasses import dataclass
from typing import List, Iterable

def load_cls(constructor, path: str):
    with open(path) as fp:
        unparsed = json.load(fp)
        return [constructor(**x) for x in unparsed]

@dataclass
class DICOMModuleClass:
    name: str
    id: str
    description: str
    linkToStandard: str

modules = {x.id: x for x in load_cls(DICOMModuleClass, "./dicom-standard/standard/modules.json")}

@dataclass
class CIODClass:
    name: str
    id: str
    description: str
    linkToStandard: str

ciods = {x.id: x for x in load_cls(CIODClass, "./dicom-standard/standard/ciods.json")}
name2ciods = {x.name: x for x in load_cls(CIODClass, "./dicom-standard/standard/ciods.json")}

@dataclass
class CIOD2Module:
    ciodId: str
    moduleId: str
    usage: str
    conditionalStatement: str
    informationEntity: str

ciod2module = load_cls(CIOD2Module, "./dicom-standard/standard/ciod_to_modules.json")
ciod2module_index = {}
for x in ciod2module:
    if x.ciodId in ciod2module_index:
        ciod2module_index[x.ciodId].append(x)
    else:
        ciod2module_index[x.ciodId] = [x]

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

module2attributes = load_cls(Module2Attribute, "./dicom-standard/standard/module_to_attributes.json")
module2attributes_index = {}
for x in module2attributes:
    if x.moduleId in module2attributes_index:
        module2attributes_index[x.moduleId].append(x)
    else:
        module2attributes_index[x.moduleId] = [x]

@dataclass
class SOP:
    name: str
    id: str
    ciod: str

sops = {x.id: x for x in load_cls(SOP, "./dicom-standard/standard/sops.json")}

# sanity checks
for x in sops.values():
    assert x.ciod in name2ciods

@dataclass
class DICOMModule:
    clazz: DICOMModuleClass
    tags: List[pydicom.tag.Tag]
    missing: List[pydicom.tag.Tag]
    informationEntity: str

def read_modules(ds) -> Iterable[DICOMModule]:
    if "SOPClassUID" not in ds:
        raise Exception("SOPClassUID not in dataset")
    sop = ds["SOPClassUID"].value
    if sop not in sops:
        raise Exception(f"Unkonwn SOPClassUID: {sop}")
    ciod = name2ciods[sops[sop].ciod]
    print(f"Identified ciod {ciod}")

    for module in ciod2module_index[ciod.id]:
        missing = []
        found = []
        for attribute in module2attributes_index[module.moduleId]:
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
                #print(attribute.description)
                missing.append(tag)
        if not found:
            print("Module is empty")
            continue
        if missing:
            pass
            #TODO find out what attributes are allowed to be absend
            #print(f"Incomplete Module, missing tags {missing}")
        else:
            print("Complete Module")
        yield DICOMModule(
            clazz=module,
            tags=found,
            missing=missing,
            informationEntity=module.informationEntity
        )

with open("demo.dcm", 'rb') as infile:
    ds = pydicom.dcmread(infile)
modules = list(read_modules(ds))
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
    objects.append(obj)

# Add uncovered tags
extra_obj = {}
for t in uncovered_tags:
        try:
            extra_obj[DicomDictionary[t][4]] = ds[t].value
        except:
            print("tag not possible")
extra_obj["type"] = "extra"
objects.append(extra_obj)

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
print(json.dumps(objects,indent=2,cls=ComplexEncoder))

# List of information entities
#print(set([x.informationEntity for x in ciod2module]))
