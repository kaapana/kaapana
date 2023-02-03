#!/usr/bin/env python3
import os
import SimpleITK as sitk
from tcia_utils import nbia
from pathlib import Path
import concurrent.futures
import multiprocessing
import shutil
import json

def create_subset_from_list(list, n):
    # create subset from list
    subset = list[0:n]
    return subset

def download_series(uid):
    # feed series_data to downloadSampleSeries function
    try:
        df = nbia.downloadSeries([uid], input_type = "list")
    except:
        raise Exception("Error downloading series: " + uid)
    return df

def create_n_chunks_from_list(list, n):
    # create n chunks from list
    chunks = [list[i::n] for i in range(n)]
    return chunks

if __name__ == "__main__":

    # manifest path
    path_to_conf_json = Path("/data", "conf", "conf.json")

    # read conf.json
    with open(path_to_conf_json) as f:
        conf = json.load(f)

    # manifest path
    manifest_path = conf['Key']
    
    # converts manifest to list of UIDs
    uids = nbia.manifestToList(Path("/minio", manifest_path))

    # create subset from list of UIDs if SUBSET is greater than 0
    if int(os.environ['SUBSET']) > 0:
        # create subset from list of UIDs
        uids = create_subset_from_list(uids, int(os.environ['SUBSET']))

    # set max_workers to PARALLEL_PROCESSES
    max_workers=int(os.environ['PARALLEL_PROCESSES'])

    # if PARALLEL_PROCESSES is greater than cpu_count, set max_workers to cpu_count
    if max_workers > multiprocessing.cpu_count():
        max_workers = multiprocessing.cpu_count()
    
    # Download series concurrently using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit the tasks to the executor
        tasks = [executor.submit(download_series, uid) for uid in uids]
    
        # Get the results
        results = [task.result() for task in tasks]

    try:
        # copy /tciaDownload to /data/tcia-download using shutil
        shutil.copytree("/tciaDownload", "/data/tcia-download")

        # remove /tciaDownload
        shutil.rmtree("/tciaDownload")
    except:
        # copy /kaapanasrc/tciaDownload to /data/tcia-download using shutil
        shutil.copytree("/kaapanasrc/tciaDownload", "/data/tcia-download")

        # remove /kaapanasrc/tciaDownload
        shutil.rmtree("/kaapanasrc/tciaDownload")