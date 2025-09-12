from os.path import basename, dirname, exists, join

import semver
from git import Repo


class GitUtils:
    @staticmethod
    def get_repo_info(repo_dir):
        # Traverse upward until we find a .git directory or reach root
        while not exists(join(repo_dir, ".git")) and repo_dir != "/":
            repo_dir = dirname(repo_dir)
        assert repo_dir != "/", "Reached filesystem root without finding .git"

        with Repo(repo_dir) as repo:
            assert not repo.bare, "Found git repo is bare"

            # Extract shared info
            def extract_common_info(repo):
                commit = repo.head.commit
                timestamp = (
                    commit.committed_datetime.astimezone()
                    .replace(microsecond=0)
                    .isoformat()
                )
                version = repo.git.describe()
                return commit, timestamp, version

            if "modules" in repo.common_dir:
                # If we're in a submodule, get correct submodule repo by name
                repo_name = basename(repo.working_dir)
                submodules = Repo(dirname(repo_dir)).submodules
                sub_repo = next(
                    (x.module() for x in submodules if x.name == repo_name), None
                )
                assert sub_repo, f"Submodule {repo_name} not found"
                commit, timestamp, version = extract_common_info(sub_repo)
                branch = sub_repo.git.branch()
                branch = (
                    branch.split("\n")[1].strip() if "\n" in branch else branch.strip()
                )
            else:
                # Regular repo
                commit, timestamp, version = extract_common_info(repo)
                try:
                    branch = repo.active_branch.name
                except TypeError:
                    branch = "DETACHED-HEAD"

                # Optionally validate version (will raise if invalid)
                _ = semver.VersionInfo.parse(version)

        return version, branch, commit, timestamp
