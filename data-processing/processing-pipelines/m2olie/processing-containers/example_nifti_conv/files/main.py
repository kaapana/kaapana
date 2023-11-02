import os
from pydicom.dataset import Dataset, FileDataset, DataElement, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.tag import Tag
import pydicom.uid
from pydicom.uid import generate_uid
from pydicom.encaps import encapsulate
from pydicom.sequence import Sequence
from pydicom.dataset import Dataset
from pydicom.datadict import dictionary_VR
import matplotlib.pyplot as plt
import glob
from datetime import datetime
import nrrd
import nibabel as nib
import nilearn
from nilearn import image
import yaml
import numpy as np

# import SimpleITK as sitk


def read_nrrd(path, *args):
    path = str(path)
    file = nrrd.read(path)
    return file


def convert_nifti2dcm_singleFrame(file, data_type, pat_name, output_path, conf, *argv):
    nrrd_data = file[0]
    dimensions = nrrd_data.shape
    if len(dimensions) > 3:
        nrrd_data = nrrd_data[:, :, :, 0]
    nrrd_data = np.transpose(nrrd_data, (1, 0, 2))
    nrrd_header = file[1]
    position = nrrd_header["space origin"]
    offset_x = position[0]
    offset_x = str(offset_x)
    offset_y = position[1]
    offset_y = str(offset_y)
    offset_z = position[2]

    pix_dim = nrrd_header["space directions"]

    # -----------Experimental Area-----------------
    row_direction_cosines = pix_dim[0]
    column_direction_cosines = pix_dim[1]
    ImageorientationPatient = np.concatenate(
        (row_direction_cosines, column_direction_cosines)
    )
    ImageorientationPatient = [str(x) for x in ImageorientationPatient]

    dim_x = max(abs(pix_dim[0, :]))
    dim_y = max(abs(pix_dim[1, :]))
    slice_thicknes = max(abs(pix_dim[2, :]))
    # -----------------------------------#

    image_data = np.asarray(nrrd_data, dtype=np.int16)
    print(image_data.shape)
    columns = image_data.shape[1]  # 0
    rows = image_data.shape[0]  # 1

    if "StudyInstanceUID" in conf:
        print("ID found")
        study_instance_UID = conf["StudyInstanceUID"]
    else:
        study_instance_UID = generate_uid()

    if "SeriesInstanceUID" in conf:
        series_instance_UID = conf["SeriesInstanceUID"]
    else:
        series_instance_UID = generate_uid()

    if "glob_implementation_class_UID" in conf:
        implementation_class_uid = glob_implementation_class_UID
    else:
        implementation_class_uid = generate_uid()
    if "FrameOfReferenceUID" in conf:
        FrameOfReferenceUID=conf["FrameOfReferenceUID"]
    else:
        FrameOfReferenceUID=generate_uid()

    pat_name = conf["PatID"]
    date_time = str(datetime.now())
    date = date_time[0:10].replace("-", "")
    time = date_time[11:].replace(":", "")

    if conf["Modality"] == "CT":
        modality_UID = "1.2.840.10008.5.1.4.1.1.2"
        modality = "CT"
    else:
        modality_UID = "1.2.840.10008.5.1.4.1.1.4"
        modality = "MR"

    for i in range(image_data.shape[2]):
        if "indexing_image" in globals():
            store_name = (indexing_image * image_data.shape[2]) + i

        else:
            store_name = i
        file_name = str(store_name)
        file_name = file_name.zfill(3)
        file_name = file_name + ".dcm"
        media_storage_SOP_Instance_UID = generate_uid()

        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = modality_UID
        file_meta.MediaStorageSOPInstanceUID = media_storage_SOP_Instance_UID
        file_meta.ImplementationClassUID = implementation_class_uid
        file_meta.FileMetaInformationVersion = b"\x00\x01"
        file_meta.ImplementationVersionName = "Nird2DCM"
        file_meta.SourceApplicationEntityTitle = "Nird2DCM"
        file_meta.TransferSyntaxUID = "1.2.840.10008.1.2.1"
        file_meta.FileMetaInformationGroupLength = len(file_meta)
        dcm_file = FileDataset(
            file_name,
            {},
            preamble=b"\0" * 128,
            file_meta=file_meta,
            is_implicit_VR=False,
            is_little_endian=True,
        )

        dcm_file.ImageType = ["DERIVED", "SECONDARY", "AXIAL"]
        dcm_file.SOPClassUID = modality_UID  # CT
        dcm_file.SOPInstanceUID = media_storage_SOP_Instance_UID
        dcm_file.StudyDate = date
        dcm_file.SeriesDate = date
        dcm_file.SeriesDescription = conf['SeriesDescription']
        dcm_file.ContentDate = date
        tag = pydicom.tag.Tag("StudyTime")
        pd_ele = DataElement(tag, "TM", time)
        dcm_file.add(pd_ele)
        tag = pydicom.tag.Tag("SeriesTime")
        pd_ele = DataElement(tag, "TM", time)
        dcm_file.add(pd_ele)
        tag = pydicom.tag.Tag("ContentTime")
        pd_ele = DataElement(tag, "TM", time)
        dcm_file.add(pd_ele)
        dcm_file.AccessionNumber = ""
        dcm_file.Modality = modality
        dcm_file.Manufacturer = "PyDICOM"
        dcm_file.ReferringPhysicianName = "SOME^PHYSICIAN"
        dcm_file.PatientName = pat_name
        dcm_file.PatientSex = ""
        dcm_file.PatientID = pat_name
        dcm_file.SliceThickness = str(slice_thicknes)
        dcm_file.PatientPosition = "HFS"
        dcm_file.StudyInstanceUID = study_instance_UID
        dcm_file.SeriesInstanceUID = series_instance_UID
        dcm_file.StudyID = pat_name
        dcm_file.SeriesNumber = "1"
        dcm_file.InstanceNumber = str(i + 1)
        running_offset_z = offset_z + (slice_thicknes * i)
        running_offset_z = "%.3f" % running_offset_z
        image_pos = str(running_offset_z)
        dcm_file.ImagePositionPatient = [offset_x, offset_y, image_pos]
        dcm_file.ImageOrientationPatient = ImageorientationPatient
        dcm_file.FrameOfReferenceUID = FrameOfReferenceUID
        dcm_file.PositionReferenceIndicator = ""
        dcm_file.SamplesPerPixel = 1
        dcm_file.PhotometricInterpretation = "MONOCHROME2"
        dcm_file.Rows = rows
        dcm_file.Columns = columns
        dcm_file.PixelSpacing = [dim_x, dim_y]
        dcm_file.BitsAllocated = 16
        dcm_file.BitsStored = 16
        dcm_file.HighBit = 15
        dcm_file.PixelRepresentation = 1

        dcm_file.RescaleIntercept = "0.0"
        dcm_file.RescaleSlope = "1.0"
        if modality == "CT":
            dcm_file.RescaleType = "HU"
        else:
            dcm_file.RescaleType = "US"

        if len(argv) != 0:
            yaml_file = argv[0]
            if yaml_file.items() != 0:
                additional_tags = []
                additional_values = []

                for key, value in yaml_file["Tags"].items():
                    additional_tags.append(key)
                    additional_values.append(value)

                for tags in range(len(additional_tags)):
                    tag = pydicom.tag.Tag(additional_tags[tags])
                    values = additional_values[tags]
                    values = values.upper()
                    if values != "SAME":
                        representation = dictionary_VR(tag)
                        representation = representation.upper()
                        pd_ele = DataElement(tag, representation, values)
                        dcm_file.add(pd_ele)

        img = image_data[:, :, i]
        arr = np.asarray(img, dtype=np.int16)
        dcm_file.PixelData = arr.tostring()
        window_width = abs(img.min()) + abs(img.max())
        dcm_file.WindowCenter = str(img.min() + (window_width / 2))
        dcm_file.WindowWidth = str(window_width)
        store_path = os.path.join(output_path, file_name)
        dcm_file.save_as(store_path, write_like_original=False)

    return 0


