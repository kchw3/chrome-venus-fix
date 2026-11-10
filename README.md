# Google Chrome hardware video decoding on Qualcomm Venus

Reproducible Linux setup for Google Chrome (`/opt/google/chrome/chrome`) on
Qualcomm systems exposing the **stateful** `qcom-venus` V4L2 decoder.
This is an experimental integration, tested on QCS6490, AArch64 Linux 6.18,
Mesa 26, libva 2.23, and Google Chrome 157 on a Wayland desktop.
Other chips, kernels, codecs, and browser versions require validation.

## Problem and fix

Chrome probes VA-API, while Venus exposes a separate V4L2 video decoder.
Installing generic Mesa VA drivers does not provide the missing Venus bridge.
This setup builds [venus-vaapi-driver](https://github.com/snowf14k3/venus-vaapi-driver)
at revision `37e1030aba11f66e303e4f5fb0c3a13e2a78265e` and applies
[the H.264 display-delay patch](patches/h264-display-delay.patch).
The unpatched bridge initialized but timed out retrieving H.264 frames;
enabling the hardware's zero-display-delay control for H.264 fixed that test.

The YouTube-only Manifest V3 extension excludes AV1 from media capability
queries so YouTube can choose VP9/H.264, which the tested hardware supports.
It has no background worker, telemetry, storage permission, or outbound requests.
It changes page media capability APIs only on the domains in its manifest.
It does not add AV1 hardware support, and cannot guarantee a site's codec choice.

## Install

Prerequisites: Debian/Ubuntu-family Linux with systemd, Google Chrome installed
at the path above, a working Wayland session, `/dev/dri/renderD128`, and a working
`qcom-venus` decoder. Users need access to the GPU and video nodes through their
active desktop session ACLs or appropriate groups. This installer does not change
device permissions, kernel modules, firmware, or group membership.

```sh
sudo python3 scripts/install.py
```

The installer refreshes package indexes and installs build dependencies. Use
`--skip-apt` when they are already present. It builds the pinned upstream source,
preserves an original backup of overwritten files under `/var/lib/chrome-venus/backups`,
installs the driver and launchers, signs the extension with a host-local key,
and enables a loopback-only extension update service. The first run requires
internet access for dependencies and source; extension installation thereafter
does not require an external server.

Restart Chrome and launch **Google Chrome from the desktop menu**, or run
`google-chrome-venus`. The launcher uses the actual Google Chrome ELF executable.
Direct execution of `/opt/google/chrome/chrome` bypasses the wrapper and its flags.
No running browser is terminated by the installer. New launches can be forwarded
to an existing browser, so closing all Chrome windows before relaunching matters.

The launcher currently targets Wayland and uses ANGLE/GLES. It enables the Linux
GL video path, ignores Chrome driver checks and the GPU blocklist, and selects the
Venus driver for that browser only. It does not disable the browser sandbox.
The offline root packaging command uses `--no-sandbox`; that flag is not installed
in any user browser launcher.

## All users and default profiles

The setup uses machine policy, not a copied browser profile:

| Item | Installed location |
|---|---|
| Shared driver | `/usr/local/lib/chrome-venus/dri/venus_drv_video.so` |
| Shared extension source | `/usr/local/share/chrome-venus/extension/` |
| Signed extension + update manifest | `/usr/local/share/chrome-venus/web/` |
| Command launchers | `/usr/local/bin/google-chrome{,-stable,-venus}` |
| Global desktop entry | `/usr/local/share/applications/google-chrome.desktop` |
| Current desktop users | `~/.local/share/applications/google-chrome.desktop`, `~/.local/bin/google-chrome-venus` |
| New Unix users | Equivalent entries in `/etc/skel/.local/` |
| Every Chrome profile | `/etc/opt/chrome/policies/managed/chrome-venus.json` |
| Update service | `/etc/systemd/system/chrome-venus-extension.service` |
| Private signing key | `/var/lib/chrome-venus/extension-signing.pem` (root only) |

Chrome's `ExtensionSettings` policy force-installs the signed codec extension in
existing and new browser profiles, including the profile named `Default`.
No history, cookies, passwords, preferences, or browser profile template is copied.
The installer aborts if another policy file defines `ExtensionSettings`, so an
administrator can merge the dictionaries deliberately rather than lose policy.
Existing unrelated machine policy files are left in place.

The systemd server binds only `127.0.0.1:18765`, serves only two public artifacts,
and drops request logs. It starts at boot and runs as a dynamic unprivileged user.
The driver, launchers, policy, and extension survive reboot. A changed extension
version requires repacking with the same private key. Keep that key in a private
backup; never publish it. Each independent installation generates its own key/ID.

References: [Chrome Linux self-hosting](https://developer.chrome.com/docs/extensions/how-to/distribute/host-on-linux),
[extension installation policy](https://chromeenterprise.google/policies/#ExtensionSettings),
[alternative Linux installation](https://developer.chrome.com/docs/extensions/how-to/distribute/install-extensions).

## Verify

Run as the desktop user:

```sh
sh scripts/check.sh
```

Check `chrome://policy` for `ExtensionSettings` without errors and
`chrome://extensions` for **YouTube codecs for Qualcomm Venus**.
Play YouTube, then inspect that player in `chrome://media-internals`:

```text
kVideoDecoderName: VaapiVideoDecoder
kIsPlatformVideoDecoder: true
```

YouTube's Stats for nerds should show `vp09` or `avc1`, rather than `av01`.
The generic `chrome://gpu` status and CDP `SystemInfo.videoDecoding` list were
insufficient in testing: the latter stayed empty even during successful hardware
playback. Prefer the actual player's decoder, frame output, and VA-API trace.

For a local H.264/VP9 sample (install FFmpeg separately):

```sh
LIBVA_DRIVER_NAME=venus \
LIBVA_DRIVERS_PATH=/usr/local/lib/chrome-venus/dri \
ffmpeg -hide_banner -hwaccel vaapi -hwaccel_device /dev/dri/renderD128 \
  -hwaccel_output_format vaapi -i /path/to/sample.mp4 -t 10 -an \
  -vf 'hwdownload,format=nv12' -f null -
```

Validation before host-wide deployment: native V4L2 H.264 output 90 frames;
patched VA-API H.264 output 300 frames with frame checksums identical to software;
VP9 output 90 frames; Google Chrome completed H.264 playback and selected
`VaapiVideoDecoder` for a real YouTube VP9 stream. These results do not establish
all codec profiles, resolutions, seeking, concurrent streams, or future versions.

Host-wide deployment was additionally checked with a new Chrome profile: the
signed extension installed automatically from machine policy, and YouTube then
selected `VaapiVideoDecoder` without CDP capability overrides or manual extension
loading. This verifies the installed package rather than only the earlier prototype.

## Roll back

Close Chrome. Remove the dedicated policy, disable the dedicated service, remove
the installed desktop/command overrides, and restore any originals from
`/var/lib/chrome-venus/backups`. Remove matching entries from existing users and
`/etc/skel` or restore their backups. Start Chrome through its vendor launcher
`/usr/bin/google-chrome-stable`. Retain the private key if you may reinstall.
Removing only the dedicated machine policy allows users to remove the extension.
Do not remove unrelated Chrome policies or browser profiles. Build dependencies
can remain installed; avoid uninstalling libraries needed by other applications.

## Public repository hygiene

Only source, scripts, the patch, and sanitized documentation are tracked.
`.gitignore` excludes build outputs, keys, binaries, logs, media, and archives.
There are no hostnames, usernames, IPs other than loopback, Tailscale data,
browser exports, signing keys, or Git remotes embedded in this project.
Localhost/standard system paths and upstream revision IDs are intentional.

Before publishing, review `git status --short` and `git ls-files`; never add
`/var/lib/chrome-venus`, installed browser profiles, raw diagnostics, or backups.
Use a privacy-safe Git author identity. This repository vendors no upstream
driver source or binary; the fetched upstream retains its own MIT license.
Project source is MIT licensed; see [LICENSE](LICENSE).
