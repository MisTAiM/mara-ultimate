"""
patch_ui_bridge.py
===================
Patches FellowshipUltimate.ahk to:
  1. Write fellowship_state.json every 100ms (the HTML reads this)
  2. Launch FellowshipUI.html in Chrome --app mode on startup
  3. Poll fellowship_cmd.txt for commands from the HTML buttons
  4. Disable the old AHK GUI (CreateMainGUI replaced with LaunchUI)

Run: python patches/patch_ui_bridge.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from patcher import Patcher

TARGET   = Path(__file__).parent.parent / "FellowshipUltimate.ahk"
UI_DIR   = Path(__file__).parent.parent / "ui"
HTML_FILE = UI_DIR / "FellowshipUI.html"

# ─────────────────────────────────────────────────────────────────────────────
# 1. GLOBALS for state bridge
# ─────────────────────────────────────────────────────────────────────────────
BRIDGE_GLOBALS = """\
; ============================================================================
; UI BRIDGE GLOBALS — HTML overlay state sync
; ============================================================================
global UIBridgeEnabled  := true
global StateFile        := A_ScriptDir "\\ui\\fellowship_state.json"
global CmdFile          := A_ScriptDir "\\ui\\fellowship_cmd.txt"
global LastCmdCheck     := 0
global ChromePID        := 0
"""

# ─────────────────────────────────────────────────────────────────────────────
# 2. STATE BUILDER — converts all globals to JSON
# ─────────────────────────────────────────────────────────────────────────────
STATE_WRITER = r"""
; ============================================================================
; HTML UI BRIDGE — STATE WRITER
; ============================================================================
BuildStateJSON() {
    global CurrentEnergy, MaxEnergy, CurrentCP, MaxCP
    global BroodingCharges, WidowCharges
    global StealthState, StealthWindowMs, StealthUsedTime
    global LastPoisonApplied, StealthConsumedBy
    global BuffTimers, MalevolenceStacks, MalevolenceTimers
    global HemotoxinStacks, HemotoxinTimer
    global DeadlySchemeEnergy
    global ResourceStats, IsRunning, RotationType, RotationStartTime
    global ActiveHero, PartyComp, Talents

    ; Stealth window percent
    stealthPct := 0
    if StealthState = "PENDING" && StealthUsedTime > 0 {
        elapsed    := A_TickCount - StealthUsedTime
        stealthPct := Max(0, Round((1 - elapsed / StealthWindowMs) * 100))
    }

    ; Next ability + details
    nextAb      := GetNextAbility()
    nextDmg     := "—"
    nextReason  := GetAbilityReason(nextAb)
    costEnergy  := 0
    costCP      := 0
    fromStealth := (StealthState = "PENDING" && AbilityData.Has(nextAb) && AbilityData[nextAb].isBuilder)

    if AbilityData.Has(nextAb) {
        d          := AbilityData[nextAb]
        costEnergy := d.energyCost
        if d.isFinisher {
            costCP     := CurrentCP
            basePct    := (nextAb = "QueensFang")         ? 1.60
                        : (nextAb = "ArachnidAssault")    ? 0.65
                        : (nextAb = "HemorrhagingStrike") ? 1.75
                        : 1.0
            cpBonus    := 0.20 * CurrentCP
            baseDmg    := PlayerStats["Agility"] * (basePct + cpBonus)
            totalM     := 1.0
            if IsBuffActive("AssassinsGuile") { totalM *= 1.4 }
            if IsBuffActive("Maiden")         { totalM *= 1.2 }
            if IsBuffActive("DeadlyScheme")   { totalM *= 2.0 }
            if Talents["Malevolence"] {
                stacks := (nextAb = "QueensFang") ? MalevolenceStacks["QueensFang"]
                        : (nextAb = "ArachnidAssault") ? MalevolenceStacks["ArachnidAssault"]
                        : 0
                if stacks > 0 { totalM *= (1.0 + stacks) }
            }
            nextDmg := "~" Round(baseDmg * totalM)
        }
    }

    ; Rotation queue (next 5)
    savedE := CurrentEnergy
    savedC := CurrentCP
    savedB := BroodingCharges
    savedS := StealthState
    queue  := []
    Loop 5 {
        n := GetNextAbility()
        if n = "" { break }
        queue.Push('"' n '"')
        if AbilityData.Has(n) {
            nd := AbilityData[n]
            CurrentEnergy := Max(0, CurrentEnergy - nd.energyCost)
            if nd.isFinisher { CurrentCP := 0 }
            else if nd.isBuilder { CurrentCP := Min(MaxCP, CurrentCP + nd.cpGain) }
        }
        if A_Index > 8 { break }
    }
    global CurrentEnergy   := savedE
    global CurrentCP       := savedC
    global BroodingCharges := savedB
    global StealthState    := savedS

    ; Buff/CD helpers
    maidenRem   := GetBuffRemaining("Maiden")
    guileRem    := GetBuffRemaining("AssassinsGuile")
    maidenCDRem := GetCooldownRemaining("MaidenOfDeath")
    weaponCDRem := GetCooldownRemaining("WeaponAbility")
    finalCDRem  := GetCooldownRemaining("FinalStratagem")
    hemoRem     := HemotoxinTimer > 0 ? Max(0, (HemotoxinTimer - A_TickCount) / 1000.0) : 0
    qfRem       := GetBuffRemaining("MalevolenceQF")
    aaRem       := GetBuffRemaining("MalevolenceAA")
    seethRem    := GetBuffRemaining("SeethingPoison")
    volatRem    := GetBuffRemaining("VolatilePoison")
    hemBleedRem := GetBuffRemaining("Hemorrhage")

    ; Party array
    partyArr := ""
    for h in PartyComp {
        if partyArr != "" { partyArr .= "," }
        partyArr .= '"' h '"'
    }

    j := '{'
    j .= '"energy":' Round(CurrentEnergy) ','
    j .= '"maxEnergy":' MaxEnergy ','
    j .= '"cp":' CurrentCP ','
    j .= '"broodingCharges":' BroodingCharges ','
    j .= '"widowReady":' (IsAbilityReady("WidowsBite") ? "true" : "false") ','
    j .= '"stealthState":"' StealthState '",'
    j .= '"stealthWindowPct":' stealthPct ','
    j .= '"lastPoison":"' LastPoisonApplied '",'
    j .= '"stealthConsumedBy":"' StealthConsumedBy '",'
    j .= '"stealthNextAbility":"' GetStealthPreferredBuilder() '",'
    j .= '"nextAbility":"' nextAb '",'
    j .= '"nextAbilityDamage":"' nextDmg '",'
    j .= '"nextAbilityReason":"' StrReplace(nextReason, '"', "'") '",'
    j .= '"nextAbilityCostEnergy":' costEnergy ','
    j .= '"nextAbilityCostCP":' costCP ','
    j .= '"nextAbilityIsFromStealth":' (fromStealth ? "true" : "false") ','
    j .= '"queue":[' ArrJoin(queue, ",") '],'
    j .= '"isRunning":' (IsRunning ? "true" : "false") ','
    j .= '"rotationType":"' RotationType '",'
    j .= '"rotationTime":' Round(ResourceStats["RotationTime"], 1) ','
    j .= '"dps":' Round(ResourceStats["DPS"], 1) ','
    j .= '"totalDamage":' Round(ResourceStats["TotalDamage"]) ','
    j .= '"totalCasts":' ResourceStats["TotalCasts"] ','
    j .= '"guileWindows":' ResourceStats["GuileWindows"] ','
    j .= '"stealthUses":' ResourceStats["StealthUses"] ','
    j .= '"energyWasted":' Round(ResourceStats["EnergyWasted"]) ','
    j .= '"seethingRemaining":' Round(seethRem, 1) ','
    j .= '"seethingMax":60,'
    j .= '"volatileRemaining":' Round(volatRem, 1) ','
    j .= '"volatileMax":8,'
    j .= '"hemRemaining":' Round(hemBleedRem, 1) ','
    j .= '"hemMax":30,'
    j .= '"maidenActive":' (IsBuffActive("Maiden") ? "true" : "false") ','
    j .= '"maidenRemaining":' Round(maidenRem, 1) ','
    j .= '"maidenReady":' (IsAbilityReady("MaidenOfDeath") ? "true" : "false") ','
    j .= '"maidenCDRemaining":' Round(maidenCDRem, 1) ','
    j .= '"maidenCD":60,'
    j .= '"guileActive":' (IsBuffActive("AssassinsGuile") ? "true" : "false") ','
    j .= '"guileRemaining":' Round(guileRem, 1) ','
    j .= '"weaponReady":' (IsAbilityReady("WeaponAbility") ? "true" : "false") ','
    j .= '"weaponCDRemaining":' Round(weaponCDRem, 1) ','
    j .= '"weaponRemaining":' Round(90 - weaponCDRem, 1) ','
    j .= '"finalReady":' (IsAbilityReady("FinalStratagem") ? "true" : "false") ','
    j .= '"finalCDRemaining":' Round(finalCDRem, 1) ','
    j .= '"finalRemaining":' Round(180 - finalCDRem, 1) ','
    j .= '"deadlySchemeEnergy":' Round(DeadlySchemeEnergy, 1) ','
    j .= '"deadlySchemeActive":' (IsBuffActive("DeadlyScheme") ? "true" : "false") ','
    j .= '"hemotoxinStacks":' HemotoxinStacks ','
    j .= '"hemotoxinRemaining":' Round(hemoRem, 1) ','
    j .= '"qfStacks":' MalevolenceStacks["QueensFang"] ','
    j .= '"qfRemaining":' Round(qfRem, 1) ','
    j .= '"aaStacks":' MalevolenceStacks["ArachnidAssault"] ','
    j .= '"aaRemaining":' Round(aaRem, 1) ','
    j .= '"activeHero":"' ActiveHero '",'
    j .= '"party":[' partyArr ']'
    j .= '}'
    return j
}

