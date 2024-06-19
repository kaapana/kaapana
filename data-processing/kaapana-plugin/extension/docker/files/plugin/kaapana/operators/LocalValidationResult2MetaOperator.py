import os
from dataclasses import dataclass
from datetime import datetime
from pytz import timezone
import json
import glob
from html.parser import HTMLParser
from enum import Enum
from typing import List
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.HelperOpensearch import HelperOpensearch
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE


@dataclass
class ValdationResultItem:
    key: str
    datatype: str
    value: any


class ClassHTMLParser(HTMLParser):
    """
    A custom HTML parser that captures data within tags that have a specific class attribute.
    This parser will read an HTML document line by line and extract the content between start
    tag to end tag of an element with provided class name.

    Attributes:
        class_name (str): The class name to look for in HTML tags.
        capture (bool): A flag indicating whether the parser is currently capturing data.
        data (list): A list to store captured data.
    """

    def __init__(self, class_name):
        super().__init__()
        self.class_name = class_name
        self.capture = False
        self.data = []

    def handle_starttag(self, tag, attrs):
        if any((attr == ("class", self.class_name) for attr in attrs)):
            self.capture = True

    def handle_endtag(self, tag):
        if self.capture:
            self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.data.append(data.strip())


def get_file_creation_time(file_path):
    # Get file stats
    stats = os.stat(file_path)
    # Get creation time (on Unix, this is the change time)
    creation_time = datetime.fromtimestamp(stats.st_ctime, tz=timezone("Europe/Berlin"))
    # Convert to a human-readable format
    readable_time = creation_time.strftime("%Y-%m-%d %H:%M:%S.%f")
    return readable_time


