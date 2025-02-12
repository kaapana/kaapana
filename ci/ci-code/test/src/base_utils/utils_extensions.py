import json
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from .KaapanaAuth import KaapanaAuth
from .logger import get_logger
import logging, sys
import time
import os, json

logger = get_logger(__name__, logging.DEBUG)

REPO_DIR = os.getenv("REPO_DIR")


class ExtensionEndpoints(KaapanaAuth):
    json_extension_params = (
        f"{REPO_DIR}/ci-code/test/jobs/extensions/extension_params.json"
    )
    with open(json_extension_params) as f:
        extension_params = json.load(f)

    def wait_for_dag(self, dag_id, timeout=300):
        """
        Wait timeout seconds for all jobs of a workflow with dag_id <dag_id> to be in state finished.
        Returns True if all jobs are in state finished for the first workflow with dag_id <dag_id> in the response body of the api call.
        """
        t_zero = time.time()
        while abs(t_zero - time.time()) < timeout:
            r = self.request(
                "kaapana-backend/client/workflows", request_type=requests.get
            )
            workflows = r.json()
            for workflow in workflows:
                if workflow.get("dag_id", None) == dag_id:
                    workflow_jobs = workflow.get("workflow_jobs", [])
                    if workflow_jobs and workflow_jobs == [
                        "finished" for _ in workflow_jobs
                    ]:
                        return True
                    else:
                        break
            time.sleep(5)
        logger.warning(f"Dag {dag_id} has unfinished jobs after {timeout=} seconds!")
        return False

    def get_helm_status(self, extension):
        """
        Get information about the helm extension.
        DEPRECATED and not used.
        """
        params = {"release_name": extension["release_name"]}
        r = self.request(
            "kube-helm-api/view-chart-status",
            request_type=requests.get,
            params=params,
            raise_for_status=False,
        )
        try:
            message = r.json()["STATUS"]
        except requests.exceptions.JSONDecodeError:
            message = r.text
        return message

    def delete_extension(self, extension):
        app = extension["chart_name"]
        version = extension["latest_version"]
        payload = {
            "helm_command_addons": "",
            "release_name": app,
            "release_version": version,
        }
        r = self.request(
            f"kube-helm-api/helm-delete-chart", request_type=requests.post, json=payload
        )

    def install_extension(self, extension):
        """
        Install extension via the kube-helm-api.
        If extension already installed log INFO message
        """
        payload = {
            "name": extension["chart_name"],
            "version": extension["latest_version"],
            "keywords": extension.get("keywords", []),
        }
        if (name := extension.get("chart_name")) in ExtensionEndpoints.extension_params:
            payload["extension_params"] = ExtensionEndpoints.extension_params.get(name)

        payload = json.dumps(payload)
        r = self.request(
            "kube-helm-api/helm-install-chart",
            request_type=requests.post,
            data=payload,
            raise_for_status=False,
        )
        if r.status_code == 500:
            logger.warning(r.text)
            return "SKIP"

    def wait_for_helm_status(self, extension):
        """
        Wait until the helm status of extension is "deployed"
        DEPRECATED!!
        """
        chart_name = extension["chart_name"]
        tries = 0
        helm_status = "Not available!"
        while helm_status != "deployed" and tries < 60:
            helm_status = self.get_helm_status(extension)
            time.sleep(5)
            tries += 1
        if tries >= 60:
            logger.debug(f"Helm Status: {helm_status} for app {chart_name}")
            logger.error(f"Maximum time for installing the {chart_name} exceeded!")
            sys.exit(1)
        logger.info(f"App {chart_name} in state {helm_status}")

    def get_all_extensions(self):
        """
        Get the information about all extensions via the kube-helm api.
        """
        r = self.request(
            "kube-helm-api/extensions", request_type=requests.get, timeout=100
        )
        return r.json()

    def extension_is_installed(self, extension):
        """
        Return true if extension is successfully installed or deployed else false.
        Decide based on the information from the kube-helm api.
        """
        extensions = self.get_all_extensions()
        for ext in extensions:
            if ext["chart_name"] == extension["chart_name"]:
                current_extension_state = ext
                break

        kind = current_extension_state.get("kind", None)
        if kind == "dag":
            if current_extension_state.get("installed") == "yes":
                return True
            else:
                return False
        elif kind == "application":
            version = current_extension_state.get("version")
            deployments = current_extension_state["available_versions"][version].get(
                "deployments", []
            )
            for dep in deployments:
                dep_helm_status = dep.get("helm_status").lower()
                dep_kube_status = dep.get("kube_status", ["not_ready"])
                return dep_helm_status == "deployed" and set(dep_kube_status).issubset(
                    {"running", "completed"}
                )
        else:
            logger.warning(f"Unknown kind of extensions: {kind}")
