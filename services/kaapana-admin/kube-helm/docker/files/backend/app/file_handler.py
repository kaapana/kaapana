import os
import math
import json
import yaml
import uuid
from pathlib import Path
from datetime import datetime, timedelta

from typing import Tuple
from fastapi import UploadFile, WebSocket, WebSocketDisconnect, Form, Request
from fastapi.logger import logger
import aiofiles
import shutil

from repeat_timer import RepeatedTimer
from config import settings
import schemas
import helm_helper
from utils import helm_get_values


chunks_fname: str = ""
chunks_fsize: int = 0
chunks_chunk_size: int = 0
chunks_endindex: int = 0
chunks_fpath: str = 0
chunks_index: int = -1


class FileSession:
    def __init__(
        self, md5, fname, fpath, fsize, chunk_size, endindex, curr_index=0
    ) -> None:
        self.md5: str = md5
        self.fname: str = fname
        self.fpath: str = fpath
        self.fsize: int = fsize
        self.chunk_size: int = chunk_size
        self.endindex: int = endindex
        self.curr_index: int = curr_index
        # wait 20 mins for the next chunk before deleting the file
        self.wait_before_del = 20
        # self.timer = RepeatedTimer(
        #     self.wait_before_del, delete_file, self.fpath)
        logger.debug(f"FileSession created with {fpath=}")

    def update(self, index):
        self.curr_index = index
        if self.curr_index > self.endindex:
            logger.error(
                f"ERROR: for {self.fpath=} {self.curr_index=} > {self.endindex=}"
            )
        # self.timer.stop()
        # self.timer.start()

    def delete_file(self):
        logger.warning(
            f"FileSession with {self.filename=} and {self.md5=} is deleting the file, {self.wait_before_del=} seconds passed"
        )
        logger.warning(f"{self.curr_index}, {self.endindex}")
        delete_file(self.fpath)

    def pause(self):
        # self.timer.stop()
        return

    def check_md5(self, md5):
        return self.md5 == md5


sessions = dict()  # {md5, FileSession}
global filepond_dict
filepond_dict = dict()


def remove_outdated_tmp_files(search_dir):
    max_hours_tmp_files = 24
    files_grabbed = (p.resolve() for p in Path(search_dir).glob("*") if p.suffix in {".json", ".tmp"})

    for file_found in files_grabbed:
        hours_since_creation = int((datetime.now() - datetime.fromtimestamp(os.path.getmtime(file_found))).total_seconds() / 3600)
        if hours_since_creation > max_hours_tmp_files:
            logger.warning(f"File {file_found} outdated -> delete")
            try:
                os.remove(file_found)
                pass
            except Exception as e:
                logger.warning(f"Something went wrong with the removal of {file_found} .. ")


def filepond_init_upload(form: Form) -> str:
    global filepond_dict
    patch = str(uuid.uuid4())
    dict_fpath = Path(settings.helm_extensions_cache) / "extension_filepond_dict.json"
    remove_outdated_tmp_files(settings.helm_extensions_cache)
    if dict_fpath.exists():
        # if the file is not removed (i.e. recent), read it into the dict
        with open(dict_fpath, "r") as fp:
            filepond_dict = json.load(fp)
    filepond_dict.update({patch: json.loads(form["filepond"])["filepath"]})
    return patch


