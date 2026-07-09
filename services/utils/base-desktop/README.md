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
A virtual framebuffer `xvfb` (display `:1`) hosts the desktop. When the container starts
(`files/startup.sh`) `supervisord` launches:
- `xvfb` / `wm` (openbox) / `tint2` / `pcmanfm`: the X server + LXDE desktop (all as `%USER%`)
- `pulseaudio`: virtual audio sink for Selkies audio
- `selkies`: streams display `:1` as H.264/JPEG stripes over a single WebSocket
  ([Selkies](https://github.com/selkies-project/selkies) v2 / `pixelflux`, decoded in-browser
  via WebCodecs). Native RANDR resize — no server-side resize workaround needed. The encoder is
  chosen per launch by `startup.sh`: hardware full-frame H.264 (NVENC) when the container has an
  NVENC-capable GPU, otherwise the CPU striped encoder (only changed stripes — cheap on CPU).
- `nginx`: serves the prebuilt Selkies web client and proxies the `.../websockets` upgrade to
  the Selkies server (`:8082`); handles the ingress sub-path (`INGRESS_PATH`) and optional
  HTTP basic auth (`HTTP_PASSWORD`).

The Selkies server and web client are pinned to a single upstream commit (`SELKIES_COMMIT`):
the server is pip-installed from it and the web dashboard SPA is built from source from the same
commit in a `selkies-frontend` builder stage. The dashboard is not part of the pip package and
has no release artifact, so it must be built with npm/Vite (this mirrors the LinuxServer selkies
build; we previously copied their prebuilt dashboard by digest instead of building it ourselves).

Note: WebCodecs require a **secure context** — the browser must reach the page over HTTPS or
via `localhost` (in the platform this is provided by the HTTPS ingress).

## Run this locally
- Build: `docker build -t local-only/base-desktop:latest .`
- Run: `docker run -p 8080:80 local-only/base-desktop:latest`
- Open `http://localhost:8080/` (use `localhost`, or an SSH tunnel to it, so the browser has a
  secure context for WebCodecs).

## Sources
- https://github.com/selkies-project/selkies
- https://github.com/linuxserver/docker-baseimage-selkies