WriteStateFile() {
    global StateFile, IsRunning
    try {
        json := BuildStateJSON()
        f    := FileOpen(StateFile, "w", "UTF-8")
        if IsObject(f) {
            f.Write(json)
            f.Close()
        }
    } catch {
        ; Silent fail — don't interrupt rotation
    }
}

; ── Command reader (HTML buttons → AHK) ──────────────────────────
PollCmdFile() {
    global CmdFile, LastCmdCheck
    if !FileExist(CmdFile) { return }
    try {
        cmd := FileRead(CmdFile, "UTF-8")
        cmd := Trim(cmd)
        if cmd = "" { return }

        ; Clear the file immediately
        f := FileOpen(CmdFile, "w")
        if IsObject(f) { f.Write("") ; f.Close() }

        switch cmd {
            case "START_ST":  StartRotation("ST")
            case "START_AOE": StartRotation("AOE")
            case "PAUSE":     PauseRotation()
            case "STOP":      StopRotation()
            case "RESET":     ResetResources()
            default:
                if SubStr(cmd, 1, 5) = "HERO:" {
                    heroName := SubStr(cmd, 6)
                    SwitchHero(heroName)
                }
        }
    } catch {
        ; Silent fail
    }
}

; ── Chrome launcher ─────────────────────────────────────────────
LaunchUI() {
    global ChromePID
    htmlPath := A_ScriptDir "\ui\FellowshipUI.html"
    if !FileExist(htmlPath) {
        MsgBox("UI file not found: " htmlPath "`n`nMake sure FellowshipUI.html is in the ui\ folder.", "UI Error", "Icon!")
        return
    }

    ; Try Chrome first, then Edge
    chromePaths := [
        "C:\Program Files\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        A_AppData "\..\Local\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]

    launched := false
    for path in chromePaths {
        if FileExist(path) {
            Run('"' path '" --app="file:///' StrReplace(htmlPath, "\", "/") '"'
                . ' --window-size=1400,920'
                . ' --window-position=50,50'
                . ' --disable-extensions'
                . ' --no-first-run'
                . ' --disable-default-apps'
                . ' --no-startup-window', , , &ChromePID)
            launched := true
            break
        }
    }

    if !launched {
        ; Fallback: open in default browser
        Run("file:///" StrReplace(htmlPath, "\", "/"))
    }
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# 3. Patch UpdateRotation to write state every tick
# ─────────────────────────────────────────────────────────────────────────────
WRITE_STATE_CALL = """\
    ; Write state to JSON for HTML UI
    WriteStateFile()
    PollCmdFile()

"""

# ─────────────────────────────────────────────────────────────────────────────
# 4. Replace CreateMainGUI call in startup with LaunchUI
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  UI Bridge Patch — HTML Overlay Integration")
    print("=" * 60)

    p = Patcher(str(TARGET))

    # 1. Inject bridge globals after TargetHP
    p.insert_after("global TargetHP    := 100", BRIDGE_GLOBALS)

    # 2. Inject state writer functions before hotkeys
    p.insert_before("F1:: StartRotation", STATE_WRITER)

    # 3. Patch UpdateRotation to write state on every tick
    p.replace_exact(
        "    UpdateGUI()\n\n    currentTime",
        "    UpdateGUI()\n    WriteStateFile()\n    PollCmdFile()\n\n    currentTime"
    )

    # 4. Replace CreateMainGUI() call in startup with LaunchUI()
    p.replace_exact(
        "    CreateMainGUI()",
        "    ; Launch HTML UI (Chrome --app mode)\n    LaunchUI()\n    ; Keep AHK GUI as fallback if needed\n    ; CreateMainGUI()"
    )

    # 5. Add a SetTimer to write state every 100ms even when idle
    p.replace_exact(
        "    SetTimer UpdateRotation, 100",
        "    SetTimer UpdateRotation, 100\n    SetTimer WriteStateFile, 100"
    )

    p.verify([
        "BuildStateJSON()",
        "WriteStateFile()",
        "PollCmdFile()",
        "LaunchUI()",
        "StateFile",
        "CmdFile",
        "fellowship_state.json",
        "fellowship_cmd.txt",
    ])

    p.print_ops()
    p.save()

    print("\n✅ UI Bridge patch complete!")
    print("   HTML UI will launch automatically when AHK starts.")
    print("   State file: ui/fellowship_state.json")
    print("   Cmd file:   ui/fellowship_cmd.txt")


if __name__ == "__main__":
    main()
