Microk8s GPU issues
**********************

This error occurs with specific GPU drivers in Almalinux, 
when the microk8s GPU is enabled. If pods in ``gpu-operator-resource`` namespace
have error (``kubectl describe -n <namespace> <pod>``): 

``/sbin/ldconfig.real was not found``,

then follow these steps to fix this issue:

1. Run ``nvidia-smi`` and assure that GPU drivers are correctly installed.
2. Check if ``/sbin/ldconfig`` file has been created. (drivers are correctly installed)
3. Create a symbolic link:
   
   ``sudo ln -s /sbin/ldconfig /sbin/ldconfig.real``

4. Restart system: ``microk8s disable gpu`` and afterwards: ``microk8s enable gpu``

