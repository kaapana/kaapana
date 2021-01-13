import sys
import os
import glob
import pydicom
import binascii
import pathlib
from datetime import datetime
from xml.dom import minidom
import xml.etree.ElementTree as et
from subprocess import PIPE, run

converter_count = 0


def combine_split_files(split_files_dir):
    input_files = sorted(glob.glob(os.path.join(split_files_dir, "*.part*")))
    final_filename = input_files[0][:-7]

    my_cmd = ['cat'] + input_files
    with open(final_filename, "w") as outfile:
        output = run(my_cmd, stdout=outfile)

    if output.returncode != 0:
        print(f"# Could not combine split files for {split_file}!")
        print(output)
        exit(1)
    else:
        print(f"# Successfully created {split_file}!")
        for part_file in input_files:
            os.remove(part_file)

    return final_filename


def split_file(file_path, size_limit):
    command = ["split", "-b", f"{size_limit}M", file_path, f"{file_path}.part"]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60)

    if output.returncode != 0:
        print("# Could not convert dicom to xml!")
        print(output)
        exit(1)

    part_files = sorted(glob.glob(f"{file_path}.part*"))
    return part_files


def xml_to_dicom(generated_xml_list):
    global converter_count

    dicom_list = []

    for xml_path in generated_xml_list:
        dcm_path = xml_path.replace("xml", "dcm")
        print("#")
        print(f"# convert XML to DICOM: {xml_path} -> {dcm_path}")
        command = ["xml2dcm", xml_path, dcm_path]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=320)

        if output.returncode != 0:
            print("# Could not convert XML to DICOM!")
            print(output)
            exit(1)
        else:
            print("# DICOM created!")
            os.remove(xml_path)
            dicom_list.append(dcm_path)

    converter_count += 1
    return dicom_list


def dicom_to_xml(dcm_path, target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    xml_path = dcm_path.replace(os.path.dirname(dcm_path), target_dir).replace("dcm", "xml").replace(".zip", "")

    print("#")
    print(f"# convert DICOM to XML: {dcm_path} -> {xml_path}")

    command = ["dcm2xml", "+Eh", "+Wb", "--load-all", dcm_path, xml_path]
    print("#")
    print(f"# command: {command}")
    print("#")
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=320)

    if output.returncode != 0:
        print("# Could not convert dicom to xml!")
        print(output)
        exit(1)
    else:
        print("# XML created!")

    return xml_path


def xml_to_binary(xml_dir):
    global converter_count
    xml_files = sorted(glob.glob(os.path.join(xml_dir, "*.xml")))
    print("#")
    print("# starting xml_to_binary")
    print(f"# xml-dir:      {xml_dir}")
    print(f"# xml-files:    {xml_files}")
    expected_file_count = int(xml_files[0].split(".")[0].split("---")[1])
    print(f"# files needed: {expected_file_count}")
    print("#")

    if len(xml_files) != expected_file_count:
        print("# ERROR!!")
        print("#")
        print(f"# Expected {expected_file_count} files -> found {len(xml_files)}")
        print("# Abort")
        print("#")
        exit(1)

    for xml_file in xml_files:
        context = et.iterparse(xml_file, events=("start", "end"))
        context = iter(context)
        ev, root = next(context)

        filename = None
        hex_data = None
        for ev, el in context:
            if ev == 'start' and el.tag == 'element' and el.attrib['name'] == "PatientName":
                filename = el.text
                print(f"# Found filename: {filename}")
                root.clear()
            elif ev == 'end' and el.tag == 'pixel-item' and el.attrib['len'] != "0":
                hex_data = el.text.strip().replace("\\", "")
                print("# Found Hex-Data!")
                root.clear()

        if filename is None or hex_data is None:
            print("# Could not extract needed data!")
            print("#")
            print(f"# filename: {filename}")
            print(f"# hex_data: {hex_data}")
            print("#")
            exit(1)

        binary_path = os.path.join(os.path.dirname(xml_file), filename)
        binstr = binascii.unhexlify(hex_data)
        with open(binary_path, "wb") as f:
            f.write(binstr)

        print(f"# Successfully extracted file: {filename} !")
        os.remove(xml_file)

    if expected_file_count > 1:
        combine_split_files(split_files_dir=xml_dir)

    converter_count += 1


