import os
import math

from typing import Dict, List, Set, Union, Tuple
from fastapi import UploadFile, WebSocket, WebSocketDisconnect
from fastapi.logger import logger
import aiofiles

from config import settings
import schemas
import helm_helper


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
        logger.warning(msg)
        if not overwrite:
            msg += ", returning without overwriting. "
            return "", msg
        msg += ", overwrite enabled"
    return fpath, msg


def add_file(file: UploadFile, content: bytes, overwrite: bool = True) -> Tuple[bool, str]:
    allowed_types = ["application/x-compressed"]
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
    logger.info(f"saving file to {fpath} all at once...")
    try:
        with open(fpath, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(e)
        err = "Failed to write chart file {0}".format(file.filename)
        logger.error(err)
        return False, err
    finally:
        f.close()
        logger.debug("write successful")

    # parse name, version
    if file.filename[-4:] != ".tgz":
        err = "File extension must be '.tgz', can not parse {0}".format(file.filename)
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


async def add_file_chunks(fname: str, fsize: int, chunk_size: int, index: int, endindex: int, chunk: str, overwrite: bool = True):
    # sanity checks
    max_iter = math.ceil(fsize / chunk_size)
    if endindex != max_iter:
        raise AssertionError(f"chunk size calculated differently: {endindex} != {max_iter}")
    if index > max_iter:
        raise AssertionError(f"max iterations already reached: {index} > {max_iter}")

    logger.debug(
        f"in function: add_file_chunks with {fname=}, {fsize=}, {chunk_size=}, {index=}, {endindex}, {max_iter}")

    fpath, msg = check_file_exists(fname, overwrite)
    if index == -1:
        logger.debug(f"add_file_chunks first call, creating file {fpath}")
        if fpath == "":
            return False, msg
        f = open(fpath, "w")
        f.close()

    else:
        logger.debug(f"adding chunk index {index} to file {fpath}")
        if fpath == "":
            return False, msg

        logger.debug(f"writing {index} / {max_iter} to file {fpath}")
        with open(fpath, "a") as f:
            f.write(chunk)
        logger.debug("write completed")

    return fpath, str(index)


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
                    logger.warning("max iterations reached, file write is completed")
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


def run_microk8s_import(fname: str) -> Tuple[bool, str]:
    fpath = make_fpath(fname)
    # check if file exists
    if not os.path.exists(fpath):
        logger.error(f"file can not be found in path {fpath}")
        return False,  f"file {fname} can not be found"
    cmd = f"microk8s.ctr image import {fpath}"
    res, stdout = helm_helper.execute_shell_command(cmd, shell=True, blocking=True, timeout=30)

    if not res:
        logger.error(f"microk8s import failed: {stdout}")
        return res, f"Failed to import container {fname}"

    return res, f"Successfully imported container {fname}"


async def delete_file(fname: str) -> bool:
    fpath = make_fpath(fname)
    if not os.path.exists(fpath):
        return True
    try:
        os.remove(fpath)
        return True
    except Exception as e:
        logger.error(f"Error when deleting file {fname}: {e}")
        return False
