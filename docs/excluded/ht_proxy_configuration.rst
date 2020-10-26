.. _proxy_conf_doc:

Proxy configuration
===================

If you need to configure a proxy in your institution to access interent, you can do this as following:

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