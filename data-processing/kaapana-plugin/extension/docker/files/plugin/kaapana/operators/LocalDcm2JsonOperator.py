# !!! DEPRECATION WARNING: Local Operators are deprecated and will be replaced with operators that run in Kubernetes pods in the next release v0.7.0.
# If you have a custom Local Operator, it should be migrated to a processing container based operator.
import json
import logging
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Union

import pydicom
import pytz
from dateutil import parser
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb
from kaapanapy.settings import KaapanaSettings
from pydicom.tag import Tag

TIMEZONE = KaapanaSettings().timezone

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")


class LocalDcm2JsonOperator(KaapanaPythonBaseOperator):
    """
    Operator to convert DICOM files to JSON.
    Additionally some keywords and values are transformed to increase the usability to find/search key-values.

    **Inputs:**

    * exit_on_error: exit with error, when some key/values are missing or mismatching.
    * delete_pixel_data: uses dcmtk's dcmodify to remove some specific to be known private tags
    * bulk: process all files of a series or only the first one (default)

    **Outputs:**

    * json file: output json file. DICOM tags are converted to a json file.
    """

    MODALITY_TAG = "00080060 Modality_keyword"
    IMAGE_TYPE_TAG = "00080008 ImageType_keyword"
    KAAPANA_TIME_FORMAT = "%H:%M:%S.%f"
    KAAPANA_DATE_FORMAT = "%Y-%m-%d"
    KAAPANA_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
    DCM_DATETIME_FORMAT = "%Y%m%d%H%M%S.%f"
    DCM_DATE_FORMAT = "%Y%m%d"
    DCM_TIME_FORMAT = "%H%M%S.%f"

    def load_dicom_tag_dict(self):
        # kaapana/services/flow/airflow/docker/files/scripts/dicom_tag_dict.json
        dicom_tag_dict_path = os.getenv("DICT_PATH", None)
        if dicom_tag_dict_path is None:
            raise KeyError("DICT_PATH ENV NOT FOUND")

        else:
            with open(dicom_tag_dict_path, encoding="utf-8") as dict_data:
                self.dicom_tag_dict = json.load(dict_data)

    def __init__(
        self,
        dag,
        exit_on_error=False,
        delete_pixel_data=True,
        data_type="dcm",
        bulk=False,
        issuer_of_patient_id=None,
        resolve_issuer_conflicts_with_pacs=False,
        **kwargs,
    ):
        """
        :param exit_on_error: 'True' or 'False' (default). Exit with error, when some key/values are missing or mismatching.
        :param delete_pixel_data: 'True' (default) or 'False'. removes pixel-data from DICOM.
        :param bulk: 'True' or 'False' (default). Process all files of a series or only the first one.
        :param issuer_of_patient_id: Optional value written to
            ``IssuerOfPatientID`` before metadata extraction.
        :param resolve_issuer_conflicts_with_pacs: If ``True``, look up the
            issuer of already stored instances in PACS for the same study and
            normalize incoming files to that issuer. The operator fails if the
            existing study already contains multiple issuers.
        """

        self.bulk = bulk
        self.exit_on_error = exit_on_error
        self.delete_pixel_data = delete_pixel_data
        self.data_type = data_type
        self.issuer_of_patient_id = issuer_of_patient_id
        self.resolve_issuer_conflicts_with_pacs = resolve_issuer_conflicts_with_pacs

        os.environ["PYTHONIOENCODING"] = "utf-8"
        self.load_dicom_tag_dict()

        super().__init__(
            dag=dag,
            name="dcm2json",
            python_callable=self.start,
            ram_mem_mb=10,
            **kwargs,
        )

    def _is_radiotherapy_modality(self, metadata: Dict) -> bool:
        """Check if the modality is either RTSTRUCT or SEG."""
        modality_tag = metadata.get("00080060")
        return bool(modality_tag and modality_tag["Value"][0] in ("RTSTRUCT", "SEG"))

    @cache_operator_output
    def start(self, **kwargs):
        logger.info("Starting module dcm2json...")
        config = kwargs["dag_run"].conf
        self.default_project = config.get("project_form", {}).get("name", "admin")
        self.dcmweb_helper = None
        self.study_issuer_cache = {}

        if (
            self.data_type == "dcm"
            and self.issuer_of_patient_id is not None
            and self.resolve_issuer_conflicts_with_pacs
        ):
            self.dcmweb_helper = HelperDcmWeb()
            logger.info(
                "Issuer reconciliation enabled: default issuer '%s', PACS conflict resolution enabled.",
                self.issuer_of_patient_id,
            )
        elif self.data_type == "dcm" and self.issuer_of_patient_id is not None:
            logger.info(
                "Issuer normalization enabled without PACS lookup: default issuer '%s'.",
                self.issuer_of_patient_id,
            )

        run_dir: Path = Path(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folders: List[Path] = list((run_dir / self.batch_name).glob("*"))
        logger.info(f"Number of series: {len(batch_folders)}")
        for batch_element_dir in batch_folders:
            files: List[Path] = sorted(
                list(
                    (batch_element_dir / self.operator_in_dir).rglob(
                        f"*.{self.data_type}"
                    )
                )
            )

            if len(files) == 0:
                raise FileNotFoundError(
                    f"No dicom file found in {batch_element_dir / self.operator_in_dir}"
                )

            self._normalize_issuer_of_patient_id_for_files(files)
            logger.info(f"length {len(files)}")
            for dcm_file_path in files:
                logger.info(f"Extracting metadata: {dcm_file_path}")

                target_dir: Path = batch_element_dir / self.operator_out_dir
                target_dir.mkdir(exist_ok=True)
                json_file_path = target_dir / f"{batch_element_dir.name}.json"
                if self.data_type == "dcm":
                    dcm = pydicom.read_file(dcm_file_path, stop_before_pixels=True)
                    if self.delete_pixel_data:
                        dcm = self._delete_pixel_data(dcm)
                    json_dict = dcm.to_json_dict()
                    del dcm
                elif self.data_type == "json":
                    with open(dcm_file_path, "r", encoding="utf-8") as f:
                        json_dict = json.load(f)
                else:
                    raise NotImplementedError(
                        f"Unsupported input data_type {self.data_type}. Only `json` and `dcm` supported."
                    )
                json_dict = self._clean_json(json_dict)
                with open(json_file_path, "w", encoding="utf-8") as jsonData:
                    json.dump(
                        json_dict,
                        jsonData,
                        indent=4,
                        sort_keys=True,
                        ensure_ascii=True,
                    )

                if not self.bulk:
                    break
        out_files = set(out_files)
        print("Output json files:", out_files)

    def _normalize_issuer_of_patient_id_for_files(self, dcm_file_paths: List[Path]) -> None:
        """Normalize ``IssuerOfPatientID`` for all files of an incoming series.

        Args:
            dcm_file_paths: Paths of DICOM files that belong to the same batch
                element.

        Side Effects:
            Rewrites DICOM files in-place when the resolved issuer differs from
            the current one.
        """
        if self.data_type != "dcm" or self.issuer_of_patient_id is None:
            return

        logger.info(
            "Normalizing IssuerOfPatientID for %s file(s) in current batch element.",
            len(dcm_file_paths),
        )
        for dcm_file_path in dcm_file_paths:
            self._normalize_issuer_of_patient_id_for_file(dcm_file_path)

    def _normalize_issuer_of_patient_id_for_file(self, dcm_file_path: Path) -> None:
        """Normalize ``IssuerOfPatientID`` in the DICOM file on disk.

        Args:
            dcm_file_path: Path to the DICOM file that should be normalized.

        Side Effects:
            Rewrites the DICOM file in-place when the resolved issuer differs
            from the current one.
        """
        if self.issuer_of_patient_id is None:
            return

        # Read the full dataset before saving to avoid truncating pixel data.
        dcm = pydicom.dcmread(dcm_file_path, force=True)
        current_issuer = self._get_issuer_of_patient_id(dcm)
        study_uid_tag = dcm.get((0x0020, 0x000D))
        study_uid = str(study_uid_tag.value).strip() if study_uid_tag is not None else ""
        logger.info(
            "Checking IssuerOfPatientID for file %s (study=%s, current_issuer='%s').",
            dcm_file_path,
            study_uid or "unknown",
            current_issuer,
        )
        target_issuer = self._resolve_target_issuer_of_patient_id(dcm)

        if current_issuer == target_issuer:
            logger.info(
                "IssuerOfPatientID already matches target '%s' for file %s. Skipping rewrite.",
                target_issuer,
                dcm_file_path,
            )
            return

        if (0x0010, 0x0021) not in dcm:
            dcm.add_new("0x00100021", "LO", target_issuer)
        else:
            dcm[(0x0010, 0x0021)].value = target_issuer
        dcm.save_as(dcm_file_path)
        logger.info(
            "Normalized IssuerOfPatientID for %s from '%s' to '%s'",
            dcm_file_path,
            current_issuer,
            target_issuer,
        )

    def _resolve_target_issuer_of_patient_id(self, dcm: pydicom.Dataset) -> str:
        """Resolve the issuer that should be used for an incoming DICOM.

        Args:
            dcm: The DICOM dataset whose issuer should be normalized.

        Returns:
            str: The issuer value that should be written to the DICOM.

        Raises:
            ValueError: The existing study in PACS already contains multiple
                issuer values and therefore cannot be reconciled automatically.
        """
        if self.issuer_of_patient_id is None:
            return self._get_issuer_of_patient_id(dcm)

        target_issuer = self.issuer_of_patient_id
        logger.info("Default target issuer is '%s'.", target_issuer)

        if not self.resolve_issuer_conflicts_with_pacs or self.dcmweb_helper is None:
            logger.info(
                "PACS issuer conflict resolution disabled or unavailable. Using default issuer '%s'.",
                target_issuer,
            )
            return target_issuer

        study_uid_tag = dcm.get((0x0020, 0x000D))
        if study_uid_tag is None:
            logger.info(
                "StudyInstanceUID missing in incoming DICOM. Falling back to default issuer '%s'.",
                target_issuer,
            )
            return target_issuer

        study_uid = str(study_uid_tag.value).strip()
        logger.info("Looking up existing PACS issuer for study %s.", study_uid)
        archive_issuer = self._get_archive_issuer_of_study(study_uid)
        if archive_issuer:
            current_issuer = self._get_issuer_of_patient_id(dcm)
            if current_issuer and current_issuer != archive_issuer:
                logger.warning(
                    "IssuerOfPatientID conflict for study %s: incoming '%s', "
                    "archive '%s'. Rewriting incoming DICOM to match PACS.",
                    study_uid,
                    current_issuer,
                    archive_issuer,
                )
            else:
                logger.info(
                    "Using issuer '%s' already present in PACS for study %s.",
                    archive_issuer,
                    study_uid,
                )
            return archive_issuer

        logger.info(
            "No issuer found in PACS for study %s. Using default issuer '%s'.",
            study_uid,
            target_issuer,
        )
        return target_issuer

    def _get_archive_issuer_of_study(self, study_uid: str) -> str:
        """Fetch the unique issuer used by already stored instances of a study.

        Args:
            study_uid: Study Instance UID used to look up existing instances.

        Returns:
            str: The unique issuer found in PACS for the study, or an empty
            string if no issuer is stored for that study.

        Raises:
            ValueError: The study already contains multiple issuer values in
                PACS and cannot be reconciled automatically.
        """
        if study_uid in self.study_issuer_cache:
            logger.info(
                "Using cached PACS issuer '%s' for study %s.",
                self.study_issuer_cache[study_uid],
                study_uid,
            )
            return self.study_issuer_cache[study_uid]

        if not self.dcmweb_helper.check_if_study_in_archive(study_uid):
            logger.info("Study %s not found in PACS.", study_uid)
            self.study_issuer_cache[study_uid] = ""
            return ""

        logger.info(
            "Study %s found in PACS. Fetching instance metadata including IssuerOfPatientID.",
            study_uid,
        )
        # Request the issuer tag explicitly because dcm4chee does not include
        # it in the default /instances response payload.
        instances = self.dcmweb_helper.get_instances_of_study(
            study_uid, params={"includefield": "00100021"}
        ) or []
        logger.info(
            "Retrieved %s instance metadata entrie(s) from PACS for study %s.",
            len(instances),
            study_uid,
        )
        issuers = sorted(
            {
                str(instance["00100021"]["Value"][0]).strip()
                for instance in instances
                if "00100021" in instance
                and instance["00100021"].get("Value")
                and str(instance["00100021"]["Value"][0]).strip()
            }
        )

        if len(issuers) > 1:
            logger.error(
                "Issuer conflict detected in PACS for study %s: %s",
                study_uid,
                issuers,
            )
            raise ValueError(
                "Conflicting IssuerOfPatientID values already exist in PACS for "
                f"study {study_uid}: {issuers}"
            )

        resolved_issuer = issuers[0] if issuers else ""
        logger.info(
            "Resolved PACS issuer for study %s to '%s'.",
            study_uid,
            resolved_issuer,
        )
        self.study_issuer_cache[study_uid] = resolved_issuer
        return resolved_issuer

    def _get_issuer_of_patient_id(self, dcm: pydicom.Dataset) -> str:
        """Read ``IssuerOfPatientID`` from a DICOM dataset.

        Args:
            dcm: DICOM dataset to inspect.

        Returns:
            str: The stripped issuer value, or an empty string if the tag is
            missing.
        """
        issuer_tag = dcm.get((0x0010, 0x0021))
        return str(issuer_tag.value).strip() if issuer_tag is not None else ""

    def _delete_pixel_data(self, dcm: pydicom.Dataset) -> pydicom.Dataset:
        """Remove pixel payload tags from a DICOM dataset.

        Args:
            dcm: Dataset to strip pixel-related elements from.

        Returns:
            pydicom.Dataset: The modified dataset without pixel payload tags.
        """
        # (0014,3080) Bad Pixel Image
        # (7FE0,0008) Float Pixel Data
        # (7FE0,0009) Double Float Pixel Data
        # (7FE0,0010) Pixel Data
        pixel_data_elements = [
            (0x0014, 0x3080),
            (0x7FE0, 0x0008),
            (0x7FE0, 0x0009),
            (0x7FE0, 0x0010),
        ]

        for elem in pixel_data_elements:
            tag = Tag(*elem)
            if tag in dcm:
                del dcm[tag]
        return dcm

    def _clean_json(self, metadata: Dict) -> Dict:
        annotations_dict = {}
        if self._is_radiotherapy_modality(metadata):
            # Preprocess annotations into simplified tags
            annotations_dict = self._process_annotation_tags(metadata)

        # Tag normalization
        # 00080020 -> 00080020 DcmTagKeyword_type for all tags.
        metadata = self._normalize_tags(metadata)

        # Adding RTSTRUCT and SEG labels if present.
        metadata.update(annotations_dict)

        # Processing datetime, date and time tags
        metadata = self._process_time_tags(metadata)

        # Processing - deducting and validating patient age from multiple tags
        metadata = self._process_patient_age(metadata)

        # Process aetitles used for kaapana datasets titles
        metadata = self._process_clinical_trial_protocol_id(metadata)

        # Change modality from CT to XR under specific conditions
        metadata = self._process_modality(metadata)

        # TODO Why is this necessary?
        metadata["predicted_bodypart_string"] = "N/A"

        self._sanitize_project_and_dataset(
            metadata, default_project=self.default_project
        )
        return metadata

    def _sanitize_project_and_dataset(
        self, metadata, default_project: str = "admin", default_dataset: str = None
    ):
        """ """
        sanitized_project_name = default_project
        sanitized_dataset = default_dataset or datetime.now(
            pytz.timezone(TIMEZONE)
        ).strftime("%y-%m-%d-%H:%M:%S%f")

        if (
            dataset := metadata.get("00120010 ClinicalTrialSponsorName_keyword")
        ) and dataset.startswith("kp-"):
            sanitized_dataset = dataset[3:]  # Remove "kp-" prefix

        if (
            project_name := metadata.get("00120020 ClinicalTrialProtocolID_keyword")
        ) and project_name[0].startswith("kp-"):
            sanitized_project_name = project_name[0][3:]  # Remove "kp-" prefix

        metadata["00120010 ClinicalTrialSponsorName_keyword"] = sanitized_dataset
        metadata["00120020 ClinicalTrialProtocolID_keyword"] = sanitized_project_name
        return metadata

    def _process_annotation_tags(self, metadata: Dict) -> Dict:
        update_metadata = {}
        annotation_label_list = []

        # RTSTRUCT: ROI Structures
        label_entries = metadata.get("30060020", {}).get("Value", [])
        for label_entry in label_entries:
            if "30060026" in label_entry:
                value = label_entry["30060026"]["Value"][0].replace(",", "-")
                annotation_label_list.append(value)

        # SEG: Segments
        segment_entries = metadata.get("00620002", {}).get("Value", [])
        if segment_entries:
            update_metadata["00620002 SegmentSequence_object_object"] = {}
            for label_entry in segment_entries:
                # setting alg_name, alg_type and value default to None if they do not exist.
                alg_name = label_entry.get("00620009", {}).get("Value", [None])[0]
                alg_type = label_entry.get("00620008", {}).get("Value", [None])[0]
                value = (
                    label_entry.get("00620005", {})
                    .get("Value", [""])[0]
                    .replace(",", "-")
                    .strip()
                )

                if alg_name:
                    update_metadata["00620002 SegmentSequence_object_object"][
                        "00620009 SegmentAlgorithmName_keyword"
                    ] = alg_name
                if alg_type:
                    update_metadata["00620002 SegmentSequence_object_object"][
                        "00620008 SegmentAlgorithmType_keyword"
                    ] = alg_type
                if value:
                    annotation_label_list.append(value)

        update_metadata["00000000 AnnotationLabelsList_keyword"] = (
            ",".join(sorted(annotation_label_list)) if annotation_label_list else None
        )
        update_metadata["00000000 AnnotationLabel_keyword"] = annotation_label_list
        return update_metadata

    def _normalize_tag(
        self, new_tag: str, vr: str, value_str: Any, metadata: Dict
    ) -> Dict:
        if vr in (
            "AE",
            "AS",
            "AT",
            "CS",
            "LO",
            "LT",
            "OB",
            "OW",
            "SH",
            "ST",
            "UC",
            "UI",
            "UN",
            "UT",
            "UR",
        ):
            new_tag += "_keyword"
            metadata[new_tag] = value_str

        elif vr == "DT":
            datetime_formatted = self._format_datetime_value(new_tag, value_str)
            if datetime_formatted is not None:
                new_tag += "_datetime"
                metadata[new_tag] = datetime_formatted

        elif vr == "DA":
            date_formatted = self._format_date_value(value_str)
            if date_formatted is not None:
                new_tag += "_date"
                metadata[new_tag] = date_formatted

        elif vr == "TM":
            time_formatted = self._format_time_value(value_str)
            if time_formatted is not None:
                new_tag += "_time"
                metadata[new_tag] = time_formatted

        elif vr in ("DS", "FL", "FD", "OD", "OF"):
            checked_val = convert(value_str, float)
            if checked_val is not None:
                new_tag += "_float"
                metadata[new_tag] = checked_val

        elif vr in ("IS", "SL", "SS", "UL", "US"):
            checked_val = convert(value_str, int)
            if checked_val is not None:
                new_tag += "_integer"
                metadata[new_tag] = checked_val

        elif vr == "SQ":
            checked_val = self._process_sequence_value(value_str)
            if checked_val is not None:
                new_tag += "_object"
                metadata[new_tag] = checked_val

        elif vr == "PN":
            # Person Name
            # A character string encoded using a 5 component convention. The character code 5CH (the BACKSLASH "\"
            # in ISO-IR 6) shall not be present, as it is used as the delimiter between values in multiple valued data
            # elements. The string may be padded with trailing spaces. For human use, the five components in their order
            # of occurrence are: family name complex, given name complex, middle name, name prefix, name suffix.
            new_tag += "_keyword"
            subcategories = ["Alphabetic", "Ideographic", "Phonetic"]

            for cat in subcategories:
                if cat in value_str:
                    new_cat_tag = f"{new_tag}_{cat.lower()}"
                    metadata[new_cat_tag] = value_str[cat]

        else:
            logger.warning(highlight_message("UNKNOWN VR"))
            logger.warning(f"Tag: {new_tag}")
            logger.warning(f"VR: {vr}")
            logger.warning(f"Value: {value_str}")

            new_tag += "_keyword"
            metadata[new_tag] = value_str
        return metadata

    def _normalize_tags(self, metadata: Dict) -> Dict:
        new_meta_data = {}

        for tag, tag_metadata in metadata.items():
            new_tag = self.dicom_tag_dict.get(tag, None)

            if new_tag is None:
                logger.info(f"Tag {tag} not found in DICOM TAG database. Skipping ...")
                continue

            if "vr" in tag_metadata and "Value" in tag_metadata:
                vr = str(tag_metadata["vr"])
                value_str = tag_metadata["Value"]
                value_str = strip_if_possible(value_str)

                if "nan" in value_str:
                    logger.info(f"Found NAN in value_str: {value_str}. Skipping ...")
                    continue

                if isinstance(value_str, list):
                    if len(value_str) == 1:
                        value_str = value_str[0]

                try:
                    new_meta_data = self._normalize_tag(
                        new_tag, vr, value_str, new_meta_data
                    )
                except Exception as e:
                    logger.error(highlight_message("KNOWN VR EXCEPTION"))
                    logger.error(f"Tag: {new_tag}")
                    logger.error(f"Tag metadata: {tag_metadata}")
                    logger.error(traceback.format_exc())
                    logger.error(e)
                    raise ValueError(tag_metadata)

            else:
                logger.info(f"New tag: {new_tag}")
                handle_incomplete_tag_metadata(tag_metadata)

        return new_meta_data

    def _process_modality(self, metadata: Dict) -> Dict:
        """
        If dicom modality tag is "CT" and ImageType tag contains "Localizer", "CT" (3D) is changed to "XR" (2D)
        :param dcm_file: path to first slice of dicom image
        :param modality: dicom modality tag
        :return: _description_
        """
        assert self.MODALITY_TAG in metadata
        modality = metadata[self.MODALITY_TAG]

        metadata.update({"00000000 CuratedModality_keyword": modality})
        if self.IMAGE_TYPE_TAG in metadata:
            image_type = metadata[self.IMAGE_TYPE_TAG]
            if isinstance(image_type, list):
                if (
                    modality == "CT"
                    and "LOCALIZER" in image_type
                    and len(image_type) >= 3
                ):
                    metadata.update({"00000000 CuratedModality_keyword": "XR"})

        return metadata

    def _process_time_tags(self, metadata: Dict) -> Dict:
        time_tag_used = ""
        extracted_date = None
        extracted_time = None

        # Check for AcquisitionDateTime
        if "0008002A AcquisitionDateTime_datetime" in metadata:
            time_tag_used = "AcquisitionDateTime_datetime"
            datetime_formatted = metadata["0008002A AcquisitionDateTime_datetime"]

        else:
            # Define a mapping of date and time tags
            date_tags = (
                "00080022 AcquisitionDate_date",
                "00080021 SeriesDate_date",
                "00080023 ContentDate_date",
                "00080020 StudyDate_date",
            )
            time_tags = (
                "00080032 AcquisitionTime_time",
                "00080031 SeriesTime_time",
                "00080033 ContentTime_time",
                "00080030 StudyTime_time",
            )

            for tag in date_tags:
                if tag in metadata:
                    time_tag_used = get_tag_stem(tag)
                    extracted_date = metadata[tag]
                    break

            for tag in time_tags:
                if tag in metadata:
                    time_tag_used += " + " + get_tag_stem(tag)
                    extracted_time = metadata[tag]
                    break

            if extracted_date is None:
                logger.warning("NO AcquisitionDate! -> set to today")
                time_tag_used += "date not found -> arriving date"
                extracted_date = datetime.now().strftime(self.KAAPANA_DATE_FORMAT)

            if extracted_time is None:
                logger.warning("NO AcquisitionTime! -> set to now")
                time_tag_used += " + time not found -> arriving time"
                extracted_time = datetime.now().strftime(self.KAAPANA_TIME_FORMAT)

            datetime_string = f"{extracted_date} {extracted_time}"
            datetime_formatted = parser.parse(datetime_string).strftime(
                self.KAAPANA_DATETIME_FORMAT
            )

        # TODO NAIVE! Expects BerlinTime datetime and convert to UTC
        datetime_formatted = self.convert_time_to_utc(
            datetime_formatted, self.KAAPANA_DATETIME_FORMAT
        )

        # Update the metadata with the formatted datetime
        metadata["00000000 Timestamp_datetime"] = datetime_formatted

        # Update the metadata with arrival time
        current_utc_datetime = datetime.utcnow()
        formatted_utc_datetime = current_utc_datetime.strftime(
            self.KAAPANA_DATETIME_FORMAT
        )
        formatted_utc_date = current_utc_datetime.strftime(self.KAAPANA_DATE_FORMAT)

        # Formatted strings
        metadata["00000000 TimestampArrived_datetime"] = formatted_utc_datetime
        metadata["00000000 TimestampArrived_date"] = formatted_utc_date

        # Integers
        metadata["00000000 TimestampArrivedHour_integer"] = current_utc_datetime.hour
        metadata["00000000 DayOfWeek_integer"] = datetime.strptime(
            datetime_formatted, self.KAAPANA_DATETIME_FORMAT
        ).weekday()

        # Keywords
        metadata["00000000 TimeTagUsed_keyword"] = time_tag_used
        return metadata

    def _calculate_patient_age(self, metadata: Dict) -> int:
        birthdate = metadata["00100030 PatientBirthDate_date"]
        birthday_datetime = datetime.strptime(birthdate, self.KAAPANA_DATE_FORMAT)
        series_datetime = datetime.strptime(
            metadata["00000000 Timestamp_datetime"],
            self.KAAPANA_DATETIME_FORMAT,
        )
        patient_age_scan = (
            series_datetime.year
            - birthday_datetime.year
            - (
                (series_datetime.month, series_datetime.day)
                < (birthday_datetime.month, birthday_datetime.day)
            )
        )
        return patient_age_scan

    def _process_patient_age(self, metadata: Dict) -> Dict:
        if "00101010 PatientAge_keyword" in metadata:
            dcm_patient_age = process_age_string(
                metadata["00101010 PatientAge_keyword"]
            )
        else:
            dcm_patient_age = None

        if "00100030 PatientBirthDate_date" in metadata:
            calculated_patient_age = self._calculate_patient_age(metadata)
            metadata["00000000 DerivedPatientAge_integer"] = calculated_patient_age

            if dcm_patient_age and calculated_patient_age != dcm_patient_age:
                logger.error(highlight_message("Patient AGE inconsistency"))
                logger.error(
                    f"00000000 Timestamp: {metadata['00000000 Timestamp_datetime']}"
                )
                logger.error(
                    f"00100030 PatientBirthDate: {metadata['00100030 PatientBirthDate_date']}"
                )
                logger.error(f"Timestamp - PatientBirthDate: {calculated_patient_age}")
                logger.error(
                    f"00101010 PatientAge_keyword: {metadata['00101010 PatientAge_keyword']}"
                )
                logger.error(f"PatientAge: {dcm_patient_age}")

        elif "00101010 PatientAge_keyword" in metadata and dcm_patient_age:
            metadata["00000000 DerivedPatientAge_integer"] = dcm_patient_age
        return metadata

    def _process_clinical_trial_protocol_id(self, metadata: Dict) -> Dict:
        if "00120020 ClinicalTrialProtocolID_keyword" in metadata:
            protocol_ids = metadata["00120020 ClinicalTrialProtocolID_keyword"].split(
                ";"
            )
            logger.info(f"ClinicalTrialProtocolIDs: {protocol_ids}")
            metadata["00120020 ClinicalTrialProtocolID_keyword"] = protocol_ids
        return metadata

    def _format_datetime_value(self, new_tag, value_str):
        # Date Time
        # A concatenated date-time character string in the format:
        # YYYYMMDDHHMMSS.FFFFFF&ZZXX
        # 20020904000000.000000
        # "%Y-%m-%d %H:%M:%S.%f"
        try:
            datetime_formatted = None
            if validate_format(value_str, self.DCM_DATETIME_FORMAT):
                datetime_formatted = datetime.strptime(
                    value_str, self.DCM_DATETIME_FORMAT
                ).strftime(self.KAAPANA_DATETIME_FORMAT)
            else:
                logger.info(f"Value: {value_str} not complete dcm date time.")
                logger.info(f"Dicom Standard Format: {self.DCM_DATETIME_FORMAT}")

            if datetime_formatted is None:
                if len(value_str) > 8:
                    logger.info("Trying to parse long datetime format.")
                    datetime_formatted = parser.parse(value_str).strftime(
                        self.KAAPANA_DATETIME_FORMAT
                    )
                else:
                    logger.info("Trying to parse short date format with default time.")
                    date = parser.parse(value_str).date()
                    time = parser.parse("01:00:00").time()
                    datetime_formatted = datetime.combine(date, time).strftime(
                        self.KAAPANA_DATETIME_FORMAT
                    )

            datetime_formatted = self.convert_time_to_utc(
                datetime_formatted, self.KAAPANA_DATETIME_FORMAT
            )
            return datetime_formatted
        except Exception as e:
            logger.error(highlight_message("COULD NOT EXTRACT DATETIME"))
            logger.error(f"Tag  : {new_tag}")
            logger.error(f"Value: {value_str}")
            logger.error(f"Size : {len(value_str)}")
            logger.error(traceback.format_exc())
            logger.error(e)

            if self.exit_on_error:
                raise ValueError("COULD NOT EXTRACT DATETIME")

    def _format_date_value(self, value_str):
        # date
        # A string of characters of the format YYYYMMDD; where YYYY shall contain year,
        # MM shall contain the month, and DD shall contain the day, interpreted as a date of the Gregorian calendar system.
        # Example:
        # "19930822" would represent August 22, 1993.
        # Note:
        # The ACR-NEMA Standard 300 (predecessor to DICOM) supported a string of characters of the format
        # YYYY.MM.DD for this VR. Use of this format is not compliant.
        # See also DT VR in this table.
        try:
            if isinstance(value_str, list):
                date_formatted = [
                    parser.parse(date_str).strftime(self.KAAPANA_DATE_FORMAT)
                    for date_str in value_str
                    if date_str != ""
                ]
            elif isinstance(value_str, str):
                date_formatted = parser.parse(value_str).strftime(
                    self.KAAPANA_DATE_FORMAT
                )
            else:
                raise TypeError(
                    f"Not supported type {type(value_str)} of value {value_str}"
                )
            return date_formatted

        except Exception as e:
            logger.error(highlight_message("COULD NOT EXTRACT DATE"))
            logger.error(f"Value: {value_str}")
            logger.error(f"Size : {len(value_str)}")
            logger.error(traceback.format_exc())
            logger.error(e)

            if self.exit_on_error:
                raise ValueError("COULD NOT EXTRACT DATE")

    def _format_time_value(self, value_str):
        # Time
        # A string of characters of the format HHMMSS.FFFFFF; where HH contains hours (range "00" - "23"), MM contains minutes (range "00" - "59"),
        # SS contains seconds (range "00" - "60"), and FFFFFF contains a fractional part of a second as small as 1 millionth of a second (range "000000" - "999999").
        # A 24-hour clock is used. Midnight shall be represented by only "0000" since "2400" would violate the hour range. The string may be padded with trailing spaces.
        # Leading and embedded spaces are not allowed. One or more of the components MM, SS, or FFFFFF may be unspecified as long as every component
        # to the right of an unspecified component is also unspecified, which indicates that the value is not precise to the precision of those unspecified components.
        # The FFFFFF component, if present, shall contain 1 to 6 digits. If FFFFFF is unspecified the preceding "." shall not be included.

        # Examples:
        # "070907.0705 " represents a time of 7 hours, 9 minutes and 7.0705 seconds.
        # "1010" represents a time of 10 hours, and 10 minutes.
        # "021 " is an invalid value.
        # Note
        # The ACR-NEMA Standard 300 (predecessor to DICOM) supported a string of characters of the format HH:MM:SS.frac for this VR. Use of this format is not compliant.
        # See also DT VR in this table.
        # The SS component may have a value of 60 only for a leap second.
        if isinstance(value_str, list):
            time_formatted = []

            for time_str in value_str:
                if time_str == "" or time_str is None:
                    continue
                time_formatted.append(self._get_time(time_str))
        else:
            time_formatted = self._get_time(value_str)

        return time_formatted

    def _get_time(self, time_str):
        if validate_format(time_str, self.DCM_TIME_FORMAT):
            return datetime.strptime(time_str, self.DCM_TIME_FORMAT).strftime(
                self.KAAPANA_TIME_FORMAT
            )

        hour = 0
        minute = 0
        sec = 0
        fsec = 0
        if "." in time_str:
            time_str = time_str.split(".")
            if time_str[1] != "":
                fsec = int(time_str[1])
            time_str = time_str[0]

        if len(time_str) == 6:
            hour = int(time_str[:2])
            minute = int(time_str[2:4])
            sec = int(time_str[4:6])
        elif len(time_str) == 4:
            hour = int(time_str[:2])
            minute = int(time_str[2:4])
        elif len(time_str) == 2:
            hour = int(time_str)

        else:
            logger.error(highlight_message("COULD NOT EXTRACT TIME"))
            logger.error(f"Value: {time_str}")

            if self.exit_on_error:
                raise ValueError("COULD NOT EXTRACT TIME")

        # HH:mm:ss.SSSSS
        time_string = f"{hour:02}:{minute:02}:{sec:02}.{fsec:06}"
        time_formatted = parser.parse(time_string).strftime(self.KAAPANA_TIME_FORMAT)

        return time_formatted

    def _process_sequence_value(self, value_str):
        if isinstance(value_str, dict):
            return self._normalize_tags(value_str)

        elif isinstance(value_str, list):
            processed_values = self._check_list(value_str)
            if isinstance(processed_values, dict):
                return processed_values

            elif isinstance(processed_values, list):
                for value in processed_values:
                    if isinstance(value, dict):
                        logger.info("Sequence value is nested too much. Skipping...")
                        logger.info("Nesting: dict -> list -> dict -> ... ")

                    else:
                        logger.error("Unexpected nested sequence")
                        if self.exit_on_error:
                            raise ValueError("Unexpected nested sequence")
            else:
                logger.error("Unexpected nested sequence")
                if self.exit_on_error:
                    raise ValueError("Unexpected nested sequence")
        else:
            return None

    def _check_list(self, value_list):
        tmp_data = []
        for element in value_list:
            if isinstance(element, dict):
                tags_replaced = self._normalize_tags(element)
                tmp_data.append(tags_replaced)

            elif isinstance(element, list):
                tmp_data.append(self._check_list(element))

            else:
                tmp_data.append(element)

        return tmp_data

    @staticmethod
    def convert_time_to_utc(time_berlin: str, date_format: str):
        local = pytz.timezone("Europe/Berlin")
        naive = datetime.strptime(time_berlin, date_format)
        local_dt = local.localize(naive, is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)

        return utc_dt.strftime(date_format)


def handle_incomplete_tag_metadata(tag_metadata: Dict):
    if "InlineBinary" in tag_metadata:
        logger.info(highlight_message("SKIPPING BINARY"))
    elif "Value" not in tag_metadata:
        logger.info(
            f"No value found in entry: {str(tag_metadata).strip('[]').encode('utf-8')}"
        )
    elif "vr" not in tag_metadata:
        logger.info(
            f"No vr found in entry: {str(tag_metadata).strip('[]').encode('utf-8')}"
        )
    else:
        logger.error(highlight_message("IMPOSSIBLE REACH"))
        logger.error("Value or vr missing but present at the same time.")
        if "vr" in tag_metadata:
            logger.error(f"VR: {tag_metadata['vr'].encode('utf-8')}")
        if "Value" in tag_metadata:
            entry_value = str(tag_metadata["Value"]).strip("[]").encode("utf-8")
            logger.error(f"value: {entry_value}")


def get_tag_stem(tag: str) -> str:
    # Example 000800016 SomethingVeryImportant_datetime -> SomethingVeryImportant
    return tag.split(" ")[-1].split("_")[0]


def highlight_message(message: str) -> str:
    highlight = "#" * 10
    highlighted_message = f"{highlight} {message} {highlight}"
    return highlighted_message


def can_be_type(value, value_type):
    try:
        value_type(value)
        return True
    except ValueError:
        return False


def convert(obj: Any, val_type: type):
    if isinstance(obj, val_type):
        return obj

    if isinstance(obj, list):
        return [val_type(element) for element in obj]

    if can_be_type(obj, val_type):
        return val_type(obj)

    if val_type is int and can_be_type(obj, float):
        return val_type(float(obj))

    logger.error("Cannot convert!")
    logger.error(f"Value: {obj}")
    logger.error(f"Needed-Type: {val_type}")
    logger.error(f"Found-Type:  {type(obj)}")
    return obj


def validate_format(value_str, format_str):
    try:
        datetime.strptime(value_str, format_str)
        return True
    except ValueError:
        return False


def strip_if_possible(value_str):
    if isinstance(value_str, str):
        return value_str.strip()
    elif isinstance(value_str, list):
        return [strip_if_possible(value) for value in value_str]
    else:
        return value_str


def process_age_string(age_string: str) -> Union[int, None]:
    try:
        unit = age_string[-1]  # Unit can be 'D', 'M', or 'Y'
        quantity = age_meta = int(age_string[:-1])
        if unit == "D":
            age_meta = quantity // 365
        elif unit == "M":
            age_meta = quantity // 12
        elif unit == "W":
            age_meta = quantity // 7
        elif unit == "Y":
            age_meta = quantity
        else:
            raise ValueError(f"Unknown patient age unit {age_string}")
        return age_meta

    except Exception as e:
        logger.error(f"Could not extract age-int from metadata. {age_string}")
        logger.error(traceback.format_exc())
        logger.error(e)
        return None