# TODO: after successful upload, check if it's tgz and update the cache accordingly
async def filepond_upload_stream(
    request: Request, patch: str, ulength: str, uname: str
) -> Tuple[str, bool]:
    global filepond_dict
    fpath = Path(settings.helm_extensions_cache) / f"{patch}.tmp"
    with open(fpath, "ab") as f:
        async for chunk in request.stream():
            f.write(chunk)
    if ulength == str(fpath.stat().st_size):
        logger.debug(f"filepond upload completed {fpath}")
        # upload completed
        try:
            dict_fpath = Path(settings.helm_extensions_cache) / "extension_filepond_dict.json"
            if dict_fpath.exists():
                with open(dict_fpath, "r") as fp:
                    filepond_dict = json.load(fp)
            else:
                logger.error(f"upload mapping dictionary file {dict_fpath} does not exist, using the global variable (not thread-safe)")
            logger.debug(f"{patch=}, {filepond_dict=}")
            object_name = filepond_dict[patch]
            target_path = Path(settings.helm_extensions_cache) / object_name.strip("/")
            target_path.parents[0].mkdir(parents=True, exist_ok=True)
            logger.info(f"Moving file {fpath} to {target_path}")
            shutil.move(fpath, target_path)
            logger.info(f"Successfully saved file {uname} using filepond")
            filename = filepond_dict.pop(patch, "already deleted")

            if filename[-3:] == "tgz":
                logger.info("tgz file uploaded, checking namespaces")
                # check if there is any kubernetes object specified under admin namespace
                is_file_safe = check_file_namespace(filename)
                if not is_file_safe:
                    raise AttributeError(
                        f"Chart files can not contain resources under admin_namespace"
                    )
            return filename, True

        except Exception as e:
            logger.error(f"Failed to upload via filepond: {e}")
            if fpath.is_file():
                fpath.unlink()
            filename = filepond_dict.pop(patch, "already deleted")
            return str(e), False
    return "", True


def filepond_get_offset(patch: str, ulength: str):
    fpath = Path(settings.helm_extensions_cache) / f"{patch}.tmp"
    if fpath.is_file():
        offset = int(ulength) - fpath.stat().st_size
    else:
        offset = 0

    return offset


def filepond_delete(patch):
    fpath = Path(settings.helm_extensions_cache) / f"{patch}.tmp"
    if fpath.is_file():
        fpath.unlink()
        filename = filepond_dict.pop(patch, "already deleted")
        return filename
    else:
        return ""


def make_fpath(fname: str, platforms=False):
    pre = settings.helm_extensions_cache
    if platforms:
        pre = settings.helm_platforms_cache
    if pre[-1] != "/":
        pre += "/"

    fpath = pre + fname

    return fpath


def check_file_exists(filename, overwrite, platforms: bool = False):
    logger.debug(f"checking if file {filename} exists")
    fpath = make_fpath(filename, platforms=platforms)

    msg = ""
    # check if file exists
    logger.debug(f"full path: {fpath=}")
    if os.path.exists(fpath):
        msg = f"File {fpath} already exists"
        logger.warning(msg + "overwrite:" + str(overwrite))
        if not overwrite:
            msg += ", returning without overwriting. "
            return "", msg
        msg += ", overwrite enabled"
    return fpath, msg


def check_file_namespace(filename: str) -> bool:
    fpath = Path(settings.helm_extensions_cache) / f"{filename}"
    logger.info(f"Checking namespaces of {filename=} in {fpath=}")

    # get chart's release name
    chart = helm_helper.helm_show_chart(package=str(fpath))

    # get --set values from admin-chart
    release_values = helm_get_values(settings.release_name, helm_namespace="default")
    logger.debug(f"{release_values=}")
    default_sets = {}
    if "global" in release_values:
        for k, v in release_values["global"].items():
            default_sets[f"global.{k}"] = v
    default_sets.pop("global.preinstall_extensions", None)
    default_sets.pop("global.kaapana_collections", None)
    logger.debug(f"{default_sets=}")

    helm_sets = ""
    for key, value in default_sets.items():
        if type(value) == str:
            value = (
                str(value)
                .replace(",", "\,")
                .replace("'", "'\"'")
                .replace(" ", "")
                .replace(" ", "")
                .replace("{", "\{")
                .replace("}", "\}")
            )
            helm_sets = helm_sets + f" --set-string {key}='{value}'"
        else:
            helm_sets = helm_sets + f" --set {key}='{value}'"
    logger.debug(f"{helm_sets=}")

    cmd = f"{settings.helm_path} install {chart['name']} {helm_sets} {str(fpath)} -o json --dry-run "
    success, stdout = helm_helper.execute_shell_command(
        cmd, shell=True, blocking=True, timeout=60
    )
    if not success:
        err = "Failed to check chart namespace"
        logger.error(f"{err} {stdout=}")
        raise RuntimeError(err)

    res = json.loads(stdout)
    manifest = list(yaml.load_all(res["manifest"], yaml.FullLoader))
    logger.debug(f"{manifest=}")

    if "global.admin_namespace" not in default_sets:
        raise AssertionError(
            "Failed to check chart namespace, admin_namespace is not present"
        )

    admin_namespace = default_sets["global.admin_namespace"]

    # if any kubernetes resource (except hooks) is running under admin namespace, the check fails
    for resource in manifest:
        if (
            (resource is None)
            or ("metadata" not in resource)
            or ("namespace" not in resource["metadata"])
        ):
            continue

        if resource["metadata"]["namespace"] == admin_namespace:
            logger.error(
                f"Uploaded chart {filename} has a Kubernetes resource {resource} which contains admin_namespace"
            )
            return False

    logger.info(f"no resource running under admin_namespace in {filename}, returning")
    return True


