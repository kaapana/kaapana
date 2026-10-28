from pathlib import Path

from build_cli.build import BuildConfig


def make_config(**overrides) -> BuildConfig:
    """
    Build a config without validation, so that a test sets only the fields it needs.
    """
    values = dict(
        default_registry="10.0.0.5:5000",
        registry_username="user",
        registry_password="password",
        build_dir=Path("/tmp/build"),
        kaapana_dir=Path("/tmp/kaapana"),
        container_engine="docker",
        exit_on_error=False,
        cache_from=True,
        http_proxy=None,
    )
    values.update(overrides)
    return BuildConfig.model_construct(**values)
