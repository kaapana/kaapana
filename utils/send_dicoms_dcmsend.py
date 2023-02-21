#!/usr/bin/env python3

from os.path import join, dirname, basename
from subprocess import PIPE, run
from glob import glob
from multiprocessing.pool import ThreadPool
from argparse import ArgumentParser
import os
import csv
import time
import json
# import pydicom

send_delay = 0


def search_metadata_csv(target_dir):
    collection_extracted = None
    max_updir_count = 5
    updir_count = 0
    print(f"#")
    print(f"#")
    while updir_count < max_updir_count:
        print(f"# search_metadata: {target_dir}")
        metadata_file = glob(join(target_dir, "metadata.csv"), recursive=True)
        if len(metadata_file) == 1:
            print(f"# found: {metadata_file[0]}")
            with open(metadata_file[0]) as fp:
                reader = csv.reader(fp, delimiter=",", quotechar='"')
                data_read = [row for row in reader]
            # next(reader, None)  # skip the headers
            if len(data_read) >= 2:
                index_collection = data_read[0].index('Collection')
                collection_extracted = data_read[1][index_collection]
                break
        else:   
            metadata_file = glob(join(target_dir, "info.txt"), recursive=True)
            if len(metadata_file) == 1:
                print(f"# found: {metadata_file[0]}")
                with open(metadata_file[0], 'r') as f:
                    metadata = json.load(f)
                if "collection" in metadata:
                    collection_extracted = metadata["collection"]
                    break
        if collection_extracted is None and target_dir != ".":
            updir_count += 1
            target_dir = dirname(target_dir)
        else:
            break
    print(f"#")
    print(f"# collection_extracted: {collection_extracted}")
    print(f"#")
    return collection_extracted


def send_dcm_dir(input_dir):
    global processed_count, execution_timeout, server, port, dataset, scan_pattern,init_send_delay, send_delay

    if dataset == None:
        extracted_dataset = search_metadata_csv(input_dir)
        local_dataset = extracted_dataset if extracted_dataset != None else "push_dicom"
    else:
        local_dataset = dataset
    print(f"#")
    print(f"# Sending dir: {dirname(input_dir)}")
    print(f"# dataset:     {local_dataset}")
    print(f"#")
        
    command = ["dcmsend", "-v", f"{server}", f"{port}", "-aet", f"push_tool", "-aec", f"{local_dataset}", "--scan-directories", "--scan-pattern", f"{scan_pattern}", "--recurse", f"{input_dir}"]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=execution_timeout)
    if output.returncode != 0:
        print("Something went wrong -> sending failed!")
        print(f"Message: {output.stdout}")
        print(f"Error:   {output.stderr}")
        if "timeout" in str(output.stderr):
            send_delay += 10
            send_delay += 10
        time.sleep(send_delay)
        return False, dirname(input_dir)
    # command stdout output -> output.stdout
    # command stderr output -> output.stderr
    if output.returncode != 0 or "with status SUCCESS" not in str(output):
        print("############### Something went wrong with dcmsend!")
        for line in str(output).split("\\n"):
            print(line)
        print("##################################################")
        return False, dirname(input_dir)

    processed_count += 1
    if send_delay > 0:
        send_delay -= 10

    if init_send_delay > 0:
        time.sleep(init_send_delay)
    return True, dirname(input_dir)


if __name__ == '__main__':
    cwd = os.getcwd()
    parser = ArgumentParser()
    parser.add_argument("-i", "--input", dest="input_dir", default=cwd, help="Path with DICOM files")
    parser.add_argument("-s", "--server", dest="server", default=None, required=True, help="Server address")
    parser.add_argument("-p", "--port", dest="port", default="11112", required=False, help="DICOM port server")
    parser.add_argument("-d", "--dataset", dest="dataset", default=None, required=False, help="Dataset name")
    parser.add_argument("-t", "--threads", dest="threads", default="3", required=False, help="Parallel threads to send the data.")
    parser.add_argument("-sp", "--scan-pattern", dest="scan_pattern", default="*.dcm", required=False, help="Scan pattern.")
    parser.add_argument("-max", "--max-series", dest="max_series", default="0", required=False, help="Max series count")
    parser.add_argument("-dl", "--delay", dest="init_delay", default="0", required=False, help="Delay between series")

    args = parser.parse_args()
    input_dir = args.input_dir
    server = args.server
    dataset = args.dataset
    scan_pattern = args.scan_pattern
    threads = int(args.threads)
    port = int(args.port)
    max_series = int(args.max_series)
    init_send_delay = int(args.init_delay)

    processed_count = 0
    execution_timeout = 300

    print(f"# ")
    print(f"# ")
    print(f"# server:     {server}")
    print(f"# port:       {port}")
    print(f"# input_dir:  {input_dir}")
    print(f"# dataset:    {dataset}")
    print(f"# max_series: {max_series}")
    print(f"# ")
    print(f"# threads:          {threads}")
    print(f"# scan_pattern:      {scan_pattern}")
    print(f"# execution_timeout: {execution_timeout}")
    print(f"# ")
    print(f"# ")

    # dicom = pydicom.dcmread(dcm_file_path)
    dicom_dirs = []
    dicom_files = glob(join(input_dir, "**", "*dcm"), recursive=True)
    for dcm_file in dicom_files:
        dcm_dir = dirname(dcm_file)
        if dcm_dir not in dicom_dirs:
            dicom_dirs.append(dcm_dir)

    dicom_dirs = sorted(dicom_dirs)
    print(f"# ")
    print(f"# ")
    print(f"# Found {len(dicom_dirs)} DICOM-dirs.")
    print(f"# ")
    print(f"# ")
    time.sleep(5)
    if max_series != 0 and len(dicom_dirs) > max_series:
        print(f"# Set series limit to max_series: {max_series} ...")
        dicom_dirs = dicom_dirs[:max_series]

    print(f"# Start sending {len(dicom_dirs)} DICOM-dirs with {threads} threads...")
    with ThreadPool(threads) as threadpool:
        results = threadpool.imap_unordered(send_dcm_dir, dicom_dirs)
        for result, input_dir in results:
            if result:
                print(f"# Dir ok: {input_dir}")
            else:
                print(f"# Issue with dir: {input_dir}")

            print("#")
            print("#")
            print(f"# {processed_count} series sent!")
            print("#")
            print("#")
