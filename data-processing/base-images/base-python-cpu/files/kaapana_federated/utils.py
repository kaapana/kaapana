import functools
import json
import os
import tarfile
import time

from cryptography.fernet import Fernet


class Profiler(object):
    def __init__(self, log_dir) -> None:
        self.filename = os.path.join(log_dir, "fl_stats.json")
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        # not accumulating anything because this leads to a decrease in speed over many epochs!

    @staticmethod
    def _write_json(filename, data):
        with open(filename, "w") as json_file:
            json.dump(data, json_file)

    @staticmethod
    def _load_json(filename):
        try:
            with open(filename) as json_file:
                workflow_data = json.load(json_file)
        except FileNotFoundError:
            workflow_data = []
        return workflow_data

    def append_data_dict(self, data_dict):
        workflow_data = self._load_json(self.filename)
        workflow_data.append(data_dict)
        self._write_json(self.filename, workflow_data)

    def timeit(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            ts = time.time()
            x = func(self, *args, **kwargs)
            te = time.time()
            self.json_writer.append_data_dict(
                {
                    "name": func.__name__,
                    "execution_time": te - ts,
                    "timestamp": time.time(),
                    "args": args,
                    "kwargs": kwargs,
                }
            )
            return x

        return wrapper


class Encryption:
    @staticmethod
    def encryptfile(filepath: str, key: str):
        if key == "deactivated":
            return
        fernet = Fernet(key.encode())
        with open(filepath, "rb") as file:
            original = file.read()
        encrypted = fernet.encrypt(original)
        with open(filepath, "wb") as encrypted_file:
            encrypted_file.write(encrypted)

    @staticmethod
    def decryptfile(filepath: str, key: str):
        if key == "deactivated":
            return
        fernet = Fernet(key.encode())
        with open(filepath, "rb") as enc_file:
            encrypted = enc_file.read()
        decrypted = fernet.decrypt(encrypted)
        with open(filepath, "wb") as dec_file:
            dec_file.write(decrypted)


class TarUtils:
    def untar(src_filename: str, dst_dir: str):
        print(f"Untar {src_filename} to {dst_dir}")
        with tarfile.open(
            src_filename, "r:gz" if src_filename.endswith("gz") is True else "r"
        ) as tar:
            tar.extractall(dst_dir)

    def tar(dst_filename: str, src_dir: str):
        print(f"Tar {src_dir} to {dst_filename}")
        with tarfile.open(
            dst_filename, "w:gz" if dst_filename.endswith("gz") is True else "w"
        ) as tar:
            tar.add(src_dir, arcname=os.path.basename(src_dir))
