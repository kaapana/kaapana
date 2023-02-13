import os
import math
import time

from typing import Dict, List, Set, Union, Tuple
from fastapi import UploadFile, WebSocket, WebSocketDisconnect
from fastapi.logger import logger
import aiofiles

from repeat_timer import RepeatedTimer
from config import settings
import schemas
import helm_helper


chunks_fname: str = ""
chunks_fsize: int = 0
chunks_chunk_size: int = 0
chunks_endindex: int = 0
chunks_fpath: str = 0
chunks_index: int = -1


class FileSession:
    def __init__(self, md5, fname, fpath, fsize, chunk_size, endindex, curr_index=0) -> None:
        self.md5: str = md5
        self.fname: str = fname
        self.fpath: str = fpath
        self.fsize: int = fsize
        self.chunk_size: int = chunk_size
        self.endindex: int = endindex
        self.curr_index: int = curr_index
        # wait 30 mins for the next chunk before deleting the file
        self.wait_before_del = 20
        self.timer = RepeatedTimer(
            self.wait_before_del, delete_file, self.fpath)

    def update(self, index):
        self.curr_index = index
        if self.curr_index > self.endindex:
            logger.error(
                f"ERROR: for {self.fpath=} {self.curr_index=} > {self.endindex=}")
        self.timer.stop()
        self.timer.start()

    def delete_file(self):
        logger.warning(
            f"FileSession with {self.filename=} and {self.md5=} is deleting the file, {self.wait_before_del=} seconds passed")
        logger.warning(f"{self.curr_index}, {self.endindex}")
        delete_file(self.fpath)

    def pause(self):
        self.timer.stop()

    def check_md5(self, md5):
        return self.md5 == md5


sessions = dict()  # {md5, FileSession}


def make_fpath(fname: str):
    pre = settings.helm_extensions_cache
    if pre[-1] != "/":
        pre += "/"

    fpath = pre + fname

    return fpath


def check_file_exists(filename, overwrite):
    logger.debug(f"checking if file {filename} exists")
    fpath = make_fpath(filename)

    msg = ""
    # check if file exists
    logger.debug(f"full path: {fpath=}")
    if os.path.exists(fpath):
        msg = "File {0} already exists".format(fpath)
        logger.warning(msg + "overwrite:" + str(overwrite))
        if not overwrite:
            msg += ", returning without overwriting. "
            return "", msg
        msg += ", overwrite enabled"
    return fpath, msg


def check_file_namespace(fpath):
    # TODO: get file folder instead of the file path
    # TODO: decide on how to best check the namespace, what keyword to search in file actually?

    # open tgz to temp folder and check namespaces
    cwd = os.getcwd()
    tmp_dir = "/tmp"
    logger.info(f"untarring file into temp directory {tmp_dir}")
    os.mkdir(tmp_dir)
    cmd = f"tar -xf {fpath} --directory {tmp_dir}"
    helm_helper.execute_shell_command(cmd, shell=True, blocking=True)

    os.chdir(tmp_dir)
    os.chdir(os.listdir()[0])
    # TODO: if it doesnt' have any kube objects defined, still check or not?
    if "templates" in os.listdir():
        os.chdir("templates")
        for f in os.listdir():
            with open(f, "r") as stream:
                if "admin_namespace" in f.read():
                    raise AssertionError(
                        f"Permission denied: admin_namespace present in file {f}")
                if "kube-system" in f.read():
                    raise AssertionError(
                        f"Permission denied: kube-system present in file {f}")


