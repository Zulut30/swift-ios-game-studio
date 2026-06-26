#!/usr/bin/env python3
"""swift-doctor — diagnose a Swift iOS/iPadOS *game* project against the
swift-ios-game-studio skill's standards and print a categorized PASS/WARN/FAIL
report with remediation and an exit code. The analog of `flutter doctor`.

Dependency-free: Python 3 standard library only.

It scans SOURCE and CONFIG only — Swift source (**/*.swift, excluding build dirs
and leading-dot directories), Package.swift, Podfile/Cartfile, project.pbxproj,
Info.plist, *.xcprivacy, Assets.xcassets — and NEVER opens Markdown/docs/txt as a
check input, so a doc that says "do not use analytics" is never flagged.

Usage:
    swift-doctor.py [PATH] [--json] [--build] [--strict] [--only DIM[,DIM...]]
                    [--quiet] [-h|--help]

Exit codes: 0 = healthy / no error failures (and, with --strict, no warn failures);
            1 = at least one error failure (or, with --strict, a warn failure);
            2 = usage error / fatal internal error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import subprocess
import sys

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

TOOL_NAME = "swift-doctor"
TOOL_VERSION = "1.0"

# Directory components that are always excluded from scans. Any path that has one
# of these as a component (or any leading-dot directory component) is skipped.
EXCLUDED_DIR_NAMES = {
    ".build",
    "DerivedData",
    ".git",
    "Pods",
    "Carthage",
    ".swiftpm",
}

# Report grouping order (also the set of valid --only dimension ids).
DIMENSIONS = [
    "environment",
    "architecture",
    "swift-quality",
    "performance",
    "kids-safety",
    "accessibility",
    "assets-licensing",
    "build-tests",
]

# Status glyphs (unicode + ascii fallback).
GLYPHS_UNICODE = {
    "PASS": "✓",   # ✓
    "WARN": "⚠",   # ⚠
    "FAIL": "✗",   # ✗
    "INFO": "•",   # •
    "SKIP": "∅",   # ∅
    "NA": "✓",     # ✓ (rendered as pass / "not applicable")
}
GLYPHS_ASCII = {
    "PASS": "[OK]",
    "WARN": "[WARN]",
    "FAIL": "[FAIL]",
    "INFO": "[INFO]",
    "SKIP": "[SKIP]",
    "NA": "[OK]",
}


# --------------------------------------------------------------------------- #
# Path / exclusion helpers
# --------------------------------------------------------------------------- #


def _is_excluded_component(name: str) -> bool:
    """A single path component is excluded if it is a known build dir OR a
    leading-dot directory (e.g. .cursor, .agents, .claude, .swiftpm)."""
    if name in EXCLUDED_DIR_NAMES:
        return True
    if name.startswith(".") and name not in (".", ".."):
        return True
    return False


def _path_is_excluded(root: str, abspath: str) -> bool:
    """True if any directory component of `abspath` (relative to `root`) is excluded."""
    rel = os.path.relpath(abspath, root)
    if rel == ".":
        return False
    parts = rel.split(os.sep)
    # The final part is the file name; directory components are parts[:-1].
    for comp in parts[:-1]:
        if _is_excluded_component(comp):
            return True
    return False


def walk_files(root: str):
    """Yield absolute paths of all files under root, pruning excluded directories.
    Uses os.walk (no dependency on the `find` binary)."""
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune excluded dirs in place so os.walk doesn't descend into them.
        dirnames[:] = [d for d in dirnames if not _is_excluded_component(d)]
        for fn in filenames:
            yield os.path.join(dirpath, fn)


def iter_swift_files(root: str):
    """Yield absolute paths of Swift source files under root, obeying exclusions."""
    for path in walk_files(root):
        if path.endswith(".swift"):
            yield path


def is_test_path(path: str) -> bool:
    """A Swift file is part of the test subset if any directory component matches
    `Tests`, `*Tests`, or `*Test`, OR the file itself is named like a test
    (e.g. `FooTests.swift`, `FooSpec.swift`) — covers flat, single-file test suites."""
    comps = path.split(os.sep)
    for comp in comps[:-1]:  # directory components
        if comp == "Tests" or comp.endswith("Tests") or comp.endswith("Test"):
            return True
    name = comps[-1]
    if name.endswith(".swift"):
        stem = name[:-len(".swift")]
        if stem.endswith(("Tests", "Test", "Spec", "Specs")):
            return True
    return False


def has_path_component(path: str, component: str) -> bool:
    """Case-sensitive exact match of a directory component anywhere in the path."""
    return component in path.split(os.sep)


# --------------------------------------------------------------------------- #
# Comment / string stripping (cheap heuristics)
# --------------------------------------------------------------------------- #


def _strip_line_comment(line: str) -> str:
    """Remove a trailing `// ...` when the `//` is not inside a string literal.
    Cheap heuristic: walk the line tracking whether we're inside a double-quoted
    string (respecting backslash escapes); cut at the first `//` seen outside one."""
    in_string = False
    i = 0
    n = len(line)
    while i < n - 1:
        c = line[i]
        if c == "\\" and in_string:
            i += 2
            continue
        if c == '"':
            in_string = not in_string
            i += 1
            continue
        if not in_string and c == "/" and line[i + 1] == "/":
            return line[:i]
        i += 1
    return line


def strip_comments_text(text: str) -> str:
    """Return `text` with line comments removed and block comments (/* ... */)
    blanked out, preserving line counts so line numbers stay accurate."""
    # Blank out block comments while preserving newlines.
    def _blank_block(match: "re.Match") -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    text = re.sub(r"/\*.*?\*/", _blank_block, text, flags=re.DOTALL)
    out_lines = []
    for line in text.split("\n"):
        out_lines.append(_strip_line_comment(line))
    return "\n".join(out_lines)


def strip_xml_comments(text: str) -> str:
    """Blank out XML/HTML comment regions (<!-- ... -->), preserving newlines."""
    def _blank(match: "re.Match") -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    return re.sub(r"<!--.*?-->", _blank, text, flags=re.DOTALL)


# --------------------------------------------------------------------------- #
# Finding / CheckResult records
# --------------------------------------------------------------------------- #


class Finding:
    __slots__ = ("file", "line", "snippet")

    def __init__(self, file=None, line=None, snippet=None):
        self.file = file
        self.line = line
        self.snippet = snippet

    def to_dict(self):
        d = {}
        if self.file is not None:
            d["file"] = self.file
        if self.line is not None:
            d["line"] = self.line
        if self.snippet is not None:
            d["snippet"] = self.snippet
        return d


class CheckResult:
    __slots__ = ("id", "dimension", "severity", "status", "title", "findings", "remediation")

    def __init__(self, id, dimension, severity, status, title, findings=None, remediation=""):
        self.id = id
        self.dimension = dimension
        self.severity = severity
        self.status = status
        self.title = title
        self.findings = findings or []
        self.remediation = remediation

    def to_dict(self):
        return {
            "id": self.id,
            "dimension": self.dimension,
            "severity": self.severity,
            "status": self.status,
            "title": self.title,
            "findings": [f.to_dict() for f in self.findings],
            "remediation": self.remediation,
        }


def status_for(severity: str, failed: bool) -> str:
    """Map a check's severity + pass/fail into the status model."""
    if not failed:
        return "PASS"
    return {"error": "FAIL", "warn": "WARN", "info": "INFO"}[severity]


# --------------------------------------------------------------------------- #
# Context (precomputed, cached)
# --------------------------------------------------------------------------- #


class Context:
    """Precomputes and caches everything the checks reuse so the 41 checks don't
    re-walk the tree: the Swift file list with per-file text, prod/test partitions,
    manifest presence, UI-framework flags, the SpriteKit file set, and an asset list."""

    def __init__(self, root: str):
        self.root = root

        # --- Swift source enumeration + text cache ---
        self.swift_files = []          # all production+test swift abspaths
        self._text_cache = {}          # abspath -> text (lazy)
        for p in iter_swift_files(root):
            self.swift_files.append(p)
        self.swift_files.sort()

        self.test_swift = [p for p in self.swift_files if is_test_path(p)]
        self.prod_swift = [p for p in self.swift_files if not is_test_path(p)]

        # --- Manifest / config discovery (by name) ---
        self.package_swift = []        # all Package.swift paths
        self.podfiles = []
        self.cartfiles = []            # Cartfile + Cartfile.private
        self.pbxprojs = []
        self.info_plists = []          # files literally named Info.plist
        self.all_plists = []           # any *.plist
        self.xcprivacy = []            # *.xcprivacy
        self.gitignore = None
        self.workflow_files = []       # .github/workflows/*.yml|*.yaml
        self.swift_format_config = None
        self.json_files = []           # bundled *.json (for cleartext/secret scans)
        self.dep_manifest_files = []   # for tracking-sdk dependency scan
        self.project_containers = []   # .xcodeproj / .xcworkspace dirs + Package.swift
        self.has_xcodeproj = False
        self.has_xcworkspace = False
        self.objc_files = []           # *.m / *.mm

        self._discover(root)

        # --- UI-framework import flags + SpriteKit file set ---
        self.ui_import_files = set()       # files importing SwiftUI/UIKit/SpriteKit
        self.spritekit_files = set()
        self._scan_imports()

        # --- Asset enumeration (one walk, cached) ---
        self.asset_files = []          # absolute paths of all non-source files (for asset checks)
        self.imageset_dirs = []        # *.imageset/.dataset/.appiconset/.colorset dirs
        self._enumerate_assets(root)

    # ---- text access ----

    def text(self, path: str) -> str:
        """Return the file's text (utf-8, errors replaced), cached."""
        if path in self._text_cache:
            return self._text_cache[path]
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                t = fh.read()
        except (OSError, IOError):
            t = ""
        self._text_cache[path] = t
        return t

    # ---- discovery ----

    def _discover(self, root: str):
        for path in walk_files(root):
            base = os.path.basename(path)
            if base == "Package.swift":
                self.package_swift.append(path)
            elif base == "Podfile":
                self.podfiles.append(path)
            elif base in ("Cartfile", "Cartfile.private"):
                self.cartfiles.append(path)
            elif base == "project.pbxproj":
                self.pbxprojs.append(path)
            elif base == "Info.plist":
                self.info_plists.append(path)
            elif base.endswith(".xcprivacy"):
                self.xcprivacy.append(path)
            elif base == ".gitignore" and self.gitignore is None:
                # Prefer the root .gitignore.
                if os.path.dirname(path) == root:
                    self.gitignore = path
                elif self.gitignore is None:
                    self.gitignore = path
            elif base in (".swift-format", ".swift-format.json", "swift-format.json"):
                # Prefer one at the root.
                if self.swift_format_config is None or os.path.dirname(path) == root:
                    self.swift_format_config = path
            elif base == "Podfile.lock":
                self.dep_manifest_files.append(path)
            elif base in ("Cartfile.resolved",):
                self.dep_manifest_files.append(path)

            if base.endswith(".plist"):
                self.all_plists.append(path)
            if base.endswith(".json"):
                self.json_files.append(path)
            if base.endswith(".m") or base.endswith(".mm"):
                self.objc_files.append(path)

        # dep manifest set (for the tracking-SDK dependency scan)
        self.dep_manifest_files = list(
            self.package_swift
            + [p for p in walk_files(root) if os.path.basename(p) == "Package.resolved"]
            + self.podfiles
            + [p for p in walk_files(root) if os.path.basename(p) == "Podfile.lock"]
            + self.cartfiles
            + [p for p in walk_files(root) if os.path.basename(p) in ("Cartfile.resolved",)]
            + self.pbxprojs
        )

        # GitHub workflow files.
        wf_dir = os.path.join(root, ".github", "workflows")
        if os.path.isdir(wf_dir):
            for fn in sorted(os.listdir(wf_dir)):
                if fn.endswith(".yml") or fn.endswith(".yaml"):
                    self.workflow_files.append(os.path.join(wf_dir, fn))

        # Project containers (bundle dirs), depth-limited scan.
        for dirpath, dirnames, _ in os.walk(root):
            depth = os.path.relpath(dirpath, root).count(os.sep)
            if depth > 4:
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if not _is_excluded_component(d)]
            for d in list(dirnames):
                full = os.path.join(dirpath, d)
                if d.endswith(".xcodeproj"):
                    self.has_xcodeproj = True
                    self.project_containers.append(full)
                elif d.endswith(".xcworkspace"):
                    self.has_xcworkspace = True
                    self.project_containers.append(full)
        for p in self.package_swift:
            self.project_containers.append(p)

    def _scan_imports(self):
        ui_re = re.compile(r"^[ \t]*import[ \t]+(SwiftUI|UIKit|SpriteKit|SceneKit)\b", re.MULTILINE)
        sk_re = re.compile(r"^[ \t]*import[ \t]+SpriteKit\b", re.MULTILINE)
        for p in self.swift_files:
            t = strip_comments_text(self.text(p))
            if ui_re.search(t):
                self.ui_import_files.add(p)
            if sk_re.search(t):
                self.spritekit_files.add(p)

    def has_ui_framework(self) -> bool:
        return len(self.ui_import_files) > 0

    def uses_spritekit(self) -> bool:
        """SpriteKit used anywhere — by import, SKView/SpriteView/SKScene tokens."""
        if self.spritekit_files:
            return True
        tok = re.compile(r"\b(SKView|SpriteView|SKScene)\b")
        for p in self.swift_files:
            if tok.search(strip_comments_text(self.text(p))):
                return True
        return False

    def _enumerate_assets(self, root: str):
        set_suffixes = (".imageset", ".dataset", ".appiconset", ".colorset")
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not _is_excluded_component(d)]
            for d in dirnames:
                if d.endswith(set_suffixes):
                    self.imageset_dirs.append(os.path.join(dirpath, d))
            for fn in filenames:
                self.asset_files.append(os.path.join(dirpath, fn))


