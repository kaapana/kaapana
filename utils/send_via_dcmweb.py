"""
Script to send dicom-files to a kaapana platform using dicom web.
"""

import pydicom
import os
from argparse import ArgumentParser
from dicomweb_client.api import DICOMwebClient
import glob

def init(url, cert_file, ignore_ssl_verify):
    global client

    kaapana_url = url + "/dicomweb"
    client = DICOMwebClient(url=kaapana_url, ca_bundle=cert_file)
    if ignore_ssl_verify:
        print("Warning: You are disabling https verification!")
        client._session.verify = False


def uploadDicomObject(file_list):
    global client
    dicom_list = []
    file_count = 0
    for dicom_file in file_list:
        ds = pydicom.dcmread(dicom_file)
        file_count += 1
        print("File added to send list: %s" % dicom_file)
        dicom_list.append(ds)
    if file_count == 0:
        print("No corresponding dcm file found!")
        exit(1)
    print("Sending all %s files" % file_count)
    client.store_instances(dicom_list)
    print("DICOMweb send done.")
    return

if __name__ == '__main__':

    parser = ArgumentParser()
    parser.add_argument("-u", "--u", dest="url", default=None,
                        help="url of the kaapana instance (e.g. https://my-instance.org")
    parser.add_argument("-d", "--directory", dest="directory", default=None, help="crawl directory with dicom files.")
    parser.add_argument("-c", "--cert", dest="cert_file", default=None, help="Cert file, if needed.")
    parser.add_argument('-i', "--ignore-ssl-verify", dest='ignore_ssl_verify', default=False, help='Unverified HTTPS')

    args = parser.parse_args()
    url = args.url
    directory = args.directory
    cert_file = args.cert_file
    ignore_ssl_verify_str = args.ignore_ssl_verify
    ignore_ssl_verify = False
    if ignore_ssl_verify_str:
        val = str(ignore_ssl_verify_str).upper()
        if 'TRUE'.startswith(val):
            ignore_ssl_verify = True

    if not url:
        print("No kaapana url specified. -> exit ")
        exit(1)
    if not directory:
        print("No crawl directory specified.-> exit")
        exit(1)
    if not os.path.isdir(directory):
        print("No crawl directory specified.-> exit")
        exit(1)
    print("kappana url: ", url)

    print("crawl directory:", directory)

    file_list = glob.glob(os.path.join(directory, '**/*.dcm*'), recursive=True)
    init(url=url, cert_file=cert_file, ignore_ssl_verify=ignore_ssl_verify)
    uploadDicomObject(file_list)
