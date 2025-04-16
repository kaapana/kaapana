import os
import glob
import numpy as np
import glob
import os
import pydicom
import wsidicomizer
from wsidicomizer import WsiDicomizer
from pathlib import Path
from wsidicom.conceptcode import (
    AnatomicPathologySpecimenTypesCode,
    ContainerTypeCode,
    SpecimenCollectionProcedureCode,
    SpecimenEmbeddingMediaCode,
    SpecimenFixativesCode,
    SpecimenSamplingProcedureCode,
    SpecimenStainsCode,
)
from wsidicom.metadata import (
    Collection,
    Embedding,
    Equipment,
    Fixation,
    Label,
    Patient,
    Sample,
    Series,
    Slide,
    SlideSample,
    Specimen,
    Staining,
    Study,
)
from wsidicomizer.sources import TiffSlideSource
from wsidicomizer.metadata import WsiDicomizerMetadata
study = Study(identifier="Study identifier")
series = Series(number=1)
patient = Patient(name="FamilyName^GivenName")
label = Label(text="Label text")
equipment = Equipment(
    manufacturer="Kaapana",
    model_name="Scanner model name",
    device_serial_number="Scanner serial number",
    software_versions=["Scanner software versions"],
)

specimen = Specimen(
    identifier="Specimen",
    extraction_step=Collection(method=SpecimenCollectionProcedureCode("Excision")),
    type=AnatomicPathologySpecimenTypesCode("Gross specimen"),
    container=ContainerTypeCode("Specimen container"),
    steps=[Fixation(fixative=SpecimenFixativesCode("Neutral Buffered Formalin"))],
)

block = Sample(
    identifier="Block",
    sampled_from=[specimen.sample(method=SpecimenSamplingProcedureCode("Dissection"))],
    type=AnatomicPathologySpecimenTypesCode("tissue specimen"),
    container=ContainerTypeCode("Tissue cassette"),
    steps=[Embedding(medium=SpecimenEmbeddingMediaCode("Paraffin wax"))],
)

slide_sample = SlideSample(
    identifier="Slide sample",
    sampled_from=block.sample(method=SpecimenSamplingProcedureCode("Block sectioning")),
)

slide = Slide(
    identifier="Slide",
    stainings=[
        Staining(
            substances=[
                SpecimenStainsCode("hematoxylin stain"),
                SpecimenStainsCode("water soluble eosin stain"),
            ]
        )
    ],
    samples=[slide_sample],
)




work_dir=os.path.join(os.environ['WORKFLOW_DIR'],os.environ['OPERATOR_IN_DIR'])+'/'
_,_,all_WS_files=next(os.walk(work_dir))
output_path=os.path.join(os.environ['WORKFLOW_DIR'],os.environ['OPERATOR_OUT_DIR'])+'/'
if not os.path.exists(output_path):
    os.makedirs(output_path)
WSI_files=[]
for all in all_WS_files:
    if not all.startswith('.'):
        WSI_files.append(all)


for files in WSI_files:
    load_path=work_dir+files
    file_name = load_path.rpartition('/')[2]
    file_name = file_name.replace('.', '')
    output_dcm_file_path = os.path.join(output_path, file_name)
    try:
        os.makedirs(output_dcm_file_path,exist_ok=True)
    except ValueError:
        print('Directory cannot be created')

    metadata = WsiDicomizerMetadata(
    study=study,
    series=series,
    patient=Patient(name=file_name),
    equipment=equipment,
    slide=slide,
    label=label,
    )
    try:
        WsiDicomizer.convert(load_path, output_dcm_file_path, metadata=metadata, add_missing_levels=True,include_confidential=False)
    except Exception as e:
        print(f"Primary conversion failed with error: {e}. Retrying with TiffSlideSource.")
        WsiDicomizer.convert(load_path,output_dcm_file_path,preferred_source=TiffSlideSource,metadata=metadata,add_missing_levels=True,include_confidential=False)
    postprocessing_files = glob.glob(output_dcm_file_path + '/*.dcm')
    a = 0
    for i in postprocessing_files:
        ds = pydicom.dcmread(i)
        instance_number = ds.InstanceNumber
        new_filename = f"instance_{instance_number}_a{a}.dcm"
        new_filepath = os.path.join(os.path.dirname(i), new_filename)

        # Rename the file
        os.rename(i, new_filepath)
        if ds.ImageType[2]=='THUMBNAIL':
            os.remove(new_filepath)
        a += 1

print("This conversion was done with wsidicomizer as backbone. wsidicomizer: Copyright 2021 Sectra AB, licensed under Apache 2.0. This project is part of a project that has received funding from the Innovative Medicines Initiative 2 Joint Undertaking under grant agreement No 945358. This Joint Undertaking receives support from the European Union’s Horizon 2020 research and innovation programme and EFPIA. www.github.com/imi-bigpicture/wsidicomizer")
