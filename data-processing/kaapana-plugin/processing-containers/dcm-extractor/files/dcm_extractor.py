import os
from pathlib import Path
import json
import pydicom

def predict_modality(dcm_file: str, modality: str):
    """
    If dicom modality tag is "CT" and ImageType tag contains "Localizer", "CT" (3D) is changed to "XR" (2D)
    :param dcm_file: path to first slice of dicom image
    :param modality: dicom modality tag
    :return: _description_
    """
    if modality=="CT":
        # check if projection is localizer
        dcm_slice = pydicom.dcmread(dcm_file)
        if hasattr(dcm_slice, 'ImageType') and len(dcm_slice.ImageType)>=3:
            img_type = dcm_slice.ImageType[2]
            return "XR" if img_type=='LOCALIZER' else "CT"
        else:
            return "CT"
    else:
        return modality


if __name__ == "__main__":
    batch_folders = Path(os.environ["WORKFLOW_DIR"]).joinpath(os.environ["BATCH_NAME"]).glob('*')

    for batch_element_dir in batch_folders:
        
        element_input_dir = batch_element_dir.joinpath(os.environ['OPERATOR_IN_DIR'])
        json_input_dir = batch_element_dir.joinpath(os.environ['OPERATOR_IN_JSON']) #metadata json dict
        element_output_dir = batch_element_dir.joinpath(os.environ['OPERATOR_OUT_DIR'])
        Path(element_output_dir).mkdir(parents=True, exist_ok=True)
        
        id_name = batch_element_dir.name
        input_path = Path(str(json_input_dir.joinpath(id_name)) + ".json")
        output_path = Path(str(element_output_dir.joinpath(id_name)) + ".json")
        
        with open(input_path) as f:
            json_dict = json.load(f)
        dcm_files = list(element_input_dir.rglob('*.dcm'))
        
        predicted_modality = predict_modality(dcm_file=dcm_files[0], modality=json_dict["00080060 Modality_keyword"])
        
        json_dict_extracted = {"curated_modality": predicted_modality}
        
        json_dict.update(json_dict_extracted)
        
        with open(output_path, "w", encoding='utf-8') as f:
            json.dump(json_dict, f, indent=4, sort_keys=True, ensure_ascii=True)