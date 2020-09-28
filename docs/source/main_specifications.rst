.. _specs_doc:

Default Configuration
#####################

Default credentials
-------------------

**Main JIP Login:**
  | username: kaapana
  | password: kaapana

**Keycloak Usermanagement Administrator:**
  | username: jipadmin
  | password: DKjipTK

**Minio:**
  | username: jipadmin
  | password: DKjipTK2019

Dicom Receiver Specs
--------------------
To register the dicom receiver within your local clinic pacs, you should ask your local IT department. 
They will need the some information about the system:

  | address:  the IP address or domain of the server
  | port:     11112 
  | AE-title: JIP

The selection of the AE-title has a special meaning.
The system can filter data by this AE-title and mark it as seperate datasets.
This is especially important when it comes to different trails.
You can setup multiple dicom receivers in your pacs with different AE-titles.
This way it will be easy to mark images for a special collection on the platform.



After that you can send images to the server via the normal pacs interface.

Port Configuration
------------------
In the default configuration only four ports are open on the server:

1. Port  **80**:   Redirects to https port 443

2. Port **443**:   Main https communication with the server

3. Port **11112**: DICOM receiver port, which should be used as DICOM node in your pacs

4. Port **6443**:  Kubernetes API port -> used for external kubectl communication and secured via the certificate



Filesystem directories
----------------------
In the default configuration there are two locations on the filesystem:

1. **/home/kaapana/** SSD is mounted here and all persistant data from the platform is saved here

2. **/mnt/dicom/**     HDD is mounted here and all received dicom files are stored here
