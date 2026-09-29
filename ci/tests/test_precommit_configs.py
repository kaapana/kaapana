from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    return yaml.safe_load((ROOT / name).read_text())


def revs(config):
    return {repo["repo"]: repo.get("rev") for repo in config["repos"] if repo["repo"] != "local"}


def hook_ids(config):
    return {hook["id"] for repo in config["repos"] for hook in repo["hooks"]}


def test_strict_config_pins_the_same_tool_versions():
    assert revs(load(".pre-commit-config.strict.yaml")) == revs(load(".pre-commit-config.yaml"))


def test_strict_config_has_a_strict_variant_of_every_enforcing_hook():
    default = hook_ids(load(".pre-commit-config.yaml"))
    strict = hook_ids(load(".pre-commit-config.strict.yaml"))
    assert strict <= default
    assert default - strict == {"ui-quality"}
