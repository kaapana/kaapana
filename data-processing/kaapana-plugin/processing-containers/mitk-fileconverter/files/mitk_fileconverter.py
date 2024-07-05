from os import getenv
from os.path import join, exists, dirname, basename
from glob import glob
import pydicom
from pathlib import Path

# For multiprocessing -> usually you should scale via multiple containers!
from multiprocessing.pool import ThreadPool

# For shell-execution
from subprocess import PIPE, run

execution_timeout = 1200

# Counter to check if smth has been processed
processed_count = 0

# Alternative Process smth via shell-command


def process_input_file(paras):
    global execution_timeout, input_file_extension, convert_to
    input_filepaths, element_output_dir = paras

    SeriesInstanceUIDs = []
    total = 0
    existing = 0
    converted = 0
    errors = 0

    for input_filepath in input_filepaths:
        ds = pydicom.dcmread(input_filepath, specific_tags=['SeriesInstanceUID'], stop_before_pixels=True)
        if ds.SeriesInstanceUID not in SeriesInstanceUIDs:
            SeriesInstanceUIDs.append(ds.SeriesInstanceUID)
            total += 1

            print('Found new SeriesInstanceUID: ' + ds.SeriesInstanceUID)

            output_filepath = join(element_output_dir, f"{ds.SeriesInstanceUID}.{convert_to}")

            if exists(output_filepath):
                print(f"# {basename(output_filepath)} already exists!")
                existing += 1
                continue

            command = [
                "/kaapana/app/MitkFileConverter.sh",
                "-i",
                input_filepath,
                "-o",
                output_filepath,
            ]
            output = run(
                command,
                stdout=PIPE,
                stderr=PIPE,
                universal_newlines=True,
                timeout=execution_timeout,
            )

            if output.returncode != 0:
                errors += 1
                print('##################  START ERROR MESSAGE ' + str(errors) + ' #######################')
                print('Error converting ' + ds.SeriesInstanceUID)
                print('Input file: ' + basename(input_filepath))
                print('Output file: ' + basename(output_filepath))
                print(f"Command:  {command}")
                print(output.stderr)
                print('################## END ERROR MESSAGE ' + str(errors) + ' #######################\n')
            else:
                print('Converted ' + ds.SeriesInstanceUID)
                converted += 1
    
    print('Total series: ' + str(total))
    print('Already existing nrrds: ' + str(existing))
    print('Converted series: ' + str(converted))
    print('Errors: ' + str(errors))

    return True, input_filepaths


workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
assert workflow_dir is not None

batch_name = getenv("BATCH_NAME", "None")
batch_name = batch_name if batch_name.lower() != "none" else None
assert batch_name is not None

operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
assert operator_in_dir is not None

operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
assert operator_out_dir is not None

parallel_processes = getenv("THREADS", "1")
parallel_processes = (
    int(parallel_processes) if parallel_processes.lower() != "none" else None
)
assert parallel_processes is not None

operator_out_dir = getenv("OPERATOR_OUT_DIR", "None")
operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
assert operator_out_dir is not None

input_file_extension = getenv("CONVERTFROM", "*.dcm")
input_file_extension = (
    input_file_extension if input_file_extension.lower() != "none" else None
)
assert input_file_extension is not None

convert_to = getenv("CONVERTTO", "None")
convert_to = convert_to if convert_to.lower() != "none" else None
assert convert_to is not None

issue = False

print("##################################################")
print("#")
print("# Starting FileConverter:")
print("#")
print(f"# workflow_dir:     {workflow_dir}")
print(f"# batch_name:       {batch_name}")
print(f"# operator_in_dir:  {operator_in_dir}")
print(f"# operator_out_dir: {operator_out_dir}")
print("#")
print(f"# convert_to:           {convert_to}")
print(f"# input_file_extension: {input_file_extension}")
print("#")
print(f"# parallel_processes: {parallel_processes}")
print("#")
print("##################################################")
print("#")
print("# Starting processing on BATCH-ELEMENT-level ...")
print("#")
print("##################################################")
print("#")

