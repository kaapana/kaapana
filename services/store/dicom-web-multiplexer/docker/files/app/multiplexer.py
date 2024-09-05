def decide_pacs(dicom_tag):
    if dicom_tag.startswith("local"):
        return "http://local-pacs/dicomweb"
    elif dicom_tag.startswith("gcp"):
        return "https://gcp-dicomstore-url/dicomweb"
    # Add more PACS selection logic as needed
    return "default-pacs-url"
