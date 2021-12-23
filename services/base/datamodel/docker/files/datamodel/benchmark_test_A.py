import unittest
import datamodel.Datamodel as DatamodelA
import os
import time
import csv
RESUTL_DIR = "/home/ubuntu/results"
INPUT_DIR = '/home/ubuntu/input_dicom'
namelist = ["Brands", "Charon", "deJonge","deRoo", "Doorhof", "Ernst", "Geerling", "Haring", "Hondeveld"]
time_modelA = 0.0
time_list_A = []
time_list_B = []
function_name = str

def write_to_csv():
    global time_list_A, time_list_B, function_name
    if not os.path.exists(RESUTL_DIR):
        os.makedirs(RESUTL_DIR)
    csv_file = RESUTL_DIR + "/benchmark.csv"
    if not os.path.isfile(csv_file):
        with open(csv_file, 'w', encoding='utf-8') as cvsFile:
            writer = csv.writer(cvsFile)
            writer.writerow(['value', 'modelA', '', '', 'modelB'])
    with open(csv_file, 'a+', newline='', encoding='utf-8') as cvsFile:
        writer = csv.writer(cvsFile)
        write_list = []
        write_list.append(function_name)
        if len(time_list_A)< 3:
            for i in range(len(time_list_A),3):
                time_list_A.append(None)
        write_list += time_list_A
        write_list += time_list_B
        writer.writerow(write_list)


def timing(f):
    def wrap(*args, **kwargs):
        time1 = time.time()
        ret = f(*args, **kwargs)
        time2 = time.time()
        global time_list_A, time_list_B, function_name
        if type(args[0]) == DatamodelA.KaapanaDatamodel:
            time_list_A.append(time2-time1)
        else:
            time_list_B.append(time2 - time1)
        print('{:s} function took {:.3f} ms'.format(f.__name__, (time2-time1)*1000.0))
        function_name = f.__name__
        return ret
    return wrap

@timing
def import_dicom(model, content):
    model.import_data(content)

@timing
def import_data(model, content):
    model.import_data(content)

@timing
def query_patient(model, name):
    patients = model.get_data(name)
    return patients

@timing
def query_patient_age_range(model, ages: tuple):
    patients = model.get_patient_age_range(ages)
    return patients

@timing
def query_study_description(model, study_description: str):
    studies = model.get_studies_study_description(study_description)
    return studies

@timing
def query_modality(model, modality):
    series = model.get_series_modality(modality)
    return series

@timing
def query_seg(model, patient):
    seg_series = model.get_segs_to_patient(patient)
    return seg_series


@timing
def query_reference(model, seg):
    series = model.get_reference(seg)
    return series

@timing
def query_number_of_instances(model, name):
    number_of_instances = model.get_number_of_instances(name)
    return number_of_instances

@timing
def query_get_specific_instance(model, patient, instance_number):
        file = model.get_specific_instance(patient, instance_number)


## other search creteria of meta
#'00180015 BodyPartExamined_keyword'
#'00100040 PatientSex_keyword'