# --------------------------------------------------------------------------- #
# Grep helpers
# --------------------------------------------------------------------------- #


def grep_files(ctx, files, pattern, flags=0, strip_comments=False, strip_xml=False):
    """Run regex `pattern` over each file, returning a list of Finding(file, line,
    snippet) for every match. Line numbers are 1-based and computed against the
    (possibly stripped) text so they line up with the original file."""
    rx = re.compile(pattern, flags)
    findings = []
    for path in files:
        text = ctx.text(path)
        if strip_comments:
            text = strip_comments_text(text)
        elif strip_xml:
            text = strip_xml_comments(text)
        # Precompute line start offsets for line-number lookup.
        for m in rx.finditer(text):
            start = m.start()
            line_no = text.count("\n", 0, start) + 1
            # Snippet: the source line from the ORIGINAL text (not stripped) when possible.
            snippet = _line_at(ctx.text(path), line_no).strip()
            findings.append(Finding(file=path, line=line_no, snippet=snippet[:200]))
    return findings


def _line_at(text: str, line_no: int) -> str:
    lines = text.split("\n")
    if 1 <= line_no <= len(lines):
        return lines[line_no - 1]
    return ""


def count_matches(ctx, files, pattern, flags=0, strip_comments=False):
    return len(grep_files(ctx, files, pattern, flags, strip_comments))


# --------------------------------------------------------------------------- #
# update(_:) body extractor
# --------------------------------------------------------------------------- #

_UPDATE_SIG_RE = re.compile(
    r"func\s+update\s*\(\s*_\s+currentTime\s*:\s*(?:TimeInterval|CFTimeInterval|Double)\s*\)"
)


def extract_update_bodies(text: str):
    """Return a list of (body_text, body_start_line) for each `update(_:)` override
    in `text`, brace-balanced from the signature. Falls back to ~40 lines after the
    signature (flagged via the 'verify location' note carried by the caller)."""
    bodies = []
    for sig in _UPDATE_SIG_RE.finditer(text):
        # Find the opening brace after the signature.
        brace_pos = text.find("{", sig.end())
        if brace_pos == -1:
            continue
        depth = 0
        i = brace_pos
        end = None
        in_string = False
        n = len(text)
        while i < n:
            c = text[i]
            if c == "\\" and in_string:
                i += 2
                continue
            if c == '"':
                in_string = not in_string
            elif not in_string:
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            i += 1
        start_line = text.count("\n", 0, brace_pos) + 1
        if end is not None:
            bodies.append((text[brace_pos : end + 1], start_line))
        else:
            # Fallback: ~40 lines after the signature.
            sig_line = text.count("\n", 0, sig.start())
            lines = text.split("\n")
            slice_lines = lines[sig_line : sig_line + 40]
            bodies.append(("\n".join(slice_lines), start_line))
    return bodies


def grep_update_bodies(ctx, files, pattern, flags=0):
    """Grep `pattern` only inside update(_:) bodies of each file. Returns Findings
    with line numbers relative to the whole file."""
    rx = re.compile(pattern, flags)
    findings = []
    for path in files:
        text = strip_comments_text(ctx.text(path))
        for body, body_start_line in extract_update_bodies(text):
            for m in rx.finditer(body):
                line_in_body = body.count("\n", 0, m.start())
                line_no = body_start_line + line_in_body
                snippet = _line_at(ctx.text(path), line_no).strip()
                findings.append(Finding(file=path, line=line_no, snippet=snippet[:200]))
    return findings


def file_has_update_override(ctx, path) -> bool:
    return bool(_UPDATE_SIG_RE.search(strip_comments_text(ctx.text(path))))


# --------------------------------------------------------------------------- #
# Image header readers (stdlib only)
# --------------------------------------------------------------------------- #


def png_dimensions(path):
    """Return (width, height) from a PNG IHDR, or None."""
    try:
        with open(path, "rb") as fh:
            header = fh.read(24)
        if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        # IHDR width/height are big-endian uint32 at bytes 16..24.
        w, h = struct.unpack(">II", header[16:24])
        return (w, h)
    except (OSError, struct.error):
        return None


def jpeg_dimensions(path):
    """Return (width, height) from a JPEG SOFn marker, or None."""
    try:
        with open(path, "rb") as fh:
            data = fh.read(2)
            if data != b"\xff\xd8":
                return None
            while True:
                b = fh.read(1)
                if not b:
                    return None
                if b != b"\xff":
                    continue
                # Skip fill bytes.
                marker = fh.read(1)
                while marker == b"\xff":
                    marker = fh.read(1)
                if not marker:
                    return None
                mval = marker[0]
                # SOF markers: C0-C3, C5-C7, C9-CB, CD-CF (not C4/C8/CC).
                if mval in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    seg = fh.read(7)
                    if len(seg) < 7:
                        return None
                    h, w = struct.unpack(">HH", seg[3:7])
                    return (w, h)
                else:
                    seg_len_bytes = fh.read(2)
                    if len(seg_len_bytes) < 2:
                        return None
                    seg_len = struct.unpack(">H", seg_len_bytes)[0]
                    fh.seek(seg_len - 2, os.SEEK_CUR)
    except (OSError, struct.error):
        return None


# --------------------------------------------------------------------------- #
# Subprocess runner
# --------------------------------------------------------------------------- #


def which(name):
    """shutil.which without importing shutil at module import for clarity (still stdlib)."""
    import shutil

    return shutil.which(name)


def run_cmd(cmd, timeout=20):
    """Run a command. Returns (found, exit_code, combined_output).
    `found` is False when the executable is not on PATH (then exit_code=None)."""
    exe = cmd[0]
    if which(exe) is None:
        return (False, None, "")
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            text=True,
        )
        return (True, proc.returncode, proc.stdout or "")
    except subprocess.TimeoutExpired as e:
        out = e.output or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return (True, None, (out or "") + "\n[timed out]")
    except (OSError, ValueError) as e:
        return (True, None, "[error running command: %s]" % e)


# --------------------------------------------------------------------------- #
# CHECKS
# --------------------------------------------------------------------------- #
#
# Each check is a function ctx -> CheckResult. They are registered (with metadata)
# in CHECKS below. A shared cache on ctx carries cross-check state (the toolchain
# banner reused by the swift6 check).


# ============================ 6.1 environment ============================== #


def check_env_swift_toolchain_present(ctx):
    cid, dim, sev = "env-swift-toolchain-present", "environment", "error"
    title = "Swift toolchain present"
    found, code, out = run_cmd(["swift", "--version"], timeout=20)
    ctx.cache["swift_version_banner"] = out if found else ""
    ctx.cache["swift_version_found"] = found
    if not found:
        return CheckResult(
            cid, dim, sev, "FAIL", title,
            [Finding(snippet="`swift` not found on PATH")],
            "Install Xcode (App Store) or `xcode-select --install`; on Linux install a "
            "swift.org toolchain. Confirm with `swift --version`.",
        )
    m = re.search(r"Swift version\s+(\d+)\.(\d+)", out)
    no_tools = "no developer tools were found" in out
    if code == 0 and m and not no_tools:
        major = int(m.group(1))
        ctx.cache["swift_major"] = major
        return CheckResult(
            cid, dim, sev, "PASS",
            "%s (Swift %s.%s)" % (title, m.group(1), m.group(2)),
            [], "",
        )
    return CheckResult(
        cid, dim, sev, "FAIL", title,
        [Finding(snippet=(out.strip().splitlines() or ["no version banner"])[0][:160])],
        "Install Xcode (App Store) or `xcode-select --install`; on Linux install a "
        "swift.org toolchain. Confirm with `swift --version`.",
    )


def check_env_swift6_language_version(ctx):
    cid, dim, sev = "env-swift6-language-version", "environment", "warn"
    title = "Swift 6 language toolchain"
    major = ctx.cache.get("swift_major")
    if major is None:
        # The toolchain probe already failed; don't double-report.
        return CheckResult(cid, dim, sev, "NA", title + " (toolchain not detected)", [], "")
    if major >= 6:
        return CheckResult(cid, dim, sev, "PASS", "%s (major %d)" % (title, major), [], "")
    return CheckResult(
        cid, dim, sev, "WARN", "%s (found major %d)" % (title, major),
        [Finding(snippet="Swift major version %d < 6" % major)],
        "Quality bar #6 targets Swift 6 strict concurrency. Upgrade to Xcode 16+ or a "
        "swift.org Swift 6 toolchain.",
    )


def check_env_xcodebuild_present(ctx):
    cid, dim, sev = "env-xcodebuild-present", "environment", "warn"
    title = "xcodebuild present"
    if sys.platform != "darwin":
        return CheckResult(cid, dim, sev, "NA", title + " (Linux — not applicable)", [], "")
    found, code, out = run_cmd(["xcodebuild", "-version"], timeout=20)
    if not found:
        return CheckResult(
            cid, dim, sev, "WARN", title,
            [Finding(snippet="xcodebuild not found on PATH")],
            "Install full Xcode and `sudo xcode-select -s /Applications/Xcode.app`. A pure "
            "SPM core can still build with `swift build`.",
        )
    if "requires Xcode" in out or "requires Xcode" in (out or ""):
        return CheckResult(
            cid, dim, sev, "WARN", title,
            [Finding(snippet="Command Line Tools only (full Xcode required)")],
            "Install full Xcode and `sudo xcode-select -s /Applications/Xcode.app`. A pure "
            "SPM core can still build with `swift build`.",
        )
    m = re.search(r"Xcode\s+\d+(\.\d+)*", out)
    if code == 0 and m:
        return CheckResult(cid, dim, sev, "PASS", "%s (%s)" % (title, m.group(0)), [], "")
    return CheckResult(
        cid, dim, sev, "WARN", title,
        [Finding(snippet=(out.strip().splitlines() or ["no version"])[0][:160])],
        "Install full Xcode and `sudo xcode-select -s /Applications/Xcode.app`. A pure SPM "
        "core can still build with `swift build`.",
    )


def check_env_swift_format_present(ctx):
    cid, dim, sev = "env-swift-format-present", "environment", "warn"
    title = "swift-format available"
    version_re = re.compile(r"\d+(\.\d+)+")
    for cmd in (["swift", "format", "--version"], ["swift-format", "--version"]):
        found, code, out = run_cmd(cmd, timeout=20)
        if found and code == 0 and version_re.search(out or ""):
            return CheckResult(
                cid, dim, sev, "PASS",
                "%s (%s)" % (title, version_re.search(out).group(0)),
                [], "",
            )
    return CheckResult(
        cid, dim, sev, "WARN", title,
        [Finding(snippet="neither `swift format` nor `swift-format` produced a version")],
        "Swift 6 bundles `swift format`; else `brew install swift-format`.",
    )


def check_env_project_container(ctx):
    cid, dim, sev = "env-project-container", "environment", "error"
    title = "Project container present"
    if ctx.project_containers:
        labels = []
        for c in ctx.project_containers:
            labels.append(os.path.relpath(c, ctx.root))
        return CheckResult(
            cid, dim, sev, "PASS",
            "%s (%s)" % (title, ", ".join(sorted(set(labels))[:4])),
            [], "",
        )
    return CheckResult(
        cid, dim, sev, "FAIL", title,
        [Finding(snippet="No Package.swift / .xcodeproj / .xcworkspace found")],
        "Run from project root, or `swift package init`, or commit the `.xcodeproj`.",
    )


def _first_line_tools_version(text):
    """Return (major, minor, raw_line) for the swift-tools-version directive if the
    FIRST non-empty line declares it, else None."""
    for line in text.split("\n"):
        if line.strip() == "":
            continue
        m = re.match(r"^//\s*swift-tools-version\s*:\s*([0-9]+)\.([0-9]+)", line)
        if m:
            return (int(m.group(1)), int(m.group(2)), line.strip())
        return ("BAD", None, line.strip())  # first non-empty line is not the directive
    return None


def check_env_detect_spm(ctx):
    cid, dim, sev = "env-detect-spm", "environment", "info"
    title = "SPM package classifier"
    if not ctx.package_swift:
        return CheckResult(cid, dim, sev, "NA", title + " (no Package.swift)", [], "")
    findings = []
    for p in ctx.package_swift:
        tv = _first_line_tools_version(ctx.text(p))
        if tv and tv[0] != "BAD":
            findings.append(Finding(file=p, line=1, snippet="swift-tools-version: %d.%d" % (tv[0], tv[1])))
        else:
            findings.append(Finding(file=p, line=1, snippet="SPM package (tools-version unparsed)"))
    return CheckResult(cid, dim, sev, "INFO", "SPM package detected", findings,
                       "Informational: a repo can be both SPM and Xcode.")


