.. _too_many_files_open:

Operator fails, because too many open files
********************************************

If an operator fails and the operator logs show the following message,

.. code-block:: 

    failed to create fsnotify watcher: too many open files

it is possible that the maximum number of allowed inotify watchers on the host machine is set to low.
To check this number run the command :code:`cat /proc/sys/fs/inotify/max_user_instances` on the host machine of your instance.
To resolve this issue, execute the following two commands on your host machine:

.. code-block:: 

    sysctl -w fs.inotify.max_user_watches=10000
    sysctl -w fs.inotify.max_user_instances=10000
