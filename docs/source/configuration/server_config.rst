.. _server_config:

Deployment Server Config
************************

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

    curl www.dkfz-heidelberg.de 

Should work -> network connection is working

SSL/TLS Certificates
--------------------

Custom DNS Server
-----------------

If your want to specify the DNS server, edit the netplan config:

| Open **/etc/netplan/00-installer-config.yaml** with vi/nano and edit as follows:

::
    # This is the network config written by 'subiquity'
    network:
      version: 2
      ethernets:
        eth0:
          addresses:
            - 192.168.0.4/24
          gateway4: 192.168.0.1
          nameservers:
            addresses: [4.4.4.4, 8.8.8.8] # add the nameserver IPs here
            
reload the config with

::

    sudo netplan apply
