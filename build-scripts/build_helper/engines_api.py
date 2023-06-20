from build_helper.build_utils import BuildUtils
import os
from importlib import import_module
from os.path import dirname, basename, exists, join

class Docker:
    def __init__(self, tag):
        docker = import_module('docker')
        client = docker.from_env()

    def build(self):
        try:
            build_result = self.client.images.build(
                path=os.path.dirname(self.path), tag=self.build_tag, quiet=False
            )

        except self.docker.errorsBuildError as e:
            print("BuildError:")
            print(e)

        except self.docker.errors.APIError as e:
            print("APIError:")
            print(e)

        except TypeError as e:
            print("TypeError:")
            print(e)

        except Exception as e:
            print("Unknown Exception:")
