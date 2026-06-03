#!/usr/bin/env python3
"""
run_patches.py — Master patch runner for Fellowship Ultimate Bot.

Usage:
    python patches/run_patches.py --all
    python patches/run_patches.py --module 3
    python patches/run_patches.py --module 3 --module 5 --module 6
    python patches/run_patches.py --verify-only
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from patcher import Patcher, PatchError

ROOT   = Path(__file__).parent.parent
TARGET = ROOT / "FellowshipUltimate.ahk"


def check_target():
    if not TARGET.exists():
        print(f"\n[ERROR] Target not found: {TARGET}")
        print("  Rename MaraUltimate_v6.ahk -> FellowshipUltimate.ahk first.")
        sys.exit(1)
    print(f"[OK] Target: {TARGET.name} ({TARGET.stat().st_size:,} bytes)")


def verify_final(applied_modules):
    print("\n" + "=" * 60)
    print("  FINAL VERIFICATION")
    print("=" * 60)
    p = Patcher(str(TARGET))

    required = [
        "GetSTPriority()",
        "GetAOEPriority()",
        "StealthState",
        "EnterStealth()",
        "ConsumeStealthWith(",
    ]

    if 3 in applied_modules:
        required += [
            "GetHelenaRotation()",
            "GetMeikoRotation()",
            "GetXavianRotation()",
            "GetSylvieRotation()",
            "GetVigourRotation()",
            "GetAeonaRotation()",
            "GetArdeoRotation()",
            "GetRimeRotation()",
            "GetTariqRotation()",
            "GetElarionRotation()",
            "CreateHeroRosterPanel()",
            "SwitchHero(",
        ]

    if 5 in applied_modules:
        required += [
            "pulseToggle",
            "ShowBigAlert(",
            "GetGuileFlashColor()",
            "UpdateStatusTip()",
        ]

    if 6 in applied_modules:
        required += [
            "HemotoxinDetonationCheck()",
            "GetHemotoxinBuildPriority()",
            "UpdateHemotoxinDisplay()",
        ]

    p.verify(required)
    print(f"\n[OK] Modules verified: {sorted(applied_modules)}")
    print(f"     File : {TARGET.name}")
    print(f"     Size : {TARGET.stat().st_size:,} bytes")
    print(f"     Lines: {TARGET.read_text(encoding='utf-8').count(chr(10)):,}")


def run_module_3():
    print("\n" + "=" * 60)
    print("  MODULE 3 — Hero Roster + All Hero Rotations")
    print("=" * 60)
    from patch_m3_hero_roster import main as m3
    m3()


def run_module_5():
    print("\n" + "=" * 60)
    print("  MODULE 5 — UI Polish")
    print("=" * 60)
    from patch_m5_m6 import main as m5
    m5()


def run_module_6():
    print("\n" + "=" * 60)
    print("  MODULE 6 — Hemotoxin Build")
    print("=" * 60)
    from patch_m5_m6 import patch_m6
    patch_m6(str(TARGET))


def main():
    parser = argparse.ArgumentParser(description="Fellowship Ultimate Bot — Patch Runner")
    parser.add_argument("--module", type=int, action="append",
                        help="Module number to apply (3, 5, or 6). Repeatable.")
    parser.add_argument("--all", action="store_true", help="Apply all modules (3->5->6)")
    parser.add_argument("--verify-only", action="store_true",
                        help="Verify all modules without patching")
    args = parser.parse_args()

    check_target()

    if args.verify_only:
        verify_final({3, 5, 6})
        return

    modules = set(args.module or [])
    if args.all:
        modules = {3, 5, 6}

    if not modules:
        parser.print_help()
        print("\n[!] No modules specified. Use --all or --module N")
        sys.exit(1)

    applied = set()
    errors  = []

    if 3 in modules:
        try:
            run_module_3()
            applied.add(3)
        except PatchError as e:
            print(f"\n[FAIL] Module 3:\n{e}")
            errors.append(3)

    if 5 in modules:
        try:
            run_module_5()
            applied.add(5)
        except PatchError as e:
            print(f"\n[FAIL] Module 5:\n{e}")
            errors.append(5)

    if 6 in modules:
        try:
            run_module_6()
            applied.add(6)
        except PatchError as e:
            print(f"\n[FAIL] Module 6:\n{e}")
            errors.append(6)

    if applied:
        try:
            verify_final(applied)
        except Exception as e:
            print(f"\n[WARN] Verify failed: {e}")

    if errors:
        print(f"\n[!] {len(errors)} module(s) failed: {errors}")
        sys.exit(1)
    else:
        print("\n[DONE] Fellowship Ultimate Bot — all patches applied!")
        print("       Run FellowshipUltimate.ahk in AutoHotkey v2.0")


if __name__ == "__main__":
    main()
