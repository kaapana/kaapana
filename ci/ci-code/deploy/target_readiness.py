#!/usr/bin/env python3
"""Readiness check for a Kaapana deployment target.

Runs on the target as the deploying SSH user. Every check is read-only and
needs no sudo. Anything that needs root belongs in server_installation.yaml.

Table on stdout and --log, JSON report to --report. Exit 1 means a fatal check
failed.
"""

import argparse
import getpass
import grp
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone

# A fatal check blocks the deployment, a warning is only reported.
FATAL = "fatal"
WARNING = "warning"

PASSED = "passed"
FAILED = "failed"
WARNED = "warning"
SKIPPED = "skipped"

# snap binaries are missing from the PATH of some non-interactive SSH sessions.
EXTRA_PATH = ("/snap/bin", "/usr/local/bin")

MICROK8S_APISERVER_ARGS = "/var/snap/microk8s/current/args/kube-apiserver"

# kaapanactl.sh deploys this release into this namespace (PLATFORM_NAME in
# HELM_NAMESPACE) and keeps the platform prefix in its values.
ADMIN_CHART_RELEASE = "kaapana-admin-chart"
HELM_NAMESPACE = "default"


class Report:
    def __init__(self):
        self.checks = []

    def add(self, name, title, status, severity, details="", remediation=""):
        if status == FAILED and severity == WARNING:
            status = WARNED
        self.checks.append(
            {
                "name": name,
                "title": title,
                "status": status,
                "severity": severity,
                "details": details,
                "remediation": remediation if status in (FAILED, WARNED) else "",
            }
        )
        return status

    def counts(self, status):
        return len([c for c in self.checks if c["status"] == status])

    @property
    def ready(self):
        return self.counts(FAILED) == 0

    def as_dict(self, target):
        return {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "target": target,
            "ready": self.ready,
            "summary": {
                "total": len(self.checks),
                "passed": self.counts(PASSED),
                "warnings": self.counts(WARNED),
                "failed": self.counts(FAILED),
                "skipped": self.counts(SKIPPED),
            },
            "checks": self.checks,
        }

    def table(self):
        lines = [
            "",
            "Kaapana target readiness",
            "========================",
            f"{'STATUS':<8} {'SEV':<8} {'CHECK':<52} DETAILS",
        ]
        for check in self.checks:
            lines.append(
                f"{check['status']:<8} {check['severity']:<8} "
                f"{check['title'][:52]:<52} {check['details']}"
            )
            if check["remediation"]:
                lines.append(f"{'':<8} {'':<8} -> {check['remediation']}")
        summary = self.as_dict({})["summary"]
        lines += [
            "",
            (
                f"passed: {summary['passed']}  warnings: {summary['warnings']}  "
                f"failed: {summary['failed']}  skipped: {summary['skipped']}"
            ),
            "TARGET READY" if self.ready else "TARGET NOT READY",
            "",
        ]
        return "\n".join(lines)


