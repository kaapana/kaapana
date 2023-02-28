import os
import re
import time
import json 
import shutil
import glob 
import warnings

import SimpleITK as sitk

from pathlib import Path
from pydicom.uid import generate_uid


def make_out_dir(series_uid, dataset, case, segmentation=False, human_readable=False):
    # operator_output = "/data/output" 
    batch_output = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME']) #, os.environ['OPERATOR_OUT_DIR'])


    os.environ["OPERATOR_OUT_DIR"] if os.environ[ "OPERATOR_OUT_DIR"] is not None else "/data/output"
    
    if not os.path.exists(batch_output):
        os.mkdir(batch_output)
    if human_readable:
        case_dir = Path(batch_output)/dataset/str(case).split(".")[0]
    else:
        case_dir = Path(f"{batch_output}/{series_uid}/{os.environ['OPERATOR_OUT_DIR']}")
    dicom_dir =  case_dir/ 'dicoms' # Dicom Directory
    dicom_dir.mkdir(exist_ok=True, parents=True)
    
    if segmentation:
        nii_segmentation_dir = case_dir / 'segmentations'
        nii_segmentation_dir.mkdir(exist_ok=True, parents=True)
    
    return case_dir


class Nifti2DcmConverter:
    """ Converter for itk compatible file formats as nifti and nrrd to dicom. Since these formats do 
    not include all necessary meta information, it is possible to provide additional meta information 
    on a 'per study' basis. (See __call__(self, ...))
    """
    def __init__(self, meta_data=None, seed=42):
        self.parser = Parser()
        self.seed = str(seed)
        self.root_dir = self.get_root()
        self.workflow_conf = self.get_workflow_conf()
        self.data_dir = self.get_data_dir()
        self.meta_data = self.get_metadata()

    def get_root(self):
        return os.path.join("/" + os.environ.get("WORKFLOW_DIR"),os.environ.get("OPERATOR_IN_DIR"))

    def get_workflow_conf(self):
        with open("/data/conf/conf.json", 'r') as conf_file:
            workflow_conf = json.load(conf_file)
        return workflow_conf

    def get_data_dir(self):
        data_dir = self.workflow_conf.get("workflow_form").get("data_dir")
        return data_dir
        
        
    def get_metadata(self):
        try:
            with open(os.path.join(f"/{self.root_dir}", self.data_dir, "meta_data.json"), "r") as meta_file:
                meta_data = json.load(meta_file)

        except FileNotFoundError:
            meta_data = {}
        return meta_data

        
    
    def __call__(self):
        """ Run the converter on a path with the following directory structure:

        path
        |----dataset
        |    | meta_data.json
        |    | seg_info.json
        |    | series1.nii.gz
        |    | series1_seg.nii.gz
        |    | series2.nii.gz
        |    | series2_seg.nii.gz
        |    | ...


        The meta_data.json can be used to set values for patient ids, study uids, series ids and also arbitrary dicom tags. The expected structure is as follows:

        {
            'Patients': 'all_same' | 'all_different' | [name1, name2, ..., nameN],
            'Study UIDs': 'all_same' | 'all_different' | [study1, study2, ..., studyN],
            'Modality': 'MR' | 'CT' | 'OT' | ...   # any valid value listed under dicom tag (0008,0060) 
            'Series instance UID': [series_instance_uid1, series_instance_uid1, ..., series_instance_uidN]
            'Series descriptions': some_description | [desc1, desc2, ..., descN],
            
            'add_tags': {
                '/some/path/*nii.gz':{
                    '(xxxx|xxxx)': tag_value,
                    ...
                }
            }

            'seg_args': {
                'input_type': 'multi_label_seg' | 'single_label_segs',
                'single_label_seg_info': 'prostate',
                'multi_label_seg_info_json': 'seg_info.json'
            }
        }

        All fields are optional, but it is highly recommended, to at least set the modality since the default is set to "OT" i.e. "Other" which will omit necessary positioning data for image processing.
        The field "add_tags" allows to set specific tags on all series matching the given file name pattern. At the moment this is just a simple glob pattern matching.
        If needed we could also add regex syntax here, but for now this seems unnecessarily complex.

        The 'seg_args' parameter passes arguments to the Itk2DcmSegOperator which is responsible for the conversion of the segmentation objects if any are present.
        If there are no segmentation files 'seg_args' will be ignored.
        """
        # TODO: In theory it would be possible to derive a minimal set of segmentation args from the given files. Probably nice to have in the future.



        # dataset = self.workflow_conf.get("workflow_form").get("data_dir")
        
        self.convert_dataset(Path(self.root_dir)/self.data_dir, self.meta_data)


    def convert_dataset(self, path, meta_data={}):

        cases = self.parser(path, log='Info')

        patients = meta_data.get("Patients") if meta_data.get("Patients") else "all_different"
        # series_filenames = glob.glob()
        if patients == 'all_same':
            patients = ['single_patient' for _ in range(len(cases))]
        elif patients == 'all_different':
            patients = [f'patient_{i}' for i in range(len(cases))]
        else:
            if not isinstance(self.patients, list):
                raise AttributeError("Patients attribute must be 'all_same', 'all_different' or list of patients.") 
            for pat in self.patients:
                if not isinstance(pat, str):
                    raise AttributeError("Patient list must be list of strings.")

        # generate study uids
        study_instance_UIDs = meta_data.get("Study UIDs", 'all_same')
        if study_instance_UIDs == "all_same":
            study_instance_UIDs = [generate_uid(entropy_srcs=[str(patients[i]), self.seed]) for i in range(len(patients))]
        elif study_instance_UIDs == "all_different":
            study_instance_UIDs = [generate_uid(entropy_srcs=[str(patients[i]), str(case[0]), self.seed]) for i,case in enumerate(cases)]
        else:
            assert(isinstance(study_instance_UIDs, list))
            assert(len(study_instance_UIDs) == len(patients))

        
        series_descriptions = meta_data.get("Series Descriptions") if meta_data.get("Series descriptions") else [None for _ in range(len(cases))]
        modality = meta_data.get("Modality") if meta_data.get("Modality") else "OT"
        added_tags = meta_data.get("add_tags")
        
        seg_args = None
        seg_path = None
        # check if there are volumes with associated segmentations
        if any([s != None for _, s in cases]):
            # check if there are seg_args in meta_data
            try:
                seg_args = meta_data['seg_args']
                seg_path = path/seg_args['multi_label_seg_info_json'] if seg_args['multi_label_seg_info_json'] else None

                # print("### Checking for segmentation information.")
                if seg_args is not None:
                    print("### Extracting parameters for segmentation converter.")                    
                    self.workflow_conf["seg_args"] = seg_args
                    with open("/data/conf/conf.json", 'w+') as conf_file:
                        # conf = json.load(conf_file)
                        json.dump(self.workflow_conf, conf_file)
                print("### Processing segmentation parameters finished.")
            except KeyError:
                print("No arguments for Itk2DcmSegOperator found. Please provide 'seg_args' in the 'meta_data.json'.")
                seg_args = make_seg_args()

        for i, case in enumerate(cases):
            series_tag_values = {}
            # series_tag_values["0020|0010"] = # study_id
            series_tag_values["0020|000d"] = study_instance_UIDs[i]
            series_tag_values["0020|0011"] = str(i)
            if added_tags is not None:
                for p in added_tags.keys():
                    p = f"/{p}" if p[0] != "/" else p
                    if str(case[0]) in glob.glob(f"{str(path)}{p}"):
                        series_tag_values= {**series_tag_values, **added_tags[p]}

            self.convert_series(
                Path(case[0]), 
                patient_id=patients[i], 
                series_description=series_descriptions[i], 
                modality=modality, 
                series_tag_values=series_tag_values,
                seg_args=seg_args,
                segmentation=case[1],
                seg_info_path=seg_path or None
            )
        

    def convert_series(self, case_path, patient_id, series_tag_values, segmentation=None, seg_args=None, seg_info_path=None, *args, **kwds):
        """
        :param data: data to process given as list of paths of the ".nii.gz" files to process.
        
        :returns: None type. Writes dicoms to $OPERATOR_OUT_DIR.
        """
        series_id = str(case_path).split('/')[-1].split('.')[0]
        series_description = kwds.get("series_description")
        dataset = str(case_path).split('/')[-2]
        if series_description == None:
            series_description = f"{str(case_path).split('/')[-2]}-{series_id}-{patient_id}"
    
        modality = kwds.get("modality") or "OT"
        if modality == "OT":
            warnings.warn("Modality is 'other' (OT). Unspecific modality does not not support correct representation of translation and rotation.", UserWarning)


        study_uid = series_tag_values['0020|000d']
        series_instance_UID = kwds.get("series_uid") or generate_uid(entropy_srcs=[patient_id, study_uid, series_id, self.seed])
        out_dir = make_out_dir(series_instance_UID, dataset=dataset, case=series_id, segmentation=segmentation, human_readable=False)

        new_img = sitk.ReadImage(case_path) 
        modification_time = time.strftime("%H%M%S")
        modification_date = time.strftime("%Y%m%d")

        direction = new_img.GetDirection()
        
        if "0008|0008" in series_tag_values.keys():
            pass
        else:
            series_tag_values["0008|0008"] = "DERIVED\\SECONDARY" # Image Type

        series_tag_values["0008|0031"] = modification_time # Series Time
        series_tag_values["0008|0021"] = modification_date # Series Date
        series_tag_values["0020|0037"] = '\\'.join(map(str, (direction[0], direction[3], direction[6], direction[1],direction[4],direction[7])))
        series_tag_values["0008|103e"] = series_description # Series Description
        series_tag_values["0020|000e"] = series_instance_UID
        series_tag_values["0008|0060"] = modality
        series_tag_values["0010|0020"] = patient_id
        
        
        castFilter = sitk.CastImageFilter()
        castFilter.SetOutputPixelType(sitk.sitkInt16)
        imgFiltered = castFilter.Execute(new_img)
        
        for i in range(imgFiltered.GetDepth()):
            self.write_slices(imgFiltered, series_tag_values, i, out_dir/'dicoms')
        print("***", out_dir, "written.")
        

        if segmentation:
            print("### Checking for segmentation information.")
            shutil.copy2(segmentation, out_dir/'segmentations/')
            # if seg_args is not None:
            # print("### Copying segmentatin file.")

            if seg_info_path:
                print("### Passing seg_info.json to segmentation converter.")
                #study_dir = '/'.join(str(path).split('/')[:-1])
                shutil.copy2(seg_info_path, out_dir/'segmentations/')
        #     print("### Processing segmentation parameters finished.")
            

    def write_slices(self, new_img, series_tag_values, i, out_dir):
        image_slice = new_img[:,:,i]
        writer = sitk.ImageFileWriter()
        writer.KeepOriginalImageUIDOn()
        
        patient_id = series_tag_values["0010|0020"]
        study_uid = series_tag_values["0020|000d"]
        series_uid = series_tag_values["0020|000e"]

        prefix = ".".join(series_uid.split(".")[:4])+"." # ugly syntax for strap the prefix from the series uid and reuse it for slice identifier but w/e
        slice_instance_uid = generate_uid(prefix=prefix, entropy_srcs=[patient_id, study_uid, series_uid, str(i), self.seed])

        series_tag_values["0008|0018"] = slice_instance_uid

        # set metadata shared by series
        for tag, value in series_tag_values.items():
            image_slice.SetMetaData(tag, value)

        # set slice specific metadata tags.
        image_slice.SetMetaData("0008|0012", time.strftime("%Y%m%d")) # Instance Creation Date
        image_slice.SetMetaData("0008|0013", time.strftime("%H%M%S")) # Instance Creation Time

        # (0020, 0032) image position patient determines the 3D spacing between slices.
        image_slice.SetMetaData("0020|0032", '\\'.join(map(str,new_img.TransformIndexToPhysicalPoint((0,0,i))))) # Image Position (Patient)
        image_slice.SetMetaData("0020|0013", str(i)) # Instance Number

        # Write to the output directory and add the extension dcm, to force writing in DICOM format.
        writer.SetFileName(os.path.join(out_dir,'slice' + str(i).zfill(4) + '.dcm'))
        writer.Execute(image_slice)



