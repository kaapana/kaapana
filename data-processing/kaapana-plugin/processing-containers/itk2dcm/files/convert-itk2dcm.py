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

#http://dicomlookup.com/modalities.asp
VALID_MODALITIES = ["CR", "CT", "MR", "US", "OT", "BI", "CD", "DD", "DG", "ES", "LS", "PT", "RG", "ST", "TG", "XA", "RF", "RTIMAGE", "RTDOSE", "RTSTRUCT", "RTPLAN", "RTRECORD", "HC", "DX", "NM", "MG", "IO", "PX", "GM", "SM", "XC", "PR", "AU", "EPS", "HD", "SR", "IVUS", "OP", "SMR"]

def make_out_dir(series_uid, dataset, case, segmentation=False, human_readable=False):
    # operator_output = "/data/output" 
    batch_output = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME']) #, os.environ['OPERATOR_OUT_DIR'])
    if not os.path.exists(batch_output):
        os.mkdir(batch_output)
    if human_readable:
        case_dir = Path(batch_output)/dataset/str(case).split(".")[0]
    else:
        case_dir = Path(f"{batch_output}/{series_uid}/{os.environ['OPERATOR_OUT_DIR']}")
        
    case_dir.mkdir(exist_ok=True, parents=True)
    return case_dir


