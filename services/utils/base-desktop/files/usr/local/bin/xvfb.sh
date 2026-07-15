#!/bin/sh

# Large virtual screen + RANDR so Selkies can set the display resolution to match the
# client's browser window live (replaces the old one-shot resize backend). The framebuffer
# size is the max RANDR mode; sized generously to cover hi-DPI/retina windows (devicePixelRatio 2).
exec /usr/bin/Xvfb :1 -screen 0 5120x2880x24 +extension RANDR -noreset
