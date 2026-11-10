#!/usr/bin/env python3
"""Build and deploy a host-wide Chrome/Venus fix. Run with sudo."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess

REPO = Path(__file__).resolve().parents[1]
UPSTREAM = "https://github.com/snowf14k3/venus-vaapi-driver.git"
REVISION = "37e1030aba11f66e303e4f5fb0c3a13e2a78265e"
STATE = Path("/var/lib/chrome-venus")
SHARE = Path("/usr/local/share/chrome-venus")
MANAGED = Path("/etc/opt/chrome/policies/managed")
POLICY = MANAGED / "chrome-venus.json"
URL = "http://127.0.0.1:18765/updates.xml"


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def backup(path):
    target = STATE / "backups" / path.relative_to("/")
    absent = target.with_name(target.name + ".absent")
    if target.exists() or absent.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not path.is_dir():
        shutil.copy2(path, target)
    else:
        absent.touch(mode=0o600)


def write(path, content, mode=0o644, owner=None):
    path = Path(path)
    backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(mode)
    if owner:
        os.chown(path, *owner)


def desktop(content):
    return re.sub(r"(?m)^Exec=(?:/usr/bin/google-chrome(?:-stable)?|/opt/google/chrome/(?:google-chrome|chrome)|/home/[^/]+/\.local/bin/google-chrome-venus)(?=\s|$)",
                  "Exec=/usr/local/bin/google-chrome-venus", content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-apt", action="store_true", help="Dependencies already installed")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("Run with sudo python3 scripts/install.py")
    if not Path("/opt/google/chrome/chrome").is_file():
        raise SystemExit("Google Chrome /opt/google/chrome/chrome is required")
    STATE.mkdir(parents=True, exist_ok=True)
    STATE.chmod(0o700)
    for policy in MANAGED.glob("*.json"):
        if policy != POLICY and "ExtensionSettings" in json.loads(policy.read_text()):
            raise SystemExit("Existing ExtensionSettings policy detected; merge policies before installing")
    if not args.skip_apt:
        run("apt-get", "update")
        run("apt-get", "install", "-y", "--no-install-recommends", "build-essential", "git", "meson", "ninja-build", "pkg-config", "libva-dev", "libdrm-dev", "vainfo", "openssl", "python3")
    build = REPO / "build"
    build.mkdir(exist_ok=True)
    source = build / "venus-vaapi-driver"
    if not source.exists():
        run("git", "clone", UPSTREAM, str(source))
    actual = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if actual != REVISION:
        if subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True).strip():
            raise SystemExit("Existing build source has local changes at a different revision")
        run("git", "-C", str(source), "checkout", "--detach", REVISION)
    patch = str(REPO / "patches/h264-display-delay.patch")
    applied = subprocess.run(["git", "-C", str(source), "apply", "--reverse", "--check", patch], capture_output=True).returncode == 0
    if not applied:
        run("git", "-C", str(source), "apply", "--check", patch)
        run("git", "-C", str(source), "apply", patch)
    out = build / "driver"
    if not (out / "build.ninja").exists():
        run("meson", "setup", str(out), str(source), "--buildtype=release")
    run("meson", "compile", "-C", str(out))
    driver = Path("/usr/local/lib/chrome-venus/dri/venus_drv_video.so")
    driver.parent.mkdir(parents=True, exist_ok=True)
    backup(driver)
    shutil.copy2(out / driver.name, driver)
    driver.chmod(0o755)
    SHARE.mkdir(parents=True, exist_ok=True)
    shutil.copytree(REPO / "extension", SHARE / "extension", dirs_exist_ok=True)
    pack = build / "extension"
    shutil.copytree(REPO / "extension", pack, dirs_exist_ok=True)
    manifest = json.loads((pack / "manifest.json").read_text())
    manifest["update_url"] = URL
    (pack / "manifest.json").write_text(json.dumps(manifest, indent=2))
    key = STATE / "extension-signing.pem"
    if not key.exists():
        run("openssl", "genrsa", "-out", str(key), "2048")
    key.chmod(0o600)
    # --no-sandbox applies only to this root-owned offline packaging process.
    # Normal browser launches retain their sandbox.
    run("/opt/google/chrome/chrome", "--headless", "--no-sandbox", "--no-message-box", "--user-data-dir=" + str(build / "pack-profile"),
        "--pack-extension=" + str(pack), "--pack-extension-key=" + str(key))
    public = subprocess.check_output(["openssl", "rsa", "-in", str(key), "-pubout", "-outform", "DER"], stderr=subprocess.DEVNULL)
    extension_id = "".join(chr(ord("a") + int(n, 16)) for n in hashlib.sha256(public).hexdigest()[:32])
    web = SHARE / "web"
    web.mkdir(exist_ok=True)
    shutil.copy2(build / "extension.crx", web / "youtube-codecs.crx")
    (web / "youtube-codecs.crx").chmod(0o644)
    write(web / "updates.xml", '<?xml version="1.0"?><gupdate xmlns="http://www.google.com/update2/response" protocol="2.0"><app appid="' + extension_id + '"><updatecheck codebase="http://127.0.0.1:18765/youtube-codecs.crx" version="' + manifest["version"] + '"/></app></gupdate>\n')
    write(SHARE / "extension-server.py", (REPO / "scripts/extension-server.py").read_text())
    write("/etc/systemd/system/chrome-venus-extension.service", (REPO / "systemd/chrome-venus-extension.service").read_text())
    run("systemctl", "daemon-reload")
    run("systemctl", "enable", "--now", "chrome-venus-extension.service")
    run("systemctl", "restart", "chrome-venus-extension.service")
    # Machine policy covers every existing and future Chrome browser profile.
    write(POLICY, json.dumps({"ExtensionSettings": {extension_id: {
        "installation_mode": "force_installed", "update_url": URL, "override_update_url": True
    }}}, indent=2) + "\n")
    wrapper = (REPO / "scripts/google-chrome-venus").read_text()
    for name in ["google-chrome-venus", "google-chrome", "google-chrome-stable"]:
        write(Path("/usr/local/bin") / name, wrapper, 0o755)
    template = Path("/usr/share/applications/google-chrome.desktop").read_text()
    write("/usr/local/share/applications/google-chrome.desktop", desktop(template))
    homes = [(Path(u.pw_dir), (u.pw_uid, u.pw_gid)) for u in pwd.getpwall()
             if 1000 <= u.pw_uid < 65534 and Path(u.pw_dir).is_dir()
             and not u.pw_shell.endswith(("nologin", "false"))]
    homes.append((Path("/etc/skel"), (0, 0)))
    for home, owner in homes:
        local = home / ".local"
        for folder in [local, local / "bin", local / "share", local / "share/applications"]:
            if not folder.exists():
                folder.mkdir(parents=True, exist_ok=True)
                os.chown(folder, *owner)
        app = local / "share/applications/google-chrome.desktop"
        content = app.read_text() if app.exists() else template
        write(app, desktop(content), owner=owner)
        write(local / "bin/google-chrome-venus", wrapper, 0o755, owner)
        # Redirect the earlier per-user driver/extension paths without copying profiles.
        for relative, target in [("lib/venus-vaapi/venus_drv_video.so", str(driver)),
                                 ("share/chrome-youtube-codec/codec.js", str(SHARE / "extension/codec.js")),
                                 ("share/chrome-youtube-codec/manifest.json", str(SHARE / "extension/manifest.json"))]:
            old = local / relative
            if old.is_file():
                backup(old)
                old.unlink()
                old.symlink_to(target)
    write(STATE / "installation.json", json.dumps({"extension_id": extension_id, "upstream_revision": REVISION, "version": manifest["version"]}, indent=2), 0o600)
    print("Installed host-wide. Extension ID:", extension_id)
    print("Restart Chrome to apply the launcher. Machine policy installs the extension in all profiles.")


if __name__ == "__main__":
    main()
