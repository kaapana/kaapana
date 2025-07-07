import os
import requests
import json
import argparse
import shutil

default_static_dir = os.path.join(os.path.dirname(__file__), "img")
image_url_path = os.path.join(os.path.dirname(__file__), "image_urls.json")


def download_image(name, url, output_dir):
    dest_path = os.path.join(output_dir, name)
    if os.path.exists(dest_path):
        print(f"image {name} already exists, skipping")
        return

    print(f"downloading {name}...")
    try:
        r = requests.get(url)
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(r.content)
        print(f"image saved to {dest_path}")
    except Exception as e:
        print(f"failed to download media {name}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=str,
        default=default_static_dir,
        help="Directory where images will be saved",
    )
    parser.add_argument(
        "--remove",
        type=str,
        help="folder to remove downloaded images from",
    )
    args = parser.parse_args()

    if args.remove:
        if os.path.exists(args.remove):
            print(f"removing directory: {args.remove}")
            shutil.rmtree(args.remove)
        else:
            print(f"directory does not exist: {args.remove}")
        exit(0)

    os.makedirs(args.output_dir, exist_ok=True)

    # load image urls from json
    try:
        with open(image_url_path, "r") as f:
            image_urls = json.load(f)
    except FileNotFoundError:
        print(f"image_urls.json not found at expected path: {image_url_path}")
        exit(1)

    # download all images
    for name, url in image_urls.items():
        download_image(name, url, args.output_dir)
