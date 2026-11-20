import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
IGNORE_FILE = ".trivyignore.yaml"
BASE_IMAGE_DIR = "data-processing/base-images"
SERVICE_DIR = "services"
SERVICE_IMAGES = {"node", "nginx", "nginx-unprivileged"}
SKIPPED_DIRS = (
    "services/applications",
    "services/base/kaapana-backend",
    "services/kaapana-admin/kube-helm",
    "services/meta",
)
VULNERABLE = 3
FROM_LINE = re.compile(r"^\s*FROM\s+(?:--\S+\s+)*(\S+)(?:\s+AS\s+(\S+))?", re.IGNORECASE | re.MULTILINE)


def from_images(dockerfile: Path) -> list[str]:
    images = []
    stages = set()
    for match in FROM_LINE.finditer(dockerfile.read_text()):
        image, stage = match.group(1), match.group(2)
        if image.lower() not in stages and not image.startswith("local-only/") and "$" not in image:
            images.append(normalized(image))
        if stage:
            stages.add(stage.lower())
    return images


def normalized(image: str) -> str:
    return image.removeprefix("docker.io/").removeprefix("library/")


def repository_name(image: str) -> str:
    return image.split("@")[0].split(":")[0].rsplit("/", 1)[-1]


def dockerfiles(root: Path, directory: str) -> list[Path]:
    return sorted(
        path
        for path in (root / directory).rglob("Dockerfile")
        if not any(path.relative_to(root).as_posix().startswith(f"{skipped}/") for skipped in SKIPPED_DIRS)
    )


def base_images(root: Path = REPO) -> list[str]:
    images = {image for path in dockerfiles(root, BASE_IMAGE_DIR) for image in from_images(path)}
    images |= {
        image
        for path in dockerfiles(root, SERVICE_DIR)
        for image in from_images(path)
        if repository_name(image) in SERVICE_IMAGES
    }
    return sorted(images)


def scan(image: str, cache_dir: str | None, ignore_file: Path) -> int:
    cmd = [
        "trivy",
        "image",
        "--image-src",
        "remote",
        "--severity",
        "CRITICAL",
        "--ignore-unfixed",
        "--exit-code",
        str(VULNERABLE),
        "--no-progress",
        "--table-mode",
        "detailed",
    ]
    if cache_dir:
        cmd += ["--cache-dir", cache_dir]
    if ignore_file.exists():
        cmd += ["--ignorefile", str(ignore_file)]
    print(f"Scanning {image}", flush=True)
    return subprocess.run([*cmd, image], check=False).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail when a base image has a CRITICAL vulnerability with a fix.")
    parser.add_argument("--cache-dir", help="Trivy cache directory")
    parser.add_argument("--list", action="store_true", help="only print the images that are scanned")
    args = parser.parse_args(argv)

    images = base_images()
    if args.list:
        print("\n".join(images))
        return 0

    results = {image: scan(image, args.cache_dir, REPO / IGNORE_FILE) for image in images}
    vulnerable = [image for image, code in results.items() if code == VULNERABLE]
    failed = [image for image, code in results.items() if code not in (0, VULNERABLE)]
    for title, found in (("CRITICAL vulnerabilities with a fix", vulnerable), ("Scan failed", failed)):
        if found:
            print(f"\n{title}:")
            print("\n".join(f"  - {image}" for image in found))
    if vulnerable or failed:
        return 1
    print(f"\nNo CRITICAL vulnerability with a fix in {len(images)} base images.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