class Nifti2DcmConverter:
    """ Converter for itk compatible file formats as nifti and nrrd to dicom. Since these formats do 
    not include all necessary meta information, it is possible to provide additional meta information 
    on a 'per study' basis. (See __call__(self, ...))
    """
    def __init__(self, root_dir: Path, parser=None, seed=42):
        self.parser = parser or Parser()
        self.seed = str(seed)
        self.root_dir = root_dir #self.get_root()
    
    def __call__(self):
        """ Run the converter on a path with either the following directory structure:

        path
        |----dataset
        |    | meta_data.json
        |    | seg_info.json
        |    | series1.nii.gz
        |    | series1_seg.nii.gz
        |    | series2.nii.gz
        |    | series2_seg.nii.gz
        |    | ...

        or a Dataset directory structure of the nnU-Net (https://github.com/MIC-DKFZ/nnUNet) 

        The meta_data.json can be used to set DICOM tags. The expected structure is as follows:
        {
            "global_tags": {
                "0008|0060": "MR"
            },
            "series_tags": {
                "Case00.nii": {
                    "0008|103e": "I am unique"
                }
            }
        }

        where global tags are written to all dicoms and series tags only to the specific file specified by the filename. 

        In case of the Dataset directory structure of the nnU-Net, the file is created automatically based on the dataset.json.

        Good to know:
        - Unique identifier for series: study_id, parent folder_name and filename!
        - Enforce same study instance uid by specifying the study_id (0020|0010)!
        """
        # TODO: In theory it would be possible to derive a minimal set of segmentation args from the given files. Probably nice to have in the future.
        
        self.convert_dataset(self.root_dir)


    def convert_dataset(self, path):
        print(path)
        cases = self.parser(path, log='Info')

        try:
            with open(self.root_dir / "meta_data.json", "r") as meta_file:
                meta_data = json.load(meta_file)
        except FileNotFoundError:
            meta_data = {}


        def _update_tag(series_tag_values, pattern, k, v):
            if not pattern.match(k):
                raise Exception(r"Not a valid dicom tag! Needs to fullfil the followinr regex ^([a-f0-9]{4})\|([a-f0-9]{4})$")
            print(f"Setting {k}={v}")
            series_tag_values[k] = v

        for i, case in enumerate(cases):
            case_path = Path(case[0])
            # defaults
            series_tag_values = {
                "0008|0008": "DERIVED\\SECONDARY", # Image Type Attribute
                "0008|0031": time.strftime("%H%M%S"), # Series Time Attribute
                "0008|0021": time.strftime("%Y%m%d"), # Series Date Attribute
                "0008|0060": os.getenv("MODALITY", "OT"), # Modality
                "0008|1070": case_path.parents[0].name, # Operators' Name Attribute
                "0020|0011": str(i), # Series Number 
                "0008|103E": f"{str(case[0].name).rstrip(''.join(case[0].suffixes))}", # Series Description Attribute
                "0020|0010": str(case[0].name).rstrip(''.join(case[0].suffixes)) # Study ID Attribute
            }

            pattern = re.compile(r"^([a-f0-9]{4})\|([a-f0-9]{4})$")

            for k, v in meta_data.get("global_tags", {}).items():
                _update_tag(series_tag_values, pattern, k, v)
            
            for path_posix, series_tags in meta_data.get("series_tags", {}).items():
                if path_posix in str(case_path):
                    for k, v in series_tags.items():
                        _update_tag(series_tag_values, pattern, k, v)

            # Derived and generated tags: 
            if "0010|0020" not in series_tag_values: # Patient ID Attribute
                series_tag_values["0010|0020"] = series_tag_values["0020|0010"] # Fallback
            if "0010|0010" not in series_tag_values: # Patient's Name Attribute
                series_tag_values["0010|0010"] = series_tag_values["0010|0020"] # Fallback
            if "0020|000d" not in series_tag_values: # Study Instance UID
                series_tag_values["0020|000d"] =  generate_uid(entropy_srcs=[series_tag_values["0020|0010"], series_tag_values["0008|1070"], self.seed])
            if "0020|000e" not in series_tag_values: # Series Instance UID
                series_tag_values["0020|000e"] =  generate_uid(entropy_srcs=[series_tag_values["0020|000d"], str(case[0].name), self.seed])


            self.convert_series(
                case_path, 
                series_tag_values=series_tag_values,
                segmentation=case[1]
            )
        

    def convert_series(self, case_path, series_tag_values, segmentation=None):
        """
        :param data: data to process given as list of paths of the ".nii.gz" files to process.
        
        :returns: None type. Writes dicoms to $OPERATOR_OUT_DIR.
        """
        dataset = str(case_path).split('/')[-2]

        if series_tag_values["0008|0060"] not in VALID_MODALITIES:
            raise Exception("Invalid modality!")

        if series_tag_values["0008|0060"] == "OT":
            warnings.warn("Modality is 'other' (OT). Unspecific modality does not not support correct representation of translation and rotation.", UserWarning)

        out_dir = make_out_dir(series_tag_values["0020|000e"], dataset=dataset, case=series_tag_values["0020|000e"], segmentation=segmentation, human_readable=False)

        new_img = sitk.ReadImage(str(case_path)) 

        direction = new_img.GetDirection()

        series_tag_values["0020|0037"] = '\\'.join(map(str, (direction[0], direction[3], direction[6], direction[1],direction[4],direction[7])))

        castFilter = sitk.CastImageFilter()
        castFilter.SetOutputPixelType(sitk.sitkInt16)
        imgFiltered = castFilter.Execute(new_img)
        
        # with open(out_dir / "atags.json", "w", encoding='utf-8') as jsonData:
        #     json.dump(series_tag_values, jsonData, indent=2, sort_keys=True, ensure_ascii=True)

        for i in range(imgFiltered.GetDepth()):
            self.write_slices(imgFiltered, series_tag_values, i, out_dir) #/'dicoms')
        print("***", out_dir, "written.")
        

        if segmentation:
            seg_out_dir = Path(os.environ['BATCHES_INPUT_DIR']) / series_tag_values["0020|000e"] / 'segmentations'
            seg_out_dir.mkdir(exist_ok=True)
            print("### Checking for segmentation information.")
            shutil.copy2(segmentation, seg_out_dir)
            print("### Passing seg_info.json to segmentation converter.")
            shutil.copy2( self.root_dir / "seg_info.json", seg_out_dir)
            

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

        # str_segs = [str(s) for s in segs]
        case_identifier = {re.sub(r"\.nii(.gz)?", "", c.name): c for c in cases}

        cases_without_segs = []
        cases_with_segs = []
        for k, v in case_identifier.items():
            seg_canditate = None
            for s in segs:
                if s.name.startswith(k):
                    if seg_canditate is None:
                        seg_canditate = s
                    else:
                        raise Exception("Duplicate identifiers...")
            if seg_canditate is None:
                cases_without_segs.append((v, seg_canditate))
            else:
                cases_with_segs.append((v, seg_canditate))
        
        res = [*cases_with_segs, *cases_without_segs]
        return res


