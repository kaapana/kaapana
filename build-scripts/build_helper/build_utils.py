from time import time
import json
import semver
import networkx as nx
from os.path import join, dirname, basename, exists, isfile, isdir
from git import Repo

class BuildUtils:
    max_build_rounds = 4
    container_images_available = None
    container_images_unused = None
    charts_available = None
    charts_unused = None
    base_images_used = None
    logger = None
    kaapana_dir = None
    default_registry = None
    platform_filter = None
    external_source_dirs = None
    build_ignore_patterns = None
    issues_list = None
    exit_on_error = True
    enable_build_kit = None
    create_offline_installation = None
    skip_push_no_changes = None
    push_to_microk8s = None
    kaapana_build_version = None
    kaapana_build_branch = None
    kaapana_last_commit_timestamp = None
    build_timestamp = None
    parallel_processes = None
    
    platform_name = None
    platform_build_version = None
    platform_build_branch = None
    platform_last_commit_timestamp = None

    @staticmethod
    def add_container_images_available(container_images_available):
        BuildUtils.container_images_available = container_images_available

        BuildUtils.container_images_unused = {}
        for image_av in BuildUtils.container_images_available:
            BuildUtils.container_images_unused[image_av.tag] = image_av

    @staticmethod
    def add_charts_available(charts_available):
        BuildUtils.charts_available = charts_available

        BuildUtils.charts_unused = {}
        for chart_av in BuildUtils.charts_available:
            BuildUtils.charts_unused[chart_av.chart_id] = chart_av

        for chart_object in BuildUtils.charts_available:
            chart_object.check_dependencies()

    @staticmethod
    def init(kaapana_dir, build_dir, external_source_dirs, build_ignore_patterns, platform_filter, default_registry, http_proxy, logger, exit_on_error, enable_build_kit,
             create_offline_installation, skip_push_no_changes, parallel_processes, include_credentials, registry_user, registry_pwd, push_to_microk8s):

        BuildUtils.logger = logger
        BuildUtils.kaapana_dir = kaapana_dir
        BuildUtils.build_dir = build_dir
        BuildUtils.platform_filter = platform_filter
        BuildUtils.default_registry = default_registry
        BuildUtils.http_proxy = http_proxy
        BuildUtils.external_source_dirs = external_source_dirs
        BuildUtils.build_ignore_patterns = build_ignore_patterns        
        BuildUtils.exit_on_error = exit_on_error
        BuildUtils.issues_list = []

        BuildUtils.base_images_used = {}
        BuildUtils.enable_build_kit = enable_build_kit
        BuildUtils.create_offline_installation = create_offline_installation
        BuildUtils.skip_push_no_changes = skip_push_no_changes
        BuildUtils.push_to_microk8s = push_to_microk8s

        BuildUtils.registry_user = registry_user
        BuildUtils.registry_pwd = registry_pwd
        BuildUtils.include_credentials = include_credentials

        BuildUtils.parallel_processes = parallel_processes

    @staticmethod
    def get_timestamp():
        return str(int(time() * 1000))

    @staticmethod
    def get_repo_info(repo_dir):
        while not exists(join(repo_dir, ".git")) and repo_dir != "/":
            repo_dir = dirname(repo_dir)
        assert repo_dir != "/"


        requested_repo = Repo(repo_dir)
        assert not requested_repo.bare

        if "modules" in requested_repo.common_dir:
            repo_name = basename(requested_repo.working_dir)
            requested_repo = [Repo(x) for x in Repo(dirname(repo_dir)).submodules if x.name == repo_name]
            assert len(requested_repo) == 1
            requested_repo = requested_repo[0]
            last_commit = requested_repo.head.commit
            last_commit_timestamp = last_commit.committed_datetime.strftime("%d-%m-%Y")
            build_version = requested_repo.git.describe()
            build_branch = requested_repo.git.branch()
            if "\n" in build_branch:
                build_branch = build_branch.split("\n")[1].strip()
            # version_check = semver.VersionInfo.parse(build_version)
        else:
            last_commit = requested_repo.head.commit
            last_commit_timestamp = last_commit.committed_datetime.strftime("%d-%m-%Y")
            build_version = requested_repo.git.describe()
            build_branch = requested_repo.active_branch.name.split("/")[-1]
            version_check = semver.VersionInfo.parse(build_version)

        return build_version, build_branch, last_commit, last_commit_timestamp

    @staticmethod
    def get_build_order(build_graph):
        graph_bottom_up = list(reversed(list(nx.topological_sort(build_graph))))

        build_order = []
        for entry in graph_bottom_up:
            if "root" in entry.lower():
                continue

            name = entry.split(":")[1]
            version = entry.split(":")[2]
            entry_id = f"{name}:{version}"

            if "chart:" in entry:
                unused_chart = [x_chart for x_key, x_chart in BuildUtils.charts_unused.items() if f"{x_chart.name}:{x_chart.repo_version}" == entry_id]
                if len(unused_chart) == 1:
                    del BuildUtils.charts_unused[unused_chart[0].name]
                    BuildUtils.logger.debug(f"{entry_id} removed from charts_unused!")
                else:
                    BuildUtils.logger.debug(f"{entry_id} not found in charts_unused!")
                continue

            elif "base-image:" in entry:
                if "local-only" not in entry and BuildUtils.default_registry not in entry:
                    BuildUtils.logger.debug(f"Skip non-local base-image: {entry_id}")
                    continue
                if entry_id in BuildUtils.container_images_unused:
                    BuildUtils.logger.debug(f"{entry_id} removed from container_images_unused!")
                    del BuildUtils.container_images_unused[entry_id]
                else:
                    BuildUtils.logger.debug(f"{entry_id} not found in container_images_unused!")

            elif "container:" in entry:
                if entry_id in BuildUtils.container_images_unused:
                    BuildUtils.logger.debug(f"{entry_id} removed from container_images_unused!")
                    del BuildUtils.container_images_unused[entry_id]
                else:
                    BuildUtils.logger.debug(f"{entry_id} not found in container_images_unused!")

            if "local-only" in name or BuildUtils.default_registry in name:
                build_order.append(entry_id)

        return build_order

    @staticmethod
    def make_log(output):
        std_out = output.stdout.split("\n")[-100:]
        log = {}
        len_std = len(std_out)
        for i in range(0, len_std):
            log[i] = std_out[i]
        std_err = output.stderr.split("\n")
        for err in std_err:
            if err != "":
                len_std += 1
                log[len_std] = f"ERROR: {err}"
        return log

    @staticmethod
    def generate_issue(component, name, level, msg, path="", output=None):
        log = ""
        if output != None:
            log = BuildUtils.make_log(output)
            BuildUtils.logger.error("LOG:")
            BuildUtils.logger.error(log)

        issue = {
            "component": component,
            "name": name,
            "filepath": path,
            "level": level,
            "msg": msg,
            "log": log,
            "timestamp": BuildUtils.get_timestamp(),
        }
        BuildUtils.issues_list.append(issue)
        BuildUtils.logger.warning(json.dumps(issue, indent=4, sort_keys=False))

        if BuildUtils.exit_on_error or level == "FATAL":
            exit(1)

    @staticmethod
    def generate_component_usage_info():
        unused_containers_json_path = join(BuildUtils.build_dir, "build_containers_unused.json")
        BuildUtils.logger.debug("")
        BuildUtils.logger.debug("Collect unused containers:")
        BuildUtils.logger.debug("")
        unused_container = []
        for container_id, container in BuildUtils.container_images_unused.items():
            BuildUtils.logger.debug(f"{container.tag}")
            unused_container.append(container.get_dict())
        with open(unused_containers_json_path, 'w') as fp:
            json.dump(unused_container, fp, indent=4)

        base_images_json_path = join(BuildUtils.build_dir, "build_base_images.json")
        base_images = {}
        BuildUtils.logger.debug("")
        BuildUtils.logger.debug("Collect base-images:")
        BuildUtils.logger.debug("")
        for base_image_tag, child_containers in BuildUtils.base_images_used.items():
            if "python" in base_image_tag:
                pass
            if base_image_tag not in base_images:
                base_images[base_image_tag] = {}
            BuildUtils.logger.debug(f"{base_image_tag}")
            for child_container in child_containers:
                if child_container.build_tag is not None:
                    child_tag = child_container.build_tag
                else:
                    child_tag = f"Not build: {child_container.tag}"
                    
                if child_tag not in base_images[base_image_tag]:
                    base_images[base_image_tag][child_tag] = {}
        
        
        changed = True
        runs = 0
        base_images = dict(sorted(base_images.items(),reverse=True, key=lambda item: len(item[1])))
        while changed and runs <= BuildUtils.max_build_rounds:
            runs +=1 
            del_tags = [] 
            changed = False
            for base_image_tag, child_images in base_images.items():
                if base_image_tag == "python:3.9.16-slim":
                    pass
                for child_image_tag, child_image in child_images.items():
                    if child_image_tag in base_images:
                        base_images[base_image_tag][child_image_tag] = base_images[child_image_tag]
                        del_tags.append(child_image_tag)
            
            for del_tag in del_tags:
                del base_images[del_tag]
                changed = True
        

        base_images = dict(sorted(base_images.items(),reverse=True, key=lambda item: sum(len(v) for v in item[1].values())))
        with open(base_images_json_path, 'w') as fp:
            json.dump(base_images, fp, indent=4)

        all_containers_json_path = join(BuildUtils.build_dir, "build_containers_all.json")
        BuildUtils.logger.debug("")
        BuildUtils.logger.debug("Collect all containers present:")
        BuildUtils.logger.debug("")
        all_container = []
        for container in BuildUtils.container_images_available:
            BuildUtils.logger.debug(f"{container.tag}")
            all_container.append(container.get_dict())

        with open(all_containers_json_path, 'w') as fp:
            json.dump(all_container, fp, indent=4)

        all_charts_json_path = join(BuildUtils.build_dir, "build_charts_all.json")
        BuildUtils.logger.debug("")
        BuildUtils.logger.debug("Collect all charts present:")
        BuildUtils.logger.debug("")
        all_charts = []
        for chart in BuildUtils.charts_available:
            BuildUtils.logger.debug(f"{chart.chart_id}")
            all_charts.append(chart.get_dict())

        with open(all_charts_json_path, 'w') as fp:
            json.dump(all_charts, fp, indent=4)

        unused_charts_json_path = join(BuildUtils.build_dir, "build_charts_unused.json")
        BuildUtils.logger.debug("")
        BuildUtils.logger.debug("Collect all charts present:")
        BuildUtils.logger.debug("")
        unused_charts = []
        for chart_id, chart in BuildUtils.charts_unused.items():
            BuildUtils.logger.debug(f"{chart.chart_id}")
            unused_charts.append(chart.get_dict())

        with open(unused_charts_json_path, 'w') as fp:
            json.dump(unused_charts, fp, indent=4)

    @staticmethod
    def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
        """
        Call in a loop to create terminal progress bar
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            length      - Optional  : character length of bar (Int)
            fill        - Optional  : bar fill character (Str)
            printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
        """
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        print(f'\r{prefix} |{bar}| {percent}% {suffix.tag.ljust(100)}', end=printEnd)
        # Print New Line on Complete
        if iteration == total:
            print()


if __name__ == '__main__':
    print("Please use the 'start_build.py' script to launch the build-process.")
    exit(1)
