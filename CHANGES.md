# Sanitized host change inventory

## Earlier diagnosis and per-user fix

- Read OS, kernel, device ACLs, graphics details, package metadata, browser process
  paths, journal messages, and saved GPU reports. No firmware, kernel, group,
  device permission, or browser executable changes were made.
- Refreshed APT indexes after stale Armbian download URLs returned HTTP 404.
  Installed Meson, Ninja, libva/libdrm development headers, vainfo, and strace,
  plus package dependencies (Wayland headers/tools, PCI access headers, and
  available libdrm components). FFmpeg was used for local decode tests; it was
  installed/present when the sample tests were run.
- Cloned the Venus VA-API driver into a temporary working directory, built it,
  and patched H.264 display-delay handling. Upstream is pinned in the installer.
- Created isolated browser test profiles, local media samples, temporary CDP
  diagnostic scripts, VA-API traces, package logs, and decoded-frame checksums.
  An early comparison used Chromium; later validation used Google Chrome's
  `/opt/google/chrome/chrome` executable exclusively. Diagnostic files are not
  included in this repository.
- Installed a per-user driver, source snapshot, codec extension source, wrapper,
  and desktop entry under one desktop user's `.local/` tree. Saved validation
  notes and logs under that user's home. No normal Chrome profile was copied,
  edited offline, or terminated.
- Verified H.264 frames match software and that Chrome/YouTube use VA-API when
  the stream is H.264 or VP9. Used CDP page injection in an isolated test profile
  to prove AV1 exclusion works before packaging the extension.

## Host-wide deployment in this repository

- Rebuild the driver with the one-condition H.264 patch and install it into a
  root-owned shared directory. Preserve existing overwritten files privately.
- Install shared extension source plus a locally signed CRX and update manifest.
  Keep the signing private key outside the repository, readable only by root.
- Add the dedicated loopback systemd extension update service and Chrome machine
  `ExtensionSettings` policy for all existing/future browser profiles.
- Add global launchers and desktop entry; update existing desktop users and
  `/etc/skel` so new Unix accounts receive the launcher. Do not copy a Chrome
  profile, history, cookies, or credentials into defaults.
- Redirect the earlier per-user driver/extension file paths to shared files so
  an already loaded unpacked extension can continue reading the shared source.
- Keep unrelated policy and vendor executables intact. All persistent paths and
  rollback guidance are in README.md. Earlier private diagnostic artifacts are
  deliberately excluded from the public repository, not exported or published.
- Verified automatic extension installation in a fresh browser profile and a
  second Unix desktop account. Verified YouTube uses the shared setup's hardware
  decoder without diagnostic page injection. Repeated installation successfully
  with the same signing identity; confirmed the service is enabled at boot.
- Created a sanitized local Git repository and source package. Closed only
  diagnostic browser instances created during this work; normal browser
  sessions were left alone and use the wrapper after a normal restart.

Actual package transactions and private backups remain local to the installed
host. This inventory deliberately omits account names and machine identifiers.
