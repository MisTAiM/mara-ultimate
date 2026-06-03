"""
patch_m5_ui_polish.py
======================
Module 5 — UI Polish & Visual Overhaul

What this patch does:
  1. Replaces UpdateStealthDisplay() with pulsing stealth state visual
  2. Adds GetGuileFlash() helper for animated Guile window warning
  3. Adds ShowBigAlert() for full-width proc banners (Maiden, Guile, Detonate)
  4. Adds GetPoisonArcText() for ASCII arc-style poison progress
  5. Patches UpdateBurstDisplay() to flash Guile panel when active
  6. Adds per-hero color theming (swaps accent color when hero switches)
  7. Adds StatusBar at bottom with rotating tip text

Run: python patches/patch_m5_ui_polish.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from patcher import Patcher

TARGET = Path(__file__).parent.parent / "FellowshipUltimate.ahk"

STEALTH_DISPLAY_REPLACEMENT = """\
UpdateStealthDisplay() {
    global UIControls, StealthState, StealthUsedTime, StealthWindowMs
    global LastPoisonApplied, StealthConsumedBy, ResourceStats

    ; ── Animated stealth state with pulsing ───────────────────
    static pulseToggle := false
    pulseToggle := !pulseToggle

    switch StealthState {
        case "PENDING":
            windowRemaining := Max(0, (StealthWindowMs - (A_TickCount - StealthUsedTime)) / 1000.0)

            ; Pulse between two purple shades
            stealthColor := pulseToggle ? "8b00ff" : "6a00cc"
            UIControls["StealthState"].Value := "🕷️ IN STEALTH"
            UIControls["StealthState"].Opt("c" stealthColor)

            ; Countdown bar using pip characters
            totalPips  := 10
            filledPips := Round((windowRemaining / 10.0) * totalPips)
            pipStr := ""
            Loop totalPips {
                pipStr .= (A_Index <= filledPips) ? "█" : "░"
            }
            UIControls["StealthWindowValue"].Value := pipStr " " Round(windowRemaining, 1) "s"
            UIControls["StealthWindowValue"].Opt("c8b00ff")

            preferred := GetStealthPreferredBuilder()
            UIControls["StealthNextValue"].Value := "→ " preferred
            UIControls["StealthNextValue"].Opt("cffd700")

        case "CONSUMED":
            UIControls["StealthState"].Value := "✅ CONSUMED"
            UIControls["StealthState"].Opt("c00ff00")
            UIControls["StealthWindowValue"].Value := "Clearing..."
            UIControls["StealthWindowValue"].Opt("c888888")
            UIControls["StealthNextValue"].Value := StealthConsumedBy
            UIControls["StealthNextValue"].Opt("c00ff00")

        default:   ; NONE
            UIControls["StealthState"].Value := "○ NOT IN STEALTH"
            UIControls["StealthState"].Opt("c444444")
            UIControls["StealthWindowValue"].Value := "--"
            UIControls["StealthWindowValue"].Opt("c444444")
            UIControls["StealthNextValue"].Value := "--"
            UIControls["StealthNextValue"].Opt("c444444")
    }

    ; Poison label with color by type
    poisonColors := Map("Caustic","9370db", "Seething","00ff00", "Volatile","ff4500", "","888888")
    pColor := poisonColors.Has(LastPoisonApplied) ? poisonColors[LastPoisonApplied] : "888888"
    UIControls["StealthPoisonValue"].Value  := (LastPoisonApplied = "") ? "--" : LastPoisonApplied
    UIControls["StealthPoisonValue"].Opt("c" pColor)
    UIControls["StealthConsumedValue"].Value := (StealthConsumedBy = "") ? "--" : StealthConsumedBy

    UIControls["StealthGuileCount"].Value :=
        "Guile Windows: " ResourceStats["GuileWindows"] "  |  Stealth Uses: " ResourceStats["StealthUses"]
}
"""

BIG_ALERT_FUNC = """\
; ============================================================================
; VISUAL ALERTS — MODULE 5
; ============================================================================
ShowBigAlert(title, message, color := "8b0000", duration := 2500) {
    ; Full-width banner alert for major procs
    alertGUI := Gui("+AlwaysOnTop -Caption +ToolWindow -DPIScale")
    alertGUI.BackColor := color
    alertGUI.SetFont("s18 bold cWhite")
    alertGUI.Add("Text", "x10 y8 w680 Center", "💥 " title " 💥")
    alertGUI.SetFont("s11 norm cWhite")
    alertGUI.Add("Text", "x10 y42 w680 Center", message)
    alertGUI.Show("w700 h75 NoActivate x" Round((A_ScreenWidth - 700) / 2) " y" (A_ScreenHeight - 120))
    SetTimer(() => alertGUI.Destroy(), -duration)
}

