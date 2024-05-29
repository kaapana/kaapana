import os
from typing import Literal, Optional


class ValidationItem:

    def __init__(
        self, tag, type, message, name="", module="", index=None, raw=""
    ) -> None:
        if not tag or tag == "":
            raise ValueError("Invalid Tag provided")
        self.tag = tag
        self.type = type
        self.message = message
        self.name = name
        self.module = module
        self.index = index
        self.raw = raw
        self.list_of_dicoms = []
        return

    def __str__(self):
        if self.raw != "":
            return self.raw
        return f'{self.type}:\nTag: {self.tag}\nName: {self.name}\nIndex: {self.index}\nMessage: {self.message}\nDicoms: {",".join(self.list_of_dicoms)}\n'

    def add_dicom(self, dicom_name: str):
        self.list_of_dicoms.append(dicom_name)


class DicomValidatorInterface:
    def __init__(self) -> None:
        return

    def validate_dicom(self, dicom_path: str) -> tuple:
        """
        Args:
            dicom_path (str): The file path of the DICOM file to be validated.

        Returns:
            Tuple[List[ValidationItem], List[ValidationItem]]: Two lists containing error and warning ValidationItems respectively.
        """
        return NotImplementedError


def ensure_dir(target: str):
    """
    Ensure that the specified directory path exists; if not, create it.

    Parameters:
    - target (str): The directory path to ensure existence for.
    """
    if not os.path.exists(target):
        os.makedirs(target)


def merge_similar_validation_items(all_items: dict):
    """
    Merge similar validation items across multiple DICOM files.

    This function takes a dictionary of DICOM files path and their corresponding validation items,
    then merges the items with similar tags (and indices, if present). Each unique tag (and
    index combination) is combined, and the list of DICOM files where they appear is updated.

    If an item appears in all DICOM files, its list of DICOM files is replaced with ["all"].

    Args:
        all_items (dict): A dictionary where keys are DICOM file identifiers and values are
                          lists of validation items from the class ValidationItem

    Returns:
        dict: A dictionary where keys are tag/index combinations (as strings) and values are
              the merged validation items with updated lists of associated DICOM files.
    """
    tag_item_pair = {}
    # tag_dicom_pair = {}
    for dicom in all_items.keys():
        for e in all_items[dicom]:
            key = e.tag
            if e.index:
                key = e.tag + "," + str(e.index)
            if key not in tag_item_pair:
                e.add_dicom(dicom)
                tag_item_pair[key] = e
            else:
                tag_item_pair[key].add_dicom(dicom)

    for tag in tag_item_pair:
        if (len(tag_item_pair[tag].list_of_dicoms) % len(list(all_items.keys()))) == 0:
            tag_item_pair[tag].list_of_dicoms = ["all"]

    return tag_item_pair