class LocalValidationResult2MetaOperator(KaapanaPythonBaseOperator):
    """
    This Operator extracts validation results from HTML files in the operator input directory
    and stores these results as metadata for DICOM files in OpenSearch.

    Attributes:
        validator_output_dir (str): Directory where validation output files are stored.
        validation_tag (str): Base tag used for validation.
        tag_field (str): Field in the OpenSearch index used for validation results.
        opensearch_host (str): Hostname of the OpenSearch service.
        opensearch_port (int): Port of the OpenSearch service.
        opensearch_index (str): Index in OpenSearch where metadata is stored.
        os_client (OpenSearch): OpenSearch client for interacting with the OpenSearch service.

    Methods:
        _get_next_hex_tag(current_tag): Generates the next hexadecimal tag based on the current tag.
        add_tags_to_opensearch(series_instance_uid, validation_tags, clear_results): Adds validation tags to OpenSearch.
        _extract_validation_results_from_html(html_output_path): Extracts validation results from an HTML file.
        _init_client(): Initializes the OpenSearch client.
        start(ds, **kwargs): Main execution method called by Airflow to run the operator.
    """

    class Action(Enum):
        ADD = "add"
        DELETE = "delete"

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
        print(series_instance_uid)
        print(f"Tags 2 add: {validation_tags}")

        doc = self.os_client.get(index=self.opensearch_index, id=series_instance_uid)
        print(doc)

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

        print(f"Final tags: {final_tags}")

        # Write validation results to doc
        body = {"doc": {self.tag_field: final_tags}}
        self.os_client.update(
            index=self.opensearch_index, id=series_instance_uid, body=body
        )

    def _extract_validation_results_from_html(self, html_output_path: str):
        """
        Extracts validation results from an HTML file.

        Args:
            html_output_path (str): Path to the HTML file containing validation results.

        Returns:
            tuple: A tuple containing the number of errors, number of warnings, and the validation time.
        """
        error_parser = ClassHTMLParser("item-count-label error")
        with open(html_output_path, "r") as file:
            error_parser.feed(file.read())

        warning_parser = ClassHTMLParser("item-count-label warning")
        with open(html_output_path, "r") as file:
            warning_parser.feed(file.read())

        n_errors = error_parser.data[0] if len(error_parser.data) > 0 else ""
        n_warnings = warning_parser.data[0] if len(warning_parser.data) > 0 else ""
        validation_time = get_file_creation_time(html_output_path)

        return n_errors, n_warnings, validation_time

    def _init_client(self):
        """
        Point to the already initialized HelperOpensearch client.

        Returns:
            None
        """
        self.os_client = HelperOpensearch.os_client

    def start(self, ds, **kwargs):
        """
        Main execution method called by Airflow to run the operator.

        Args:
            ds (str): The execution date as a string.
            **kwargs: Additional keyword arguments provided by Airflow.

        Returns:
            None
        """
        print("Start tagging")

        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folder = [
            f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))
        ]

        self._init_client()

        for batch_element_dir in batch_folder:
            html_outputs = []
            if self.validator_output_dir != "":
                html_outputs = sorted(
                    glob.glob(
                        os.path.join(
                            batch_element_dir, self.validator_output_dir, "*.html*"
                        ),
                        recursive=True,
                    )
                )

            if len(html_outputs) == 0:
                print(
                    f"No validation output file found to update validation results in batch directory {batch_element_dir}. Skipping validation meta tagging"
                )
                continue

            n_errors, n_warnings, validation_time = (
                self._extract_validation_results_from_html(html_outputs[0])
            )

            json_files = sorted(
                glob.glob(
                    os.path.join(batch_element_dir, self.operator_in_dir, "*.json*"),
                    recursive=True,
                )
            )

            tags_tuple = [
                ValdationResultItem(
                    "Errors", "integer", n_errors
                ),  # (key, opensearch datatype, value)
                ValdationResultItem("Warnings", "integer", n_warnings),
                ValdationResultItem("Date", "datetime", validation_time),
            ]

            for meta_files in json_files:
                print(f"Do tagging for file {meta_files}")
                with open(meta_files) as fs:
                    metadata = json.load(fs)
                    series_uid = metadata[
                        HelperOpensearch.series_uid_tag
                    ]  # "0020000E SeriesInstanceUID_keyword"
                    existing_tags = metadata.get(self.tag_field, None)

                    clear_old_results = False
                    if existing_tags:
                        print(
                            f"Warning!! Data found on tag {self.tag_field}. Will be replaced by newer results"
                        )
                        clear_old_results = True

                    self.add_tags_to_opensearch(
                        series_uid,
                        validation_tags=tags_tuple,
                        clear_results=clear_old_results,
                    )

    def __init__(
        self,
        dag,
        validator_output_dir: str,
        validation_tag: str = "00111001",
        name: str = "results-to-open-search",
        opensearch_host=f"opensearch-service.{SERVICES_NAMESPACE}.svc",
        opensearch_port=9200,
        opensearch_index="meta-index",
        *args,
        **kwargs,
    ):
        """
        Initializes the LocalValidationResult2MetaOperator.

        Args:
            dag (DAG): The DAG to which the operator belongs.
            validator_output_dir (str): Directory where validation output files are stored.
            validation_tag (str): Base tag used for validation (default: "00111001").
                    Multiple items of the validation results will be tagged by incrementing
                    this tag. e.g. 00111002, 00111003, ..
            name (str): Name of the operator (default: "results-to-open-search").
            opensearch_host (str): Hostname of the OpenSearch service (default: "opensearch-service.{SERVICES_NAMESPACE}.svc").
            opensearch_port (int): Port of the OpenSearch service (default: 9200).
            opensearch_index (str): Index in OpenSearch where metadata will be stored (default: "meta-index").
            *args: Additional arguments for the parent class.
            **kwargs: Additional keyword arguments for the parent class.

        Returns:
            None
        """

        self.validator_output_dir = validator_output_dir
        self.validation_tag = validation_tag
        self.tag_field = f"{validation_tag} ValidationResults_object"
        self.opensearch_host = opensearch_host
        self.opensearch_port = opensearch_port
        self.opensearch_index = opensearch_index
        self.os_client = None

        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