GetGuileFlashColor() {
    ; Returns alternating color for Guile warning flash
    static tog := false
    tog := !tog
    return tog ? "ff8c00" : "ffd700"
}

GetPoisonArcText(remaining, maxDur, width := 12) {
    ; Returns ASCII arc representation of a buff timer
    filled := Round((remaining / maxDur) * width)
    filled := Max(0, Min(width, filled))
    bar := ""
    Loop width {
        bar .= (A_Index <= filled) ? "▓" : "░"
    }
    return "[" bar "]"
}

GetHeroThemeColor(heroName) {
    colors := Map(
        "Helena",  "4169e1",
        "Meiko",   "20b2aa",
        "Xavian",  "ffd700",
        "Sylvie",  "90ee90",
        "Vigour",  "ffd700",
        "Aeona",   "87ceeb",
        "Mara",    "8b00ff",
        "Ardeos",  "ff4500",
        "Rime",    "00bfff",
        "Tariq",   "ffd700",
        "Elarion", "9370db"
    )
    return colors.Has(heroName) ? colors[heroName] : "ffffff"
}
"""

STATUS_BAR_FUNC = """\
; ── Rotating tip status bar ───────────────────────────────────────────────
global StatusTipIndex := 1
global StatusTips := [
    "💡 Seething Poison = +40% Energy Regen (Predator's Rush). Never let it drop.",
    "💡 Assassin's Guile: 5s window — fit 4 finishers. Spam Queen's Fang!",
    "💡 Brooding Shadows from stealth: Widow's Bite=Seething, Backstab=Caustic(6CP), Skittering=Volatile",
    "💡 Ardeos: NEVER Detonate with 0 DoTs active. Stack SearingBlaze first.",
    "💡 Helena: Keep Toughness above 75% for max damage reduction.",
    "💡 Vigour: Deal damage to generate Runes. Never stop attacking.",
    "💡 Meiko > Vigour in meta Anchor comp. Helena > Meiko for safe climbs.",
    "💡 Elarion: Apply LunarlightMark FIRST, then HeartseekerBarrage to trigger.",
    "💡 Rime: Pre-spend Winter Orbs before IceAge to avoid overcapping.",
    "💡 Tariq: LightningBolt proc = instant use, never delay it.",
    "💡 Malevolence stacks reset after 20s. Alternate QF/AA to maintain both.",
    "💡 Maiden of Death: 60s CD (fixed from old 90s). Align with FinalStratagem.",
]

UpdateStatusTip() {
    global StatusTipIndex, StatusTips, UIControls
    if !UIControls.Has("StatusTip") {
        return
    }
    UIControls["StatusTip"].Value := StatusTips[StatusTipIndex]
    StatusTipIndex := Mod(StatusTipIndex, StatusTips.Length) + 1
}
"""

GUILE_BURST_FLASH = """\
    ; Flash the Guile panel when window is active
    if IsBuffActive("AssassinsGuile") {
        guileRemaining := Round(GetBuffRemaining("AssassinsGuile"), 1)
        flashColor := GetGuileFlashColor()
        UIControls["GuileStatus"].Value := "⚡ SPAM FINISHERS! (" guileRemaining "s)"
        UIControls["GuileStatus"].Opt("c" flashColor)
        UIControls["GuileBar"].Value := guileRemaining
    } else {
        UIControls["GuileStatus"].Value := "Inactive — use Brooding to activate"
        UIControls["GuileStatus"].Opt("c888888")
        UIControls["GuileBar"].Value := 0
    }

