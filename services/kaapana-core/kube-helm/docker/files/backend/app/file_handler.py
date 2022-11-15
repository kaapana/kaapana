import os

from typing import Dict, List, Set, Union, Tuple
from fastapi import UploadFile
from fastapi.logger import logger
import aiofiles

from config import settings
import schemas
import helm_helper


def check_file_exists(filename, overwrite):
    pre = settings.helm_extensions_cache
    if pre[-1] != "/":
        pre += "/"

    msg = ""
    # check if file exists
    fname = pre + filename
    if os.path.exists(fname):
        msg = "File {0} already exists".format(fname)
        logger.warning(msg)
        if not overwrite:
            msg += ", returning without overwriting. "
            return "", msg
        msg += ", overwritten"

    return fname, msg


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


async def add_file_chunks(file: UploadFile, chunk_size=100*1024*1024, overwrite: bool = True) -> Tuple[bool, str]:
    allowed_ext = ["tgz", "tar.gz", "tar"]
    f_ext = file.filename.split(".")[1]
    if f_ext not in allowed_ext:
        err = f"Wrong file extension '{f_ext}'  allowed extensions are {allowed_ext}"
        logger.error(err)
        return False, err
    logger.debug("filename {0}".format(file.filename))

    fpath, msg = check_file_exists(file.filename, overwrite)
    if fpath == "":
        return False, msg

    # write file in chunks
    logger.info(f"async saving file to {fpath} with chunk size {chunk_size}...")
    try:
        async with aiofiles.open(fpath, "wb") as f:
            i = 1
            while chunk := await file.read(chunk_size):
                await f.write(chunk)
                logger.debug(f"wrote chunk #{i}")
                i += 1

    except Exception as e:
        logger.error(e)
        err = "Failed to write container file {0}".format(file.filename)
        logger.error(err)
        return False, err
    finally:
        f.close()
        logger.info("write successful")

    if msg == "":
        msg = "Successfully added chart file {0}".format(file.filename)

    return True, msg
