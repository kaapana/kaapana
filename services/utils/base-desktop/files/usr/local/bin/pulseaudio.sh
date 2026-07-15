#!/bin/sh

# PulseAudio for Selkies audio. The container has no sound hardware, so create a virtual
# null sink named "output"; its ".monitor" source is what pcmflux captures (Selkies'
# audio_device_name defaults to "output.monitor"). Start with -n (no autodetect) and load
# only what we need to keep container logs clean.
exec pulseaudio \
    --exit-idle-time=-1 \
    --disable-shm=true \
    -n \
    --load="module-native-protocol-unix" \
    --load="module-null-sink sink_name=output sink_properties=device.description=Selkies_Output" \
    --load="module-always-sink"