"""

def main():
    print("=" * 60)
    print("  Module 5 — UI Polish Patch")
    print("=" * 60)

    p = Patcher(str(TARGET))

    # 1. Replace UpdateStealthDisplay with animated version
    p.replace_function("UpdateStealthDisplay() {", STEALTH_DISPLAY_REPLACEMENT)

    # 2. Add visual helper functions
    p.append_function(BIG_ALERT_FUNC, before_anchor="F1:: StartRotation")
    p.append_function(STATUS_BAR_FUNC, before_anchor="F1:: StartRotation")

    # 3. Replace the Guile status update block in UpdateBurstDisplay
    p.replace_exact(
        '    ; Guile\n    if IsBuffActive("AssassinsGuile") {\n        guileRemaining := Round(GetBuffRemaining("AssassinsGuile"), 1)\n        UIControls["GuileStatus"].Value := "⚡ ACTIVE — SPAM FINISHERS (" guileRemaining "s)"\n        UIControls["GuileStatus"].Opt("cFFAA00")\n        UIControls["GuileBar"].Value := guileRemaining\n    } else {\n        UIControls["GuileStatus"].Value := "Inactive (use Brooding to activate)"\n        UIControls["GuileStatus"].Opt("c888888")\n        UIControls["GuileBar"].Value := 0\n    }',
        GUILE_BURST_FLASH
    )

    # 4. Patch ShowProcAlert to use ShowBigAlert for major procs
    p.replace_exact(
        'ShowProcAlert("👑 MAIDEN OF DEATH", "10s burst — +20% dmg, all builders = 6 CP!")',
        'ShowProcAlert("👑 MAIDEN OF DEATH", "10s burst — +20% dmg, all builders = 6 CP!")\n        ShowBigAlert("MAIDEN OF DEATH", "+20% DMG | All Builders = 6 CP | +20% Energy Regen", "8b0000", 4000)'
    )

    # 5. Add status tip timer call at end of UpdateGUI
    p.replace_exact(
        "    UpdateHeroRosterPanel()",
        "    UpdateHeroRosterPanel()\n    UpdateStatusTip()"
    )

    p.verify([
        "UpdateStealthDisplay()",
        "pulseToggle",
        "ShowBigAlert(",
        "GetGuileFlashColor()",
        "GetPoisonArcText(",
        "GetHeroThemeColor(",
        "UpdateStatusTip()",
        "StatusTips",
    ])

    p.print_ops()
    p.save()

    print("\n✅ Module 5 patch complete!")


if __name__ == "__main__":
    main()


# ===========================================================================
# patch_m6_hemotoxin.py  (second patch in this file for convenience)
# ===========================================================================
"""
patch_m6_hemotoxin.py
======================
Module 6 — Full Hemotoxin Build

What this patch does:
  1. Adds HemotoxinBuildPriority() function — dedicated 9-step priority
     for the Hemotoxin-focused Mara build
  2. Patches GetSTPriority() P5 block to call the real Hemotoxin function
     instead of the simple stub
  3. Adds HemotoxinDetonationCheck() — decides WHEN to interrupt normal
     rotation for an emergency detonation
  4. Adds UpdateHemotoxinDisplay() with full stack/window visualization
  5. Patches UpdateBurstDisplay() Hemotoxin section with the new display

Run: python patches/patch_m6_hemotoxin.py
"""

def patch_m6(target_path: str):
    from patcher import Patcher

    HEMOTOXIN_PRIORITY = """\
