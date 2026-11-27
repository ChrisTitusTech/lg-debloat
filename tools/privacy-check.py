#!/usr/bin/env python3
"""Heuristic scan of staged blobs. Reports paths and rules, never matched values."""
import hashlib
import re
import subprocess
import sys

rules = {
    "private-key": re.compile(r"-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----"),
    "private-ipv4": re.compile(r"\b(?:10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)\b"),
    "mac-address": re.compile(r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b"),
    "personal-home-path": re.compile(r"(?<![A-Za-z0-9_/])/(?:home|Users)/[A-Za-z0-9_.-]+/"),
    "github-token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b"),
    "aws-key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+\b"),
    "credential-value": re.compile(r'''(?i)["']?(?:client[-_]?key|password|passphrase|access[-_]?token|refresh[-_]?token)["']?\s*[:=]\s*["'][A-Za-z0-9_+/=.-]{6,}["']'''),
    "credential-url": re.compile(r"https?://[^\s/@]+:[^\s/@]+@"),
    "email-address": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
}
# Only these exact, visually reviewed documentation captures are allowed.
reviewed_screenshots = {
    "docs/screenshots/custom-home.png": "8c9a59a6f81dc65a2a5c9d43fddbc989384d0fdf8a2e3358f116e934bcf9998c",
    "docs/screenshots/hdmi-input.png": "cd9e9080c52a5b972ed7be8ff33eadbd2af4260294ffb711a9ed1d57d5add3f3",
    "docs/screenshots/hdmi-selected.png": "7828f88b1607e4bd9bedf3da1e0c20bd934699c11c2ae73a7aac4dbaff393127",
    "docs/screenshots/homebrew-channel.png": "01ec0d064241df847c9c78371c4567cb882c00b704aa2005fcf953d8bb09e415",
    "docs/screenshots/homebrew-settings.png": "bfccb5578f231944a39837fafb685c9341c336aa6f286551d1df52ea721806e0",
    "docs/screenshots/lg-additional-settings.png": "28e8d6fd9beb46eab8bca4a37da32d8d69cd44dd6cf43cea0dde6ccf9efc78f8",
    "docs/screenshots/lg-home-promotion.png": "1c6102611d4bf71ecbcd6ab8db8532543d79ba3cb34f0f3e7bda71ff61541289",
    "docs/screenshots/lg-home-ribbon.png": "2ea09e012951ccc47b290a83437346e36c82af7b286cc4fed93756a9be846004",
}

paths = subprocess.check_output(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]).split(b"\0")
issues = []
count = 0
for raw in filter(None, paths):
    path = raw.decode()
    count += 1
    data = subprocess.check_output(["git", "show", ":" + path])
    if path in reviewed_screenshots:
        if hashlib.sha256(data).hexdigest() != reviewed_screenshots[path]:
            issues.append((path, "unreviewed-screenshot-content"))
        continue
    if path.startswith(("private/", "backups/", "logs/", "dist/")) or path.endswith((".ipk", ".pem", ".key", ".tar", ".gz", ".png", ".jpg", ".jpeg")):
        issues.append((path, "private-or-binary-artifact"))
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        issues.append((path, "non-text-blob"))
        continue
    for name, pattern in rules.items():
        if pattern.search(text):
            issues.append((path, name))
for path, reason in issues:
    print(f"REVIEW {path}: {reason}")
print(f"Scanned {count} staged files; {len(issues)} findings.")
sys.exit(bool(issues))
