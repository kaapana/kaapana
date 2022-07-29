.. _faq_extensions:

Failing to install an extension 
*******************************

Since we use deletion hooks for extension, there might be the problem that the helm release of the extension gets stuck in the uninstalling process. To check if this is the case or if the release is stuck in another stage, get a terminal on your server and execute

::

   helm ls --uninstalled
   helm ls --pending
   helm ls --failed

Then delete the resource with:

::

   helm uninstall <release-name>

If the resource is still there delete it with the ``no-hooks`` options:

::

   helm uninstall --no-hooks <release-name>
