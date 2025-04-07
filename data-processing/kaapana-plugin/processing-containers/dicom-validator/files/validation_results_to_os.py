import glob
import json
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from html.parser import HTMLParser
from os import getenv
from typing import List

from kaapanapy.helper import get_opensearch_client, load_workflow_config
from kaapanapy.helper.HelperOpensearch import DicomTags
from kaapanapy.logger import get_logger
from kaapanapy.settings import OpensearchSettings, OperatorSettings
from pytz import timezone

logger = get_logger(__name__, level="INFO")


@dataclass
class ValdationResultItem:
    key: str
    datatype: str
    value: any


class ValidationResult2Meta:
    """
    This Class extracts validation results from HTML files in the operator input directory
    and stores these results as metadata for DICOM files in OpenSearch.

    Attributes:
        validation_tag (str): Base tag used for validation.
        tag_field (str): Field in the OpenSearch index used for validation results.
        opensearch_index (str): Index in OpenSearch where metadata is stored.
        os_client (OpenSearch): OpenSearch client for interacting with the OpenSearch service.

    Methods:
        _get_next_hex_tag(current_tag): Generates the next hexadecimal tag based on the current tag.
        add_tags_to_opensearch(series_instance_uid, validation_tags, clear_results): Adds validation tags to OpenSearch.
        _extract_validation_results_from_html(html_output_path): Extracts validation results from an HTML file.
        _init_client(): Initializes the OpenSearch client.
        start(ds, **kwargs): Main execution method called by Airflow to run the operator.
    """

    def __init__(
        self,
        opensearch_index: str = None,
        validation_tag: str = "00111001",
    ):
        # OS settings
        self.opensearch_settings = OpensearchSettings()
        self.helper_opensearch = get_opensearch_client()

        self.opensearch_index = opensearch_index

        self.validation_tag = validation_tag
        self.tag_field = f"{validation_tag} ValidationResults_object"

        # Airflow variables
        workflow_config = load_workflow_config()

        # set the opensearch_index if not provided
        # Set the project index from workflow config or else default index from settings
        if not opensearch_index:
            project_opensearch_index = workflow_config["project_form"][
                "opensearch_index"
            ]
            self.opensearch_index = (
                project_opensearch_index
                if project_opensearch_index is not None
                else OpensearchSettings().default_index
            )

        self.os_client = get_opensearch_client()

    @staticmethod
    def _get_next_hex_tag(current_tag: str):
        """
        Generates the next hexadecimal tag based on the current tag.

        Args:
            current_tag (str): The current hexadecimal tag as a string.

        Returns:
            str: The next hexadecimal tag as a string.
        """
        # Split the current tag into the first and second parts
        first_part = current_tag[0:4]
        second_part = current_tag[-4:]

        # Convert the second part to an integer
        item_num = int(second_part, 16)

        # Increment the integer
        item_num += 1

        # Convert the incremented number back to a hexadecimal string
        item_hex = hex(item_num)[2:]

        # Combine the first part and the new hexadecimal number to form the next tag
        next_tag = f"{first_part}{item_hex}"

        return next_tag

    def add_tags_to_opensearch(
        self,
        series_instance_uid: str,
        validation_tags: List[ValdationResultItem],
        clear_results: bool = False,
    ):
        """
        Adds validation tags to a document in OpenSearch.

        Args:
            series_instance_uid (str): The unique identifier for the series in OpenSearch.
            validation_tags (List[tuple]): A list of tuples containing validation tags to be added.
            clear_results (bool): Whether to clear existing validation results before adding new ones. Defaults to False.

        Returns:
            None
        """
        logger.info(series_instance_uid)
        logger.info(f"Tags 2 add: {validation_tags}")

        doc = self.os_client.get(index=self.opensearch_index, id=series_instance_uid)
        logger.info(doc)

        if clear_results:
            # Write Tags back
            body = {"doc": {self.tag_field: None}}
            self.os_client.update(
                index=self.opensearch_index, id=series_instance_uid, body=body
            )

        final_tags = {}

        current_tag = str(self.validation_tag)
        for _, item in enumerate(validation_tags):
            item_tag = self._get_next_hex_tag(current_tag)
            item_key = f"{item_tag} Validation{item.key}_{item.datatype}"
            final_tags[item_key] = item.value
            current_tag = str(item_tag)

        logger.info(f"Final tags: {final_tags}")

        # Write validation results to doc
        body = {"doc": {self.tag_field: final_tags}}
        self.os_client.update(
            index=self.opensearch_index, id=series_instance_uid, body=body
        )
