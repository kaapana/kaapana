"""
Script to send dicom-files to a kaapana platform using dcmsend.
Prerequisites:
The script useres dcmtk dcmsend: https://support.dcmtk.org/docs-snapshot/dcmsend.html,
therefore the commandline tool dcmsend has to be installed to run the script.

"""
import os
from argparse import ArgumentParser
import subprocess
import glob


def dcmsend(ip, port, file_list, aet, aec):
    for dcmfile in file_list:
        bash_command = (
            "dcmsend -aec "
            + aec
            + " -aet "
            + aet
            + " -v "
            + ip
            + " "
            + port
            + " "
            + dcmfile
        )
        print("bashCommand: ", bash_command)
        process = subprocess.Popen(bash_command.split(), stderr=subprocess.PIPE)
        process.communicate()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-ip", "--ip", dest="ip", default=None, help="IP of the kaapana instance"
    )
    parser.add_argument(
        "-p",
        "--port",
        dest="port",
        default="11112",
        help="DICOM port of the kaapana instance",
    )
    parser.add_argument(
        "-d",
        "--directory",
        dest="directory",
        default=None,
        help="Crawl directory with dicom files",
    )
    parser.add_argument(
        "-aet",
        "--aetitle",
        dest="aet",
        default="DCMSEND",
        help=" Application Entity Title: set my calling AE title.",
    )
    parser.add_argument(
        "-aec", "--call", dest="aec", default="SEND", help="set called AE title of peer"
    )

    args = parser.parse_args()
    ip = args.ip
    port = args.port
    directory = args.directory
    aet = args.aet
    aec = args.aec

    if not ip:
        print("No IP of the kaapana instance specified. -> exit ")
        exit(1)
    if not directory:
        print("No crawl directory specified.-> exit")
        exit(1)
    if not os.path.isdir(directory):
        print("No crawl directory specified.-> exit")
        exit(1)
    print("kappana IP: ", ip)

    print("crawl directory:", directory)

    file_list = glob.glob(os.path.join(directory, "**/*.dcm*"), recursive=True)
    dcmsend(ip=ip, port=port, file_list=file_list, aet=aet, aec=aec)