class Parser:
    """Parser for nifti or nrrd files. Lists all cases to process within a certain directory, along with the respective segmentation files. 
    Can be overwritten to support custom file trees.
    """
    def __init__(self) -> None:
        pass

    def __call__(self, path, *args, **kwds):
        def get_depth(path, depth=0):
            if not os.path.isdir(path): return depth
            maxdepth = depth
            for entry in os.listdir(path):
                fullpath = os.path.join(path, entry)
                maxdepth = max(maxdepth, get_depth(fullpath, depth + 1))
            return maxdepth
    
        if os.path.isdir(os.path.join(path, "cases")) and os.path.isdir(os.path.join(path, "segs")):
            return self.parse_by_structure(path, *args, **kwds)
        elif get_depth(path) == 1:
            return self.parse_combined_dir(path, *args, **kwds)
        else:
            raise FileNotFoundError("Could not parse file structure, please verify input data.")
        

    def parse_combined_dir(self,path, *args, **kwds):
        
        cases = [f for f in Path(path).rglob("*") if (re.match(r'^(?!.*(?:seg|Seg|segmentation|Segmentation)).*$', str(f.name)) and re.search(r"[0-9]*.\.nii(.gz)?", str(f.name)) ) ]
        segs = [f for f in Path(path).rglob("*") if re.search(r"[sS]eg(mentation)?\.nii(\.gz)?", str(f.name))]

        return self.zip_cases_with_segs(cases, segs)

    def parse_by_structure(self, path, *args, **kwds):
        img_dir = os.path.join(path, "cases")
        seg_dir = os.path.join(path, "segs")
        cases = glob.glob(os.path.join(img_dir, "*.nii*"))  # TODO: use a proper regex to specifically filter for .nii, .nii.gz and .nrrd
        segs = glob.glob(os.path.join(seg_dir, "*.nii*"))
        
        return self.zip_cases_with_segs(cases, segs, **kwds)


    def zip_cases_with_segs(self, cases, segs, *args, **kwds):
        cases.sort()
        segs.sort()
        if kwds.get("log") in ["Info", "Debug"]:
            print("----cases----")
            for x in cases: print(x)
            print("----segs-----")
            for x in segs: print(x)

        str_segs = [str(s) for s in segs]
        c_names = [os.path.basename(str(c)).split(".") for c in cases]
        s_names = [os.path.basename(str(s)).split(".") for s in segs]

        case_nr = [re.findall(r'\d+', str(c)) for c in c_names]
        seg_nr = [re.findall(r'\d+', str(s)) for s in s_names]

        c_l = [len(case_nr[i]) != 1 for i in range(len(cases))]
        s_l = [len(seg_nr[i]) != 1 for i in range(len(segs))]

        case_nr = [c[0] for c in case_nr]
        seg_nr = [s[0] for s in seg_nr]

        if any(c_l) or any(s_l):
            raise AttributeError("Input file names have multiple numeric values, as a result matching images to segmentations is ambiguous. Please rename your files in a consistent way.")

        seg_dict = {seg_nr[i]: seg for i, seg in enumerate(segs)}
        cases_with_segs = [(cases[i], seg_dict[case_nr[i]]) for i in range(len(cases)) if case_nr[i] in seg_dict.keys()]
        cases_without_segs = [(cases[i], None) for i in range(len(cases)) if case_nr[i] not in seg_dict.keys()]
        print("cases with segs:")
        for c in cases_with_segs:
            print(c)
        print("cases without segs")
        for c in cases_without_segs:
            print(c)

        
        res = [*cases_with_segs, *cases_without_segs]
        return res

