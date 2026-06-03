#!/usr/bin/env python3
"""
run_patches.py
==============
Master patch runner for Fellowship Ultimate Bot.

Applies all modules in order against FellowshipUltimate.ahk.
Run this from the repo root:

    python patches/run_patches.py [--module 3] [--module 5] [--module 6] [--all]

Or just: python patches/run_patches.py --all

The target file must be named FellowshipUltimate.ahk and sit at the repo root.
Each module patch is idempotent-safe when run via verify_not_duplicate checks.
"""

import argparse
import sys
from pathlib import Path

# Add patches dir to path
sys.path.insert(0, str(Path(__file__).parent))

from patcher import Patcher, PatchError

ROOT   = Path(__file__).parent.parent
TARGET = ROOT / "FellowshipUltimate.ahk"


def check_target():
    if not TARGET.exists():
        print(f"\n❌ ERROR: Target file not found: {TARGET}")
        print("   Rename MaraUltimate_v6.ahk → FellowshipUltimate.ahk first.")
        print("   (Or update TARGET path in run_patches.py)")
        sys.exit(1)
    print(f"✅ Target found: {TARGET.name} ({TARGET.stat().st_size:,} bytes)")


def run_module_3():
    print("\n" + "═" * 60)
    print("  APPLYING MODULE 3 — Hero Roster + All Hero Rotations")
    print("═" * 60)
    from patch_m3_hero_roster import main as m3
    m3()


def run_module_5():
    print("\n" + "═" * 60)
    print("  APPLYING MODULE 5 — UI Polish")
    print("═" * 60)
    from patch_m5_m6 import main as m5
    m5()


def run_module_6():
    print("\n" + "═" * 60)
    print("  APPLYING MODULE 6 — Hemotoxin Build")
    print("═" * 60)
    from patch_m5_m6 import patch_m6
    patch_m6(str(TARGET))


def verify_final():
    """Quick sanity check on final file."""
    print("\n" + "═" * 60)
    print("  FINAL VERIFICATION")
    print("═" * 60)
    p = Patcher(str(TARGET))
    p.verify([
        # Core existing
        "GetSTPriority()",
        "GetAOEPriority()",
        "StealthState",
        "EnterStealth()",
        "ConsumeStealthWith(",
        # Module 3
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
        # Module 5
        "pulseToggle",
        "ShowBigAlert(",
        "GetGuileFlashColor()",
        "UpdateStatusTip()",
        # Module 6
        "HemotoxinDetonationCheck()",
        "GetHemotoxinBuildPriority()",
        "UpdateHemotoxinDisplay()",
    ])
    print(f"\n✅ ALL MODULES VERIFIED")
    print(f"   Final file: {TARGET.name}")
    print(f"   Size: {TARGET.stat().st_size:,} bytes")
    print(f"   Lines: {TARGET.read_text(encoding='utf-8').count(chr(10)):,}")


def main():
    parser = argparse.ArgumentParser(
        description="Fellowship Ultimate Bot — Patch Runner"
    )
    parser.add_argument("--module", type=int, action="append",
                        help="Apply specific module (3, 5, 6). Repeatable.")
    parser.add_argument("--all", action="store_true",
                        help="Apply all modules in order (3 → 5 → 6)")
    parser.add_argument("--verify-only", action="store_true",
                        help="Only run final verification, no patching")
    args = parser.parse_args()

    check_target()

    if args.verify_only:
        verify_final()
        return

    modules = set(args.module or [])
    if args.all:
        modules = {3, 5, 6}

    if not modules:
        parser.print_help()
        print("\n⚠️  No modules specified. Use --all or --module N")
        sys.exit(1)

    errors = []

    try:
        if 3 in modules:
            run_module_3()
    except PatchError as e:
        print(f"\n❌ Module 3 FAILED:\n{e}")
        errors.append(3)

    try:
        if 5 in modules:
            run_module_5()
    except PatchError as e:
        print(f"\n❌ Module 5 FAILED:\n{e}")
        errors.append(5)

    try:
        if 6 in modules:
            run_module_6()
    except PatchError as e:
        print(f"\n❌ Module 6 FAILED:\n{e}")
        errors.append(6)

    if errors:
        print(f"\n⚠️  {len(errors)} module(s) failed: {errors}")
        print("   Check anchor strings against current .ahk file.")
        sys.exit(1)
    else:
        verify_final()
        print("\n🕷️  Fellowship Ultimate Bot patching complete!")
        print("    Run FellowshipUltimate.ahk in AutoHotkey v2.0")


if __name__ == "__main__":
    main()