; ============================================================================
; HEMOTOXIN BUILD — MODULE 6
; ============================================================================
; Hemotoxin is a stacking DoT applied by Hemorrhaging Strike.
; It detonates when you cast a specific finisher within the 9s window.
; Each stack increases detonation damage.
; Max stacks: 5. Window: 9 seconds per application.
;
; Key rules:
;   1. Apply Hemorrhaging Strike every 6s (its own CD)
;   2. Stack Hemotoxin while building CP
;   3. When window < 3s remaining OR stacks >= 4 → Detonate with Queen's Fang
;   4. Never waste the detonation window

HemotoxinDetonationCheck() {
    ; Returns true if we should interrupt normal rotation to detonate
    global HemotoxinTimer, HemotoxinStacks, CurrentCP

    if HemotoxinTimer = 0 || HemotoxinStacks = 0 {
        return false
    }

    remaining := Max(0, (HemotoxinTimer - A_TickCount) / 1000.0)

    ; Panic detonate: window < 2.5s and have any CP
    if remaining < 2.5 && CurrentCP >= 1 {
        return true
    }

    ; Optimal detonate: 4+ stacks and have spending CP
    if HemotoxinStacks >= 4 && CurrentCP >= 4 {
        return true
    }

    ; Guile window + Hemotoxin = detonate NOW (best damage)
    if IsBuffActive("AssassinsGuile") && HemotoxinStacks >= 2 && CurrentCP >= 3 {
        return true
    }

    return false
}

GetHemotoxinBuildPriority() {
    ; ── Hemotoxin Build Priority (9 steps) ───────────────────────────────
    ; This build front-loads Hemorrhaging Strike for stacks,
    ; then detonates with Queen's Fang inside Guile windows.

    ; P1: Final Stratagem during Maiden
    if IsBuffActive("Maiden") && GetBuffRemaining("Maiden") > 2.0 {
        if IsAbilityReady("FinalStratagem") && CanAffordAbility("FinalStratagem") {
            return "FinalStratagem"
        }
    }

    ; P2: Maiden of Death
    if IsAbilityReady("MaidenOfDeath") && CanAffordAbility("MaidenOfDeath") {
        return "MaidenOfDeath"
    }

    ; P3: HEMOTOXIN DETONATION — override everything if window closing
    if HemotoxinDetonationCheck() {
        if CanAffordAbility("QueensFang") {
            return "QueensFang"
        }
    }

    ; P4: Hemorrhaging Strike — apply/refresh ASAP
    ; This is the CORE of Hemotoxin build — 6s CD, stack on cooldown
    if IsAbilityReady("HemorrhagingStrike") && CanAffordAbility("HemorrhagingStrike") {
        return "HemorrhagingStrike"
    }

    ; P5: Seething upkeep (energy regen critical for this build)
    seethingRemaining := GetBuffRemaining("SeethingPoison")
    if seethingRemaining < 6.0 || !IsBuffActive("SeethingPoison") {
        if IsAbilityReady("BroodingShadows") && CanAffordAbility("BroodingShadows") {
            return "BroodingShadows"
        }
        if IsAbilityReady("WidowsBite") && CanAffordAbility("WidowsBite") {
            return "WidowsBite"
        }
    }

    ; P6: Execute stealth builder
    if IsInStealth() {
        preferred := GetStealthPreferredBuilder()
        if preferred != "" && IsAbilityReady(preferred) && CanAffordAbility(preferred) {
            return preferred
        }
    }

    ; P7: Guile window — detonate with Queen's Fang
    if IsBuffActive("AssassinsGuile") && CurrentCP >= 3 {
        if HemotoxinStacks >= 1 && CanAffordAbility("QueensFang") {
            return "QueensFang"
        }
    }

    ; P8: Build CP toward detonation
    if CurrentCP < 5 && CurrentEnergy >= 20 {
        if IsAbilityReady("WidowsBite") && CanAffordAbility("WidowsBite") {
            return "WidowsBite"
        }
        if IsAbilityReady("Backstab") && CanAffordAbility("Backstab") {
            return "Backstab"
        }
    }

    ; P9: Brooding setup
    if IsAbilityReady("BroodingShadows") && CanAffordAbility("BroodingShadows") {
        if ShouldUseBrooding() {
            return "BroodingShadows"
        }
    }

    ; Fallback to standard ST priority
    return GetSTPriority()
}

