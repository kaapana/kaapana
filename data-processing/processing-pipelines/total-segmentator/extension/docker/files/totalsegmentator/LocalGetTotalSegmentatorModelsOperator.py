import http.client
import os
import time
import zipfile
from pathlib import Path

import requests

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalGetTotalSegmentatorModelsOperator(KaapanaPythonBaseOperator):
    """
    This operator downloads all the models available for the total segmentator workflow.
    """

    @staticmethod
    def download_url_and_unpack(url, config_dir, task_id):

        # helps to solve incomplete read erros
        # https://stackoverflow.com/questions/37816596/restrict-request-to-only-ask-for-http-1-0-to-prevent-chunking-error
        http.client.HTTPConnection._http_vsn = 10
        http.client.HTTPConnection._http_vsn_str = 'HTTP/1.0'

        tempfile = config_dir / f"{task_id}.zip"

        try:
            st = time.time()
            with open(tempfile, 'wb') as f:
                # session = requests.Session()  # making it slower
                with requests.get(url, stream=True) as r:
                    r.raise_for_status()
                    for chunk in r.iter_content(chunk_size=8192 * 16):
                        # If you have chunk encoded response uncomment if
                        # and set chunk_size parameter to None.
                        # if chunk:
                        f.write(chunk)

            print("Download finished. Extracting...")
            # call(['unzip', '-o', '-d', network_training_output_dir, tempfile])
            with zipfile.ZipFile(config_dir / f"{task_id}.zip", 'r') as zip_f:
                zip_f.extractall(config_dir)
            print(f"  downloaded in {time.time() - st:.2f}s")
        except Exception as e:
            raise e
        finally:
            if tempfile.exists():
                os.remove(tempfile)

    @staticmethod
    def download_pretrained_weights(task_id:int, config_dir:Path, force_download: bool = False):
        if task_id == 251:
            weights_path = config_dir / "Task251_TotalSegmentator_part1_organs_1139subj"
            WEIGHTS_URL = "https://zenodo.org/record/6802342/files/Task251_TotalSegmentator_part1_organs_1139subj.zip?download=1"
        elif task_id == 252:
            weights_path = config_dir / "Task252_TotalSegmentator_part2_vertebrae_1139subj"
            WEIGHTS_URL = "https://zenodo.org/record/6802358/files/Task252_TotalSegmentator_part2_vertebrae_1139subj.zip?download=1"
        elif task_id == 253:
            weights_path = config_dir / "Task253_TotalSegmentator_part3_cardiac_1139subj"
            WEIGHTS_URL = "https://zenodo.org/record/6802360/files/Task253_TotalSegmentator_part3_cardiac_1139subj.zip?download=1"
        elif task_id == 254:
            weights_path = config_dir / "Task254_TotalSegmentator_part4_muscles_1139subj"
            WEIGHTS_URL = "https://zenodo.org/record/6802366/files/Task254_TotalSegmentator_part4_muscles_1139subj.zip?download=1"
        elif task_id == 255:
            weights_path = config_dir / "Task255_TotalSegmentator_part5_ribs_1139subj"
            WEIGHTS_URL = "https://zenodo.org/record/6802452/files/Task255_TotalSegmentator_part5_ribs_1139subj.zip?download=1"
        elif task_id == 256:
            weights_path = config_dir / "Task256_TotalSegmentator_3mm_1139subj"
            WEIGHTS_URL = "https://zenodo.org/record/6802052/files/Task256_TotalSegmentator_3mm_1139subj.zip?download=1"
        elif task_id == 258:
            weights_path = config_dir / "Task258_lung_vessels_248subj"
            WEIGHTS_URL = "https://zenodo.org/record/7064718/files/Task258_lung_vessels_248subj.zip?download=1"
        elif task_id == 200:
            weights_path = config_dir / "Task200_covid_challenge"
            WEIGHTS_URL = "TODO"
        elif task_id == 201:
            weights_path = config_dir / "Task201_covid"
            WEIGHTS_URL = "TODO"
        elif task_id == 150:
            weights_path = config_dir / "Task150_icb_v0"
            WEIGHTS_URL = "https://zenodo.org/record/7079161/files/Task150_icb_v0.zip?download=1"
        elif task_id == 260:
            weights_path = config_dir / "Task260_hip_implant_71subj"
            WEIGHTS_URL = "https://zenodo.org/record/7234263/files/Task260_hip_implant_71subj.zip?download=1"
        elif task_id == 503:
            weights_path = config_dir / "Task503_cardiac_motion"
            WEIGHTS_URL = "https://zenodo.org/record/7271576/files/Task503_cardiac_motion.zip?download=1"
        elif task_id == 517:
            weights_path = config_dir / "Task517_Bones40"
            WEIGHTS_URL = "TODO"

        if WEIGHTS_URL is not None and (not weights_path.exists() or force_download):
            print(f"Downloading pretrained weights for Task {task_id} (~230MB) ...")
            weights_path.mkdir(exist_ok=True, parents=True)
            LocalGetTotalSegmentatorModelsOperator.download_url_and_unpack(WEIGHTS_URL, config_dir, task_id)

    @staticmethod
    def start():
        # Downstream TotalSegmentatorOperator expects the files to be located here:
        config_dir = Path("models/total_segmentator/nnUNet/3d_fullres")

        config_dir.mkdir(exist_ok=True, parents=True)
        for task_id in [251, 252, 253, 254, 255]:  # [251, 252, 253, 254, 255, 256, 258, 150, 260, 503]:
            LocalGetTotalSegmentatorModelsOperator.download_pretrained_weights(
                task_id,
                config_dir,
                force_download=False
            )

    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="get-total-segmentator-models",
            python_callable=self.start,
            **kwargs
        )
