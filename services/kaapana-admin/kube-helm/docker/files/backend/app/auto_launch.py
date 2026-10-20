"""Keep configured multi-installable apps running once per project.

AUTO_LAUNCH_PROJECT_APPS (rendered from global.auto_launch_project_apps) lists the
apps. A periodic reconciler installs each of them for every project that has no
instance yet, so they come back after a redeploy and new projects get them without
a manual launch from the UI. AUTO_LAUNCH_EXCLUDE_PROJECTS names the projects that
get none; an app's own "exclude_projects" replaces that list for this app.
"""

import fnmatch
import json

import httpx
from kaapanapy.logger import get_logger

from . import helm_helper, utils
from .config import settings
from .repeat_timer import RepeatedTimer

logger = get_logger(__name__)


def reconcile_project_apps():
    """Install every configured app for every project that has no instance of it."""
    # An undeploy uninstalls the platform release and the app releases in parallel;
    # installing while it runs would leave behind releases the undeploy just removed.
    platform_status = utils.get_helm_status_name(settings.release_name, "default")
    if platform_status != helm_helper.CHART_STATUS_DEPLOYED:
        logger.info(f"auto-launch: platform release is '{platform_status}', skipping")
        return
    response = httpx.get(f"{settings.aii_service_url}/projects", timeout=30)
    response.raise_for_status()
    projects = response.json()
    releases = {
        release["name"]
        for chart_releases in utils.collect_helm_deployments().values()
        for release in chart_releases
    }
    default_excluded = json.loads(settings.auto_launch_exclude_projects)
    for app in json.loads(settings.auto_launch_project_apps):
        # Per app, because apps differ in where they belong: one may have to reach
        # the admin project that the default list keeps the others out of.
        excluded = app.get("exclude_projects", default_excluded)
        version = app.get("version") or settings.kaapana_build_version
        chart = helm_helper.helm_show_chart(name=app["name"], version=version)
        label = chart.get("annotations", {}).get("ui-visible-name", app["name"])
        for project in projects:
            # short_id is immutable and DNS-safe, so it gives each project exactly
            # one release name per app; finding that release makes this idempotent.
            release_name = f"{app['name']}-{project['short_id']}"
            if (
                release_name in releases
                or project.get("is_archived")
                or any(fnmatch.fnmatch(project["name"], p) for p in excluded)
            ):
                continue
            # The same project context routes.helm_install_chart adds to a launch.
            extension_params = {
                **app.get("extension_params", {}),
                "project_id": project["id"],
                "project_name": project["name"],
                "project_short_id": project["short_id"],
                "project_namespace": project["kubernetes_namespace"],
                "display_name": f"{label}-{project['name']}",
            }
            logger.info(f"auto-launch: installing {release_name}")
            utils.helm_install(
                {
                    "name": app["name"],
                    "version": version,
                    "release_name": release_name,
                    "extension_params": extension_params,
                },
                shell=True,
                blocking=True,
            )


def _reconcile():
    try:
        reconcile_project_apps()
    except Exception:
        logger.exception("auto-launch: reconcile failed, retrying next interval")


def start_reconciler():
    """Start the periodic reconciler if any app is configured; return its timer."""
    if not json.loads(settings.auto_launch_project_apps):
        return None
    # The first cycle runs one interval after startup, which gives the extension
    # cache and the AII time to come up after a deploy.
    return RepeatedTimer(settings.auto_launch_interval_seconds, _reconcile)
