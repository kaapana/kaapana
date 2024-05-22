import os
import time
from datetime import datetime
from pytz import timezone
import json
import glob
from html.parser import HTMLParser
from opensearchpy import OpenSearch
from enum import Enum
from typing import List
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE


class ClassHTMLParser(HTMLParser):
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


class LocalStoreValidationResultsOperator(KaapanaPythonBaseOperator):
    """
    This Operator extracts validation results from HTML files from the operator input dir
    and stores these results as metadata for DICOM files in OpenSearch.
    """

    @staticmethod
    def _get_next_hex_tag(current_tag: str):
        """
        Generates the next hexadecimal tag based on the current tag.

        :param current_tag: The current hexadecimal tag as a string.
        :return: The next hexadecimal tag as a string.
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

    def tagging(
        self,
        series_instance_uid: str,
        validation_tags: List[tuple],
        clear_results: bool = False,
    ):
        """
        Updates the tags for a given series instance UID in OpenSearch.

        :param series_instance_uid: The series instance UID for which the tags are to be updated.
        :param validation_tags: A list of tuples containing the validation tags to add.
        :param clear_results: Boolean indicating whether to clear existing results.
        """
        print(series_instance_uid)
        print(f"Tags 2 add: {validation_tags}")

        # Read Tags
        auth = None
        os_client = OpenSearch(
            hosts=[{"host": self.opensearch_host, "port": self.opensearch_port}],
            http_compress=True,  # enables gzip compression for request bodies
            http_auth=auth,
            # client_cert = client_cert_path,
            # client_key = client_key_path,
            use_ssl=False,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            timeout=2,
            # ca_certs = ca_certs_path
        )

        doc = os_client.get(index=self.opensearch_index, id=series_instance_uid)
        print(doc)

        if clear_results:
            # Write Tags back
            body = {"doc": {self.tag_field: None}}
            os_client.update(
                index=self.opensearch_index, id=series_instance_uid, body=body
            )

        final_tags = {}

        current_tag = str(self.validation_tag)
        for idx, item in enumerate(validation_tags):
            item_tag = self._get_next_hex_tag(current_tag)
            item_key = f"{item_tag} Validation{item[0]}_{item[1]}"
            final_tags[item_key] = item[2]
            current_tag = str(item_tag)

        print(f"Final tags: {final_tags}")

        # Write Tags back
        body = {"doc": {self.tag_field: final_tags}}
        os_client.update(index=self.opensearch_index, id=series_instance_uid, body=body)

    def _extract_validation_results_from_html(self, html_output_path: str):
        """
        Extracts validation results from an HTML file.

        :param html_output_path: The path to the HTML file containing validation results.
        :return: A tuple containing the number of errors, number of warnings, and the validation time.
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

    def start(self, ds, **kwargs):
        print("Start tagging")

        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folder = [
            f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))
        ]

        print(self.batch_name, batch_folder)

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

            # tags = n_errors
            tags_tuple = [
                ("Errors", "integer", n_errors),  # (key, opensearch datatype, value)
                ("Warnings", "integer", n_warnings),
                ("Date", "datetime", validation_time),
            ]

            for meta_files in json_files:
                print(f"Do tagging for file {meta_files}")
                with open(meta_files) as fs:
                    metadata = json.load(fs)
                    series_uid = metadata["0020000E SeriesInstanceUID_keyword"]
                    existing_tags = metadata.get(self.tag_field, None)

                    clear_old_results = False
                    if existing_tags:
                        print(
                            f"Warning!! Data found on tag {self.tag_field}. Will be replaced by newer results"
                        )
                        clear_old_results = True

                    self.tagging(
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
        :param validator_output_dir: Directory where validation output files are stored.
        :param validation_tag: Base tag used for validation (default: "00111001").
        :param name: Name of the operator (default: "results-to-open-search").
        :param opensearch_host: Hostname of the OpenSearch service.
        :param opensearch_port: Port of the OpenSearch service.
        :param opensearch_index: Index in OpenSearch where metadata will be stored.
        """

        self.tag_field = f"{validation_tag} ValidationResults_object"
        self.validator_output_dir = validator_output_dir
        self.validation_tag = validation_tag
        self.opensearch_host = opensearch_host
        self.opensearch_port = opensearch_port
        self.opensearch_index = opensearch_index

        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
