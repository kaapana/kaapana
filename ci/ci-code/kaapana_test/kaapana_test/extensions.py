import json
import logging

import requests
from kaapana_test.utils.KaapanaAuth import KaapanaAuth
from kaapana_test.utils.logger import get_logger

logger = get_logger(__name__, logging.DEBUG)


class ExtensionEndpoints(KaapanaAuth):
    def __init__(self, host, client_secret):
        super().__init__(host, client_secret)

    def install_extension(self, extension, extension_params) -> bool:
        """
        Install extension via the kube-helm-api.
        If extension already installed log INFO message
        """
        chart_name = extension.get("chart_name")
        release_version = extension.get(
            "release_version", extension.get("latest_version")
        )
        payload = {
            "name": chart_name,
            "version": release_version,
            "keywords": extension.get("keywords", []),
        }
        payload["extension_params"] = extension_params
        payload = json.dumps(payload)
        r = self.request(
            "kube-helm-api/helm-install-chart",
            request_type=requests.post,
            data=payload,
            raise_for_status=False,
        )
        if r.status_code == 409:
            logger.info("Extension %s already installed, skipping.", chart_name)
            return True

        if r.status_code == 200:
            logger.info("Extension %s installed successfully.", chart_name)
            return True

        logger.error(
            "Install extension %s failed (%s): %s", chart_name, r.status_code, r.text
        )
        return False

    def delete_extension(self, extension) -> bool:
        # Prefer explicit release identifiers when present (multi-instance releases).
        chart_name = extension.get("chart_name")
        release_name = extension.get("releaseName", chart_name)
        release_version = extension.get(
            "release_version", extension.get("latest_version")
        )
        payload = {
            "helm_command_addons": "",
            "release_name": release_name,
            "release_version": release_version,
        }
        payload = json.dumps(payload)
        r = self.request(
            "kube-helm-api/helm-delete-chart",
            request_type=requests.post,
            data=payload,
            raise_for_status=False,
        )

        if r.status_code == 404:
            logger.info(
                "Extension %s (release=%s) already deleted, skipping.",
                chart_name,
                release_name,
            )
            return True

        if r.status_code == 200:
            logger.info(
                "Extension %s (release=%s version=%s) deleted successfully.",
                chart_name,
                release_name,
                release_version,
            )
            return True

        logger.error(
            "Delete extension %s (release=%s) failed (%s): %s",
            chart_name,
            release_name,
            r.status_code,
            getattr(r, "text", r.content),
        )
        return False

    def get_all_extensions(self):
        """
        Get the information about all extensions via the kube-helm api.
        """
        r = self.request(
            "kube-helm-api/extensions", request_type=requests.get, timeout=100
        )
        return r.json()

    @staticmethod
    def resolve_extension(ext, all_extensions):
        for ext in all_extensions:
            if (
                ext["chart_name"] == ext["chart_name"]
                and ext["latest_version"] == ext["latest_version"]
            ):
                return ext
        return None

    @staticmethod
    def parse_extension_specs(spec: list[str], available_extensions) -> list:
        """Parse a single extension spec string like 'chart_name:version' into dict."""
        extensions = []
        for s in spec:
            name, version = s.split(":", 1)
            ext = {
                "chart_name": name,
                "latest_version": version,
                "release_name": version,
            }
            resolved = ExtensionEndpoints.resolve_extension(ext, available_extensions)
            if not resolved:
                raise ValueError(
                    f"Extension {name}:{version} not found in available extensions"
                )
            extensions.append(resolved)

        return extensions

    @staticmethod
    def load_extensions_from_file(path: str, available_extensions) -> list:
        """Load extension dicts from a YAML file or JSON list file.

        This keeps the script simple: callers can pass a filename and get
        a list of extension dicts back.
        """
        resolved_extensions = []
        extensions = []
        try:
            from yaml import safe_load_all

            with open(path) as f:
                data = list(safe_load_all(f))
                # yaml.safe_load_all may return generator of docs; flatten
                for doc in data:
                    if isinstance(doc, list):
                        extensions.extend(doc)
                    elif isinstance(doc, dict):
                        extensions.append(doc)
                return extensions
        except Exception:
            # fallback: try json
            with open(path) as f:
                extensions.extend(json.load(f))

        for ext in extensions:
            resolved = ExtensionEndpoints.resolve_extension(ext, available_extensions)
            if not resolved:
                raise ValueError(
                    f"Extension {ext.get('chart_name')}:{ext.get('latest_version')} not found in available extensions"
                )
            resolved_extensions.append(resolved)
        return resolved_extensions

    def extension_is_installed(self, extension) -> bool:
        """
        Return true if extension is successfully installed or deployed else false.
        Decide based on the information from the kube-helm api.
        """
        if (
            extension.get("kind") == "application"
            and extension.get("multiinstallable") == "yes"
            and extension.get("helmStatus") is None
        ):
            return True

        extensions = self.get_all_extensions()
        current_extension_state = None
        for ext in extensions:
            if ext.get("chart_name") == extension.get("chart_name"):
                current_extension_state = ext
                break

        if not current_extension_state:
            logger.debug("Extension %s not found", extension.get("chart_name"))
            return False

        kind = current_extension_state.get("kind")
        if kind == "dag":
            return current_extension_state.get("installed") == "yes"
        elif kind == "application":
            version = current_extension_state.get("version")
            available_versions = current_extension_state.get("available_versions", {})
            version_info = available_versions.get(version, {})
            deployments = version_info.get("deployments", [])
            for dep in deployments:
                dep_helm_status = (dep.get("helm_status") or "").lower()
                dep_kube_status = dep.get("kube_status") or []
                if dep_helm_status == "deployed" and set(dep_kube_status).issubset(
                    {"running", "completed"}
                ):
                    return True
            return False
        else:
            logger.warning("Unknown kind of extensions: %s", kind)
            return False

    def delete_extensions(self, extensions):
        failed = []
        processed = []
        for ext in extensions:
            extension_installed = self.extension_is_installed(ext)
            if extension_installed:
                result = self.delete_extension(ext)
                if not result:
                    failed.append(ext)
            processed.append(ext)
        return processed, failed

    def install_extensions(self, extensions, extension_params):
        failed = []
        processed = []
        for ext in extensions:
            extension_installed = self.extension_is_installed(ext)
            if not extension_installed:
                result = self.install_extension(
                    ext, extension_params.get(ext.get("chart_name"), {})
                )
                if not result:
                    failed.append(ext)
            processed.append(ext)
        return processed, failed

    @staticmethod
    def wait_for_extensions_installation():
        pass
