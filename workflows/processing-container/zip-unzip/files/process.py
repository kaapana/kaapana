import sys
import os
import glob
import pathlib
import zipfile

processed_count = 0

def unzip_file(zip_path,target_path):
    global processed_count
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(target_path)
    processed_count += 1

def zip_dir(zip_dir_path, target_file):
    global processed_count
    
    print(f"# Zipping {zip_dir_path} --> {target_file}")

    zipf = zipfile.ZipFile(target_file, 'w', zipfile.ZIP_DEFLATED)
    whitelist_extensions=os.getenv("WHITELIST_EXTENSIONS","NONE").split(",")
    whitelist_extensions=None if whitelist_extensions[0] == "NONE" else whitelist_extensions
    blacklist_extensions=os.getenv("BLACKLIST_EXTENSIONS","NONE").split(",")
    blacklist_extensions=None if blacklist_extensions[0] == "NONE" else blacklist_extensions
    print("#")
    print(f"# whitelist_extensions: {whitelist_extensions}")
    print(f"# blacklist_extensions: {blacklist_extensions}")
    print("#")

    for root, dirs, files in os.walk(zip_dir_path):
        for file in files:
            skip_file = False
            present_extensions = "".join(pathlib.Path(file).suffixes).replace("*","").replace(".","")
            
            if blacklist_extensions != None: 
                for blacklist_extension in blacklist_extensions:
                    if blacklist_extension.replace("*","").replace(".","") in present_extensions:
                        skip_file=True
                        break

            if whitelist_extensions != None: 
                for whitelist_extension in whitelist_extensions:
                    if whitelist_extension.replace("*","").replace(".","") not in present_extensions:
                        skip_file=True
                        break
            
            if not skip_file:
                print(f"# zip: {file}")
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(zip_dir_path, '..')))
                processed_count += 1
            else:
                print(f"# skipping: {file}")
            
    print("#")
    print("# ZIPPING DONE")
    print("#")

    zipf.close()

if __name__ == '__main__':
    
    target_filename = os.getenv("TARGET_FILENAME","NONE")
    target_filename = None if target_filename == "NONE" else target_filename
    subdir = os.getenv("SUBDIR","NONE")
    subdir = "" if subdir == "NONE" else subdir
    mode=os.getenv("MODE","unzip").lower().strip()
    batch_level=True if os.getenv("BATCH_LEVEL","False").lower() == "true" else False

    print("##################################################")
    print("#")
    print("# Starting ZIP-UNZIP ...")
    print("#")
    print(f"# mode:        {mode}")
    print(f"# batch_level: {batch_level}")
    print("#")
    
    batch_folders = [f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))]
    
    if mode == "zip":
        print(f"# target_filename: {target_filename}")

        if not batch_level:
            for batch_element_dir in batch_folders:
                target_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_OUT_DIR'])
                pathlib.Path(target_dir).mkdir(parents=True, exist_ok=True)
                zip_target = os.path.join(target_dir,target_filename)
                zip_dir_path = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'],subdir)
                zip_dir(zip_dir_path=zip_dir_path,target_file=zip_target)

        else:
            target_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_OUT_DIR'])
            pathlib.Path(target_dir).mkdir(parents=True, exist_ok=True)
            zip_target = os.path.join(target_dir,target_filename)
            
            zip_dir_path = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'],subdir)
            zip_dir(zip_dir_path=zip_dir_path,target_file=zip_target)


    elif mode == "upzip":
        if not batch_level:
            for batch_element_dir in batch_folders:
                element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
                element_output_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_OUT_DIR'])
                pathlib.Path(element_output_dir).mkdir(parents=True, exist_ok=True)

                zip_files = glob.glob(os.path.join(element_input_dir,"*.zip"), recursive=True)
                for zip_file in zip_files:
                    unzip_file(zip_path=zip_file,target_path=element_output_dir)

        else:
            batch_input_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])
            batch_output_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_OUT_DIR'])
            pathlib.Path(batch_output_dir).mkdir(parents=True, exist_ok=True)

            zip_files = glob.glob(os.path.join(batch_input_dir,"*.zip"), recursive=True)
            for zip_file in zip_files:
                unzip_file(zip_path=zip_file,target_path=batch_output_dir)
    
    else:
        print("##################################################")
        print("#")
        print(f"# MODE: {mode} is not supported.")
        print("# ABORT")
        print("#")
        print("##################################################")
        exit(1)

if processed_count == 0:
    print("#")
    print("##################################################")
    print("#")
    print("#################  ERROR  #######################")
    print("#")
    print("# ----> NO FILES HAVE BEEN PROCESSED!")
    print("#")
    print("##################################################")
    print("#")
    exit(1)