def add_file(
    file: UploadFile, content: bytes, overwrite: bool = True, platforms: bool = False
) -> Tuple[bool, str]:
    """writes tgz file into fast_data_dir/extensions or fast_data_dir/platforms"""
    allowed_types = [
        "application/x-compressed",
        "application/x-compressed-tar",
        "application/gzip",
    ]
    if file.content_type not in allowed_types:
        err = f"Wrong content type '{file.content_type}'  allowed types are {allowed_types}"
        logger.error(err)
        return False, err
    logger.debug(f"filename {file.filename}")
    logger.debug(f"file type {file.content_type}")

    fpath, msg = check_file_exists(file.filename, overwrite, platforms=platforms)
    if fpath == "":
        return False, msg

    multiinstallable = False

    # write file
    logger.info(f"saving file to {fpath}...")
    try:
        with open(fpath, "wb") as f:
            f.write(content)
        success, stdout = helm_helper.execute_shell_command(
            f"{settings.helm_path} show chart {fpath}"
        )
        if not success:
            raise Exception(stdout)
        if "kaapanamultiinstallable" in stdout:
            multiinstallable = True
    except Exception as e:
        logger.error(e)
        err = f"Failed to write chart file {file.filename}"
        logger.error(err)
        deleted = delete_file(fpath)
        if deleted:
            logger.info(f"deleted file {fpath}")
        return False, err
    finally:
        # TODO: os.chdir(cwd)
        f.close()

    # parse name, version
    if file.filename[-4:] != ".tgz":
        err = f"File extension must be '.tgz', can not parse {file.filename}"
        return False, err

    fname, fversion = file.filename.split(".tgz")[0].rsplit("-", 1)

    helm_helper.update_extension_state(
        schemas.ExtensionStateUpdate.construct(
            extension_name=fname,
            extension_version=fversion,
            state=schemas.ExtensionStateType.NOT_INSTALLED,
            multiinstallable=multiinstallable,
        )
    )

    if msg == "":
        msg = f"Successfully added chart file {fname=}"

    return True, msg


def init_file_chunks(
    fname: str,
    fsize: int,
    chunk_size: int,
    index: int,
    endindex: int,
    md5: str = "placeholder",
    overwrite: bool = True,
    platforms=False,
):
    global chunks_fname, chunks_fsize, chunks_chunk_size, chunks_endindex, chunks_fpath, chunks_index

    # sanity checks
    max_iter = math.ceil(fsize / chunk_size)
    if endindex != max_iter:
        raise AssertionError(
            f"chunk size calculated differently: {endindex} != {max_iter}"
        )
    if index > max_iter:
        raise AssertionError(f"max iterations already reached: {index} > {max_iter}")

    logger.debug(
        f"in function: init_file_chunks with {fname=}, {fsize=}, {chunk_size=}, {index=}, {endindex=}, {max_iter=}"
    )

    fpath, msg = check_file_exists(fname, overwrite, platforms=platforms)
    logger.debug(f"add_file_chunks first call, creating file {fpath}")
    if fpath == "":
        return False, msg

    f = open(fpath, "wb")
    f.close()

    sess = FileSession(
        md5=md5,
        fname=fname,
        fsize=fsize,
        chunk_size=chunk_size,
        endindex=endindex,
        fpath=fpath,
    )
    sessions[sess.md5] = sess

    # TODO: delete after testing FileSession
    chunks_fname = fname
    chunks_fsize = fsize
    chunks_chunk_size = chunk_size
    chunks_endindex = endindex
    chunks_fpath = fpath
    chunks_index = 0

    return fpath, "Successfully initialized file"


