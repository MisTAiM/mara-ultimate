"""
Fellowship Ultimate Bot — Core Patcher Engine
=============================================
Shared by all patch scripts (patch_m3_*.py, patch_m5_*.py, etc.)

Usage from any patch script:
    from patcher import Patcher
    p = Patcher("../FellowshipUltimate.ahk")
    p.insert_after("anchor text", new_block)
    p.replace_block("start anchor", "end anchor", new_block)
    p.append_function(func_code)
    p.save()
    p.verify(["string_that_must_exist_after_patch"])

All operations are ANCHOR-BASED — if an anchor isn't found,
the script errors out loudly instead of silently corrupting the file.
"""

import re
import sys
import shutil
from pathlib import Path
from datetime import datetime


class PatchError(Exception):
    pass


class Patcher:
    def __init__(self, filepath: str):
        self.path = Path(filepath).resolve()
        if not self.path.exists():
            raise PatchError(f"Target file not found: {self.path}")

        self.source = self.path.read_text(encoding="utf-8")
        self.original = self.source  # keep original for diff/rollback
        self._ops = []  # log of operations performed

        print(f"[Patcher] Loaded: {self.path.name} ({len(self.source):,} chars)")

    # ─────────────────────────────────────────────────────────────────
    # FIND HELPERS
    # ─────────────────────────────────────────────────────────────────

    def find(self, anchor: str) -> int:
        """Return index of anchor in source, raise if not found."""
        idx = self.source.find(anchor)
        if idx == -1:
            raise PatchError(
                f"\n\n❌ ANCHOR NOT FOUND:\n  '{anchor}'\n\n"
                f"File may have changed since this patch was written.\n"
                f"Check the .ahk file and update the anchor string.\n"
            )
        return idx

    def find_line(self, anchor: str) -> int:
        """Return the line number (1-based) containing anchor."""
        idx = self.find(anchor)
        return self.source[:idx].count("\n") + 1

    def anchor_exists(self, anchor: str) -> bool:
        return anchor in self.source

    def find_function_end(self, func_start_anchor: str) -> int:
        """
        Find the closing brace of an AHK function starting at func_start_anchor.
        Counts { and } to find the matching close.
        Returns index of the closing } + 1.
        """
        start = self.find(func_start_anchor)
        depth = 0
        i = start
        found_first = False

        while i < len(self.source):
            ch = self.source[i]
            if ch == "{":
                depth += 1
                found_first = True
            elif ch == "}" and found_first:
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1

        raise PatchError(
            f"Could not find closing brace for function starting at:\n  '{func_start_anchor}'"
        )

    # ─────────────────────────────────────────────────────────────────
    # INSERT OPERATIONS
    # ─────────────────────────────────────────────────────────────────

    def insert_after(self, anchor: str, new_code: str, newlines: int = 2) -> "Patcher":
        """
        Insert new_code immediately after the first occurrence of anchor.
        Adds `newlines` blank lines between anchor and new_code.
        """
        idx = self.find(anchor)
        insert_pos = idx + len(anchor)
        padding = "\n" * newlines
        self.source = (
            self.source[:insert_pos]
            + padding
            + new_code
            + self.source[insert_pos:]
        )
        self._log(f"insert_after: '{anchor[:60]}...' (+{len(new_code)} chars)")
        return self

    def insert_before(self, anchor: str, new_code: str, newlines: int = 2) -> "Patcher":
        """Insert new_code immediately before the first occurrence of anchor."""
        idx = self.find(anchor)
        padding = "\n" * newlines
        self.source = (
            self.source[:idx]
            + new_code
            + padding
            + self.source[idx:]
        )
        self._log(f"insert_before: '{anchor[:60]}...' (+{len(new_code)} chars)")
        return self

    def insert_after_line(self, anchor: str, new_code: str) -> "Patcher":
        """Insert new_code after the entire LINE containing anchor."""
        idx = self.find(anchor)
        # Find end of that line
        eol = self.source.find("\n", idx)
        if eol == -1:
            eol = len(self.source)
        insert_pos = eol + 1
        self.source = (
            self.source[:insert_pos]
            + new_code
            + "\n"
            + self.source[insert_pos:]
        )
        self._log(f"insert_after_line: '{anchor[:60]}...'")
        return self

    # ─────────────────────────────────────────────────────────────────
    # REPLACE OPERATIONS
    # ─────────────────────────────────────────────────────────────────

    def replace_block(self, start_anchor: str, end_anchor: str, new_code: str) -> "Patcher":
        """
        Replace everything from start_anchor to end_anchor (inclusive) with new_code.
        Both anchors must be unique in the file.
        """
        start_idx = self.find(start_anchor)
        end_idx = self.source.find(end_anchor, start_idx)
        if end_idx == -1:
            raise PatchError(
                f"End anchor not found after start anchor.\n"
                f"  Start: '{start_anchor[:60]}'\n"
                f"  End:   '{end_anchor[:60]}'"
            )
        end_idx += len(end_anchor)
        self.source = self.source[:start_idx] + new_code + self.source[end_idx:]
        self._log(f"replace_block: '{start_anchor[:50]}' → '{end_anchor[:50]}'")
        return self

    def replace_exact(self, old_text: str, new_text: str) -> "Patcher":
        """
        Replace an exact string with new_text.
        Raises if old_text appears 0 or more than once (ambiguous).
        """
        count = self.source.count(old_text)
        if count == 0:
            raise PatchError(f"replace_exact: text not found:\n  '{old_text[:80]}'")
        if count > 1:
            raise PatchError(
                f"replace_exact: text appears {count} times (ambiguous):\n  '{old_text[:80]}'"
            )
        self.source = self.source.replace(old_text, new_text, 1)
        self._log(f"replace_exact: '{old_text[:60]}...' → '{new_text[:60]}...'")
        return self

    def replace_function(self, func_start_anchor: str, new_function_code: str) -> "Patcher":
        """
        Replace an entire AHK function (from func_start_anchor to its closing })
        with new_function_code.
        """
        start_idx = self.find(func_start_anchor)
        end_idx = self.find_function_end(func_start_anchor)
        self.source = self.source[:start_idx] + new_function_code + self.source[end_idx:]
        self._log(f"replace_function: '{func_start_anchor[:60]}'")
        return self

    # ─────────────────────────────────────────────────────────────────
    # APPEND OPERATIONS
    # ─────────────────────────────────────────────────────────────────

    def append_function(self, new_code: str, before_anchor: str = None) -> "Patcher":
        """
        Append a new function block.
        If before_anchor is given, inserts before that anchor.
        Otherwise appends before the hotkey section (F1:: line).
        """
        if before_anchor:
            return self.insert_before(before_anchor, new_code)

        # Default: insert before the hotkeys block
        hotkey_anchor = "F1:: StartRotation"
        if not self.anchor_exists(hotkey_anchor):
            # Fallback: just append at end
            self.source = self.source.rstrip() + "\n\n" + new_code + "\n"
            self._log("append_function: appended at end of file")
        else:
            self.insert_before(hotkey_anchor, new_code)
        return self

    def set_global_value(self, var_name: str, new_value: str) -> "Patcher":
        """
        Replace a global variable declaration line.
        Example: set_global_value("GCDDelay", "1400")
        Finds: global GCDDelay := <anything>
        """
        pattern = rf"(global {re.escape(var_name)} := )[^\n]+"
        new_line = rf"\g<1>{new_value}"
        new_source, count = re.subn(pattern, new_line, self.source)
        if count == 0:
            raise PatchError(f"set_global_value: 'global {var_name}' not found")
        self.source = new_source
        self._log(f"set_global_value: {var_name} := {new_value}")
        return self

    # ─────────────────────────────────────────────────────────────────
    # VALIDATION
    # ─────────────────────────────────────────────────────────────────

    def verify(self, required_strings: list[str]) -> "Patcher":
        """Confirm all required_strings exist in patched source. Raise if any missing."""
        missing = [s for s in required_strings if s not in self.source]
        if missing:
            raise PatchError(
                f"Verification FAILED — these strings missing from patched file:\n"
                + "\n".join(f"  - '{s}'" for s in missing)
            )
        print(f"[Patcher] ✅ Verified {len(required_strings)} required strings present")
        return self

    def verify_not_duplicate(self, anchor: str) -> "Patcher":
        """Confirm an anchor appears exactly once (detect accidental double-patch)."""
        count = self.source.count(anchor)
        if count != 1:
            raise PatchError(
                f"verify_not_duplicate: '{anchor[:60]}' appears {count} times.\n"
                f"Patch may have been applied twice!"
            )
        return self

    # ─────────────────────────────────────────────────────────────────
    # SAVE
    # ─────────────────────────────────────────────────────────────────

    def backup(self) -> str:
        """Create a timestamped backup of the original file before saving."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.path.with_suffix(f".{ts}.bak")
        backup_path.write_text(self.original, encoding="utf-8")
        print(f"[Patcher] 📦 Backup: {backup_path.name}")
        return str(backup_path)

    def save(self, auto_backup: bool = True) -> "Patcher":
        """Write patched source back to disk."""
        if auto_backup:
            self.backup()
        self.path.write_text(self.source, encoding="utf-8")
        delta = len(self.source) - len(self.original)
        sign = "+" if delta >= 0 else ""
        print(f"[Patcher] 💾 Saved: {self.path.name} ({sign}{delta:,} chars)")
        return self

    def diff_summary(self) -> str:
        """Return a short summary of what changed (line count delta)."""
        orig_lines = self.original.count("\n")
        new_lines = self.source.count("\n")
        return f"Lines: {orig_lines} → {new_lines} ({new_lines - orig_lines:+d})"

    # ─────────────────────────────────────────────────────────────────
    # INTERNAL
    # ─────────────────────────────────────────────────────────────────

    def _log(self, msg: str):
        self._ops.append(msg)
        print(f"[Patcher]   ✏️  {msg}")

    def print_ops(self):
        print(f"\n[Patcher] Operations performed ({len(self._ops)}):")
        for i, op in enumerate(self._ops, 1):
            print(f"  {i}. {op}")
        print(self.diff_summary())
