import importlib
import os
import shutil
import sys
from typing import Callable, Dict, Optional, Any, Sequence, List
from pathlib import Path
import numpy as np
import SimpleITK as sitk

from loguru import logger
from omegaconf import OmegaConf
import nndet.io


def get_env_param(name: str, mandatory: bool = True, dtype: Optional[Callable] = None, default: Optional[Any] = None):
    """
    Get environment variable and convert to output dtype
    :param name: name of environment variable
    :param mandatory: defaults to True
    :param dtype: defaults to None, if specificed env param is converted to dtype
    :param default: environment variable is set to default if not defined and not mandatory
    :raises ValueError: if environment variable is mandatory and not defined
    :return: value of environment variable
    """
    param = os.getenv(name, "none")
    param = param if param.lower() != "none" else None
    if param is None and mandatory:
        print("#")
        print("##################################################")
        print("#                                                #")
        print(f"# Mandatory param: {param} is missing....       #")
        print("#                                                #")
        print("##################################################")
        print("#")
        raise ValueError(f"{param} can not be None!")
    elif param is None and not mandatory:
        param = default
        
    if param is not None and dtype is not None:
        param = dtype(param)
        
    return param
    
    
class NnDetKaapanaInterface():
    def __init__(
        self,
        ) -> None:
        """
        Helper class for nndetection

        Args:
            prediction_dir: directory where model predictions are saved
            output_dir: directory to copy final output / prediction into
        """
        super().__init__()
        self.det_models = Path(get_env_param("det_models"))
        self.det_data = Path(get_env_param("det_data"))
        self.task = get_env_param("TASK", dtype=str)
        self.model = get_env_param("MODEL", dtype=str)
        self.fold = get_env_param("FOLD", dtype=str)
        self.rename_files_dict = {}  # replace "." by "_" in filenames for nndet
        
        # non-mandatory parameters
        self.n_models = get_env_param("N_MODELS", mandatory=False, dtype=str)
        self.ntta = get_env_param("NTTA", mandatory=False, dtype=str)
        self.ov = get_env_param("OVERWRITES", mandatory=False)
        if self.ov is not None:
            self.ov = self.ov.split(" ")
        self.no_preprocess = get_env_param("NO_PREPROCESS", mandatory=False, dtype=lambda x: bool(int(x)), default=False,)
        self.check = get_env_param("CHECK", mandatory=False, dtype=lambda x: bool(int(x)))
        self.num_processes_preprocessing = get_env_param("NUM_PROCESSES_PREPROCESSING", mandatory=False, dtype=int, default=3)
        
        self.__print_init_nndet()
        
        all_tasks = [d.stem for d in self.det_models.iterdir() if d.is_dir() and "Task" in d.name]
        print("Tasks: ", all_tasks)
        
        self.task_name = nndet.io.get_task(self.task, name=True, models=True)
        self.training_dir = nndet.io.get_training_dir(Path(self.det_models) / self.task_name / self.model, self.fold)
        self.fold_str = f"fold{self.fold}" if self.fold != -1 else "consolidated"
        
        # data will be copied to this directory with correct naming
        self.data_target_dir = self.det_data / self.task_name / "raw_splitted" / "imagesTs"
        self.data_target_dir_preprocessed = self.det_data / self.task_name / "preprocessed"
        # results will be located here after prediction
        self.model_prediction_dir = self.det_models / self.task_name / self.model / self.fold_str / "test_predictions"
        # boxes to mask
        self.model_prediction_dir_nii = Path(str(self.model_prediction_dir) + "_nii")
        
        self.cfg = self.__update_kaapana_nndet_config()
       

    def __update_kaapana_nndet_config(self):
        # overwrite data and model dir in training config
        cfg_path = str(self.training_dir / "config.yaml")
        cfg = OmegaConf.load(cfg_path)
        # support legacy models
        overwrites = self.ov if self.ov is not None else []
        overwrites.append("host.parent_data=${env:det_data}")
        overwrites.append("host.parent_results=${env:det_models}")
        cfg.merge_with_dotlist(overwrites)
        OmegaConf.save(cfg, cfg_path)
        
        for imp in cfg.get("additional_imports", []):
            print(f"Additional import found {imp}")
            importlib.import_module(imp)
        return cfg

    def __print_init_nndet(self):
        print("##################################################")
        print("#")
        print("# nnDetection Parameters: ")
        print("#")
        print(f"# task:  {self.task}")
        print(f"# model:  {self.model}")
        print(f"# fold: {self.fold}")
        print("#")
        print(f"# n_models: {self.n_models}")
        print(f"# ntta: {self.ntta}")
        print(f"# overwrites: {self.ov}")
        print("#")
        print(f"# no_preprocess: {self.no_preprocess}")
        print(f"# check: {self.check}")
        print("#")
        print(f"# num_processes_preprocessing: {self.num_processes_preprocessing}")
        print("#")
        print("##################################################")
        print("#")
        
    
    def create_dataset(self, nifti_dir, copy_target_data: bool):
        """
        Prepares kaapana input dataset structure for nndetection
        :param nifti_dir: kaapana input data dir
        :param copy_target_data: if True, data is copied from search_dir to target_dir, otherwise it's moved
        :return: number of nifti files in target_dir
        """
        self.data_target_dir.mkdir(exist_ok=True, parents=True)

        modality_count = 0  # ToDo: how to assign modality count from input_modality subdir? If there are several datasets per patient?

        print(f"# Searching NIFTIs at {nifti_dir}.")
        nifti_list = nifti_dir.glob("**/*.nii.gz")

        for input_filename in nifti_list:
            input_name = input_filename.name.replace(".nii.gz", "")
            target_name = str(input_name).replace(".", "_")
            self.rename_files_dict[target_name] = input_name
            target_name += f"_{modality_count:04d}"
            # nndet cannot handle "." in filename, replace with "_"
            target_filename = (self.data_target_dir / target_name).with_suffix(".nii.gz")

            if target_filename.exists():
                print(
                    f"# Target input-data {target_filename} already exists -> skipping"
                )
                continue

            if copy_target_data:
                print(f"# Copy file {input_filename} to {target_filename}")
                shutil.copy2(input_filename, target_filename)
            else:
                print(f"# Moving file {input_filename} to {target_filename}")
                shutil.move(input_filename, target_filename)
            modality_count += 1
        input_count = len(list(self.data_target_dir.glob("**/*.nii.gz")))
        return input_count
        
    def format_kaapana_input_for_nndet(self, batch_folder_list: List, operator_in_dir: str):
        """reformats directory and file structure for nndet

        :param batch_folder_list: list of kaapana subdirectories inside batch to read input
        :param operator_in_dir: input operator identifier
        """
        
        print("#")
        print("##################################################")
        print("#")
        print("# Starting directory and file structure restructuring for nndet ...")
        print("#")
        print("##################################################")
        print("#")
        
        processed_count = 0
        
        for batch_element_dir in batch_folder_list:

            input_count = self.create_dataset(
                nifti_dir=batch_element_dir.joinpath(operator_in_dir),
                copy_target_data=True,
            ) 
            
            if input_count == 0:
                print("#")
                print("##################################################")
                print("#")
                print("# No NIFTI files found on batch-element-level!")
                print("#")
                print("##################################################")
                print("#")
                break
            else:
                processed_count += 1
        
        if processed_count == 0:
            print("#")
            print("##################################################")
            print("#")
            print("##################  ERROR  #######################")
            print("#")
            print("# ----> NO FILES HAVE BEEN PROCESSED!")
            print("#")
            print("##################################################")
            print("#")
            exit(1)
        else:
            print("#")
            print(f"# ----> {processed_count} FILES HAVE BEEN PROCESSED!")
            print("#")
            
            
    def inference(self):
        print("#")
        print("##################################################")
        print("#")
        print("# nnDet inference")
        print("#")
        
        bash_command = f"nndet_predict {self.task} {self.model} -f {self.fold} -npp {self.num_processes_preprocessing}"  # --check
        if self.ntta is not None:
            bash_command += f" -ntta {self.ntta}"
        if self.n_models is not None:
            bash_command += f" -nmodels {self.n_models}"
        if self.no_preprocess:
            bash_command += f" --no_preprocess"
        print(bash_command)
        os.system(bash_command)
        
        print("# Boxes to mask")
        print("##################################################")
        print("#")
        bash_command = f"nndet_boxes2nii {self.task} {self.model} -f {self.fold} --test"
        print(bash_command)
        os.system(bash_command)
            
            
    def format_nndet_output_for_kaapana(self, batch_folder_list: List, operator_out_dir: str):
        """formats nndet output filestructure to kaapana file strucutre and deletes nndet model, preprocessed and data dirs

        :param batch_folder_list: list of kaapana subdirectories inside batch to save output
        :param operator_out_dir: output operator identifier for directory structure
        """

        print("#")
        print("##################################################")
        print("#")
        print("# Starting directory and file structure restructuring for kaapana ...")
        print("#")
        print("##################################################")
        print("#")


        
        for batch_element_dir in batch_folder_list:
            element_output_dir = batch_element_dir / operator_out_dir
            element_output_dir.mkdir(parents=True, exist_ok=True)
            
            # copy everything by default
            
            case_ids = [c.name.replace(".nii.gz", "") for c in self.model_prediction_dir_nii.glob("*.nii.gz")]
            case_ids_rename = [self.rename_files_dict[c.replace("_boxes", "")] for c in case_ids.copy()]
            print("##################################################")
            print(f"# Copy cases {case_ids} to output")
            print("##################################################")
            
            for cid, cid_rename in zip(case_ids, case_ids_rename):
                print(f"FROM: {self.model_prediction_dir_nii} / {cid}.nii.gz To: {element_output_dir} / {cid_rename}_boxes.nii.gz")
                shutil.copy(self.model_prediction_dir_nii / f"{cid}.nii.gz", element_output_dir / f"{cid_rename}_boxes.nii.gz")
                shutil.copy(self.model_prediction_dir_nii / f"{cid}.json", element_output_dir / f"{cid_rename}_boxes.json")
            
        # cleanup
        print("#")
        print("##################################################")
        print("#")
        print("# Clean nndet directories")
        print("#")
        print(f"# data_target_dir: {self.data_target_dir}")
        print(f"# preprocessed_data_dir: {self.data_target_dir_preprocessed}")
        print(f"# model_prediction_dir: {self.model_prediction_dir}")
        print(f"# preprocessed_data_dir_nii: {self.model_prediction_dir_nii}")
        print("##################################################")
        print("#")

        #shutil.rmtree(self.data_target_dir)
        #shutil.rmtree(self.data_target_dir_preprocessed)
        #shutil.rmtree(self.model_prediction_dir)
        #shutil.rmtree(self.model_prediction_dir_nii)
        