def run(cmd, timeout=60):
    """Run a command, never raise. Returns (rc, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()
    except FileNotFoundError:
        return 127, "", f"{cmd[0]}: command not found"
    except subprocess.TimeoutExpired:
        return 124, "", f"{' '.join(cmd)}: timed out after {timeout}s"
    except OSError as exc:
        return 126, "", f"{cmd[0]}: {exc}"


def read_int(path):
    try:
        with open(path) as handle:
            return int(handle.read().strip())
    except (OSError, ValueError):
        return None


def check_binary(report, name, binary, remediation, severity=FATAL):
    path = shutil.which(binary)
    report.add(
        name,
        f"{binary} is installed",
        PASSED if path else FAILED,
        severity,
        details=path or f"{binary} not found in PATH ({os.environ.get('PATH', '')})",
        remediation=remediation,
    )
    return path


def check_home_writable(report):
    home = os.path.expanduser("~")
    writable = os.path.isdir(home) and os.access(home, os.W_OK)
    report.add(
        "home_writable",
        "Home directory of the SSH user is writable",
        PASSED if writable else FAILED,
        FATAL,
        details=f"HOME={home}",
        remediation=(
            "The deployment copies kaapanactl.sh into the home directory of the "
            "SSH user and runs it from there. Fix the ownership of "
            f"{home} or deploy as another user."
        ),
    )


def check_microk8s_group(report):
    user = getpass.getuser()
    try:
        group = grp.getgrnam("microk8s")
    except KeyError:
        report.add(
            "microk8s_group",
            "SSH user is a member of the microk8s group",
            FAILED,
            FATAL,
            details="the group 'microk8s' does not exist on the target",
            remediation=(
                "microk8s is not installed. Re-run the pipeline with "
                "CI_EXEC_SERVER_INSTALLATION=true, or install microk8s on the "
                "target with 'sudo ./kaapanactl.sh install'."
            ),
        )
        return

    listed = user in group.gr_mem
    effective = group.gr_gid in os.getgroups()
    if effective:
        status, details, remediation = PASSED, f"user '{user}'", ""
    elif listed:
        status = FAILED
        details = f"user '{user}' is in /etc/group, but not in this SSH session"
        remediation = (
            "The group membership is not active yet. Reconnect the SSH session "
            "or reboot the target ('newgrp microk8s' only fixes the local shell)."
        )
    else:
        status = FAILED
        details = f"user '{user}' is not a member of the microk8s group"
        remediation = (
            f"On the target: sudo usermod -a -G microk8s {user}, then reconnect. "
            "Without it every microk8s call needs sudo and the deployment fails."
        )
    report.add(
        "microk8s_group",
        "SSH user is a member of the microk8s group",
        status,
        # Listed but not active: the microk8s checks below decide.
        FATAL if not listed else WARNING,
        details=details,
        remediation=remediation,
    )


def check_microk8s_ready(report, microk8s, timeout):
    if not microk8s:
        report.add(
            "microk8s_ready",
            "microk8s is up and ready",
            SKIPPED,
            FATAL,
            details="microk8s not installed",
        )
        return
    rc, out, err = run(
        [microk8s, "status", "--wait-ready", "--timeout", str(timeout)],
        timeout=timeout + 30,
    )
    first_line = (out or err).splitlines()[0] if (out or err) else ""
    report.add(
        "microk8s_ready",
        "microk8s is up and ready",
        PASSED if rc == 0 else FAILED,
        FATAL,
        details=first_line,
        remediation=(
            "On the target: 'microk8s start' and 'microk8s status --wait-ready'. "
            "A permission error here means the SSH user is not in the microk8s "
            "group (see the group check above)."
        ),
    )


def check_kubernetes_api(report, microk8s):
    if not microk8s:
        report.add(
            "kubernetes_api",
            "Kubernetes API answers without sudo",
            SKIPPED,
            FATAL,
            details="microk8s not installed",
        )
        return
    rc, out, err = run(
        [microk8s, "kubectl", "get", "nodes", "--no-headers"], timeout=120
    )
    node_ready = rc == 0 and any(
        line.split()[1].startswith("Ready")
        for line in out.splitlines()
        if len(line.split()) > 1
    )
    report.add(
        "kubernetes_api",
        "Kubernetes API answers without sudo and the node is Ready",
        PASSED if node_ready else FAILED,
        FATAL,
        details=out.replace("\n", "; ") if rc == 0 else err,
        remediation=(
            "Check 'microk8s kubectl get nodes' on the target. A working API but "
            "a NotReady node usually means the CNI or DNS addon is broken."
        ),
    )


def check_helm(report, helm):
    if not helm:
        report.add(
            "helm_cluster_access",
            "helm reaches the cluster",
            SKIPPED,
            FATAL,
            details="helm not installed",
        )
        return False

    rc, out, err = run([helm, "ls", "-A", "-o", "json"], timeout=180)
    releases = []
    if rc == 0:
        try:
            releases = json.loads(out or "[]")
        except json.JSONDecodeError as exc:
            rc, err = 1, f"unreadable helm output: {exc}"
    report.add(
        "helm_cluster_access",
        "helm reaches the cluster",
        PASSED if rc == 0 else FAILED,
        FATAL,
        details=f"{len(releases)} release(s) installed" if rc == 0 else err,
        remediation=(
            "helm talks to the cluster through ~/.kube/config. Refresh it with "
            "'microk8s kubectl config view --raw > ~/.kube/config' on the target."
        ),
    )
    return rc == 0


def check_existing_platform(report, helm, redeploy):
    """The gate kaapanactl uses before it deploys: is its admin chart release
    there? The platform prefix comes from that release, as in
    get_platform_prefix_from_release."""
    title = "Existing Kaapana platform on the target"
    if not helm:
        report.add(
            "existing_platform", title, SKIPPED, WARNING, details="helm not installed"
        )
        return None

    rc, out, _ = run(
        [
            helm,
            "-n",
            HELM_NAMESPACE,
            "get",
            "values",
            ADMIN_CHART_RELEASE,
            "-o",
            "json",
        ],
        timeout=120,
    )
    if rc != 0:
        report.add("existing_platform", title, PASSED, WARNING, details="none")
        return None

    prefix = ""
    try:
        prefix = (json.loads(out or "{}").get("global") or {}).get(
            "platform_prefix"
        ) or ""
    except json.JSONDecodeError:
        pass
    report.add(
        "existing_platform",
        title,
        FAILED,
        WARNING if redeploy else FATAL,
        details=f"release {ADMIN_CHART_RELEASE} in namespace {HELM_NAMESPACE}, "
        f"platform prefix '{prefix or 'unknown'}'",
        remediation=(
            "platform_deployment undeploys it first."
            if redeploy
            else "Undeploy it on the target: './kaapanactl.sh deploy --undeploy', "
            "or re-run with CI_EXEC_REDEPLOY=true."
        ),
    )
    return prefix or ADMIN_CHART_RELEASE


def check_node_port_range(report, required_ports):
    """The platform publishes NodePorts far below the k8s default range."""
    try:
        with open(MICROK8S_APISERVER_ARGS) as handle:
            args = handle.read()
    except OSError as exc:
        report.add(
            "node_port_range",
            "microk8s NodePort range covers the platform ports",
            SKIPPED,
            FATAL,
            details=f"{MICROK8S_APISERVER_ARGS}: {exc}",
        )
        return

    match = re.search(r"--service-node-port-range=(\d+)-(\d+)", args)
    if match:
        low, high = int(match.group(1)), int(match.group(2))
        outside = [port for port in required_ports if not low <= port <= high]
    else:
        low, high, outside = None, None, list(required_ports)
    configured = f"{low}-{high}" if match else "not set (k8s default 30000-32767)"
    report.add(
        "node_port_range",
        "microk8s NodePort range covers the platform ports",
        PASSED if not outside else FAILED,
        FATAL,
        details=f"configured: {configured}; needed: "
        f"{','.join(str(port) for port in required_ports)}",
        remediation=(
            "Add '--service-node-port-range=80-32000' to "
            f"{MICROK8S_APISERVER_ARGS} and restart microk8s "
            "('microk8s stop && microk8s start'); without it the platform "
            "services are rejected by the API server."
        ),
    )


def listening_ports():
    """Map of listening TCP port -> local address, or None if ss is unavailable."""
    ss = shutil.which("ss")
    if not ss:
        return None
    rc, out, _ = run([ss, "-H", "-ltn"])
    if rc != 0:
        rc, out, _ = run([ss, "-ltn"])
    if rc != 0:
        return None
    ports = {}
    for line in out.splitlines():
        fields = line.split()
        if len(fields) < 4 or fields[0] == "State":
            continue
        port = fields[3].rsplit(":", 1)[-1]
        if port.isdigit():
            ports.setdefault(int(port), fields[3])
    return ports


def check_ports_free(report, required_ports, existing_platform):
    ports = listening_ports()
    if ports is None:
        report.add(
            "ports_free",
            "Platform host ports are free",
            SKIPPED,
            FATAL,
            details="'ss' is not available on the target",
        )
        return

    busy = {port: address for port, address in ports.items() if port in required_ports}
    if not busy:
        report.add(
            "ports_free",
            "Platform host ports are free",
            PASSED,
            FATAL,
            details=f"{','.join(str(port) for port in required_ports)} unused",
        )
        return

    listed = ", ".join(f"{port} ({address})" for port, address in sorted(busy.items()))
    if existing_platform:
        report.add(
            "ports_free",
            "Platform host ports are free",
            FAILED,
            WARNING,
            details=f"in use by the platform already deployed here: {listed}",
            remediation=(
                "These ports are released when that platform is undeployed, "
                "which platform_deployment does when CI_EXEC_REDEPLOY=true."
            ),
        )
    else:
        report.add(
            "ports_free",
            "Platform host ports are free",
            FAILED,
            FATAL,
            details=f"already in use: {listed}",
            remediation=(
                "Stop whatever listens on these ports (find it with "
                "'sudo ss -ltnp'); the platform publishes them as NodePorts and "
                "cannot share them."
            ),
        )


def check_sysctl(report, name, title, path, minimum, severity):
    value = read_int(path)
    if value is None:
        report.add(name, title, SKIPPED, severity, details=f"{path} not readable")
        return
    report.add(
        name,
        title,
        PASSED if value >= minimum else FAILED,
        severity,
        details=f"{value} (needed: {minimum})",
        remediation=(
            f"On the target: sudo sysctl -w {os.path.relpath(path, '/proc/sys').replace('/', '.')}"
            f"={minimum} (and add it to /etc/sysctl.conf to survive a reboot)."
        ),
    )


def check_disk_space(report, min_gib):
    path = next((p for p in ("/var/snap", "/var", "/") if os.path.isdir(p)), "/")
    stat = os.statvfs(path)
    free_gib = stat.f_bavail * stat.f_frsize / 1024**3
    report.add(
        "disk_space",
        "Enough free disk space for the container images",
        PASSED if free_gib >= min_gib else FAILED,
        FATAL,
        details=f"{free_gib:.1f} GiB free at {path} (needed: {min_gib} GiB)",
        remediation=(
            "The platform images need this space under /var/snap. Free space on "
            "the target or deploy on a bigger machine."
        ),
    )


def check_domain_resolves(report, domain):
    if not domain:
        report.add(
            "domain_resolves",
            "Platform domain resolves on the target",
            SKIPPED,
            WARNING,
            details="no domain passed",
        )
        return
    try:
        addresses = sorted({info[4][0] for info in socket.getaddrinfo(domain, None)})
        status, details = PASSED, f"{domain} -> {', '.join(addresses)}"
        remediation = ""
    except socket.gaierror as exc:
        status, details = FAILED, f"{domain}: {exc}"
        remediation = (
            "The platform certificate and the CoreDNS rewrite use this name. "
            "An unresolvable name still deploys but breaks in-cluster access to "
            "the platform URL."
        )
    report.add(
        "domain_resolves",
        "Platform domain resolves on the target",
        status,
        WARNING,
        details=details,
        remediation=remediation,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--domain", default="", help="FQDN the platform is deployed under"
    )
    parser.add_argument(
        "--required-ports",
        default="80,443,11112",
        help="host ports the platform publishes (default: 80,443,11112)",
    )
    parser.add_argument("--min-disk-gib", type=int, default=80)
    parser.add_argument(
        "--redeploy",
        default="false",
        help="whether the deployment may replace a platform found here "
        "(CI_EXEC_REDEPLOY); 'false' makes finding one a fatal check",
    )
    parser.add_argument(
        "--microk8s-timeout",
        type=int,
        default=120,
        help="seconds to wait for 'microk8s status --wait-ready'",
    )
    parser.add_argument(
        "--report",
        default="",
        help="write the JSON report to this file (ansible fetches it as the "
        "job artifact); stdout stays the human-readable table",
    )
    parser.add_argument(
        "--log",
        default="",
        help="write the table to this file as well",
    )
    args = parser.parse_args()

    os.environ["PATH"] = os.pathsep.join(
        [os.environ.get("PATH", "")] + [p for p in EXTRA_PATH if os.path.isdir(p)]
    )
    required_ports = [
        int(port) for port in args.required_ports.split(",") if port.strip()
    ]

    report = Report()
    check_home_writable(report)
    microk8s = check_binary(
        report,
        "microk8s_installed",
        "microk8s",
        "Re-run the pipeline with CI_EXEC_SERVER_INSTALLATION=true, or install "
        "microk8s on the target with 'sudo ./kaapanactl.sh install'.",
    )
    helm = check_binary(
        report,
        "helm_installed",
        "helm",
        "Install helm on the target ('sudo snap install helm --classic'), or "
        "re-run the pipeline with CI_EXEC_SERVER_INSTALLATION=true.",
    )
    check_binary(
        report,
        "jq_installed",
        "jq",
        "kaapanactl.sh parses helm and kubectl output with jq. Install it "
        "('sudo apt-get install -y jq').",
    )
    check_microk8s_group(report)
    check_microk8s_ready(report, microk8s, args.microk8s_timeout)
    check_kubernetes_api(report, microk8s)
    helm_works = check_helm(report, helm)
    existing_platform = check_existing_platform(
        report, helm if helm_works else "", args.redeploy.strip().lower() == "true"
    )
    check_node_port_range(report, required_ports)
    check_ports_free(report, required_ports, existing_platform)
    check_sysctl(
        report,
        "vm_max_map_count",
        "vm.max_map_count is raised for OpenSearch",
        "/proc/sys/vm/max_map_count",
        262144,
        FATAL,
    )
    check_sysctl(
        report,
        "inotify_watches",
        "inotify watch limit is raised",
        "/proc/sys/fs/inotify/max_user_watches",
        10000,
        WARNING,
    )
    check_sysctl(
        report,
        "inotify_instances",
        "inotify instance limit is raised",
        "/proc/sys/fs/inotify/max_user_instances",
        10000,
        WARNING,
    )
    check_disk_space(report, args.min_disk_gib)
    check_domain_resolves(report, args.domain)

    target = {
        "hostname": socket.gethostname(),
        "user": getpass.getuser(),
        "domain": args.domain,
    }
    table = report.table()
    print(table)
    # Files, not stdout: ansible captures the output through a pty, CRLF-mangled.
    if args.report:
        with open(args.report, "w") as handle:
            json.dump(report.as_dict(target), handle, indent=2)
            handle.write("\n")
        print(f"JSON report written to {args.report}")
    if args.log:
        with open(args.log, "w") as handle:
            handle.write(table + "\n")
    return 0 if report.ready else 1


if __name__ == "__main__":
    sys.exit(main())