def generate_xml(binary_path, target_dir, template_path="/template.xml"):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    size_limit = int(os.getenv("SIZE_LIMIT_MB", "100"))
    study_description = os.getenv("STUDY_DESCRIPTION", "Binary file")
    study_uid = os.getenv("STUDY_UID", pydicom.uid.generate_uid())

    study_date = datetime.now().strftime("%Y%m%d")
    study_time = datetime.now().strftime("%H%M%S")
    print(f"# study_date: {study_date}")
    print(f"# study_time: {study_time}")

    xml_output_list = []

    binary_file_size = os.path.getsize(binary_path) >> 20

    binary_path_list = [binary_path]
    if size_limit != 0 and binary_file_size > size_limit:
        binary_path_list = split_file(file_path=binary_path, size_limit=size_limit)

    split_part_count = len(binary_path_list)
    full_filename = os.path.basename(binary_path)
    for binary_path in binary_path_list:
        series_uid = pydicom.uid.generate_uid()

        filename = os.path.basename(binary_path)
        xml_output_path = os.path.join(target_dir, f"{filename.split('.')[0]}---{split_part_count}{''.join(pathlib.Path(filename).suffixes)}.xml")

        xml_template = minidom.parse(template_path)
        elements = xml_template.getElementsByTagName('element')

        for element in elements:
            el_name = element.attributes['name'].value

            if el_name == "StudyInstanceUID":
                element.firstChild.data = study_uid
                print(f"# StudyInstanceUID: {element.firstChild.data}")

            elif el_name == "StudyDate":
                element.firstChild.data = study_date
                print(f"# StudyDate: {element.firstChild.data}")

            elif el_name == "StudyTime":
                element.firstChild.data = study_time
                print(f"# StudyTime: {element.firstChild.data}")

            elif el_name == "StudyDescription":
                element.firstChild.data = study_description
                print(f"# StudyDescription: {element.firstChild.data}")

            elif el_name == "SeriesInstanceUID":
                element.firstChild.data = series_uid
                print(f"# SeriesInstanceUID: {element.firstChild.data}")

            elif el_name == "PatientName":
                element.firstChild.data = filename
                print(f"# PatientName: {element.firstChild.data}")

            elif el_name == "PatientComments":
                patient_comments = f"full_filename={full_filename};part_count={split_part_count}"
                element.firstChild.data = patient_comments
                print(f"# PatientComments: {element.firstChild.data}")

        file_size = os.path.getsize(binary_path)

        with open(binary_path, 'rb') as f:
            hex_data = f.read().hex("\\")

        print(f"# Loaded file {binary_path}: {file_size}")

        binary_item = xml_template.getElementsByTagName('pixel-item')[0]
        binary_item.attributes['len'].value = f"{file_size}"
        binary_item.firstChild.data = hex_data

        print("# Generated XML from template -> export file...")
        with open(xml_output_path, "w") as xml_file:
            xml_template.writexml(xml_file)

        xml_output_list.append(xml_output_path)

    return xml_output_list


# START
binary_file_extensions = os.getenv("EXTENSIONS", "*.zip").split(",")
batch_folders = [f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))]

for batch_element_dir in batch_folders:
    element_input_dir = os.path.join(batch_element_dir, os.getenv("OPERATOR_IN_DIR", ""))
    element_output_dir = os.path.join(batch_element_dir, os.getenv("OPERATOR_OUT_DIR", ""))

    binaries_found = []
    for extension in binary_file_extensions:
        binaries_found.extend(glob.glob(os.path.join(element_input_dir, extension)))

    if len(binaries_found) == 0:
        print("############### No binaries found at {} ".format(element_input_dir))
        print("############### Extensions: {} ".format(binary_file_extensions))
        continue

    convert_binary = False
    for binary in binaries_found:
        if not os.path.exists(element_output_dir):
            os.makedirs(element_output_dir)
        print("##################################################")
        print("#")
        print("# Found file: {}".format(binary))
        print("#")
        if ".dcm" in binary:
            print("# --> identified DICOM --> execute dcm2binary")
            print("#")
            print("# --> extract xml")
            extracted_xml = dicom_to_xml(dcm_path=binary, target_dir=element_output_dir)
            print("#")
            convert_binary = True

        else:
            print("# --> no DICOM --> execute bin2dcm")
            print(f"# --> generate_xml -> {element_output_dir}")
            generated_xml_list = generate_xml(binary_path=binary, target_dir=element_output_dir)
            print("#")
            print("# --> xml_to_dicom")
            dcm_path_list = xml_to_dicom(generated_xml_list=generated_xml_list)
            print("#")

    if convert_binary:
        print("# --> get_binary_from_xml")
        xml_to_binary(xml_dir=element_output_dir)
        print("#")

print("##################################################")
print("#")
print("# Searching for files on batch-level....")
print("#")
print("##################################################")
print("#")

batch_input_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])
batch_output_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_OUT_DIR'])

print(f"# batch_input_dir:  {batch_input_dir}")
print(f"# batch_output_dir: {batch_output_dir}")
# if "bcm2bin" in batch_output_dir:
#     batch_output_dir="/data/dcm2bin"
# print(f"# batch_output_dir: {batch_output_dir}")

binaries_found = []
for extension in binary_file_extensions:
    binaries_found.extend(glob.glob(os.path.join(batch_input_dir, extension)))

if len(binaries_found) == 0:
    print("############### No binaries found at {} ".format(batch_input_dir))
    print("############### Extensions: {} ".format(binary_file_extensions))

convert_binary = False
for binary in binaries_found:
    if not os.path.exists(batch_output_dir):
        os.makedirs(batch_output_dir)
    print("#")
    print("# Found file: {}".format(binary))
    print("#")
    if ".dcm" in binary:
        print("# --> identified DICOM --> execute dcm2binary")
        print("#")
        print(f"# --> extract xml: {binary} -> {batch_output_dir}")
        extracted_xml = dicom_to_xml(dcm_path=binary, target_dir=batch_output_dir)
        print("#")
        convert_binary = True

    else:
        print("# --> no DICOM --> execute bin2dcm")
        print("#")
        print(f"# --> generate_xml: {binary} -> {batch_output_dir}")
        print("#")
        generated_xml_list = generate_xml(binary_path=binary, target_dir=batch_output_dir)
        print(f"# --> xml_to_dicom: {generated_xml_list} -> {batch_output_dir}")
        print("#")
        dcm_path_list = xml_to_dicom(generated_xml_list=generated_xml_list)

if convert_binary:
    print("# --> get_binary_from_xml")
    xml_to_binary(xml_dir=batch_output_dir)
    print("#")


if converter_count == 0:
    print("#")
    print("##################################################")
    print("#")
    print("#################  ERROR  #######################")
    print("#")
    print("# ----> NO FILES HAVE BEEN CONVERTED!")
    print("#")
    print("##################################################")
    print("#")
    exit(1)

print("#")
print("#")
print("##################################################")
print("#")
print("##################  DONE  ########################")
print("#")
print("##################################################")
print("#")
print("#")
