How to backup a Kaapana instance
===================================
In case of platform related system failures, you might have to uninstall the platform. If you have important data/code already in the platform, then in such cases it is best to take a backup of your data before uninstalling the platform. The platform data is stored in stateful directories on your host filesystem.


Data storage in the Kaapana platform
------------------------------------
In the default configuration there are two locations on the filesystem, which will be used for stateful data on the host machine:

#. ``fast_data_dir=/home/kaapana``: Location of (application) data that do not take a lot of space and should be loaded fast. Preferably, an SSD is mounted here.

#. ``slow_data_dir=/home/kaapana``:  Location of huge files, like images or our object store is located here.  Preferably, an HDD is mounted here.

They can be adjusted in the :term:`deploy-platform-script` and can also be identical (everything is stored at one place).

Some details about the data directories are described below:

- **dcm4che**: consists mainly of DICOM data
- **minio**: consists mainly of buckets such as ``uploads`` etc.
- **workflows**: the ``dags`` folder inside this folder consists of the code of the workflows, e.g. your workflows that were added via VSCode extension will also be found here. ``data`` folder consists of data that was created as a result of running workflows. ``models`` folder consists of the trained models, if any. 

Depending on how you assigned your data directories, you can check for the above folders and create a backup of your platform data.


Data backup options
-----------------------------------

There are several ways in which you can take a backup of your data, you can either copy the necessary folders to another folder on the same host or to a remote host. Following are just some of the various options:

- **rsync**: we can recommend using the command line tool ``rsync``. With this, you can (incrementally) create a backup of your data, e.g. by doing the following:

::

    rsync -a /<source_dir>/ /<destination_directory>

- **scp**: secure copy is another command line tool to copy data between hosts via SSH. Unlike ``rcp``, which accomplishes similar task, ``scp`` will ask for passwords or passphrases if they are needed for authentication.
- **UI based tools**: if you prefer UI based tools, then there are also tools like `WinSCP <https://winscp.net/eng/download.php>`_, `FileZilla <https://filezilla-project.org/>`_ and `Cyberduck <https://cyberduck.io/>`_ that are freely available. These would allow you to copy/backup your data safely via different protocols such as FTP, SFTP, SSH, Amazon S3 etc.
