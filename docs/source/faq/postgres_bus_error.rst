.. _postgres_bus_error:

Postgres container fails with "child process was terminated by signal 7: Bus error"
***********************************************************************************

On systems with hugepages enabled postgres containers run in a kubernetes cluster might fail with

::

    child process was terminated by signal 7: Bus error or something similar.

To check if hugepages are enabled run:
::

    cat /proc/sys/vm/nr_hugepages

If this returns a number greater than 0 hugepages are enabled. If possible one can disable hugepages as a workaround. 

::

    sudo sysctl -w vm.nr_hugepages=0

To make this change persistent add:

::

    vm.nr_hugepages = 0

to :code:`/etc/sysctl.conf`.