batch_folders = sorted(
    [
        f
        for f in glob.glob(
            os.path.join("/", os.environ["WORKFLOW_DIR"], os.environ["BATCH_NAME"], "*")
        )
        if os.path.isdir(f)
    ]
)

print("batch_folders: ", batch_folders)
if len(batch_folders) < 1:
    print("no files found")
    exit()
batch_folders = batch_folders[0]
Fixed_Folder = os.path.join(batch_folders, "get-input-data")
Moving_Folder = os.path.join(batch_folders, "get_additional_input")
fixed_imgs = glob.glob(Fixed_Folder + "/*")
moving_imgs = glob.glob(Moving_Folder + "/*")
fixed_img = pydicom.dcmread(fixed_imgs[0])
moving_img = pydicom.dcmread(moving_imgs[0])
if fixed_img.PatientID != moving_img.PatientID:
    exit()
if moving_img.Modality != "MR":
    exit()
conf = dict()
conf["Modality"] = moving_img.Modality
conf["PatID"] = moving_img.PatientID
conf["StudyInstanceUID"] = moving_img.StudyInstanceUID
conf["SeriesInstanceUID"] = generate_uid()
conf["FrameOfReferenceUID"]=fixed_img.FrameOfReferenceUID
conf['SeriesDescription']=moving_img.SeriesDescription+'_Registered'
if os.path.isdir(os.path.join(batch_folders, "manually_registered"))==True:
    working_dir='manually_registered'
    registered_image_name="file.nrrd"
    print('Taking manually registered image')
else:
    working_dir='registration'
    registered_image_name="result1.nrrd"
    os.rename(os.path.join(batch_folders, working_dir, "result.1.nrrd"),os.path.join(batch_folders, working_dir, "result1.nrrd"))
    print('Taking automatic registered image')
registeredImage = read_nrrd(os.path.join(batch_folders, working_dir, registered_image_name))


file_name = "registration1"
shape = registeredImage[0].shape
outPath = os.path.join(batch_folders, os.environ["OPERATOR_OUT_DIR"])
print("Output path:", outPath)
os.makedirs(outPath, exist_ok=True)

convert_nifti2dcm_singleFrame(registeredImage, "nrrd", file_name, outPath, conf)
