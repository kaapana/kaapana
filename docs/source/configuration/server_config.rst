.. _server_config:

Server Config
=============

Proxy
-----

If you need to configure a proxy in your institution to access internet, you can do this as following:

| Open **/etc/environment** with vi insert:

| http\_proxy="your.proxy.url:port"
| https\_proxy="your.proxy.url:port"

| HTTP\_PROXY="your.proxy.url:port"
| HTTPS\_PROXY="your.proxy.url:port"

::

    logout

Login again

::

    ping www.dkfz-heidelberg.de 

Should work -> network connection is working

SSL/TLS Certificates
--------------------

Custom DNS Server
-----------------
