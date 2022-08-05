How to install TLS certificates
*******************************

When no tls certificates are provided the platform will create a self-signed TLS certificate on its first start. This self-signed certificates lead to security warnings in the browsers when accessing the web interface of the platform.

To overcome this warnings in a productive system, the platform provides capabilities to exchange the self-signed certificates with valid ones:

1. Rename the certificate and key file to :code:`tls.crt` and :code:`tls.key` and place it in the same folder the `install_platform.sh` script is located.
2. Run :code:`./install_platform.sh --install-certs`
3. *Optional:* To make the installed certificates outlast redeployments of the platform, place :code:`tls.crt` and :code:`tls.key` in :code:`$FAST_DATA_DIR/tls` (the value of FAST_DATA_DIR is set in the `install_platform.sh` script)

This procedure will also restart the pods of the platform related for TLS and the new certificate will be used for any subsequent https requests.

