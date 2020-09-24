= Clinical trial processor service =

This image provides a dockerized clinical trial processor (CTP). It listens on a port and writes incoming DICOM files to disk.

== Building ==

You need to have an installed CTP directory on the same level as the Dockerfile. The CTP installer needs an existing X-server, which the docker image does not provide.

== Running it in the background ==

`docker run -d -v /host/data/out:/data/incoming -p 10001:10000 -p 10002:1080 ctp`