class Testquery(unittest.TestCase):
    # @classmethod
    # def setUpClass(self):
        # global time_list_A, time_list_B
        # time_list_A = []
        # time_list_B = []
        # datamodel_a = DatamodelA.KaapanaDatamodel()
        # datamodel_a.init_db()
        # self.input_path = INPUT_DIR
        # self.datamodel_a = datamodel_a
        # #TODO relace with datamodel_b
        # datamodel_b = DatamodelA.KaapanaDatamodel()
        # datamodel_b.init_db()
        # self.datamodel_b = datamodel_b
        # pack = []
        # files = []
        # print(self.input_path)
        # for dirpath, dirnames, fileNames in os.walk(self.input_path):
        #     for fileName in fileNames:
        #         if fileName.endswith('.dcm'):
        #             path = os.path.join(dirpath, fileName)
        #             files.append(path)
        #             if 10 == len(files):
        #                 pack.append(files)
        #                 files = []
        #
        # for package in pack:
        #     storage_path = {"storage_path": "test_path"}
        #     content = {"files": package, "options": storage_path}
        #     #self.datamodel_a.import_data(content)
        #     import_dicom(self.datamodel_a, content)
        #     #import_dicom(self.datamodel_b, content)
        #     # TODO import as normal files to see a difference

    def setUp(self) -> None:
        global time_list_A, time_list_B
        time_list_A = []
        time_list_B = []
        datamodel_a = DatamodelA.KaapanaDatamodel()
        datamodel_a.init_db()
        self.input_path = INPUT_DIR
        self.datamodel_a = datamodel_a
        #TODO relace with datamodel_b
        datamodel_b = DatamodelA.KaapanaDatamodel()
        datamodel_b.init_db()
        self.datamodel_b = datamodel_b
    def tearDown(self) -> None:
        global time_list_A, time_list_B
        write_to_csv()



  #  def test_import_data(self):




    def test_query_patient(self):
        name = namelist[0]
        patients_a = query_patient(self.datamodel_a, name)
        self.assertEqual(patients_a[0].family_name, name)
        #patients_a = query_patient(self.datamodel_b, name)
        #self.assertEqual(patients_a[0].family_name, name)
        name = namelist[1]
        patients_b = query_patient(self.datamodel_a, name)
        self.assertEqual(patients_b[0].family_name, name)
        #patients_a = query_patient(self.datamodel_b, name)
        #self.assertEqual(patients_a[0].family_name, name)

    def test_query_patient_age_range(self):
        ages = ("01.01.1980", "01.01.2020")
        patient_a = query_patient_age_range(self.datamodel_a, ages)
        patient_b = query_patient_age_range(self.datamodel_b, ages)
        self.assertEqual(len(patient_a), len(patient_b))

        ages = ("01.01.1950", "01.01.1970")
        patient_a = query_patient_age_range(self.datamodel_a, ages)
        patient_b = query_patient_age_range(self.datamodel_b, ages)
        self.assertEqual(len(patient_a), len(patient_b))

    def test_query_study_description(self):
        study_description = "StudyDescription_1"
        patient_a = query_study_description(self.datamodel_a, study_description)
        patient_b = query_study_description(self.datamodel_b, study_description)
        self.assertEqual(len(patient_a), len(patient_b))
        study_description = "StudyDescription_22"
        patient_a = query_study_description(self.datamodel_a, study_description)
        patient_b = query_study_description(self.datamodel_b, study_description)
        self.assertEqual(len(patient_a), len(patient_b))

    def test_query_modality(self):
        modality = "CT"
        series_a = query_modality(self.datamodel_a, modality)
        series_b = query_modality(self.datamodel_b, modality)
        self.assertEqual(len(series_a), len(series_b))
        modality = "MR"
        series_a = query_modality(self.datamodel_a, modality)
        series_b = query_modality(self.datamodel_b, modality)
        self.assertEqual(len(series_a), len(series_b))


    def test_query_seg(self):
        modality = "SEG"
        name = namelist[2]
        segmentation_a = query_seg(self.datamodel_a, name)
        segmentation_b = query_seg(self.datamodel_b, name)
        self.assertEqual(len(segmentation_a), len(segmentation_b))
        name = namelist[3]
        segmentation_a = query_seg(self.datamodel_a, name)
        segmentation_b = query_seg(self.datamodel_b, name)
        self.assertEqual(len(segmentation_a), len(segmentation_b))


    def test_query_reference(self):
        modality = "SEG"
        name = namelist[4]
        segmentation_a = query_seg(self.datamodel_a, name)
        segmentation_b = query_seg(self.datamodel_b, name)
        reference_a = query_reference(self.datamodel_a, segmentation_a[0])
        reference_b = query_reference(self.datamodel_b, segmentation_b[0])
        self.assertEqual(len(reference_a), len(reference_b))
        name = namelist[5]
        segmentation_a = query_seg(self.datamodel_a, name)
        segmentation_b = query_seg(self.datamodel_b, name)
        reference_a = query_reference(self.datamodel_a, segmentation_a[0])
        reference_b = query_reference(self.datamodel_b, segmentation_b[0])
        self.assertEqual(len(reference_a), len(reference_b))

    def test_get_numberof_instances(self):
        name = namelist[5]
        number_of_instances_a = query_number_of_instances(self.datamodel_a, name)
        number_of_instances_b = query_number_of_instances(self.datamodel_b, name)
        self.assertEqual(number_of_instances_a, number_of_instances_b)
        name = namelist[6]
        number_of_instances_a = query_number_of_instances(self.datamodel_a, name)
        number_of_instances_b = query_number_of_instances(self.datamodel_b, name)
        self.assertEqual(number_of_instances_a, number_of_instances_b)