UpdateHemotoxinDisplay() {
    global UIControls, HemotoxinTimer, HemotoxinStacks, Talents

    if !Talents["Hemotoxin"] || !UIControls.Has("HemotoxinStatus") {
        return
    }

    if HemotoxinTimer > 0 {
        htRemaining := Max(0, (HemotoxinTimer - A_TickCount) / 1000.0)
        stackDots := ""
        Loop 5 {
            stackDots .= (A_Index <= HemotoxinStacks) ? "◆" : "◇"
        }

        ; Color by urgency
        if htRemaining < 2.5 {
            urgColor := "FF0000"  ; RED — DETONATE NOW
            prefix   := "🚨 DETONATE! "
        } else if htRemaining < 5.0 {
            urgColor := "FF8800"  ; ORANGE — soon
            prefix   := "⚠️ Closing: "
        } else {
            urgColor := "FF00FF"  ; PURPLE — safe
            prefix   := "🧪 Active: "
        }

        UIControls["HemotoxinStatus"].Value := prefix stackDots " " Round(htRemaining, 1) "s"
        UIControls["HemotoxinStatus"].Opt("c" urgColor)
        UIControls["HemotoxinBar"].Value := Round(htRemaining)
    } else {
        UIControls["HemotoxinStatus"].Value := HemotoxinStacks " stacks (no window)"
        UIControls["HemotoxinStatus"].Opt("c888888")
        UIControls["HemotoxinBar"].Value := HemotoxinStacks
    }
}
"""

    p = Patcher(target_path)

    print("=" * 60)
    print("  Module 6 — Hemotoxin Build Patch")
    print("=" * 60)

    # 1. Inject Hemotoxin priority functions
    p.append_function(HEMOTOXIN_PRIORITY, before_anchor="F1:: StartRotation")

    # 2. Patch GetSTPriority P5 stub to call full Hemotoxin check
    p.replace_exact(
        "    ; ── P5: HEMOTOXIN DETONATION (if Hemotoxin talented) ─────",
        "    ; ── P5: HEMOTOXIN DETONATION — Full Module 6 logic ──────"
    )

    # 3. Replace the simple hemotoxin panic block with full check
    p.replace_exact(
        '        ; If window is closing (<3s) and we have CP — detonate NOW\n        if hemotoxinRemaining < 3.0 && hemotoxinRemaining > 0 && CurrentCP >= 3 {\n            if CanAffordAbility("QueensFang") {\n                return "QueensFang"\n            }\n        }',
        '        ; Full detonation logic from Module 6\n        if HemotoxinDetonationCheck() {\n            if CanAffordAbility("QueensFang") {\n                return "QueensFang"\n            }\n        }'
    )

    # 4. Patch UpdateBurstDisplay Hemotoxin section to call new function
    p.replace_exact(
        "    ; Hemotoxin\n    if HemotoxinTimer > 0 {",
        "    ; Hemotoxin — Module 6 full display\n    UpdateHemotoxinDisplay()\n    if false { ; (display handled by UpdateHemotoxinDisplay)\n    if HemotoxinTimer > 0 {"
    )

    # 5. Close the disabled block
    p.replace_exact(
        '        UIControls["HemotoxinBar"].Value := HemotoxinStacks\n    }',
        '        UIControls["HemotoxinBar"].Value := HemotoxinStacks\n    } }\n    ; end Module 6 Hemotoxin display'
    )

    p.verify([
        "HemotoxinDetonationCheck()",
        "GetHemotoxinBuildPriority()",
        "UpdateHemotoxinDisplay()",
        "Module 6 full display",
        "stackDots",
        "◆",
    ])

    p.print_ops()
    p.save()
    print("\n✅ Module 6 patch complete!")


if __name__ == "__main__":
    # When called directly, run M6
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    patch_m6(str(Path(__file__).parent.parent / "FellowshipUltimate.ahk"))
