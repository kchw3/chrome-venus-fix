#!/bin/sh
set -eu
echo 'Google Chrome executable:'
readlink -f /opt/google/chrome/chrome
echo 'Driver capabilities:'
LIBVA_DRIVER_NAME=venus LIBVA_DRIVERS_PATH=/usr/local/lib/chrome-venus/dri \
  vainfo --display drm --device /dev/dri/renderD128
echo 'Extension update service:'
systemctl is-active chrome-venus-extension.service
curl --fail --silent http://127.0.0.1:18765/updates.xml
echo
echo 'Verify the player in chrome://media-internals: VaapiVideoDecoder and kIsPlatformVideoDecoder=true.'