class nnUNetDatasetParser:
    """Parser for nifti or nrrd files. Lists all cases to process within a certain directory, along with the respective segmentation files. 
    Can be overwritten to support custom file trees.
    """

    @staticmethod
    def create_info_files(path, cases):
        with open(path / 'dataset.json' , 'r') as f:
            dataset_json = json.load(f)
    
        # Creating seg_info.json from datset.json
        seg_info_json = {
            "algorithm": dataset_json.get("name", path.name),
            "seg_info": []
        }
        for k, v in dataset_json["labels"].items():
            seg_info_json["seg_info"].append(
                {
                    "label_int": v,
                    "label_name": k
                }
            )

        with open(path / "seg_info.json", "w", encoding='utf-8') as jsonData:
            json.dump(seg_info_json, jsonData, indent=2, sort_keys=True, ensure_ascii=True)

        # Creating meta_data.json from datset.json
        series_tags = {}
        for case in cases:
            case_path = case[0]
            matches = re.findall(r"_[0-9]{4}\.", str(case_path.name))
            if matches and len(matches) == 1:
                channel_identifier = matches[0][1:-1]
                study_id = str(case_path.name).replace(matches[0], ".").rstrip(''.join(case_path.suffixes))
                target_tags = {
                    "0020|0010": study_id # Study ID Attribute
                }
                for channel, v in dataset_json["channel_names"].items():
                    if channel_identifier.endswith(channel):
                        v = v.replace("MRI", "MR").replace("MRT", "MR")
                        if v in VALID_MODALITIES:
                            target_tags["0008|0060"] = v
                        else:
                            target_tags["0008|0060"] = "MR"
                            target_tags["0018|1030"] = v
                        if case_path.name in series_tags:
                            raise Exception("You do not want to overwrite me")
                        series_tags[case_path.name] = target_tags
                if case_path.name not in series_tags:
                    raise Exception("I think you forgot me!")
            else:
                raise Exception("Problem identifying the channel!")

        meta_data_json = {
            "series_tags": series_tags
        }
        with open(path / "meta_data.json", "w", encoding='utf-8') as jsonData:
            json.dump(meta_data_json, jsonData, indent=2, sort_keys=True, ensure_ascii=True)


    def __init__(self) -> None:
        pass

    def __call__(self, path, *args, **kwds):
        def _get_cases(images_path, labels_path):

            images = list(images_path.glob('*'))
            labels = list(labels_path.glob('*'))

            images_with_segs = []
            images_without_segs = []
            for ct in images:
                if re.findall(r"_[0000]{4}\.", str(ct)):
                    images_with_segs.append(ct)
                else:
                    images_without_segs.append(ct)
            if len(labels) > 0:
                assert len(images_with_segs) == len(labels)

            images_with_segs.sort()
            images_without_segs.sort()
            labels.sort()
            images.sort()

            cases_with_segs = [(ct, seg) for ct, seg in zip(images_with_segs, labels)]
            cases_without_segs =  [(ct, None) for ct in images_without_segs]

            return [*cases_with_segs, *cases_without_segs]
        
        path = Path(path)
        cases = _get_cases(path / 'imagesTr', path / 'labelsTr') + _get_cases(path / 'imagesTs', path / 'labelsTs') 
        nnUNetDatasetParser.create_info_files(path, cases)
        return cases

if __name__ == "__main__":
    for root, dirs, files in os.walk(Path(os.environ['WORKFLOW_DIR']) / os.environ['OPERATOR_IN_DIR']):
        parser = None
        dataset_json = Path(root) / "dataset.json"
        if dataset_json.is_file():
            print("nnUNet dataset!")
            parser = nnUNetDatasetParser()
        elif not parser and len(files) > 0 and not root.endswith("segs") and not root.endswith("cases") and not root.endswith("imagesTr") and not root.endswith("imagesTs") and not root.endswith("labelsTr"):
            print("Custom dataset!")
            parser = Parser()
        else:
            print(f'Skipping directory {root}')
        if parser:
            converter = Nifti2DcmConverter(Path(root), parser=parser)
            converter()
        parser = None
