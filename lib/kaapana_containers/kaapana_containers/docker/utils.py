from contextlib import contextmanager
import tarfile
import io
import docker


class DockerUtils:
    @staticmethod
    @contextmanager
    def extract_file_from_image(image: str, file: str):
        """ "
        Read inidividual files from a container image via docker

        Example:
        with DockerUtils._get_file_from_container(image, "/extractor.json") as f:
            spec_object = json.load(f)
            return ExtractorSpec(**spec_object)
        """
        client = docker.from_env()
        scratch = client.containers.create(image, command="true", detach=True)

        try:
            stream, _ = scratch.get_archive(file)
            buf = io.BytesIO(b"".join(stream))

            with tarfile.open(fileobj=buf) as tar:
                # Docker tars always store files without leading slash
                tar_filename = file.lstrip("/")
                extracted = tar.extractfile(tar_filename)
                if extracted is None:
                    raise FileNotFoundError(
                        f"{file} not found in container image: {image}"
                    )
                yield extracted
        finally:
            scratch.remove()