def make_seg_args():
    import os
    import json
    json_path = os.path.join(os.environ['OPERATOR_IN_DIR'], 'seg_info.json')
    # case1: seg_info.json exists
    seg_args = {}
    try:
        with open(json_path, 'r') as f:
            seg_info_json = json.load(f)
            seg_args['input_type'] = "multi_label_seg"
            seg_args['multi_label_seg_info_json'] = "seg_info.json"
    except FileNotFoundError:
    # case2: seg_info for label comes from workflow argument
        try:
            with open("/data/conf/conf.json", 'r') as conf_file:
                conf = json.load(conf_file)
                seg_args['input_type'] = "single_label_segs"
                seg_args['single_label_seg_info']= conf['workflow_form']["seg_info"]
            print("No seg_info.json found. Assuming single label segmentation with label:{}")
        except KeyError as e:
            print("Could not find seg_info or workflow_form.")
            raise e
    
    # case3: seg_info for label comes from file_name
    seg_args['input_type'] = "single_label_segs"
    seg_args['single_label_seg_info'] = "from_file_name"
    
    # if there is also more than one segmentation per image file:
    seg_args['create_multi_label_dcm_from_single_label_segs'] = True

    return seg_args

if __name__ == "__main__":
    converter = Nifti2DcmConverter()
    converter()