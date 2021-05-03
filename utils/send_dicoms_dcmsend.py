#!/usr/bin/env python3

from os.path import join, dirname, basename
from subprocess import PIPE, run
from glob import glob
from multiprocessing.pool import ThreadPool
from argparse import ArgumentParser
import os
# import pydicom


def send_dcm_dir(input_dir):
    global processed_count, execution_timeout, server, port, dataset, scan_pattern
    print(f"#")
    print(f"# Sending dir: {input_dir}")
    print(f"#")
    print(f"#")
    command = ["dcmsend", "-v", f"{server}", f"{port}", "-aet", f"push_tool", "-aec", f"{dataset}", "--scan-directories", "--scan-pattern", f"{scan_pattern}", "--recurse", f"{input_dir}"]
    # print(f"# COMMAND: {command}")
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=execution_timeout)
    # command stdout output -> output.stdout
    # command stderr output -> output.stderr
    if output.returncode != 0 or "with status SUCCESS" not in str(output):
        print("############### Something went wrong with dcmsend!")
        for line in str(output).split("\\n"):
            print(line)
        print("##################################################")
        return False, input_dir
    else:
        print(f"Success: {input_dir}")
        print("")
    processed_count += 1
    return True, input_dir


if __name__ == '__main__':
    cwd = os.getcwd()
    parser = ArgumentParser()
    parser.add_argument("-i", "--input", dest="input_dir", default=cwd, help="Path with DICOM files")
    parser.add_argument("-s", "--server", dest="server", default=None, required=True, help="Server address")
    parser.add_argument("-p", "--port", dest="port", default="11112", required=False, help="DICOM port server")
    parser.add_argument("-d", "--dataset", dest="dataset", default="push_dicom", required=False, help="Dataset name")
    parser.add_argument("-t", "--threads", dest="threads", default="3", required=False, help="Parallel threads to send the data.")
    parser.add_argument("-sp", "--scan-pattern", dest="scan_pattern", default="*.dcm", required=False, help="Scan pattern.")
    parser.add_argument("-max", "--max-series", dest="max_series", default="0", required=False, help="Max series count")

    args = parser.parse_args()
    input_dir = args.input_dir
    server = args.server
    dataset = args.dataset
    scan_pattern = args.scan_pattern
    threads = int(args.threads)
    port = int(args.port)
    max_series = int(args.max_series)

    processed_count = 0
    execution_timeout = 30

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

    print(f"# Found {len(dicom_dirs)} DICOM-dirs.")
    if max_series != 0 and len(dicom_dirs) > max_series:
        print(f"# Set series limit to max_series: {max_series} ...")
        dicom_dirs = dicom_dirs[:max_series]

    print(f"# Start sending {len(dicom_dirs)} DICOM-dirs with {threads} threads...")
    results = ThreadPool(threads).imap_unordered(send_dcm_dir, dicom_dirs)
    for result, input_dir in results:
        if result:
            print(f"# Dir ok: {input_dir}")
        else:
            print(f"# Issue with dir: {input_dir}")

        print("#")
        print("#")
        print(f"# Sent {processed_count} series!")
        print("#")
        print("#")