def add_file(file: UploadFile, content: bytes, overwrite: bool = True) -> Tuple[bool, str]:
    """writes tgz file into fast_data_dir/extensions
    """
    allowed_types = ["application/x-compressed", "application/x-compressed-tar"]
    if file.content_type not in allowed_types:
        err = f"Wrong content type '{file.content_type}'  allowed types are {allowed_types}"
        logger.error(err)
        return False, err
    logger.debug("filename {0}".format(file.filename))
    logger.debug("file type {0}".format(file.content_type))

    fpath, msg = check_file_exists(file.filename, overwrite)
    if fpath == "":
        return False, msg

    # write file
    logger.info(f"saving file to {fpath}...")
    try:
        with open(fpath, "wb") as f:
            f.write(content)
        # TODO: check_file_namespace(fpath)
    except Exception as e:
        logger.error(e)
        err = "Failed to write chart file {0}".format(file.filename)
        logger.error(err)
        # TODO:
        # if os.path.exists(fpath):
        #     logger.debug(f"removing file {fpath}")
        #     os.remove(fpath)
        # if os.path.exists("/tmp"):
        #     shutil.rmtree("/tmp")
        return False, err
    finally:
        # TODO: os.chdir(cwd)
        f.close()
        logger.info("write successful")

    # parse name, version
    if file.filename[-4:] != ".tgz":
        err = "File extension must be '.tgz', can not parse {0}".format(
            file.filename)
        return False, err

    fname, fversion = file.filename.split(".tgz")[0].rsplit("-", 1)

    helm_helper.update_extension_state(schemas.ExtensionStateUpdate.construct(
        extension_name=fname,
        extension_version=fversion,
        state=schemas.ExtensionStateType.NOT_INSTALLED
    ))

    if msg == "":
        msg = "Successfully added chart file {0}".format(fname)

    return True, msg


def init_file_chunks(fname: str, fsize: int, chunk_size: int, index: int, endindex: int, md5: str, overwrite: bool = True):
    global chunks_fname, chunks_fsize, chunks_chunk_size, chunks_endindex, chunks_fpath, chunks_index

    # sanity checks
    max_iter = math.ceil(fsize / chunk_size)
    if endindex != max_iter:
        raise AssertionError(
            f"chunk size calculated differently: {endindex} != {max_iter}")
    if index > max_iter:
        raise AssertionError(
            f"max iterations already reached: {index} > {max_iter}")

    logger.debug(
        f"in function: init_file_chunks with {fname=}, {fsize=}, {chunk_size=}, {index=}, {endindex=}, {max_iter=}")

    fpath, msg = check_file_exists(fname, overwrite)
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
        fpath=fpath
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
        raise AssertionError(
            f"file path not available when trying to write chunks")

    if sess.curr_index > sess.endindex:
        raise AssertionError(
            f"max iterations already reached: {sess.curr_index} > {sess.endindex}")

    logger.debug(
        f"writing to file {sess.fpath} , {sess.curr_index} / {sess.endindex}")
    # write bytes
    with open(sess.fpath, "ab") as f:
        f.write(chunk)
    logger.debug("write completed")

    sess.update(sess.curr_index + 1)

    return sess.curr_index


async def ws_add_file_chunks(ws: WebSocket, fname: str, fsize: int, chunk_size: int, overwrite: bool = True):
    max_iter = math.ceil(fsize / chunk_size)

    logger.debug(
        f"in function: ws_add_file_chunks with {fname=}, {fsize=}, {chunk_size=}, {max_iter}")

    try:
        fpath, msg = check_file_exists(fname, overwrite)
        if fpath == "":
            return False, msg

        await ws.send_json({"index": -1, "success": True})

        i = 0
        async with aiofiles.open(fpath, "wb") as f:
            while True:
                if i > max_iter:
                    logger.warning(
                        "max iterations reached, file write is completed")
                    break

                logger.debug("awaiting bytes")
                data = await ws.receive_bytes()
                logger.debug(
                    f"received data from websocket, index {i}, length {len(data)}")
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


def run_containerd_import(fname: str) -> Tuple[bool, str]:
    logger.debug(f"in function: run_containerd_import, {fname=}")
    fpath = make_fpath(fname)
    # check if file exists
    if not os.path.exists(fpath):
        logger.error(f"file can not be found in path {fpath}")
        return False,  f"file {fname} can not be found"

    cmd = f"ctr --namespace k8s.io -address='{settings.containerd_sock}' image import {fpath}"
    logger.debug(f"{cmd=}")
    res, stdout = helm_helper.execute_shell_command(
        cmd, shell=True, blocking=True, timeout=30)

    if not res:
        logger.error(f"microk8s import failed: {stdout}")
        return res, f"Failed to import container {fname}"

    sess = sessions[list(sessions.keys())[0]]
    sess.timer.stop()
    del sess.timer
    del sess

    logger.info("Successfully imported container")

    return res, f"Successfully imported container {fname}"


def delete_file(fpath) -> bool:
    logger.warning("file_handler.delete_file() is called")
    global chunks_fpath
    sess = sessions[list(sessions.keys())[0]]
    sess.timer.stop()
    del sess.timer
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
