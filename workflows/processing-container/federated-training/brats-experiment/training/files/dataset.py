# customized for Federated BraTS Experiment
# Source: https://github.com/Project-MONAI/MONAI/blob/dev/monai/apps/datasets.py

import os
import sys
from typing import Callable, Dict, List, Optional, Sequence, Union

import numpy as np

from monai.apps.utils import download_and_extract
from monai.data import (
    CacheDataset,
    #load_decathlon_datalist,
    load_decathlon_properties,
    partition_dataset,
    select_cross_validation_folds,
)
from monai.transforms import LoadImaged, Randomizable
from monai.utils import ensure_tuple


from decathlon_datalist import load_decathlon_datalist


class DecathlonDataset(Randomizable, CacheDataset):
    """Customized DecathlonDataset for Federated BraTS"""

    resource = {
        "Task01_BrainTumour": "https://msd-for-monai.s3-us-west-2.amazonaws.com/Task01_BrainTumour.tar",
        "Task02_Heart": "https://msd-for-monai.s3-us-west-2.amazonaws.com/Task02_Heart.tar",
        "Task03_Liver": "https://msd-for-monai.s3-us-west-2.amazonaws.com/Task03_Liver.tar",
        "Task04_Hippocampus": "https://msd-for-monai.s3-us-west-2.amazonaws.com/Task04_Hippocampus.tar",
        "Task05_Prostate": "https://msd-for-monai.s3-us-west-2.amazonaws.com/Task05_Prostate.tar",
        "Task06_Lung": "https://msd-for-monai.s3-us-west-2.amazonaws.com/Task06_Lung.tar",
        "Task07_Pancreas": "https://msd-for-monai.s3-us-west-2.amazonaws.com/Task07_Pancreas.tar",
        "Task08_HepaticVessel": "https://msd-for-monai.s3-us-west-2.amazonaws.com/Task08_HepaticVessel.tar",
        "Task09_Spleen": "https://msd-for-monai.s3-us-west-2.amazonaws.com/Task09_Spleen.tar",
        "Task10_Colon": "https://msd-for-monai.s3-us-west-2.amazonaws.com/Task10_Colon.tar",
    }
    md5 = {
        "Task01_BrainTumour": "240a19d752f0d9e9101544901065d872",
        "Task02_Heart": "06ee59366e1e5124267b774dbd654057",
        "Task03_Liver": "a90ec6c4aa7f6a3d087205e23d4e6397",
        "Task04_Hippocampus": "9d24dba78a72977dbd1d2e110310f31b",
        "Task05_Prostate": "35138f08b1efaef89d7424d2bcc928db",
        "Task06_Lung": "8afd997733c7fc0432f71255ba4e52dc",
        "Task07_Pancreas": "4f7080cfca169fa8066d17ce6eb061e4",
        "Task08_HepaticVessel": "641d79e80ec66453921d997fbf12a29c",
        "Task09_Spleen": "410d4a301da4e5b2f6f86ec3ddba524e",
        "Task10_Colon": "bad7a188931dc2f6acf72b08eb6202d0",
    }

    def __init__(
        self,
        root_dir: str,
        task: str,
        section: str,
        transform: Union[Sequence[Callable], Callable] = (),
        download: bool = False,
        seed: int = 0,
        #val_frac: float = 0.2,
        cache_num: int = sys.maxsize,
        cache_rate: float = 1.0,
        num_workers: int = 0,
    ) -> None:
        if not os.path.isdir(root_dir):
            raise ValueError("Root directory root_dir must be a directory.")
        self.section = section
        
        #self.val_frac = val_frac
        
        self.set_random_state(seed=seed)
        
        if task not in self.resource:
            raise ValueError(f"Unsupported task: {task}, available options are: {list(self.resource.keys())}.")
        dataset_dir = os.path.join(root_dir, task)
        
        #tarfile_name = f"{dataset_dir}.tar"
        #if download:
        #    download_and_extract(self.resource[task], tarfile_name, root_dir, self.md5[task])

        if not os.path.exists(dataset_dir):
            raise RuntimeError(
                f"Cannot find dataset directory: {dataset_dir}, please use download=True to download it."
            )
        
        self.indices: np.ndarray = np.array([])
        data = self._generate_data_list(dataset_dir)
        # as `release` key has typo in Task04 config file, ignore it.
        property_keys = [
            "name",
            "description",
            "reference",
            "licence",
            "tensorImageSize",
            "modality",
            "labels",
            "numTraining",
            #"numTest",
            "numValidation",
        ]
        self._properties = load_decathlon_properties(os.path.join(dataset_dir, "dataset.json"), property_keys)
        if transform == ():
            transform = LoadImaged(["image", "label"])
        CacheDataset.__init__(
            self, data, transform, cache_num=cache_num, cache_rate=cache_rate, num_workers=num_workers
        )

    def get_indices(self) -> np.ndarray:
        """
        Get the indices of datalist used in this dataset.
        """
        return self.indices

    def randomize(self, data: List[int]) -> None:
        self.R.shuffle(data)

    def get_properties(self, keys: Optional[Union[Sequence[str], str]] = None):
        """
        Get the loaded properties of dataset with specified keys.
        If no keys specified, return all the loaded properties.
        """
        if keys is None:
            return self._properties
        if self._properties is not None:
            return {key: self._properties[key] for key in ensure_tuple(keys)}
        return {}

    def _generate_data_list(self, dataset_dir: str) -> List[Dict]:
        
        #section = "training" if self.section in ["training", "validation"] else "test"

        section = self.section
        datalist = load_decathlon_datalist(os.path.join(dataset_dir, "dataset.json"), True, section)
        #return self._split_datalist(datalist)
        return datalist

    def _split_datalist(self, datalist: List[Dict]) -> List[Dict]:
        if self.section == "test":
            return datalist
        length = len(datalist)
        indices = np.arange(length)
        self.randomize(indices)

        val_length = int(length * self.val_frac)
        if self.section == "training":
            self.indices = indices[val_length:]
        else:
            self.indices = indices[:val_length]

        return [datalist[i] for i in self.indices]
