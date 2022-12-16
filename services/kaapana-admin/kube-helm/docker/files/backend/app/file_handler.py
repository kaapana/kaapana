import os
import math

from typing import Dict, List, Set, Union, Tuple
from fastapi import UploadFile, WebSocket, WebSocketDisconnect
from fastapi.logger import logger
import aiofiles

from config import settings
import schemas
import helm_helper


chunks_fname: str = ""
chunks_fsize: int = 0
chunks_chunk_size: int = 0
chunks_endindex: int = 0
chunks_fpath: str = 0
chunks_index: int = -1


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


def init_file_chunks(fname: str, fsize: int, chunk_size: int, index: int, endindex: int, overwrite: bool = True):
    global chunks_fname, chunks_fsize, chunks_chunk_size, chunks_endindex, chunks_fpath, chunks_index

    # sanity checks
    max_iter = math.ceil(fsize / chunk_size)
    if endindex != max_iter:
        raise AssertionError(f"chunk size calculated differently: {endindex} != {max_iter}")
    if index > max_iter:
        raise AssertionError(f"max iterations already reached: {index} > {max_iter}")

    logger.debug(
        f"in function: init_file_chunks with {fname=}, {fsize=}, {chunk_size=}, {index=}, {endindex=}, {max_iter=}")

    fpath, msg = check_file_exists(fname, overwrite)
    logger.debug(f"add_file_chunks first call, creating file {fpath}")
    if fpath == "":
        return False, msg

    f = open(fpath, "wb")
    f.close()

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
    # sanity check
    if chunks_fpath == "":
        raise AssertionError(f"file path not available when trying to write chunks")

    if chunks_index > chunks_endindex:
        raise AssertionError(f"max iterations already reached: {chunks_index} > {chunks_endindex}")

    logger.debug(f"writing to file {chunks_fpath} , {chunks_index} / {chunks_endindex}")
    # write bytes
    with open(chunks_fpath, "ab") as f:
        f.write(chunk)
    logger.debug("write completed")

    chunks_index += 1

    return chunks_index


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


async def delete_file() -> bool:
    if not os.path.exists(chunks_fpath):
        return True
    try:
        os.remove(chunks_fpath)
        chunks_fpath = ""
        return True
    except Exception as e:
        logger.error(f"Error when deleting file {chunks_fname}: {e}")
        return False
