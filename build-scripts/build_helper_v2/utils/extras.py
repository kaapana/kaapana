from subprocess import PIPE, run


def get_image_stats(version: str, container_engine: str):
    images_stats: dict[str, dict] = {}
    command = [f"{container_engine} image ls | grep {version}"]
    output = run(
        command,
        shell=True,
        stdout=PIPE,
        stderr=PIPE,
        universal_newlines=True,
        timeout=5,
    )
    if output.returncode == 0:
        system_df_output = output.stdout.split("\n")
        for image_stats in system_df_output:
            if len(image_stats) == 0:
                continue
            image_name, image_tag, image_hash, image_build_time, size = [
                x for x in image_stats.strip().split("  ") if x != ""
            ]
            size = convert_size(size)
            images_stats[f"{image_name}:{image_tag}"] = {"size": size}

    command = [f"{container_engine} system df -v | grep {version}"]
    output = run(
        command,
        shell=True,
        stdout=PIPE,
        stderr=PIPE,
        universal_newlines=True,
        timeout=20,
    )
    if output.returncode == 0:
        system_df_output = output.stdout.split("\n")
        for image_stats in system_df_output:
            if len(image_stats) == 0:
                continue
            (
                image_name,
                image_tag,
                image_hash,
                image_build_time,
                size,
                shared_size,
                unique_size,
                containers,
            ) = [x for x in image_stats.strip().split("  ") if x != ""]
            size = convert_size(size)
            shared_size = convert_size(shared_size)
            unique_size = convert_size(unique_size)

            images_stats[f"{image_name}:{image_tag}"] = {
                "size": size,
                "unique_size": unique_size,
                "shared_size": shared_size,
                "image_build_time": image_build_time,
                "containers": int(containers.strip()),
            }

    images_stats = {
        k: v
        for k, v in sorted(
            images_stats.items(),
            key=lambda item: item[1]["size"],
            reverse=True,
        )
    }
    return images_stats


def convert_size(size_string):
    if "GB" in size_string:
        return float(size_string.replace("GB", ""))
    elif "MB" in size_string:
        return round(float(size_string.replace("MB", "")) / 1000, 2)
    elif "kB" in size_string:
        return 0
    elif "B" in size_string:
        return 0
    else:
        pass