def main():
    
    # For local testng
    #os.environ["WORKFLOW_DIR"] = "/opt/workflowdir"
    #os.environ["BATCH_NAME"] = "batch"
    #os.environ["OPERATOR_IN_DIR"] = "dcm-converter"
    #os.environ["OPERATOR_OUT_DIR"] = "output"
    # nndet
    #os.environ["det_models"] = "/opt/models"
    #os.environ["det_data"] = "/opt/det_data2"
    #os.environ["TASK"] = "000"
    #os.environ["MODEL"] = "RetinaUNetV001_D3V001_3d"
    #os.environ["FOLD"] = "0"
    

    # kaapana parameters
    workflow_dir = Path(os.getenv("WORKFLOW_DIR"))
    batch_name = get_env_param("BATCH_NAME")
    operator_out_dir = get_env_param("OPERATOR_OUT_DIR")
    operator_in_dir = get_env_param("OPERATOR_IN_DIR")
    batch_dir = Path("/", workflow_dir / batch_name)
    
    print("#")
    print("# Kaapana parameters:")
    print("#")
    print(f"# workflow_dir: {workflow_dir}")
    print(f"# batch_name: {batch_name}")
    print(f"# operator_out_dir: {operator_out_dir}")
    print(f"# operator_in_dir: {operator_in_dir}")
    print("#")

    # kaapana to nndet dir structure
    nnDetKp = NnDetKaapanaInterface()

    nnDetKp.format_kaapana_input_for_nndet(batch_folder_list=batch_dir.glob('*'), operator_in_dir=operator_in_dir)
    
    # nndet inference
    nnDetKp.inference()
    
    
    # nndet to kaapana dir structure and cleaning
    nnDetKp.format_nndet_output_for_kaapana(batch_folder_list=batch_dir.glob('*'), operator_out_dir=operator_out_dir)

    
    

    


if __name__ == "__main__":
    main()