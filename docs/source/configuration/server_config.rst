.. _server_config:

Deployment Server Config
************************

Proxy
-----

If you need to configure a proxy in your institution to access the internet, you can do this as follows:

#. Open **/etc/environment** on your deployment server:

    :code:`nano /etc/environment`

#. Insert the proxy variables for the proxy in your institution

    :: 

        http_proxy="your.proxy.url:port"
        https_proxy="your.proxy.url:port"
        HTTP_PROXY="your.proxy.url:port"
        HTTPS_PROXY="your.proxy.url:port"


#. Logout :code:`logout` and login again


#. Your network connection is working if you can reach the dkfz website or any other website:

    :code:`curl www.dkfz-heidelberg.de`

.. SSL/TLS Certificates
.. --------------------

Custom DNS Server
-----------------

    You can configure a custom DNS :code:`my.custom.dns` by executing:

    :code:`sed -i 's/DNS=""/DNS="my.custom.dns"/' ./kaapana/server-installation/server_installation.sh`
    
    If not set manually, the DNS will be configured according to system information.