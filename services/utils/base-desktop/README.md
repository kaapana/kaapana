# Desktop Base Container

## How to start your own applications
- Create a `supervisord.conf` file for your app (e.g. `supervisord-myapp.conf` - dont overwrite the `supervisord.conf` already present) and place it in `/etc/supervisor/conf.d` (see slicer example below).
- A default user is configured and available in the `$USER` variable
- Don't overwrite the entrypoint, during startup supervisor will be started which then launches your app according to the provided conf

Example from supervisor-slicer:
```
[program:slicer]
priority=50
process_name=Slicer
command=x-terminal-emulator -e "/opt/slicer/Slicer"
user=%USER%
environment=DISPLAY=":1",HOME="%HOME%",USER="%USER%"
```

## How does it work
On a blank container a virtual framebuffer `xvfb` is installed. When the container is started (e.g. `files/startup.sh`) `supervisord` is run to run a collection of tools:
- nginx: Reverse Proxy uniying different services and delivering the static fiels for novnc
- backend: resizing of xvfb (currently no server side resizing is implemented in x11vnc this is why this workaround is done)

## Run this localy
- Build:
- Run: `docker run -p 6080:80 -p 5900:5900 local-only/base-desktop:latest``
- Connect via VNC using port 5900
- Connect via HTTP VNC Client using port 6080

## Sources
- https://github.com/novnc/websockify
- https://github.com/novnc/noVNC
- https://github.com/Tiryoh/docker-ubuntu-vnc-desktop


