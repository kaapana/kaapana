.. _how_to_install_tls_certificates:

How to install TLS certificates
*******************************

Without a certificate of its own, the platform makes a new self-signed TLS certificate on every deploy. Browsers show a security warning for it. To use a valid certificate instead:

1. Rename the certificate file to :code:`tls.crt` and the key file to :code:`tls.key`, and put both in the directory of the :term:`kaapanactl.sh<kaapanactl>` script.
2. In that directory, run :code:`sudo ./kaapanactl.sh --install-certs`.

The command replaces the certificate of the running platform and restarts the pods that use it.

Where the certificate is stored
-------------------------------

On microk8s hostpath storage (the single-node default, see :ref:`kaapana_storage`), the command also copies both files into the host folder of the TLS volume (claim :code:`tls-pv-claim` in the :code:`admin` namespace) and prints that folder. It is in the fast data directory and named :code:`admin-tls-pv-claim-pvc-<id>`. Every deploy installs the certificate from there, so it outlasts redeployments.

On other storage, such as Longhorn, the volume has no host folder. The command prints a warning, and the certificate lasts only until the next undeploy. After every redeploy, run step 2 again.

The command also copies the files to :code:`$FAST_DATA_DIR/tls`, with the :code:`FAST_DATA_DIR` set in :code:`kaapanactl.sh`. The deploy does not read that copy.

After a hostname change
-----------------------

The next deploy installs the stored certificate under the new hostname. If it does not cover the new name, browsers reject it. Install a certificate for the new name with the steps above.

Going back to the self-signed certificate
-----------------------------------------

1. Delete :code:`tls.crt` and :code:`tls.key` from the TLS volume folder.
2. Redeploy the platform: run :code:`./kaapanactl.sh deploy --undeploy`, then :code:`./kaapanactl.sh deploy`.

The deploy then makes a new self-signed certificate.
