from pydantic import BaseModel


class PlatformConfig(BaseModel):
    platform_name: str
    platform_build_version: str
    platform_repo_version: str
    platform_build_branch: str
    platform_last_commit_timestamp: str