def add_file_chunks(chunk: bytes):
    """
    Args:
        chunk (bytes):

    Raises:
        AssertionError:
        AssertionError:

    Returns:
        int: next expected index from front end
    """
    global chunks_fpath, chunks_index
    # TODO: find a way to receive actual md5 key
    md5 = list(sessions.keys())[0]
    sess = sessions[md5]
    # sanity check
    if sess.fpath == "":
        raise AssertionError(f"file path not available when trying to write chunks")

    if sess.curr_index > sess.endindex:
        raise AssertionError(
            f"max iterations already reached: {sess.curr_index} > {sess.endindex}"
        )

    logger.debug(f"writing to file {sess.fpath} , {sess.curr_index} / {sess.endindex}")
    # write bytes
    with open(sess.fpath, "ab") as f:
        f.write(chunk)
    logger.debug("write completed")

    if sess.curr_index != sess.endindex:
        sess.update(sess.curr_index + 1)

    return sess.curr_index


async def ws_add_file_chunks(
    ws: WebSocket, fname: str, fsize: int, chunk_size: int, overwrite: bool = True
):
    max_iter = math.ceil(fsize / chunk_size)

    logger.debug(
        f"in function: ws_add_file_chunks with {fname=}, {fsize=}, {chunk_size=}, {max_iter}"
    )

    try:
        fpath, msg = check_file_exists(fname, overwrite)
        if fpath == "":
            return False, msg

        await ws.send_json({"index": -1, "success": True})

        i = 0
        async with aiofiles.open(fpath, "wb") as f:
            while True:
                if i > max_iter:
                    logger.warning("max iterations reached, file write is completed")
                    break

                logger.debug("awaiting bytes")
                data = await ws.receive_bytes()
                logger.debug(
                    f"received data from websocket, index {i}, length {len(data)}"
                )
                await f.write(data)
                await ws.send_json({"index": i, "success": True})
                i += 1

        logger.debug("closing websocket")
        await ws.close()

    except WebSocketDisconnect:
        logger.warning(f"received WebSocketDisconnect with index {i}")
        if i < max_iter:
            logger.debug(f"file write failed, removing {fpath}")
            os.remove(fpath)
        raise WebSocketDisconnect
    except Exception as e:
        logger.error(f"add_file_chunks failed {e}")
        if i < max_iter:
            logger.debug(f"file write failed, removing {fpath}")
            os.remove(fpath)
        return "", msg

    return fpath, "File successfully uploaded"


async def run_containerd_import(
    fname: str, platforms: bool = False
) -> Tuple[bool, str]:
    logger.debug(f"in function: run_containerd_import, {fname=}")
    fpath = make_fpath(fname, platforms=platforms)
    # check if file exists
    if not os.path.exists(fpath):
        logger.error(f"file can not be found in path {fpath}")
        return False, f"file {fname} can not be found"

    cmd = f"ctr --namespace k8s.io -address='{settings.containerd_sock}' image import {fpath}"
    logger.debug(f"{cmd=}")
    res, stdout = await helm_helper.exec_shell_cmd_async(cmd, shell=True, timeout=180)

    if not res:
        logger.error(f"microk8s import failed: {stdout}")
        return res, f"Failed to import container {fname}: {stdout}"

    # TODO: include below if not using filepond
    # sess = sessions[list(sessions.keys())[0]]
    # sess.timer.stop()
    # del sess.timer
    # TODO: include below if not using filepond
    # del sess

    logger.info(f"Successfully imported container {fname}")

    return res, f"Successfully imported container {fname}"


def delete_file(fpath) -> bool:
    logger.warning(f"file_handler.delete_file() is called with {fpath}")
    global chunks_fpath
    sess = sessions[list(sessions.keys())[0]]
    # sess.timer.stop()
    # del sess.timer
    if not os.path.exists(fpath):
        del sess
        return True
    try:
        os.remove(fpath)
        chunks_fpath = ""
        del sess
        return True
    except Exception as e:
        logger.error(f"Error when deleting file {fpath}: {e}")
        return False