# Loop for every batch-element (usually series)
job_list = []
batch_folders = sorted([f for f in glob(join("/", workflow_dir, batch_name, "*"))])
for batch_element_dir in batch_folders:
    element_input_dir = join(batch_element_dir, operator_in_dir)
    element_output_dir = join(batch_element_dir, operator_out_dir)

    # check if input dir present
    if not exists(element_input_dir):
        print("#")
        print(f"# Input-dir: {element_input_dir} does not exists!")
        print("# -> skipping")
        print("#")
        continue

    # creating output dir
    Path(element_output_dir).mkdir(parents=True, exist_ok=True)

    # creating output dir
    input_files = glob(
        join(element_input_dir, f"*.{input_file_extension}"), recursive=True
    )
    job_list.append((input_files, element_output_dir))


print(f"# Processing batch-element jobs: {len(job_list)}")
with ThreadPool(parallel_processes) as threadpool:
    results = threadpool.imap_unordered(process_input_file, job_list)
    for result, input_file in results:
        if result:
            print("#")
            processed_count += 1
            print(f"# ✓ {processed_count} / {len(job_list)} successful")
            print("#")
        else:
            print("#")
            print("##################################################")
            print("#")
            print("#               ERROR!")
            print("#")
            print(f"# {basename(input_file[0])} was not successful")
            print("#")
            print("##################################################")
            print("#")
            issue = True


print("#")
print("##################################################")
print("#")
print("# BATCH-ELEMENT-level processing done.")
print("#")
print("##################################################")
print("#")

if processed_count == 0:
    job_list = []
    print("##################################################")
    print("#")
    print("# -> No files have been processed so far!")
    print("#")
    print("# Starting processing on BATCH-LEVEL ...")
    print("#")
    print("##################################################")
    print("#")

    batch_input_dir = join("/", workflow_dir, operator_in_dir)
    batch_output_dir = join("/", workflow_dir, operator_in_dir)

    # check if input dir present
    if not exists(batch_input_dir):
        print("#")
        print(f"# Input-dir: {batch_input_dir} does not exists!")
        print("# -> skipping")
        print("#")
    else:
        # creating output dir
        Path(batch_output_dir).mkdir(parents=True, exist_ok=True)

        # creating output dir
        dir_names = {}
        input_files = glob(
            join(element_input_dir, f"*.{input_file_extension}"), recursive=True
        )
        for file in input_files:
            input_dirname = dirname(file)
            if input_dirname not in dir_names.keys():
                dir_names[input_dirname] = []
            dir_names[input_dirname].append(file)

        for input_dir, file_list in dir_names.items():
            job_list.append(file_list, batch_output_dir)

        print(f"# Processing batch-element jobs: {len(job_list)}")
        with ThreadPool(parallel_processes) as threadpool:
            results = threadpool.imap_unordered(process_input_file, job_list)
            for result, input_file in results:
                if result:
                    print("#")
                    processed_count += 1
                    print(f"# {processed_count} / {len(job_list)} successful")
                    print("#")
                else:
                    print("#")
                    print("##################################################")
                    print("#")
                    print("#               ERROR!")
                    print("#")
                    print(f"# {basename(input_file[0])} was not successful")
                    print("#")
                    print("##################################################")
                    print("#")
                    issue = True

    print("#")
    print("##################################################")
    print("#")
    print("# BATCH-LEVEL-level processing done.")
    print("#")
    print("##################################################")
    print("#")

if issue:
    print("#")
    print("##################################################")
    print("#")
    print("# ✘ There have been issues...")
    print("#")
    print("##################################################")
    print("#")
    exit(1)

if processed_count == 0:
    print("#")
    print("##################################################")
    print("#")
    print("##################  ERROR  #######################")
    print("#")
    print("# ----> NO FILES HAVE BEEN PROCESSED!")
    print("#")
    print("##################################################")
    print("#")
    exit(1)
else:
    print("#")
    print(f"# ----> {processed_count} FILES HAVE BEEN PROCESSED!")
    print("#")
    print("# DONE #")
