#!/usr/bin/env python3
"""Manage the CI runner fleet on Harvester.

The fleet is declared in inventory.yaml. Every change is: edit that file,
then run `up`. There are no separate create/edit/delete verbs — it is
declarative:

    ci_fleet.py list                show the declared fleet and its roles
    ci_fleet.py status              show live state: VMs, runners, versions
    ci_fleet.py up                  create missing VMs, apply runner roles
    ci_fleet.py up --force          destroy and rebuild (roles included)
    ci_fleet.py up --hosts ci-01    stop at the named VMs
    ci_fleet.py down --hosts ci-01  destroy named VMs, unregister runners

`up` always converges: a role removed from the inventory is deleted from the
VM, because config.toml is rebuilt from scratch. `down` requires --hosts so a
fleet is never destroyed by accident.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import requests
import typer

HERE = Path(__file__).resolve().parent
VERSION_CMD = (
    'echo "docker|$(docker --version 2>/dev/null)"; '
    "echo \"kubectl|$(kubectl version --client 2>/dev/null | sed -n 's/^Client Version: *//p')\"; "
    'echo "helm|$(helm version --short 2>/dev/null)"; '
    'echo "runner|$(gitlab-runner --version 2>/dev/null | head -1)"'
)
app = typer.Typer(no_args_is_help=True, help=__doc__)


def find(exe):
    return shutil.which(exe) or str(Path(sys.executable).parent / exe)


def run(*args):
    subprocess.run([find(args[0]), *args[1:]], cwd=HERE, check=True)


def env():
    """Settings from the environment, falling back to .env next to this file."""
    file_values = {}
    for line in (HERE / ".env").read_text().splitlines():
        line = re.sub(r"^export\s+", "", line.strip())
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        file_values[key.strip()] = val.strip().strip("'\"")

    def get(key):
        val = os.environ.get(key) or file_values.get(key, "")
        return os.path.expanduser(val)

    return {
        key: get(key)
        for key in (
            "GITLAB_URL",
            "GITLAB_API_TOKEN",
            "GITLAB_PROJECT_ID",
            "SSH_PRIVATE_KEY",
            "HARVESTER_KUBECONFIG",
            "HARVESTER_NAMESPACE",
            "VM_DNS_DOMAIN",
            "VM_USER",
        )
    }


def inventory():
    out = subprocess.run(
        [find("ansible-inventory"), "-i", "inventory.yaml", "--list"],
        cwd=HERE,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return json.loads(out)


def declared_fleet(data):
    hosts = data["_meta"]["hostvars"]
    fleet = data.get("ci_instances", {}).get("hosts", [])
    return [(name, hosts[name]) for name in fleet]


def role_config(h, role):
    return {**h["runner_defaults"], **h["runner_roles"][role]}


@app.command("list")
def fleet_list():
    """Show the declared fleet and its runner roles (inventory.yaml)."""
    for name, h in declared_fleet(inventory()):
        typer.echo(f"{name}: {h['cpu_cores']} CPU / {h['memory_guest']} / {h['disk_size']}")
        for role in h["runners"]:
            cfg = role_config(h, role)
            typer.echo(f"  {role:<9} tags={cfg['tags']}  limit={cfg['limit']} conc={cfg['request_concurrency']}")


def harvester_vms(cfg):
    out = subprocess.run(
        [
            find("kubectl"),
            "--kubeconfig",
            cfg["HARVESTER_KUBECONFIG"],
            "get",
            "vm",
            "-n",
            cfg["HARVESTER_NAMESPACE"],
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    vms = {}
    for r in json.loads(out)["items"]:
        s = r.get("status", {})
        vms[r["metadata"]["name"]] = {
            "state": s.get("printableStatus", "?"),
            "ready": s.get("ready", False),
            "created": r["metadata"]["creationTimestamp"],
        }
    return vms


def gitlab_runners(cfg):
    url = f"{cfg['GITLAB_URL'].rstrip('/')}/api/v4/projects/{cfg['GITLAB_PROJECT_ID']}/runners"
    res = requests.get(url, headers={"PRIVATE-TOKEN": cfg["GITLAB_API_TOKEN"]}, timeout=30)
    res.raise_for_status()
    return {
        r["description"]: {
            "status": r["status"],
            "paused": bool(r["paused"]),
            "tags": r.get("tag_list") or [],
        }
        for r in res.json()
    }


def trim_version(val):
    """`Docker version 29.8.0, build x` -> `29.8.0`, `v1.37.0` -> `v1.37.0`."""
    m = re.search(r"[vV]?\d+(?:\.\d+)+[^\s,]*", val)
    return m.group(0) if m else val


def installed_versions(cfg, vm):
    """Version line per installed tool, or None if the VM is unreachable."""
    res = subprocess.run(
        [
            "ssh",
            "-i",
            cfg["SSH_PRIVATE_KEY"],
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            f"{cfg['VM_USER']}@{vm}.{cfg['VM_DNS_DOMAIN']}",
            VERSION_CMD,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if res.returncode != 0:
        return None
    out = {}
    for line in res.stdout.splitlines():
        name, _, val = line.partition("|")
        if val.strip():
            out[name] = trim_version(val)
    return out


@app.command()
def status():
    """Show live state: Harvester VMs, registered GitLab runners, installed versions."""
    cfg = env()
    missing = [k for k, v in cfg.items() if not v]
    if missing:
        raise typer.Exit(f"missing settings: {', '.join(missing)} (put them in {HERE / '.env'})", code=1)

    fleet = dict(declared_fleet(inventory()))
    vms = harvester_vms(cfg)
    runners = gitlab_runners(cfg)

    for name, h in fleet.items():
        vm = vms.get(name)
        if vm:
            typer.echo(f"{name}  {vm['state']} (since {vm['created'][:10]})")
        else:
            typer.echo(f"{name}  NOT PROVISIONED (declared in inventory)")
            continue
        versions = installed_versions(cfg, name)
        if versions:
            typer.echo("  " + "  ".join(f"{k} {v}" for k, v in versions.items()))
        else:
            typer.echo("  unreachable via ssh")
        for role in h["runners"]:
            r = runners.get(f"{name}-{role}")
            if r:
                state = "paused" if r["paused"] else r["status"]
                typer.echo(f"  {role:<9} {state}")
            else:
                typer.echo(f"  {role:<9} missing")

    expected = {f"{name}-{role}" for name, h in fleet.items() for role in h["runners"]}
    leftovers = sorted(set(runners) - expected)
    if leftovers:
        typer.echo()
        typer.echo("registered in GitLab, not in inventory:")
        for d in leftovers:
            r = runners[d]
            typer.echo(f"  {d}  ({'paused, ' if r['paused'] else ''}{r['status']})")
    stray = sorted(set(vms) - set(fleet))
    if stray:
        typer.echo("VMs on Harvester, not in inventory: " + ", ".join(stray))


@app.command()
def up(
    force: bool = typer.Option(False, "--force", help="destroy and rebuild"),
    hosts: str = typer.Option(None, "--hosts", help="only the named VMs (comma separated)"),
):
    """Converge VMs and runner roles to the inventory."""
    cmd = ["ansible-playbook", "setup_ci.yaml"]
    if force:
        cmd += ["-e", "force_recreate=true"]
    if hosts:
        cmd += ["-e", f"ci_hosts={hosts}"]
    run(*cmd)


@app.command()
def down(hosts: str = typer.Option(..., "--hosts", help="VMs to destroy (comma separated)")):
    """Destroy named VMs and unregister their runners."""
    run("ansible-playbook", "setup_ci.yaml", "-e", "fleet_state=absent", "-e", f"ci_hosts={hosts}")


if __name__ == "__main__":
    app()
