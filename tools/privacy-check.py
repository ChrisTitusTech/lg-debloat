#!/usr/bin/env python3
"""Heuristic scan of staged blobs. Reports paths and rules, never matched values."""
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
paths = subprocess.check_output(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]).split(b"\0")
issues = []
count = 0
for raw in filter(None, paths):
    path = raw.decode()
    count += 1
    if path.startswith(("private/", "backups/", "logs/", "dist/")) or path.endswith((".ipk", ".pem", ".key", ".tar", ".gz", ".png", ".jpg", ".jpeg")):
        issues.append((path, "private-or-binary-artifact"))
    data = subprocess.check_output(["git", "show", ":" + path])
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