def check_spm_tools_version_declared(ctx):
    cid, dim, sev = "spm-tools-version-declared", "environment", "error"
    title = "swift-tools-version declared on line 1"
    if not ctx.package_swift:
        return CheckResult(cid, dim, sev, "NA", title + " (no Package.swift)", [], "")
    findings = []
    for p in ctx.package_swift:
        tv = _first_line_tools_version(ctx.text(p))
        if tv is None or tv[0] == "BAD":
            findings.append(Finding(file=p, line=1, snippet="missing/malformed swift-tools-version directive"))
    if findings:
        return CheckResult(cid, dim, sev, "FAIL", title, findings,
                           "Add `// swift-tools-version: 6.0` as the literal first line.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_spm_tools_version_min6(ctx):
    cid, dim, sev = "spm-tools-version-min6", "environment", "warn"
    title = "swift-tools-version >= 6.0"
    if not ctx.package_swift:
        return CheckResult(cid, dim, sev, "NA", title + " (no Package.swift)", [], "")
    findings = []
    any_parsed = False
    for p in ctx.package_swift:
        tv = _first_line_tools_version(ctx.text(p))
        if tv and tv[0] != "BAD" and tv[1] is not None:
            any_parsed = True
            if tv[0] < 6:
                findings.append(Finding(file=p, line=1, snippet="tools-version %d.%d < 6.0" % (tv[0], tv[1])))
    if not any_parsed:
        return CheckResult(cid, dim, sev, "NA", title + " (no parseable directive)", [], "")
    if findings:
        return CheckResult(cid, dim, sev, "WARN", title, findings,
                           "Bump to `6.0` for Swift 6 strict-concurrency default; intentional 5.x "
                           "back-compat may ignore this.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_env_swift_format_config(ctx):
    cid, dim, sev = "env-swift-format-config", "environment", "warn"
    title = "swift-format config present"
    cfg = ctx.swift_format_config
    if cfg is None:
        return CheckResult(
            cid, dim, sev, "WARN", "No .swift-format config at project root",
            [Finding(snippet="no .swift-format / swift-format.json found")],
            "Copy `assets/swift-format.json` to `./.swift-format` and gate CI with "
            "`swift format lint --strict -r .`.",
        )
    try:
        empty = os.path.getsize(cfg) == 0
    except OSError:
        empty = False
    if empty:
        return CheckResult(
            cid, dim, sev, "WARN", title,
            [Finding(file=cfg, snippet="config file is empty")],
            "Copy `assets/swift-format.json` to `./.swift-format`.",
        )
    return CheckResult(cid, dim, sev, "PASS", "%s (%s)" % (title, os.path.relpath(cfg, ctx.root)), [], "")


def check_env_swift_format_config_valid(ctx):
    cid, dim, sev = "env-swift-format-config-valid", "environment", "warn"
    title = "swift-format config is valid JSON"
    cfg = ctx.swift_format_config
    if cfg is None:
        return CheckResult(cid, dim, sev, "NA", title + " (no config)", [], "")
    try:
        with open(cfg, "r", encoding="utf-8", errors="replace") as fh:
            json.load(fh)
    except FileNotFoundError:
        return CheckResult(cid, dim, sev, "NA", title + " (config removed)", [], "")
    except (json.JSONDecodeError, ValueError) as e:
        return CheckResult(
            cid, dim, sev, "WARN", title,
            [Finding(file=cfg, snippet="invalid JSON: %s" % str(e)[:120])],
            "Fix JSON syntax or re-copy `assets/swift-format.json`.",
        )
    except OSError:
        return CheckResult(cid, dim, sev, "NA", title + " (unreadable)", [], "")
    return CheckResult(cid, dim, sev, "PASS", "%s (%s)" % (title, os.path.relpath(cfg, ctx.root)), [], "")


def check_env_third_party_dep_managers(ctx):
    cid, dim, sev = "env-third-party-dep-managers", "environment", "info"
    title = "Third-party dependency managers"
    present = []
    if ctx.podfiles:
        present.append("CocoaPods (Podfile)")
    if ctx.cartfiles:
        present.append("Carthage (Cartfile)")
    if not present:
        return CheckResult(cid, dim, sev, "PASS", title + " (none)", [], "")
    findings = [Finding(snippet=p) for p in present]
    return CheckResult(
        cid, dim, sev, "INFO", title, findings,
        "Confirm each dependency is justified, kid-safe (no tracking SDKs), and an "
        "SPM/Apple-framework alternative was considered.",
    )


def check_env_build_discovery_advisory(ctx):
    cid, dim, sev = "env-build-discovery-advisory", "environment", "info"
    title = "Build discovery (opt-in only)"
    lines = []
    if ctx.package_swift:
        pkg_dir = os.path.relpath(os.path.dirname(ctx.package_swift[0]), ctx.root) or "."
        lines.append("SPM: `swift build` / `swift test` (package at %s)" % pkg_dir)
    workspace = next((c for c in ctx.project_containers if c.endswith(".xcworkspace")), None)
    proj = next((c for c in ctx.project_containers if c.endswith(".xcodeproj")), None)
    if workspace:
        lines.append(
            "Xcode: `xcodebuild build|test -workspace %s -scheme <S> -destination <D> "
            "CODE_SIGNING_ALLOWED=NO`" % os.path.relpath(workspace, ctx.root)
        )
    elif proj:
        lines.append(
            "Xcode: `xcodebuild build|test -project %s -scheme <S> -destination <D> "
            "CODE_SIGNING_ALLOWED=NO`" % os.path.relpath(proj, ctx.root)
        )
    if not lines:
        lines.append("No container detected; run swift-doctor from the project root.")
    findings = [Finding(snippet=ln) for ln in lines]
    return CheckResult(
        cid, dim, sev, "INFO", title, findings,
        "Builds/tests are opt-in (`--build`). Only claim a build/tests passed if you ran them "
        "and saw exit 0.",
    )


# ============================ 6.2 architecture ============================== #


def check_arch_models_no_ui_imports(ctx):
    cid, dim, sev = "arch-models-no-ui-imports", "architecture", "error"
    title = "Models/ has no UI imports"
    model_files = [p for p in ctx.swift_files if has_path_component(p, "Models")]
    if not model_files:
        return CheckResult(cid, dim, sev, "NA", title + " (no Models/ folder)", [], "")
    findings = grep_files(
        ctx, model_files,
        r"^[ \t]*import[ \t]+(SwiftUI|SpriteKit|UIKit|SceneKit)\b",
        flags=re.MULTILINE, strip_comments=True,
    )
    if findings:
        return CheckResult(cid, dim, sev, "FAIL", title, findings,
                           "Move the type out of `Models/` (it's a View/Scene type) or invert the "
                           "dependency so the model stays pure.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


# A state/phase enum declaration by name. We brace-match the body in Python (NOT regex) to
# avoid catastrophic backtracking (ReDoS) on large or pathological inputs.
_STATE_ENUM_DECL_RX = re.compile(r"\benum\s+[A-Za-z_]\w*(?:State|Phase|Status|Mode)\w*\b")
_STATE_START_TOKENS = ("menu", "title", "home")
_STATE_PLAY_TOKENS = ("playing", "running", "active", "ingame")


def _balanced_brace_body(text, brace_open):
    """Return the substring between the '{' at index `brace_open` and its matching '}'.
    Linear scan, no backtracking. Returns '' if unbalanced."""
    depth = 0
    for i in range(brace_open, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[brace_open + 1:i]
    return ""


def check_arch_state_machine_present(ctx):
    cid, dim, sev = "arch-state-machine-present", "architecture", "warn"
    title = "Game state machine (enum) present"
    for p in ctx.prod_swift:
        text = strip_comments_text(ctx.text(p))
        for m in _STATE_ENUM_DECL_RX.finditer(text):
            brace = text.find("{", m.end())
            if brace == -1:
                continue
            body = _balanced_brace_body(text, brace).lower()
            if not body:
                continue
            # Heuristic: a game state machine names a start-ish AND a playing-ish case.
            if any(t in body for t in _STATE_START_TOKENS) and any(t in body for t in _STATE_PLAY_TOKENS):
                return CheckResult(cid, dim, sev, "PASS", title, [], "")
    return CheckResult(
        cid, dim, sev, "WARN", title,
        [Finding(snippet="no menu/playing state enum found")],
        "Add `enum GameState { case menu, playing, paused, won, lost }` owned by the controller; "
        "or use GKStateMachine.",
    )


def check_arch_state_terminal_case(ctx):
    cid, dim, sev = "arch-state-terminal-case", "architecture", "info"
    title = "Terminal (won/lost) state case present"
    pattern = (
        r"^[ \t]*case\b[ \t,A-Za-z0-9_]*\b"
        r"(won|lost|win|lose|gameOver|victory|defeat|finished|completed)\b"
    )
    findings = grep_files(ctx, ctx.swift_files, pattern, flags=re.MULTILINE, strip_comments=True)
    if findings:
        return CheckResult(cid, dim, sev, "PASS", title, [], "")
    return CheckResult(
        cid, dim, sev, "INFO", title + " (none found)",
        [Finding(snippet="no terminal won/lost/gameOver case")],
        "Add a terminal `won`/`lost`/`gameOver` case and route to a results screen "
        "(if the genre has an end state).",
    )


def check_arch_no_boolean_state_flags(ctx):
    cid, dim, sev = "arch-no-boolean-state-flags", "architecture", "info"
    title = "No mutually-exclusive boolean phase flags"
    pattern = (
        r"^[ \t]*(?:@Published\s+|@State\s+|private\s+|public\s+|internal\s+|fileprivate\s+)*"
        r"var\s+(isPlaying|isPaused|isGameOver|gameOver|isMenu|hasWon|hasLost|isWin|isLose)\b"
        r"\s*(?::\s*Bool|=\s*(?:true|false))"
    )
    rx = re.compile(pattern, re.MULTILINE)
    findings = []
    for p in ctx.prod_swift:
        text = strip_comments_text(ctx.text(p))
        for m in rx.finditer(text):
            # Skip computed-property blocks (line opens a `{`).
            line_no = text.count("\n", 0, m.start()) + 1
            full_line = _line_at(text, line_no)
            if "{" in full_line:
                continue
            snippet = _line_at(ctx.text(p), line_no).strip()
            findings.append(Finding(file=p, line=line_no, snippet=snippet[:200]))
    if findings:
        return CheckResult(cid, dim, sev, "INFO", title + " (boolean flags found)", findings,
                           "Collapse mutually-exclusive phase flags into one `GameState` enum "
                           "(quality bar #3).")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_arch_folder_layout(ctx):
    cid, dim, sev = "arch-folder-layout", "architecture", "warn"
    title = "Folder layout (Models/ + Views/ or Scenes/)"
    has_models = any(has_path_component(p, "Models") for p in ctx.swift_files)
    has_views = any(
        has_path_component(p, "Views") or has_path_component(p, "Scenes") for p in ctx.swift_files
    )
    if has_models and has_views:
        return CheckResult(cid, dim, sev, "PASS", title, [], "")
    return CheckResult(
        cid, dim, sev, "WARN", title,
        [Finding(snippet="missing Models/ and/or Views/|Scenes/ folders (Xcode groups may differ)")],
        "Split into `Models/ Systems/ Views/(or Scenes/) Tests/`; move pure types to `Models/`.",
    )


def check_arch_scenes_folder_spritekit(ctx):
    cid, dim, sev = "arch-scenes-folder-spritekit", "architecture", "info"
    title = "Scenes/ folder holds SpriteKit code"
    scene_files = [p for p in ctx.swift_files if has_path_component(p, "Scenes")]
    if not scene_files:
        return CheckResult(cid, dim, sev, "NA", title + " (no Scenes/ folder)", [], "")
    findings = grep_files(ctx, scene_files, r"\b(SKScene|SKNode|SpriteView|SKSpriteNode)\b",
                          strip_comments=True)
    if findings:
        return CheckResult(cid, dim, sev, "PASS", title, [], "")
    return CheckResult(
        cid, dim, sev, "INFO", title + " (no SpriteKit usage in Scenes/)",
        [Finding(snippet="Scenes/ exists but no SKScene/SpriteView usage")],
        "Move pure-SwiftUI screens to `Views/`; reserve `Scenes/` for SKScene/SpriteView code.",
    )


def check_arch_views_no_rules(ctx):
    cid, dim, sev = "arch-views-no-rules", "architecture", "info"
    title = "Views/Scenes render only (manual)"
    has_views = any(
        has_path_component(p, "Views") or has_path_component(p, "Scenes") for p in ctx.swift_files
    )
    if not has_views:
        return CheckResult(cid, dim, sev, "NA", title + " (no Views/|Scenes/)", [], "")
    return CheckResult(
        cid, dim, sev, "INFO", title + " — verify by hand",
        [Finding(snippet="Confirm win/lose/scoring verdicts live in Models/, not in views.")],
        "Extract any inline rule into a pure model method (`apply(move:)->Result`, `isWin`) and "
        "call it from the view.",
    )


# ============================ 6.3 swift-quality ============================= #


def _simple_grep_check(ctx, cid, sev, title, files, pattern, remediation, flags=0,
                       strip_comments=True, dimension="swift-quality"):
    findings = grep_files(ctx, files, pattern, flags=flags, strip_comments=strip_comments)
    if findings:
        return CheckResult(cid, dimension, sev, status_for(sev, True), title, findings, remediation)
    return CheckResult(cid, dimension, sev, "PASS", title, [], "")


def check_swift_force_try(ctx):
    return _simple_grep_check(
        ctx, "swift-force-try", "error", "No try! (force-try) in Swift source",
        ctx.prod_swift, r"(?<![A-Za-z0-9_.])try!",
        "Replace try! with do/catch, try?+guard, or throws; fail soft to a documented fallback "
        "level for asset/level loading (quality bar #4).",
    )


def check_swift_force_cast(ctx):
    return _simple_grep_check(
        ctx, "swift-force-cast", "error", "No as! (force-cast) in Swift source",
        ctx.prod_swift, r"\bas!\s",
        "Use as? with guard let/if let, or model the value with a concrete type/enum.",
    )


def check_swift_iuo_property(ctx):
    cid, dim, sev = "swift-iuo-property", "swift-quality", "warn"
    title = "No implicitly-unwrapped optional properties"
    pattern = r"\b(?:var|let)\s+\w+\s*:\s*(?:\[[^\]]+\]|\w[\w.<>, ]*?)\s*!\s*(?:=|$|//|\{)"
    rx = re.compile(pattern, re.MULTILINE)
    findings = []
    for p in ctx.prod_swift:
        raw = ctx.text(p)
        text = strip_comments_text(raw)
        for m in rx.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            prev_line = _line_at(raw, line_no - 1)
            this_line = _line_at(raw, line_no)
            if "@IBOutlet" in this_line or "@IBOutlet" in prev_line:
                continue  # IBOutlets legitimately use IUO; suppress
            findings.append(Finding(file=p, line=line_no, snippet=this_line.strip()[:200]))
    if findings:
        return CheckResult(cid, dim, sev, "WARN", title, findings,
                           "Inject the dependency in init (non-optional) or use a real Optional and "
                           "handle nil.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_swift_force_unwrap_external(ctx):
    pattern = (
        r"(?:Bundle\.[\w.]*\.(?:url|path)\([^)]*\)"
        r"|URL\(string:[^)]*\)"
        r"|\.(?:decode|object|value)\([^)]*\)"
        r"|Data\(contentsOf:[^)]*\)"
        r"|UIImage\(named:[^)]*\)"
        r"|ProcessInfo\.[\w.]*environment\[[^\]]*\]"
        r"|\.first(?:\([^)]*\))?"
        r"|\.last(?:\([^)]*\))?)\s*!"
    )
    return _simple_grep_check(
        ctx, "swift-force-unwrap-external", "error",
        "No force-unwrap on external/optional data lookups", ctx.prod_swift, pattern,
        "`guard let` the resource lookup, use `??` defaults, or `throws`; fail soft to a fallback "
        "level. (For `.first!`/`.last!` verify the collection is provably non-empty.)",
    )


def check_swift_unchecked_sendable(ctx):
    return _simple_grep_check(
        ctx, "swift-unchecked-sendable", "error", "No @unchecked Sendable",
        ctx.prod_swift, r"@unchecked\s+Sendable",
        "Make a Sendable value type, isolate mutable state to an actor/@MainActor, or use real "
        "synchronization (quality bar #6).",
    )


def check_swift_dispatchqueue(ctx):
    cid, dim, sev = "swift-dispatchqueue", "swift-quality", "warn"
    title = "Prefer structured concurrency over GCD"
    pattern = r"\b(?:DispatchQueue|DispatchGroup|DispatchSemaphore|DispatchWorkItem)\b"
    rx = re.compile(pattern)
    findings_warn = []
    findings_info = []
    for p in ctx.prod_swift:
        raw = ctx.text(p)
        text = strip_comments_text(raw)
        for m in rx.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            line = _line_at(raw, line_no)
            f = Finding(file=p, line=line_no, snippet=line.strip()[:200])
            if ".main.asyncAfter" in line:
                findings_info.append(f)
            else:
                findings_warn.append(f)
    if findings_warn:
        return CheckResult(cid, dim, sev, "WARN", title, findings_warn,
                           "Prefer Task/actor/async let/TaskGroup; hop to @MainActor for UI.")
    if findings_info:
        return CheckResult(cid, dim, "info", "INFO", title + " (only main.asyncAfter)", findings_info,
                           "Prefer Task scheduling; `Task { try await Task.sleep(...) }` over "
                           "`DispatchQueue.main.asyncAfter`.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_swift_leftover_print(ctx):
    return _simple_grep_check(
        ctx, "swift-leftover-print", "warn", "No leftover print/debugPrint/dump",
        ctx.prod_swift, r'(?<![A-Za-z0-9_."])(?:print|debugPrint|dump)\s*\(',
        "Remove or route through `os.Logger` behind `#if DEBUG`.",
    )


def check_swift_todo_fixme_count(ctx):
    cid, dim, sev = "swift-todo-fixme-count", "swift-quality", "info"
    title = "TODO/FIXME/HACK markers"
    pattern = r"(?://|/\*|\*)\s*(?:TODO|FIXME|HACK|XXX)\b"
    findings = grep_files(ctx, ctx.prod_swift, pattern, flags=re.MULTILINE, strip_comments=False)
    if findings:
        extra = " (>10 — consider tracking as issues)" if len(findings) > 10 else ""
        return CheckResult(cid, dim, sev, "INFO", "%s: %d%s" % (title, len(findings), extra),
                           findings, "Resolve or convert long-lived markers into tracked issues.")
    return CheckResult(cid, dim, sev, "PASS", title + ": 0", [], "")


def check_swift_retain_cycle_closure(ctx):
    cid, dim, sev = "swift-retain-cycle-closure", "swift-quality", "info"
    title = "Escaping closures capturing self (review)"
    patterns = [
        r"Task\s*\{(?![^{}]*\bweak self\b)",
        r"\.run\s*\(\s*\.run\s*\{(?![^{}]*\bweak self\b)",
    ]
    findings = []
    for p in ctx.prod_swift:
        text = strip_comments_text(ctx.text(p))
        for pat in patterns:
            rx = re.compile(pat)
            for m in rx.finditer(text):
                # Only flag if the (truncated) body references self.
                tail = text[m.start(): m.start() + 400]
                if re.search(r"\bself\b", tail) and "[weak self]" not in tail and "[unowned self]" not in tail:
                    line_no = text.count("\n", 0, m.start()) + 1
                    findings.append(
                        Finding(file=p, line=line_no, snippet=_line_at(ctx.text(p), line_no).strip()[:200])
                    )
    if findings:
        return CheckResult(cid, dim, sev, "INFO", title, findings,
                           "Add `[weak self]` to escaping/long-lived closures (quality bar #7). "
                           "Heuristic — review, not a gate.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_swift_format_lint(ctx):
    cid, dim, sev = "swift-format-lint", "swift-quality", "warn"
    title = "swift-format lint (strict) clean"
    cfg = ctx.swift_format_config
    # Determine the format command.
    cmd = None
    if which("swift") is not None:
        cmd = ["swift", "format", "lint", "--strict", "-r", ctx.root]
    elif which("swift-format") is not None:
        cmd = ["swift-format", "lint", "--strict", "-r", ctx.root]
    if cmd is None or cfg is None:
        why = "swift-format unavailable" if cmd is None else "no config file"
        return CheckResult(
            cid, dim, sev, "SKIP", title + " (not run — %s)" % why,
            [Finding(snippet="would run: swift format lint --strict -r .")],
            "Run `swift format format -i -r .` to autofix, then re-lint.",
        )
    # Pass the path explicitly; never mutate the process-global CWD.
    found, code, out = run_cmd(cmd, timeout=120)
    if not found:
        return CheckResult(cid, dim, sev, "SKIP", title + " (toolchain unavailable)",
                           [Finding(snippet="would run: %s" % " ".join(cmd))],
                           "Run `swift format format -i -r .` to autofix, then re-lint.")
    if code == 0:
        return CheckResult(cid, dim, sev, "PASS", title, [], "")
    snippet_lines = [ln for ln in (out or "").splitlines() if ln.strip()][:8]
    findings = [Finding(snippet=ln[:200]) for ln in snippet_lines] or [Finding(snippet="lint diagnostics")]
    return CheckResult(cid, dim, sev, "WARN", title, findings,
                       "Run `swift format format -i -r .` to autofix, then re-lint.")


# ============================ 6.4 performance =============================== #


def _perf_prod_files(ctx):
    # production swift, already excludes test subset; .swiftpm excluded globally.
    return ctx.prod_swift


def check_perf_dt_clamp_missing(ctx):
    cid, dim, sev = "perf-dt-clamp-missing", "performance", "warn"
    title = "Delta-time clamped in update(_:)"
    findings = []
    any_update = False
    dt_re = re.compile(r"\b(dt|deltaTime|delta|elapsed)\b")
    min_re = re.compile(r"min\s*\(")
    for p in _perf_prod_files(ctx):
        text = strip_comments_text(ctx.text(p))
        if not _UPDATE_SIG_RE.search(text):
            continue
        any_update = True
        if min_re.search(text) and dt_re.search(text):
            continue  # has a clamp somewhere in the file (may be cross-method → acceptable)
        line_no = text.count("\n", 0, _UPDATE_SIG_RE.search(text).start()) + 1
        findings.append(Finding(file=p, line=line_no, snippet="update(_:) with no dt clamp (min + dt id)"))
    if not any_update:
        return CheckResult(cid, dim, sev, "PASS", title + " (no update override)", [], "")
    if findings:
        return CheckResult(cid, dim, sev, "WARN", title, findings,
                           "`let dt = min(currentTime - lastUpdateTime, 1.0/30.0)`; advance systems "
                           "by clamped dt; store `lastUpdateTime`.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_perf_alloc_in_update_loop(ctx):
    cid, dim, sev = "perf-alloc-in-update-loop", "performance", "warn"
    title = "No String(format:) allocations in update loop"
    findings = grep_update_bodies(ctx, _perf_prod_files(ctx), r"String\s*\(\s*format\s*:")
    if findings:
        return CheckResult(cid, dim, sev, "WARN", title, findings,
                           "Rebuild HUD/score strings only when the value changes; hoist formatters.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_perf_interpolation_in_update_loop(ctx):
    cid, dim, sev = "perf-interpolation-in-update-loop", "performance", "info"
    title = "No .text interpolation in update loop"
    findings = grep_update_bodies(ctx, _perf_prod_files(ctx), r'\.text\s*=\s*"[^"]*\\\(')
    if findings:
        return CheckResult(cid, dim, sev, "INFO", title, findings,
                           "Gate `.text` updates behind a value-changed check.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_perf_skaction_rebuilt_in_loop(ctx):
    cid, dim, sev = "perf-skaction-rebuilt-in-loop", "performance", "info"
    title = "No SKAction rebuilt in update loop"
    findings = grep_update_bodies(ctx, _perf_prod_files(ctx), r"SKAction\.")
    if findings:
        return CheckResult(cid, dim, sev, "INFO", title, findings,
                           "Build reusable SKActions once (stored constants) and run the cached "
                           "action.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_perf_addchild_churn_no_pool(ctx):
    cid, dim, sev = "perf-addchild-churn-no-pool", "performance", "warn"
    title = "Node churn without pooling"
    files = _perf_prod_files(ctx)
    has_remove = False
    has_add = False
    has_init = False
    has_pool = False
    remove_re = re.compile(r"removeFromParent\s*\(\s*\)")
    add_re = re.compile(r"addChild\(")
    init_re = re.compile(r"SKSpriteNode\(|SKShapeNode\(")
    pool_re = re.compile(r"(?i)\bpool\b|reuse|recycle|dequeue|freeList")
    sample = None
    for p in files:
        text = strip_comments_text(ctx.text(p))
        if remove_re.search(text):
            has_remove = True
            if sample is None:
                m = remove_re.search(text)
                ln = text.count("\n", 0, m.start()) + 1
                sample = Finding(file=p, line=ln, snippet=_line_at(ctx.text(p), ln).strip()[:200])
        if add_re.search(text):
            has_add = True
        if init_re.search(text):
            has_init = True
        if pool_re.search(text):
            has_pool = True
    churn = has_remove and has_add and has_init
    if churn and not has_pool:
        return CheckResult(cid, dim, sev, "WARN", title, [sample] if sample else [],
                           "Recycle obstacle/coin/projectile nodes via a `NodePool`; reserve "
                           "addChild/removeFromParent for genuine lifecycle changes.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_perf_per_pixel_physics_body(ctx):
    return _simple_grep_check(
        ctx, "perf-per-pixel-physics-body", "warn",
        "No per-pixel (texture) physics bodies", _perf_prod_files(ctx),
        r"SKPhysicsBody\s*\(\s*texture\s*:",
        "Use `rectangleOf:`/`circleOfRadius:`/`polygonFrom:` instead.",
        dimension="performance",
    )


def check_perf_missing_showsfps_debug(ctx):
    cid, dim, sev = "perf-missing-showsfps-debug", "performance", "info"
    title = "showsFPS enabled in DEBUG"
    if not ctx.uses_spritekit():
        return CheckResult(cid, dim, sev, "NA", title + " (no SpriteKit)", [], "")
    rx = re.compile(r"\.showsFPS\s*=\s*true|debugOptions|\.showsFPS")
    for p in ctx.swift_files:
        if rx.search(strip_comments_text(ctx.text(p))):
            return CheckResult(cid, dim, sev, "PASS", title, [], "")
    return CheckResult(
        cid, dim, sev, "INFO", title + " (not set)",
        [Finding(snippet="SpriteKit used but showsFPS never set")],
        "Inside `#if DEBUG` set `view.showsFPS/showsNodeCount/showsDrawCount = true`.",
    )


def check_perf_render_loop_on_static_screen(ctx):
    cid, dim, sev = "perf-render-loop-on-static-screen", "performance", "info"
    title = "Scene paused on static screens"
    if not ctx.uses_spritekit():
        return CheckResult(cid, dim, sev, "NA", title + " (no SpriteKit)", [], "")
    rx = re.compile(r"\bisPaused\s*=|\.preferredFramesPerSecond")
    for p in ctx.swift_files:
        if rx.search(strip_comments_text(ctx.text(p))):
            return CheckResult(cid, dim, sev, "PASS", title, [], "")
    return CheckResult(
        cid, dim, sev, "INFO", title + " (no isPaused/preferredFramesPerSecond)",
        [Finding(snippet="SpriteKit used but no pause / fps control")],
        "Set `scene.isPaused = true` on menu/paused; resume on play.",
    )


def check_perf_swiftui_timeline_dt(ctx):
    cid, dim, sev = "perf-swiftui-timeline-dt", "performance", "info"
    title = "Clamped delta for continuous SwiftUI driver"
    driver_re = re.compile(r"TimelineView\s*\(\s*\.animation|CADisplayLink")
    dt_re = re.compile(r"\b(dt|deltaTime|delta|elapsed|now|last)\b")
    min_re = re.compile(r"min\s*\(")
    driver_files = [p for p in ctx.swift_files if driver_re.search(strip_comments_text(ctx.text(p)))]
    if not driver_files:
        return CheckResult(cid, dim, sev, "NA", title + " (no TimelineView(.animation)/CADisplayLink)", [], "")
    findings = []
    for p in driver_files:
        text = strip_comments_text(ctx.text(p))
        if not (min_re.search(text) and dt_re.search(text)):
            m = driver_re.search(text)
            ln = text.count("\n", 0, m.start()) + 1
            findings.append(Finding(file=p, line=ln, snippet="continuous driver without clamped delta"))
    if findings:
        return CheckResult(cid, dim, sev, "INFO", title, findings,
                           "Compute `elapsed = now - last`, clamp <= 1/30, advance by it; or prefer "
                           "discrete state + withAnimation.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_perf_oversized_textures(ctx):
    cid, dim, sev = "perf-oversized-textures", "performance", "info"
    title = "No oversized bundled textures"
    findings = []
    for path in ctx.asset_files:
        low = path.lower()
        if not (low.endswith(".png") or low.endswith(".jpg") or low.endswith(".jpeg")):
            continue
        # Skip app icons / launch images.
        if ".appiconset" in path or "launchimage" in low or "launchscreen" in low:
            continue
        # Only scan under Assets.xcassets or Resources/.
        if "Assets.xcassets" not in path and not has_path_component(path, "Resources"):
            continue
        dims = png_dimensions(path) if low.endswith(".png") else jpeg_dimensions(path)
        if dims is None:
            continue
        w, h = dims
        if w > 2048 or h > 2048 or (w * h) > 4_000_000:
            findings.append(Finding(file=path, snippet="%dx%d px (%.1f MP)" % (w, h, w * h / 1e6)))
    if findings:
        return CheckResult(cid, dim, sev, "INFO", title + " (large images found)", findings,
                           "Downscale to ~on-screen @3x size, or use vector/SF Symbol placeholders.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


# ============================ 6.5 kids-safety ============================== #


def check_kids_no_tracking_sdk_imports(ctx):
    cid, dim, sev = "kids-no-tracking-sdk-imports", "kids-safety", "error"
    title = "No tracking/analytics SDK imports"
    pattern = (
        r"^\s*(?:@_exported\s+)?import\s+("
        r"FirebaseAnalytics|FirebaseCrashlytics|Firebase(?:Core|Performance|Messaging)?|"
        r"GoogleAnalytics|GoogleMobileAds|Amplitude|Mixpanel|Adjust|AppsFlyerLib|"
        r"AppsFlyerATTrackingManager|Flurry(?:SDK|Analytics)?|Crashlytics|Sentry|SentrySwift|"
        r"FBSDK\w+|FacebookCore|FacebookSDK|OneSignal|Branch|Segment|Analytics|Heap|Smartlook|"
        r"Countly|Bugsnag|Instabug|Datadog|Kochava|Singular)\b"
    )
    findings = grep_files(ctx, ctx.swift_files, pattern, flags=re.MULTILINE, strip_comments=True)
    if findings:
        for f in findings:
            if re.search(r"\bimport\s+Analytics\b", f.snippet or ""):
                f.snippet = (f.snippet or "") + "  (confirm not a local module named Analytics)"
        return CheckResult(cid, dim, sev, "FAIL", title, findings,
                           "Remove the SDK + its manifest entry; prefer on-device MetricKit for "
                           "crash insight.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_kids_no_tracking_sdk_dependencies(ctx):
    cid, dim, sev = "kids-no-tracking-sdk-dependencies", "kids-safety", "error"
    title = "No tracking/analytics SDK dependencies"
    token = (
        r"(firebase|google-?analytics|googlemobileads|amplitude|mixpanel|appsflyer|"
        r"adjust(?:-?sdk)?|flurry|crashlytics|getsentry|sentry-cocoa|facebook-ios-sdk|FBSDK|"
        r"onesignal|branch-sdk|segment|analytics-ios|kochava|singular|countly|bugsnag|"
        r"instabug|smartlook|heap)"
    )
    # Require the token inside a quoted package URL or pod/cart name.
    rx = re.compile(r'["\'][^"\']*' + token + r'[^"\']*["\']', re.IGNORECASE)
    findings = []
    files = sorted(set(ctx.dep_manifest_files))
    for p in files:
        text = ctx.text(p)
        for m in rx.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            findings.append(Finding(file=p, line=line_no, snippet=_line_at(text, line_no).strip()[:200]))
    if findings:
        return CheckResult(cid, dim, sev, "FAIL", title, findings,
                           "Delete the package/pod/cart entry and the "
                           "XCRemoteSwiftPackageReference/PBXBuildFile rows; re-resolve.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_kids_no_idfa_att(ctx):
    cid, dim, sev = "kids-no-idfa-att", "kids-safety", "error"
    title = "No IDFA / App Tracking Transparency usage"
    pattern = (
        r"\b(ATTrackingManager|advertisingIdentifier|ASIdentifierManager|"
        r"requestTrackingAuthorization|trackingAuthorizationStatus|AppTrackingTransparency)\b"
    )
    files = ctx.swift_files + ctx.objc_files
    findings = grep_files(ctx, files, pattern, strip_comments=True)
    if findings:
        return CheckResult(cid, dim, sev, "FAIL", title, findings,
                           "Remove IDFA/ATT usage and the AppTrackingTransparency/AdSupport "
                           "imports; delete NSUserTrackingUsageDescription.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_kids_no_att_usage_string(ctx):
    cid, dim, sev = "kids-no-att-usage-string", "kids-safety", "error"
    title = "No NSUserTrackingUsageDescription in Info.plist"
    if not ctx.info_plists:
        return CheckResult(cid, dim, sev, "NA", title + " (no Info.plist)", [], "")
    findings = grep_files(ctx, ctx.info_plists,
                          r"<key>\s*NSUserTrackingUsageDescription\s*</key>",
                          strip_xml=True)
    if findings:
        return CheckResult(cid, dim, sev, "FAIL", title, findings,
                           "Remove the key; ensure no ATT call exists.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_kids_no_external_links(ctx):
    cid, dim, sev = "kids-no-external-links", "kids-safety", "warn"
    title = "No unguarded external links / web views"
    pattern = (
        r"\b(WKWebView|SFSafariViewController|ASWebAuthenticationSession|"
        r"UIApplication\.shared\.open|openURL|SKStoreReviewController|requestReview)\b"
    )
    findings = grep_files(ctx, ctx.swift_files, pattern, strip_comments=True)
    if findings:
        return CheckResult(cid, dim, sev, "WARN", title, findings,
                           "Remove arbitrary web views; route unavoidable links through a parental "
                           "gate; drop SKStoreReviewController from the kids flow.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_kids_no_cleartext_http(ctx):
    cid, dim, sev = "kids-no-cleartext-http", "kids-safety", "warn"
    title = "No cleartext http:// endpoints"
    whitelist = ("w3.org", "apple.com/DTDs", "xml.org", "purl.org", "schemas.android.com")
    pattern = r"http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)[A-Za-z0-9.\-]+"
    rx = re.compile(pattern)
    files = ctx.swift_files + ctx.objc_files + ctx.all_plists + ctx.json_files
    files = sorted(set(files))
    findings = []
    for p in files:
        raw = ctx.text(p)
        # For plist/xml, strip XML comments; for swift, strip code comments.
        if p.endswith(".plist") or p.endswith(".xcprivacy"):
            text = strip_xml_comments(raw)
        elif p.endswith(".swift"):
            text = strip_comments_text(raw)
        else:
            text = raw
        for m in rx.finditer(text):
            matched = m.group(0)
            # Whitelist schema/namespace hosts (and check the surrounding URL too).
            tail = text[m.start(): m.start() + 60]
            if any(w in matched or w in tail for w in whitelist):
                continue
            line_no = text.count("\n", 0, m.start()) + 1
            findings.append(Finding(file=p, line=line_no, snippet=_line_at(raw, line_no).strip()[:200]))
    if findings:
        return CheckResult(cid, dim, sev, "WARN", title, findings,
                           "Use `https://`; do not add `NSAllowsArbitraryLoads`.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def _read_plist(path):
    import plistlib

    try:
        with open(path, "rb") as fh:
            return plistlib.load(fh)
    except Exception:
        return None


def check_kids_no_ats_arbitrary_loads(ctx):
    cid, dim, sev = "kids-no-ats-arbitrary-loads", "kids-safety", "warn"
    title = "No NSAllowsArbitraryLoads (ATS exception)"
    files = sorted(set(ctx.info_plists + ctx.all_plists))
    if not files:
        return CheckResult(cid, dim, sev, "NA", title + " (no plist)", [], "")
    findings = []
    keys = ("NSAllowsArbitraryLoads", "NSAllowsArbitraryLoadsInWebContent",
            "NSAllowsArbitraryLoadsForMedia", "NSAllowsArbitraryLoadsInMediaContent")
    rx = re.compile(
        r"<key>\s*NSAllowsArbitraryLoads(InWebContent|ForMedia|InMediaContent)?\s*</key>\s*<true\s*/>"
    )
    for p in files:
        parsed = _read_plist(p)
        flagged = False
        if isinstance(parsed, dict):
            ats = parsed.get("NSAppTransportSecurity")
            if isinstance(ats, dict):
                for k in keys:
                    if ats.get(k) is True:
                        findings.append(Finding(file=p, snippet="%s = true" % k))
                        flagged = True
        if not flagged:
            text = strip_xml_comments(ctx.text(p))
            for m in rx.finditer(text):
                line_no = text.count("\n", 0, m.start()) + 1
                findings.append(Finding(file=p, line=line_no, snippet=_line_at(ctx.text(p), line_no).strip()[:200]))
    if findings:
        return CheckResult(cid, dim, sev, "WARN", title, findings,
                           "Remove the NSAppTransportSecurity exception; use HTTPS; scope with "
                           "NSExceptionDomains if one legacy host is unavoidable.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_kids_no_hardcoded_secrets(ctx):
    cid, dim, sev = "kids-no-hardcoded-secrets", "kids-safety", "error"
    title = "No hard-coded secrets / API keys"
    pattern = (
        r"(api[_-]?key|secret|client[_-]?secret|access[_-]?token|auth[_-]?token|bearer|"
        r"authorization)\b\s*[:=]\s*[\"'][A-Za-z0-9_\-./+]{16,}[\"']"
    )
    placeholder = re.compile(r"(?i)(your|example|placeholder|xxxx|changeme|dummy|test)")
    files = sorted(set(ctx.swift_files + ctx.objc_files + ctx.all_plists + ctx.json_files))
    fail_findings = []
    info_findings = []
    rx = re.compile(pattern, re.IGNORECASE)
    for p in files:
        raw = ctx.text(p)
        text = strip_comments_text(raw) if p.endswith(".swift") else raw
        for m in rx.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            snippet = _line_at(raw, line_no).strip()[:200]
            f = Finding(file=p, line=line_no, snippet=snippet)
            if placeholder.search(m.group(0)):
                info_findings.append(f)
            else:
                fail_findings.append(f)
    if fail_findings:
        return CheckResult(cid, dim, sev, "FAIL", title, fail_findings,
                           "Remove the literal, rotate the credential, load at runtime/Keychain; an "
                           "offline kids game needs no backend keys.")
    if info_findings:
        return CheckResult(cid, dim, "info", "INFO", title + " (placeholder values only)", info_findings,
                           "These look like placeholders; still avoid committing real credentials.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_kids_privacy_manifest_present(ctx):
    cid, dim, sev = "kids-privacy-manifest-present", "kids-safety", "warn"
    title = "Privacy manifest (PrivacyInfo.xcprivacy) present"
    present = [p for p in ctx.xcprivacy if os.path.basename(p) == "PrivacyInfo.xcprivacy"]
    if present:
        return CheckResult(cid, dim, sev, "PASS",
                           "%s (%s)" % (title, os.path.relpath(present[0], ctx.root)), [], "")
    return CheckResult(
        cid, dim, sev, "WARN", title,
        [Finding(snippet="no PrivacyInfo.xcprivacy found (pure library packages may omit)")],
        "Add a `PrivacyInfo.xcprivacy` declaring `NSPrivacyTracking=false`, empty "
        "`NSPrivacyTrackingDomains`, accurate required-reason APIs.",
    )


def check_kids_privacy_tracking_false(ctx):
    cid, dim, sev = "kids-privacy-tracking-false", "kids-safety", "error"
    title = "Privacy manifest declares NSPrivacyTracking=false"
    if not ctx.xcprivacy:
        return CheckResult(cid, dim, sev, "NA", title + " (no manifest)", [], "")
    findings = []
    for p in ctx.xcprivacy:
        parsed = _read_plist(p)
        flagged = False
        if isinstance(parsed, dict):
            if parsed.get("NSPrivacyTracking") is True:
                findings.append(Finding(file=p, snippet="NSPrivacyTracking = true"))
                flagged = True
        if not flagged:
            text = strip_xml_comments(ctx.text(p))
            m = re.search(r"<key>\s*NSPrivacyTracking\s*</key>\s*<true\s*/>", text)
            if m:
                line_no = text.count("\n", 0, m.start()) + 1
                findings.append(Finding(file=p, line=line_no, snippet="NSPrivacyTracking = true"))
    if findings:
        return CheckResult(cid, dim, sev, "FAIL", title, findings,
                           "Set NSPrivacyTracking to <false/>; keep NSPrivacyTrackingDomains empty.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_kids_sensitive_permission_strings(ctx):
    cid, dim, sev = "kids-sensitive-permission-strings", "kids-safety", "warn"
    title = "Sensitive permission usage strings"
    keys = (
        "NSCameraUsageDescription|NSMicrophoneUsageDescription|NSLocationWhenInUseUsageDescription|"
        "NSLocationAlwaysAndWhenInUseUsageDescription|NSLocationAlwaysUsageDescription|"
        "NSContactsUsageDescription|NSPhotoLibraryUsageDescription|NSPhotoLibraryAddUsageDescription|"
        "NSBluetoothAlwaysUsageDescription|NSBluetoothPeripheralUsageDescription|"
        "NSCalendarsUsageDescription|NSRemindersUsageDescription|NSMotionUsageDescription|"
        "NSSpeechRecognitionUsageDescription|NSFaceIDUsageDescription|NSHealthShareUsageDescription|"
        "NSHealthUpdateUsageDescription"
    )
    files = sorted(set(ctx.info_plists + ctx.all_plists))
    if not files:
        return CheckResult(cid, dim, sev, "NA", title + " (no plist)", [], "")
    findings = grep_files(ctx, files, r"<key>\s*(" + keys + r")\s*</key>", strip_xml=True)
    if findings:
        return CheckResult(cid, dim, sev, "WARN", title, findings,
                           "Remove unused permission keys; for kept ones confirm a clear, "
                           "child-appropriate, non-empty usage string and a real gated mechanic.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


# ============================ 6.6 accessibility ============================ #


def check_a11y_controls_vs_labels_ratio(ctx):
    cid, dim, sev = "a11y-controls-vs-labels-ratio", "accessibility", "warn"
    title = "Interactive controls have accessibility labels"
    if not ctx.has_ui_framework():
        return CheckResult(cid, dim, sev, "NA", title + " (model-only package)", [], "")
    control_pat = (
        r"\.onTapGesture\b|\.onLongPressGesture\b|"
        r"\.gesture\s*\(\s*(?:Tap|LongPress|DragGesture)|"
        r"(?<![\w.])Button\s*[\({]|\baddTarget\s*\(|\.addGestureRecognizer\s*\("
    )
    label_pat = (
        r"\.accessibilityLabel\b|\.accessibilityValue\b|\.accessibilityAddTraits\b|"
        r"\.accessibilityElement\b|\.accessibilityRepresentation\b|setAccessibilityLabel\b|"
        r"accessibilityLabel\s*=|isAccessibilityElement\s*="
    )
    total_controls = count_matches(ctx, ctx.swift_files, control_pat, strip_comments=True)
    total_labels = count_matches(ctx, ctx.swift_files, label_pat, strip_comments=True)
    if total_controls == 0:
        return CheckResult(cid, dim, sev, "NA", title + " (no interactive controls)", [], "")
    ratio = total_labels / total_controls
    detail = "%d label hits / %d controls (ratio %.2f)" % (total_labels, total_controls, ratio)
    if ratio >= 0.5:
        return CheckResult(cid, dim, sev, "PASS", "%s — %s" % (title, detail), [], "")
    note = " — NO accessibility labels at all" if total_labels == 0 else ""
    return CheckResult(
        cid, dim, sev, "WARN", "%s%s" % (title, note),
        [Finding(snippet=detail)],
        "Add `.accessibilityLabel`/`.accessibilityValue`/`.accessibilityAddTraits` to icon-only "
        "controls and the board/HUD; spot-check the VoiceOver rotor.",
    )


def check_a11y_fixed_font_size(ctx):
    cid, dim, sev = "a11y-fixed-font-size", "accessibility", "warn"
    title = "No fixed (non-Dynamic-Type) font sizes"
    pattern = (
        r"\.font\(\s*\.system\(\s*size\s*:|"
        r"\.font\(\s*Font\.system\(\s*size\s*:|"
        r"UIFont\.systemFont\(\s*ofSize\s*:|"
        r"UIFont\(\s*name\s*:[^)]*size\s*:"
    )
    findings = grep_files(ctx, ctx.swift_files, pattern, strip_comments=True)
    if findings:
        return CheckResult(cid, dim, sev, "WARN", title, findings,
                           "Use semantic styles (`.body`/`.title2`) or `.system(size:relativeTo:)` + "
                           "`@ScaledMetric`; UIKit `UIFontMetrics.scaledFont` + "
                           "`adjustsFontForContentSizeCategory`.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_a11y_reduce_motion(ctx):
    cid, dim, sev = "a11y-reduce-motion", "accessibility", "warn"
    title = "Reduce Motion consulted when animating"
    anim_pat = (
        r"withAnimation\s*\(|\.animation\s*\(|\.transition\s*\(|UIView\.animate\b|"
        r"\.spring\b|\.easeIn|\.easeOut|\.easeInOut|repeatForever"
    )
    aware_pat = r"accessibilityReduceMotion|isReduceMotionEnabled"
    anim = count_matches(ctx, ctx.swift_files, anim_pat, strip_comments=True)
    aware = count_matches(ctx, ctx.swift_files, aware_pat, strip_comments=True)
    if anim == 0 or aware >= 1:
        return CheckResult(cid, dim, sev, "PASS",
                           "%s (%d animations, %d reduce-motion guards)" % (title, anim, aware), [], "")
    return CheckResult(
        cid, dim, sev, "WARN", title,
        [Finding(snippet="%d animation sites but Reduce Motion never consulted" % anim)],
        "Read `@Environment(\\.accessibilityReduceMotion)` (or "
        "`UIAccessibility.isReduceMotionEnabled`) and gate/replace large motion with fades.",
    )


def check_a11y_spritekit_no_accessibility(ctx):
    cid, dim, sev = "a11y-spritekit-no-accessibility", "accessibility", "warn"
    title = "SpriteKit play surface exposes accessibility"
    # Exclude the skill's spritekit-scene-template.swift and any vendored copy.
    sk_files = [p for p in ctx.spritekit_files
                if os.path.basename(p) != "spritekit-scene-template.swift"]
    if not sk_files:
        return CheckResult(cid, dim, sev, "NA", title + " (no SpriteKit files)", [], "")
    aware_pat = (
        r"accessibilityElements\s*=|UIAccessibilityElement\b|isAccessibilityElement\s*=|"
        r"accessibilityFrame|\.accessibilityLabel\b"
    )
    if count_matches(ctx, sk_files, aware_pat, strip_comments=True) >= 1:
        return CheckResult(cid, dim, sev, "PASS", title, [], "")
    return CheckResult(
        cid, dim, sev, "WARN", title,
        [Finding(snippet="SpriteKit scene(s) expose no accessibility elements")],
        "Build `UIAccessibilityElement`s with `accessibilityFrame`/labels, assign to "
        "`view.accessibilityElements`, update on state change; or add an accessible SwiftUI/UIKit "
        "overlay.",
    )


def check_a11y_color_only_feedback(ctx):
    cid, dim, sev = "a11y-color-only-feedback", "accessibility", "info"
    title = "Color is not the only state cue (manual)"
    if not ctx.has_ui_framework():
        return CheckResult(cid, dim, sev, "NA", title + " (model-only)", [], "")
    return CheckResult(
        cid, dim, sev, "INFO", title + " — verify by hand",
        [Finding(snippet="Confirm every color-coded distinction also has shape/symbol/label.")],
        "Pair color with an SF Symbol/shape/border or `.accessibilityValue` text.",
    )


def check_a11y_touch_target_too_small(ctx):
    cid, dim, sev = "a11y-touch-target-too-small", "accessibility", "info"
    title = "Touch targets >= 44pt"
    pattern = r"\.frame\(\s*(?:width|height)\s*:\s*(?:[0-9]|[1-3][0-9]|4[0-3])(?:\.\d+)?\s*[,)]"
    findings = grep_files(ctx, ctx.swift_files, pattern, strip_comments=True)
    if findings:
        return CheckResult(cid, dim, sev, "INFO", title + " (small frames found)", findings,
                           "Ensure interactive elements are >=44x44 pt or expand hit area with "
                           "`.contentShape(Rectangle())`+padding/`.frame(minWidth:44,minHeight:44)`.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_a11y_decorative_nodes_not_hidden(ctx):
    cid, dim, sev = "a11y-decorative-nodes-not-hidden", "accessibility", "info"
    title = "Decorative elements hidden from a11y"
    if not ctx.has_ui_framework():
        return CheckResult(cid, dim, sev, "NA", title + " (model-only)", [], "")
    pattern = (
        r"\.accessibilityHidden\s*\(\s*true\s*\)|accessibilityElementsHidden\s*=\s*true|"
        r"\.accessibilityElement\s*\(\s*children\s*:\s*\.ignore"
    )
    if count_matches(ctx, ctx.swift_files, pattern, strip_comments=True) >= 1:
        return CheckResult(cid, dim, sev, "PASS", title, [], "")
    return CheckResult(
        cid, dim, sev, "INFO", title + " (none hidden — review focus order)",
        [Finding(snippet="no .accessibilityHidden(true) / children:.ignore found")],
        "Mark decorative Image/shapes `.accessibilityHidden(true)`; collapse composites with "
        "`.accessibilityElement(children:.ignore)`+label.",
    )


def check_a11y_timing_only_challenge(ctx):
    cid, dim, sev = "a11y-timing-only-challenge", "accessibility", "info"
    title = "Timing-based challenge (verify relaxed mode)"
    pattern = (
        r"\bTimer\.scheduledTimer\b|\bcountdown\b|\btimeRemaining\b|\btimeLimit\b|"
        r"asyncAfter\b|\.timeout\b"
    )
    findings = grep_files(ctx, ctx.swift_files, pattern, strip_comments=True)
    if findings:
        return CheckResult(cid, dim, sev, "INFO", title, findings,
                           "Add a no-timer/extended-time settings toggle; don't make speed the sole "
                           "win condition.")
    return CheckResult(cid, dim, sev, "PASS", title + " (none)", [], "")


def check_a11y_localized_vs_hardcoded_labels(ctx):
    cid, dim, sev = "a11y-localized-vs-hardcoded-labels", "accessibility", "info"
    title = "Accessibility labels localization-readiness"
    pattern = r'\.accessibility(?:Label|Value|Hint)\s*\(\s*"[^"]+"\s*\)'
    findings = grep_files(ctx, ctx.swift_files, pattern, strip_comments=True)
    if findings:
        return CheckResult(cid, dim, sev, "INFO", title + " (literal strings found)", findings,
                           "If localizing: use `String(localized:)`/`LocalizedStringKey`/"
                           "`NSLocalizedString`.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


# ============================ 6.7 assets-licensing ========================= #


def check_deps_spm_thirdparty(ctx):
    cid, dim, sev = "deps-spm-thirdparty", "assets-licensing", "warn"
    title = "SPM third-party packages"
    if not ctx.package_swift:
        return CheckResult(cid, dim, sev, "NA", title + " (no Package.swift)", [], "")
    findings = grep_files(ctx, ctx.package_swift,
                          r"\.package\s*\(\s*(?:name\s*:[^,]*,\s*)?url\s*:")
    if findings:
        return CheckResult(cid, dim, sev, "WARN", title, findings,
                           "Justify each (why Apple frameworks won't do), verify license, document "
                           "in handoff; prefer removal.")
    return CheckResult(cid, dim, sev, "PASS", title + " (none)", [], "")


def check_deps_podfile_pods(ctx):
    cid, dim, sev = "deps-podfile-pods", "assets-licensing", "warn"
    title = "CocoaPods dependencies"
    if not ctx.podfiles:
        return CheckResult(cid, dim, sev, "NA", title + " (no Podfile)", [], "")
    findings = grep_files(ctx, ctx.podfiles, r"^\s*pod\s+['\"]", flags=re.MULTILINE)
    if findings:
        return CheckResult(cid, dim, sev, "WARN", title, findings,
                           "Justify each pod, verify license, audit for tracking SDKs (kids), prefer "
                           "Apple-framework/SPM.")
    return CheckResult(cid, dim, sev, "PASS", title + " (none)", [], "")


def check_deps_cartfile(ctx):
    cid, dim, sev = "deps-cartfile", "assets-licensing", "warn"
    title = "Carthage dependencies"
    if not ctx.cartfiles:
        return CheckResult(cid, dim, sev, "NA", title + " (no Cartfile)", [], "")
    findings = grep_files(ctx, ctx.cartfiles, r"^\s*(?:github|git|binary)\s+\"", flags=re.MULTILINE)
    if findings:
        return CheckResult(cid, dim, sev, "WARN", title, findings,
                           "Justify/remove each, verify licenses, audit for tracking SDKs.")
    return CheckResult(cid, dim, sev, "PASS", title + " (none)", [], "")


_LARGE_MEDIA_EXT = (".png", ".jpg", ".jpeg", ".gif", ".mp3", ".m4a", ".caf", ".wav",
                    ".aiff", ".mp4", ".mov", ".ttf", ".otf")


def check_assets_large_binary_media(ctx):
    cid, dim, sev = "assets-large-binary-media", "assets-licensing", "warn"
    title = "Large bundled media (>256 KB) — provenance"
    findings = []
    for path in ctx.asset_files:
        if not path.lower().endswith(_LARGE_MEDIA_EXT):
            continue
        try:
            size = os.path.getsize(path)
        except OSError:
            continue
        if size > 256 * 1024:
            findings.append(Finding(file=path, snippet="%.1f KB" % (size / 1024.0)))
    if findings:
        return CheckResult(cid, dim, sev, "WARN", title, findings,
                           "Record provenance/license per file (user-created/royalty-free with kept "
                           "license) or replace with in-code vector/SF Symbol art.")
    return CheckResult(cid, dim, sev, "PASS", title + " (none)", [], "")


def check_assets_video_media(ctx):
    cid, dim, sev = "assets-video-media", "assets-licensing", "info"
    title = "Bundled video clips"
    findings = [Finding(file=p) for p in ctx.asset_files if p.lower().endswith((".mp4", ".mov", ".m4v"))]
    if findings:
        return CheckResult(cid, dim, sev, "INFO", title, findings,
                           "Verify each clip's license/necessity or replace with in-code animation; "
                           "keep a license record.")
    return CheckResult(cid, dim, sev, "PASS", title + " (none)", [], "")


_IP_TOKENS = (
    r"mario|luigi|zelda|pokemon|pikachu|sonic|minecraft|fortnite|roblox|mickey|disney|marvel|"
    r"spider[-_ ]?man|batman|superman|pixar|nintendo|sega|peppa|bluey|paw[-_ ]?patrol|frozen|"
    r"elsa|spongebob|hello[-_ ]?kitty|barbie|lego|star[-_ ]?wars|harry[-_ ]?potter|among[-_ ]?us|"
    r"squid[-_ ]?game"
)
_ASSET_FILE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".svg", ".mp3", ".m4a", ".caf",
                   ".wav", ".mp4", ".mov", ".ttf", ".otf")


def check_assets_copyrighted_name_filenames(ctx):
    cid, dim, sev = "assets-copyrighted-name-filenames", "assets-licensing", "warn"
    title = "No IP-suggestive asset filenames"
    rx = re.compile(_IP_TOKENS, re.IGNORECASE)
    findings = []
    for path in ctx.asset_files:
        if not path.lower().endswith(_ASSET_FILE_EXT):
            continue
        if rx.search(path):
            findings.append(Finding(file=path, snippet="path matches an IP token"))
    if findings:
        return CheckResult(cid, dim, sev, "WARN", title, findings,
                           "Confirm it isn't that IP; if it is, remove + replace with original art "
                           "and rename semantically (`tile_grass`).")
    return CheckResult(cid, dim, sev, "PASS", title + " (none)", [], "")


def check_assets_copyrighted_name_imagesets(ctx):
    cid, dim, sev = "assets-copyrighted-name-imagesets", "assets-licensing", "warn"
    title = "No IP-suggestive asset-catalog set names"
    # Same token list minus among/squid.
    tokens = _IP_TOKENS.replace(r"|among[-_ ]?us", "").replace(r"|squid[-_ ]?game", "")
    rx = re.compile(tokens, re.IGNORECASE)
    findings = []
    for d in ctx.imageset_dirs:
        if rx.search(os.path.basename(d)):
            findings.append(Finding(file=d, snippet="set name matches an IP token"))
    if findings:
        return CheckResult(cid, dim, sev, "WARN", title, findings,
                           "Verify contents; rename set semantically if not the IP.")
    return CheckResult(cid, dim, sev, "PASS", title + " (none)", [], "")


def check_assets_runtime_asset_download(ctx):
    cid, dim, sev = "assets-runtime-asset-download", "assets-licensing", "warn"
    title = "No runtime asset downloads"
    pattern = (
        r"(?:URLSession|URL\s*\(\s*string\s*:|dataTask|contentsOf\s*:\s*URL)\s*.{0,80}"
        r"\.(?:png|jpg|jpeg|gif|mp3|m4a|wav|mp4|mov|ttf|otf)"
    )
    findings = grep_files(ctx, ctx.swift_files, pattern, flags=re.IGNORECASE | re.DOTALL,
                          strip_comments=True)
    if findings:
        return CheckResult(cid, dim, sev, "WARN", title, findings,
                           "Bundle owned/licensed assets (offline-first); if a remote fetch is truly "
                           "required, document why and ensure no personal data.")
    return CheckResult(cid, dim, sev, "PASS", title + " (none)", [], "")


def check_assets_thirdparty_font_registration(ctx):
    cid, dim, sev = "assets-thirdparty-font-registration", "assets-licensing", "info"
    title = "Bundled (UIAppFonts) fonts"
    if not ctx.info_plists:
        return CheckResult(cid, dim, sev, "NA", title + " (no Info.plist)", [], "")
    findings = grep_files(ctx, ctx.info_plists, r"UIAppFonts", strip_xml=True)
    if findings:
        return CheckResult(cid, dim, sev, "INFO", title, findings,
                           "Confirm an app-embedding license for each bundled font; prefer Apple "
                           "system fonts/Dynamic Type.")
    return CheckResult(cid, dim, sev, "PASS", title + " (none)", [], "")


def check_assets_license_records_present(ctx):
    cid, dim, sev = "assets-license-records-present", "assets-licensing", "info"
    title = "Asset license/attribution records (manual)"
    has_media = any(p.lower().endswith(_LARGE_MEDIA_EXT) for p in ctx.asset_files)
    if not has_media:
        return CheckResult(cid, dim, sev, "PASS", title + " (no bundled media detected)", [], "")
    return CheckResult(
        cid, dim, sev, "INFO", title,
        [Finding(snippet="Bundled media detected — verify each asset's source/license is recorded.")],
        "Create an attributions/credits record listing each third-party asset, source, and "
        "license; provide a risk list, not a guarantee.",
    )


# ============================ 6.8 build-tests ============================== #


def check_tests_target_present(ctx):
    cid, dim, sev = "tests-target-present", "build-tests", "warn"
    title = "Unit test target present"
    # Test dir with a .swift file (excluding *UITests-only).
    has_test_dir_swift = any(is_test_path(p) for p in ctx.swift_files)
    has_test_target = any(re.search(r"\.testTarget\s*\(", ctx.text(p)) for p in ctx.package_swift)
    import_re = re.compile(r"^\s*import\s+(XCTest|Testing)\b", re.MULTILINE)
    has_test_import = any(import_re.search(strip_comments_text(ctx.text(p))) for p in ctx.swift_files)
    if has_test_dir_swift or has_test_target or has_test_import:
        return CheckResult(cid, dim, sev, "PASS", title, [], "")
    return CheckResult(
        cid, dim, sev, "WARN", title,
        [Finding(snippet="no test dir / .testTarget / XCTest|Testing import found")],
        "Add a `.testTarget`/Xcode test target covering scoring, win/lose, valid moves, level "
        "decoding, state transitions (mirror `examples/MemoryMatch/Tests`).",
    )


def check_tests_have_cases(ctx):
    cid, dim, sev = "tests-have-cases", "build-tests", "info"
    title = "Test files contain real cases/assertions"
    # Skip if tests-target-present would fail (no test dir at all).
    has_test_dir = any(is_test_path(p) for p in ctx.swift_files)
    has_test_target = any(re.search(r"\.testTarget\s*\(", ctx.text(p)) for p in ctx.package_swift)
    if not (has_test_dir or has_test_target):
        return CheckResult(cid, dim, sev, "NA", title + " (no test target)", [], "")
    pattern = (
        r"(^|\n)\s*(@Test\b|func\s+test[A-Z0-9_]|#expect\b|#require\b|\bXCTAssert\w*\b|"
        r"class\s+\w+\s*:\s*XCTestCase\b)"
    )
    findings = grep_files(ctx, ctx.test_swift, pattern, flags=re.MULTILINE, strip_comments=True)
    if findings:
        return CheckResult(cid, dim, sev, "PASS", "%s (%d)" % (title, len(findings)), [], "")
    return CheckResult(
        cid, dim, sev, "INFO", title + " (empty scaffold)",
        [Finding(snippet="test target/dir exists but no @Test/XCTAssert cases found")],
        "Add real cases: `@Test func winWhenAllMatched() { #expect(...) }` or "
        "`func testScores() { XCTAssertEqual(...) }`.",
    )


def check_tests_import_framework(ctx):
    cid, dim, sev = "tests-import-framework", "build-tests", "info"
    title = "Test files import Testing/XCTest"
    if not ctx.test_swift:
        return CheckResult(cid, dim, sev, "NA", title + " (no test files)", [], "")
    import_re = re.compile(r"^\s*import\s+(Testing|XCTest)\b", re.MULTILINE)
    findings = []
    for p in ctx.test_swift:
        if not import_re.search(strip_comments_text(ctx.text(p))):
            findings.append(Finding(file=p, snippet="no `import Testing`/`import XCTest` (fixture?)"))
    if findings:
        return CheckResult(cid, dim, sev, "INFO", title + " (some files import neither)", findings,
                           "Add `import Testing` (Xcode 16+) or `import XCTest` to actual test files.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def check_spm_testable_import(ctx):
    cid, dim, sev = "spm-testable-import", "build-tests", "info"
    title = "SPM tests use @testable import"
    if not ctx.package_swift or not ctx.test_swift:
        return CheckResult(cid, dim, sev, "NA", title + " (no SPM tests)", [], "")
    rx = re.compile(r"^\s*@testable\s+import\s+\w+", re.MULTILINE)
    if any(rx.search(strip_comments_text(ctx.text(p))) for p in ctx.test_swift):
        return CheckResult(cid, dim, sev, "PASS", title, [], "")
    return CheckResult(
        cid, dim, sev, "INFO", title + " (none — public-surface tests only)",
        [Finding(snippet="no @testable import found in SPM tests")],
        "Use `@testable import <Game>Core` to reach internal model types if needed.",
    )


def check_ci_workflow_present(ctx):
    cid, dim, sev = "ci-workflow-present", "build-tests", "warn"
    title = "CI workflow present"
    if ctx.workflow_files:
        return CheckResult(cid, dim, sev, "PASS",
                           "%s (%d GitHub workflow file(s))" % (title, len(ctx.workflow_files)), [], "")
    # Probe other CI systems.
    for rel in (".gitlab-ci.yml", "bitrise.yml", os.path.join(".circleci", "config.yml")):
        if os.path.exists(os.path.join(ctx.root, rel)):
            return CheckResult(cid, dim, sev, "PASS", "%s (%s)" % (title, rel), [], "")
    return CheckResult(
        cid, dim, sev, "WARN", title,
        [Finding(snippet="no .github/workflows/*.yml or other CI config found")],
        "Add a CI workflow running `swift build`/`swift test` on push/PR (see `examples/MemoryMatch` "
        "CI).",
    )


def check_ci_runs_build_and_test(ctx):
    cid, dim, sev = "ci-runs-build-and-test", "build-tests", "warn"
    title = "CI builds and tests Swift"
    if not ctx.workflow_files:
        return CheckResult(cid, dim, sev, "NA", title + " (no workflow)", [], "")
    pattern = (
        r"(swift\s+(build|test)\b|"
        r"xcodebuild\s+(?:.*\s)?(build|test|build-for-testing|test-without-building)\b)"
    )
    findings = grep_files(ctx, ctx.workflow_files, pattern)
    if findings:
        return CheckResult(cid, dim, sev, "PASS", title, [], "")
    return CheckResult(
        cid, dim, sev, "WARN", title,
        [Finding(snippet="a workflow exists but no swift build/test or xcodebuild build/test step")],
        "Add explicit `swift build && swift test` (SPM) or `xcodebuild test -scheme <S> "
        "-destination <D>` steps.",
    )


def check_build_dirs_gitignored(ctx):
    cid, dim, sev = "build-dirs-gitignored", "build-tests", "warn"
    title = "Build dirs (.build/DerivedData) gitignored"
    if ctx.gitignore is None:
        return CheckResult(cid, dim, sev, "NA", title + " (no .gitignore)", [], "")
    text = ctx.text(ctx.gitignore)
    # Strip comment lines.
    active = "\n".join(ln for ln in text.split("\n") if not ln.lstrip().startswith("#"))
    needs = []
    if ctx.package_swift:  # SPM present → expect .build/
        if not re.search(r"(^|/)(\.build)/?\s*$", active, re.MULTILINE):
            needs.append(".build/")
    if ctx.has_xcodeproj or ctx.has_xcworkspace:  # Xcode present → expect DerivedData/
        if not re.search(r"(^|/)(DerivedData)/?\s*$", active, re.MULTILINE):
            needs.append("DerivedData/")
    if needs:
        return CheckResult(cid, dim, sev, "WARN", title,
                           [Finding(file=ctx.gitignore, snippet="missing: " + ", ".join(needs))],
                           "Add `.build/` and `DerivedData/` to `.gitignore`.")
    return CheckResult(cid, dim, sev, "PASS", title, [], "")


def _nearest_spm_dir(ctx):
    if not ctx.package_swift:
        return None
    # Prefer the one nearest the root.
    best = min(ctx.package_swift, key=lambda p: os.path.relpath(p, ctx.root).count(os.sep))
    return os.path.dirname(best)


def check_build_run_spm(ctx):
    cid, dim, sev = "build-run-spm", "build-tests", "error"
    title = "swift build (SPM) succeeds"
    if not ctx.opts["build"]:
        return CheckResult(cid, dim, sev, "SKIP", title + " (opt-in: pass --build)",
                           [Finding(snippet="run with --build to compile the SPM package")], "")
    pkg_dir = _nearest_spm_dir(ctx)
    if pkg_dir is None:
        return CheckResult(cid, dim, sev, "SKIP", title + " (no Package.swift — Xcode-only)",
                           [Finding(snippet="use scripts/verify-ios-project.sh / xcodebuild instead")], "")
    if which("swift") is None:
        return CheckResult(cid, dim, sev, "SKIP", title + " (swift not on PATH — not built here)",
                           [Finding(snippet="swift build --package-path %s" % pkg_dir)], "")
    found, code, out = run_cmd(["swift", "build", "--package-path", pkg_dir], timeout=600)
    ctx.cache["spm_build_ok"] = (found and code == 0)
    if found and code == 0:
        return CheckResult(cid, dim, sev, "PASS", title, [], "")
    tail = [ln for ln in (out or "").splitlines() if ln.strip()][-12:]
    kind = "dependency-resolution" if re.search(r"(?i)resolv|dependenc", out or "") and code != 0 \
        and "error:" not in (out or "").lower() else "compile"
    findings = [Finding(snippet=ln[:200]) for ln in tail] or [Finding(snippet="build failed")]
    return CheckResult(cid, dim, sev, "FAIL", title + " (%s failure)" % kind, findings,
                       "Fix compiler diagnostics; only claim a build passed if it ran and exited 0.")


def check_test_run_spm(ctx):
    cid, dim, sev = "test-run-spm", "build-tests", "error"
    title = "swift test (SPM) succeeds"
    if not ctx.opts["build"]:
        return CheckResult(cid, dim, sev, "SKIP", title + " (opt-in: pass --build)",
                           [Finding(snippet="run with --build to run the SPM tests")], "")
    pkg_dir = _nearest_spm_dir(ctx)
    if pkg_dir is None:
        return CheckResult(cid, dim, sev, "SKIP", title + " (no Package.swift)",
                           [Finding(snippet="no SPM package to test")], "")
    if which("swift") is None:
        return CheckResult(cid, dim, sev, "SKIP", title + " (swift not on PATH — not run here)",
                           [Finding(snippet="swift test --package-path %s" % pkg_dir)], "")
    has_test_target = any(re.search(r"\.testTarget\s*\(", ctx.text(p)) for p in ctx.package_swift)
    if not has_test_target:
        return CheckResult(cid, dim, "info", "INFO", title + " (no .testTarget — nothing to test)",
                           [Finding(snippet="package declares no test target")], "")
    if ctx.cache.get("spm_build_ok") is False:
        return CheckResult(cid, dim, sev, "SKIP", title + " (skipped — build failed first)",
                           [Finding(snippet="fix the build, then re-run")], "")
    found, code, out = run_cmd(["swift", "test", "--package-path", pkg_dir], timeout=600)
    if found and code == 0:
        return CheckResult(cid, dim, sev, "PASS", title, [], "")
    tail = [ln for ln in (out or "").splitlines() if ln.strip()][-12:]
    findings = [Finding(snippet=ln[:200]) for ln in tail] or [Finding(snippet="tests failed")]
    return CheckResult(cid, dim, sev, "FAIL", title, findings,
                       "Inspect failing assertions in `swift test` output; fix model or test. From "
                       "package dir: `swift test`.")


# --------------------------------------------------------------------------- #
# Check registry (ordered by dimension)
# --------------------------------------------------------------------------- #

CHECKS = [
    # environment
    check_env_swift_toolchain_present,
    check_env_swift6_language_version,
    check_env_xcodebuild_present,
    check_env_swift_format_present,
    check_env_project_container,
    check_env_detect_spm,
    check_spm_tools_version_declared,
    check_spm_tools_version_min6,
    check_env_swift_format_config,
    check_env_swift_format_config_valid,
    check_env_third_party_dep_managers,
    check_env_build_discovery_advisory,
    # architecture
    check_arch_models_no_ui_imports,
    check_arch_state_machine_present,
    check_arch_state_terminal_case,
    check_arch_no_boolean_state_flags,
    check_arch_folder_layout,
    check_arch_scenes_folder_spritekit,
    check_arch_views_no_rules,
    # swift-quality
    check_swift_force_try,
    check_swift_force_cast,
    check_swift_iuo_property,
    check_swift_force_unwrap_external,
    check_swift_unchecked_sendable,
    check_swift_dispatchqueue,
    check_swift_leftover_print,
    check_swift_todo_fixme_count,
    check_swift_retain_cycle_closure,
    check_swift_format_lint,
    # performance
    check_perf_dt_clamp_missing,
    check_perf_alloc_in_update_loop,
    check_perf_interpolation_in_update_loop,
    check_perf_skaction_rebuilt_in_loop,
    check_perf_addchild_churn_no_pool,
    check_perf_per_pixel_physics_body,
    check_perf_missing_showsfps_debug,
    check_perf_render_loop_on_static_screen,
    check_perf_swiftui_timeline_dt,
    check_perf_oversized_textures,
    # kids-safety
    check_kids_no_tracking_sdk_imports,
    check_kids_no_tracking_sdk_dependencies,
    check_kids_no_idfa_att,
    check_kids_no_att_usage_string,
    check_kids_no_external_links,
    check_kids_no_cleartext_http,
    check_kids_no_ats_arbitrary_loads,
    check_kids_no_hardcoded_secrets,
    check_kids_privacy_manifest_present,
    check_kids_privacy_tracking_false,
    check_kids_sensitive_permission_strings,
    # accessibility
    check_a11y_controls_vs_labels_ratio,
    check_a11y_fixed_font_size,
    check_a11y_reduce_motion,
    check_a11y_spritekit_no_accessibility,
    check_a11y_color_only_feedback,
    check_a11y_touch_target_too_small,
    check_a11y_decorative_nodes_not_hidden,
    check_a11y_timing_only_challenge,
    check_a11y_localized_vs_hardcoded_labels,
    # assets-licensing
    check_deps_spm_thirdparty,
    check_deps_podfile_pods,
    check_deps_cartfile,
    check_assets_large_binary_media,
    check_assets_video_media,
    check_assets_copyrighted_name_filenames,
    check_assets_copyrighted_name_imagesets,
    check_assets_runtime_asset_download,
    check_assets_thirdparty_font_registration,
    check_assets_license_records_present,
    # build-tests
    check_tests_target_present,
    check_tests_have_cases,
    check_tests_import_framework,
    check_spm_testable_import,
    check_ci_workflow_present,
    check_ci_runs_build_and_test,
    check_build_dirs_gitignored,
    check_build_run_spm,
    check_test_run_spm,
]


# --------------------------------------------------------------------------- #
# Runner / reporting
# --------------------------------------------------------------------------- #


def run_checks(ctx, only_dims):
    results = []
    for fn in CHECKS:
        # Each check reports its own dimension; all checks are cheap (sub-second, file reads are
        # cached), so we run then filter by --only. The only genuinely expensive checks (--build)
        # are independently gated by ctx.run_build, so --only never triggers a build.
        try:
            result = fn(ctx)
        except Exception as e:  # any unexpected error → SKIP, never abort
            result = CheckResult(
                getattr(fn, "__name__", "check"), "environment", "warn", "SKIP",
                "internal check error",
                [Finding(snippet="%s: %s" % (fn.__name__, e))],
                "This is a swift-doctor bug; the check was skipped.",
            )
        if only_dims is not None and result.dimension not in only_dims:
            continue
        results.append(result)
    return results


def use_unicode():
    if os.environ.get("NO_COLOR"):
        return False
    if not sys.stdout.isatty():
        return False
    enc = (sys.stdout.encoding or "").lower()
    if "utf" not in enc:
        return False
    return True


def use_color():
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


_ANSI = {
    "PASS": "\033[32m", "NA": "\033[32m",
    "WARN": "\033[33m",
    "FAIL": "\033[31m",
    "INFO": "\033[36m",
    "SKIP": "\033[90m",
    "reset": "\033[0m",
}


def colorize(text, status, color):
    if not color:
        return text
    return _ANSI.get(status, "") + text + _ANSI["reset"]


DIMENSION_TITLES = {
    "environment": "Environment",
    "architecture": "Architecture",
    "swift-quality": "Swift quality",
    "performance": "Performance",
    "kids-safety": "Kids safety",
    "accessibility": "Accessibility",
    "assets-licensing": "Assets & licensing",
    "build-tests": "Build & tests",
}


def compute_summary(results):
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0, "INFO": 0, "SKIP": 0, "NA": 0}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    errors = counts["FAIL"]
    warnings = counts["WARN"]
    return counts, errors, warnings


def health_label(errors, warnings, strict):
    if errors >= 1:
        return "NEEDS ATTENTION"
    if warnings >= 1:
        return "OK" if not strict else "NEEDS ATTENTION"
    return "HEALTHY"


def print_human(ctx, results, opts):
    glyphs = GLYPHS_UNICODE if use_unicode() else GLYPHS_ASCII
    color = use_color()
    out = []
    out.append("%s — diagnosing %s" % (TOOL_NAME, ctx.root))
    out.append("")

    by_dim = {}
    for r in results:
        by_dim.setdefault(r.dimension, []).append(r)

    for dim in DIMENSIONS:
        if dim not in by_dim:
            continue
        out.append(DIMENSION_TITLES.get(dim, dim))
        for r in by_dim[dim]:
            if opts["quiet"] and r.status in ("PASS", "NA", "INFO"):
                continue
            glyph = glyphs[r.status]
            line = "  %s %-36s %s" % (colorize(glyph, r.status, color), r.id, r.title)
            out.append(line)
            if r.status not in ("PASS", "NA"):
                for f in r.findings:
                    loc = ""
                    if f.file:
                        loc = os.path.relpath(f.file, ctx.root)
                        if f.line:
                            loc += ":%d" % f.line
                    detail = f.snippet or ""
                    if loc and detail:
                        out.append("      %s — %s" % (loc, detail))
                    elif loc:
                        out.append("      %s" % loc)
                    elif detail:
                        out.append("      %s" % detail)
                if r.remediation:
                    out.append("      → %s" % r.remediation if use_unicode() else "      -> %s" % r.remediation)
        out.append("")

    counts, errors, warnings = compute_summary(results)
    total = len(results)
    g = GLYPHS_UNICODE if use_unicode() else GLYPHS_ASCII
    summary = (
        "Summary: %d checks · %d %s · %d %s · %d %s · %d info · %d skipped · %d n/a"
        if use_unicode() else
        "Summary: %d checks | %d %s | %d %s | %d %s | %d info | %d skipped | %d n/a"
    ) % (
        total,
        counts["PASS"], g["PASS"],
        counts["WARN"], g["WARN"],
        counts["FAIL"], g["FAIL"],
        counts["INFO"],
        counts["SKIP"],
        counts["NA"],
    )
    out.append(summary)
    health = health_label(errors, warnings, opts["strict"])
    out.append("Overall health: %s (%d errors, %d warnings)" % (health, errors, warnings))
    sys.stdout.write("\n".join(out) + "\n")


def print_json(ctx, results, opts):
    counts, errors, warnings = compute_summary(results)
    exit_code = compute_exit_code(errors, warnings, opts["strict"])
    health = health_label(errors, warnings, opts["strict"]).replace(" ", "_")
    payload = {
        "tool": TOOL_NAME,
        "version": TOOL_VERSION,
        "path": ctx.root,
        "options": {
            "build": opts["build"],
            "strict": opts["strict"],
            "only": opts["only"],
            "quiet": opts["quiet"],
        },
        "summary": {
            "total": len(results),
            "pass": counts["PASS"],
            "warn": counts["WARN"],
            "fail": counts["FAIL"],
            "info": counts["INFO"],
            "skip": counts["SKIP"],
            "na": counts["NA"],
            "errors": errors,
            "warnings": warnings,
            "health": health,
        },
        "exitCode": exit_code,
        "checks": [r.to_dict() for r in results],
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")


def compute_exit_code(errors, warnings, strict):
    if errors >= 1:
        return 1
    if strict and warnings >= 1:
        return 1
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def build_parser():
    p = argparse.ArgumentParser(
        prog="swift-doctor.py",
        description="Diagnose a Swift iOS/iPadOS game project against the swift-ios-game-studio "
                    "skill's standards (the analog of flutter doctor / brew doctor).",
        add_help=True,
    )
    p.add_argument("path", nargs="?", default=".", help="project root to diagnose (default: cwd)")
    p.add_argument("--json", action="store_true", help="emit a machine-readable JSON report")
    p.add_argument("--build", action="store_true",
                   help="opt-in: also run `swift build` then `swift test` for a detected SPM package")
    p.add_argument("--strict", action="store_true", help="warnings also fail the exit code")
    p.add_argument("--only", action="append", default=None, metavar="DIM",
                   help="run only the named dimension(s); comma-separated and/or repeated")
    p.add_argument("--quiet", action="store_true",
                   help="suppress PASS and INFO lines in the human report")
    return p


def parse_only(only_args):
    """Return a set of dimension ids, or None for all. Raises ValueError on unknown."""
    if not only_args:
        return None
    dims = set()
    for arg in only_args:
        for part in arg.split(","):
            part = part.strip()
            if not part:
                continue
            if part not in DIMENSIONS:
                raise ValueError(part)
            dims.add(part)
    return dims or None


def main(argv):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        # argparse exits 2 on usage error / 0 on -h; honor it.
        return e.code if isinstance(e.code, int) else 2

    # Resolve PATH.
    root = os.path.abspath(os.path.expanduser(args.path))
    if not os.path.isdir(root):
        sys.stderr.write("%s: error: PATH is not a directory: %s\n" % (TOOL_NAME, root))
        return 2

    # Parse --only.
    try:
        only_dims = parse_only(args.only)
    except ValueError as bad:
        sys.stderr.write(
            "%s: error: unknown dimension '%s'. Valid dimensions: %s\n"
            % (TOOL_NAME, bad, ", ".join(DIMENSIONS))
        )
        return 2

    opts = {
        "build": bool(args.build),
        "strict": bool(args.strict),
        "only": sorted(only_dims) if only_dims else None,
        "quiet": bool(args.quiet),
        "json": bool(args.json),
    }

    # Build context (cache cross-check state on it).
    try:
        ctx = Context(root)
        ctx.cache = {}
        ctx.opts = opts
    except Exception as e:
        sys.stderr.write("%s: fatal: could not analyze project: %s\n" % (TOOL_NAME, e))
        return 2

    results = run_checks(ctx, only_dims)

    counts, errors, warnings = compute_summary(results)
    exit_code = compute_exit_code(errors, warnings, opts["strict"])

    if opts["json"]:
        print_json(ctx, results, opts)
    else:
        print_human(ctx, results, opts)

    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
