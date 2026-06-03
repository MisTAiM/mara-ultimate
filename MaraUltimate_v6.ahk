#Requires AutoHotkey v2.0
#SingleInstance Force
SendMode "Input"
SetKeyDelay 0, 10
SetWinDelay 0

; ============================================================================
; MARA ULTIMATE v6.0 — STEALTH ENGINE + DATA ACCURACY + PRIORITY OVERHAUL
; Module 2: Stealth State Machine
; Module 1: Real ability data from Icy Veins / Method.gg
; Module 4: Full priority logic rewrite (opener vs sustain, Guile windows)
; ============================================================================

global AppVersion := "6.0 — Spider's Web Edition"

; ============================================================================
; CORE GLOBALS
; ============================================================================
global ConfigFile    := A_ScriptDir "\MaraConfig.ini"
global IsRunning     := false
global RotationType  := "ST"
global DebugMode     := false
global GCDDelay      := 1500
global LastGCDTime   := 0
global RotationPhase := "SUSTAIN"   ; OPENER | SUSTAIN

; ============================================================================
; ██████  MODULE 2: STEALTH STATE ENGINE
; ============================================================================
; StealthState drives poison application.
; NONE    — normal combat, no stealth pending
; PENDING — Brooding Shadows was just cast; next builder WILL consume stealth
; CONSUMED — builder cast this tick consumed stealth; clear after 1 GCD
global StealthState       := "NONE"    ; "NONE" | "PENDING" | "CONSUMED"
global StealthConsumedBy  := ""        ; which ability consumed the stealth
global LastPoisonApplied  := ""        ; "Caustic" | "Seething" | "Volatile"
global StealthUsedTime    := 0         ; A_TickCount when stealth was entered
global StealthWindowMs    := 10000     ; stealth lasts ~10s before it auto-drops
global BroodingCharges    := 2         ; max 2 charges
global BroodingMaxCharges := 2

; ============================================================================
; RESOURCE TRACKING
; ============================================================================
global CurrentEnergy    := 200
global CurrentCP        := 0
global MaxEnergy        := 200
global MaxCP            := 6
global EnergyRegenRate  := 12.0        ; base energy/sec
global LastRegenTick    := 0

; ============================================================================
; BUFF / DEBUFF TIMERS  (A_TickCount expiry timestamps, 0 = inactive)
; ============================================================================
global BuffTimers := Map(
    "Maiden",           0,
    "AssassinsGuile",   0,
    "SeethingPoison",   0,    ; 60s, +40% energy regen while active
    "VolatilePoison",   0,    ; 6-8s, AoE explosion on expiry
    "CausticPoison",    0,    ; instant damage + 6CP, very short marker
    "Hemorrhage",       0,    ; bleed DoT, 3 energy/tick
    "DeadlyScheme",     0,    ; next finisher crits for 2x
    "ShadowProtection", 0,    ; 40% dmg reduction 4s
    "StalkerStep",      0     ; +50% move speed 4s
)

; ============================================================================
; MALEVOLENCE STACK TRACKING
; ============================================================================
global MalevolenceStacks := Map("QueensFang", 0, "ArachnidAssault", 0)
global MalevolenceTimers := Map("QueensFang", 0, "ArachnidAssault", 0)

; ============================================================================
; RESOURCE STACKS
; ============================================================================
global FeedTheQueenStacks  := 0
global HemotoxinStacks     := 0        ; Module 6 foundation
global HemotoxinTimer      := 0        ; 9s detonation window
global DeadlySchemeEnergy  := 0        ; accumulates toward 200 for proc

; ============================================================================
; TALENT TREE  (matches real Fellowship talent options)
; ============================================================================
global Talents := Map(
    "Malevolence",      true,   ; finishers stack; next cast of same finisher +100% dmg per stack
    "AssassinsGuile",   true,   ; opening from stealth empowers finishers +40% for 5s
    "FeedTheQueen",     false,  ; Skittering Blades stacks bonus Queen's Fang damage
    "Hemotoxin",        true,   ; adds Hemotoxin DoT to Hemorrhaging Strike, detonates for burst
    "FromTheShadows",   true,   ; stealth opener bonus
    "Bloodrush",        false,  ; Hemorrhaging Strike ticks 20% faster
    "GushingBlood",     false,  ; Maiden: Hemorrhaging Strike spreads bleed to 4 targets
    "VenomousDelight",  false,  ; poison damage 10% chance to restore 10 Energy
    "EfficientKiller",  false,  ; finishers cost 10% less energy, +10% max energy
    "Puncture",         false,  ; Skittering Blades leaves a ground DoT
    "DeadlyScheme",     false,  ; every 200 energy spent charges next finisher for 2x crit
    "RedLedger",        false,  ; Hemorrhaging Strike grants Attack Speed, stacks per bleed target
    "CorrosiveSpill",   false   ; 20% chance finishers leave poison pool
)

; ============================================================================
; PLAYER STATS
; ============================================================================
global PlayerStats := Map(
    "Haste",     10.0,
    "Crit",      25.0,
    "Spirit",     5.0,
    "Expertise", 20.0,
    "Agility",  1000.0   ; base Agility for damage calcs
)

; ============================================================================
; TARGETING
; ============================================================================
global TargetCount := 1
global TargetHP    := 100

; ============================================================================
; KEYBINDS
; ============================================================================
global Keybinds := Map()

; ============================================================================
; ABILITY DATA  (real numbers from Icy Veins)
; CooldownSec  — real cooldown in seconds (0 = GCD only)
; EnergyCost   — energy spent on cast
; EnergyGain   — energy generated on cast
; CPGain       — combo points generated (base, before crit)
; CPGainCrit   — CP gained on a critical strike
; IsFinisher   — true = spends all CP, scales with CP count
; IsBuilder    — true = generates CP
; ============================================================================
global AbilityData := Map()

InitializeAbilityData() {
    global AbilityData, Talents, MaxEnergy

    ; ── BUILDERS ──────────────────────────────────────────────
    AbilityData["Backstab"] := {
        cooldownSec:  0,
        energyCost:   20,
        energyGain:   0,
        cpGain:       2,
        cpGainCrit:   3,
        isFinisher:   false,
        isBuilder:    true,
        stealthPoison:"Caustic",    ; from stealth: Caustic Poison
        desc:         "83% Agility dmg, +40% from behind. 2 CP (3 crit)."
    }

    AbilityData["WidowsBite"] := {
        cooldownSec:  9.0,
        energyCost:   0,
        energyGain:   30,           ; generates 30 energy
        cpGain:       4,            ; 2 CP per strike × 2 strikes (base)
        cpGainCrit:   6,            ; 3 CP per strike × 2 strikes on crit
        isFinisher:   false,
        isBuilder:    true,
        stealthPoison:"Seething",   ; from stealth: Seething Poison (+40% energy regen 60s)
        desc:         "121%+90% Agility dual strike. 4 CP, +30 Energy. Stealth→Seething Poison."
    }

    AbilityData["SkitteringBlades"] := {
        cooldownSec:  0,
        energyCost:   35,
        energyGain:   0,
        cpGain:       1,            ; 1 CP per enemy hit (2 on crit) — TargetCount applied in UseAbility
        cpGainCrit:   2,
        isFinisher:   false,
        isBuilder:    true,
        stealthPoison:"Volatile",   ; from stealth: Volatile Poison on ALL enemies hit
        desc:         "60% Agility AoE. 1 CP per enemy hit (2 crit). Stealth→Volatile Poison."
    }

    ; ── FINISHERS ─────────────────────────────────────────────
    ; All three finishers: base + 20% per CP spent (so 6 CP = +120%)
    AbilityData["QueensFang"] := {
        cooldownSec:  0,
        energyCost:   40,
        energyGain:   0,
        cpGain:       0,
        cpGainCrit:   0,
        isFinisher:   true,
        isBuilder:    false,
        stealthPoison:"",
        desc:         "160% Agility + 20%/CP. ST finisher. Malevolence: +100% dmg/stack."
    }

    AbilityData["ArachnidAssault"] := {
        cooldownSec:  0,
        energyCost:   45,
        energyGain:   0,
        cpGain:       0,
        cpGainCrit:   0,
        isFinisher:   true,
        isBuilder:    false,
        stealthPoison:"",
        desc:         "65% Agility AoE + 20%/CP. AoE finisher. Malevolence: +100% dmg/stack."
    }

    AbilityData["HemorrhagingStrike"] := {
        cooldownSec:  6.0,
        energyCost:   20,
        energyGain:   0,            ; 3 energy per bleed tick (handled in regen)
        cpGain:       0,
        cpGainCrit:   0,
        isFinisher:   true,         ; spends CP to extend bleed duration
        isBuilder:    false,
        stealthPoison:"",
        desc:         "175% Agility + 77% bleed every 3s. Duration +3s/CP. Bloodrush: ticks 20% faster."
    }

    ; ── COOLDOWNS ─────────────────────────────────────────────
    AbilityData["BroodingShadows"] := {
        cooldownSec:  15.0,
        energyCost:   0,
        energyGain:   0,
        cpGain:       0,
        cpGainCrit:   0,
        isFinisher:   false,
        isBuilder:    false,
        stealthPoison:"",
        desc:         "Enter Stealth. Next builder applies poison. 2 charges (15s CD per charge)."
    }

    ; ── MODULE 1 FIX: Maiden of Death CD is 60s, not 90s ──────
    AbilityData["MaidenOfDeath"] := {
        cooldownSec:  60.0,         ; ✅ FIXED: was 90s, real CD is 60s
        energyCost:   0,
        energyGain:   0,
        cpGain:       0,
        cpGainCrit:   0,
        isFinisher:   false,
        isBuilder:    false,
        stealthPoison:"",
        desc:         "10s: +20% dmg, all builders=6 CP, +20% Energy Regen. CD: 60s (FIXED from 90s)."
    }

    AbilityData["ShadowProtection"] := {
        cooldownSec:  30.0,         ; 40% dmg reduction 4s
        energyCost:   0,
        energyGain:   0,
        cpGain:       0,
        cpGainCrit:   0,
        isFinisher:   false,
        isBuilder:    false,
        stealthPoison:"",
        desc:         "40% dmg reduction for 4 seconds. Defensive CD."
    }

    AbilityData["StalkerStep"] := {
        cooldownSec:  25.0,
        energyCost:   0,
        energyGain:   0,
        cpGain:       0,
        cpGainCrit:   0,
        isFinisher:   false,
        isBuilder:    false,
        stealthPoison:"",
        desc:         "Teleport behind target, +50% move speed 4s. Does not break stealth."
    }

    AbilityData["Kick"] := {
        cooldownSec:  16.0,
        energyCost:   0,
        energyGain:   0,
        cpGain:       0,
        cpGainCrit:   0,
        isFinisher:   false,
        isBuilder:    false,
        stealthPoison:"",
        desc:         "Interrupt. 4s lockout. 16s CD (lower than ranged DPS)."
    }

    ; ── CUSTOM: FinalStratagem (Morpheus personal macro) ──────
    AbilityData["FinalStratagem"] := {
        cooldownSec:  180.0,
        energyCost:   0,
        energyGain:   0,
        cpGain:       0,
        cpGainCrit:   0,
        isFinisher:   false,
        isBuilder:    false,
        stealthPoison:"",
        desc:         "CUSTOM MACRO: Full resource reset. Not a real Fellowship ability."
    }

    AbilityData["WeaponAbility"] := {
        cooldownSec:  90.0,
        energyCost:   0,
        energyGain:   0,
        cpGain:       0,
        cpGainCrit:   0,
        isFinisher:   false,
        isBuilder:    false,
        stealthPoison:"",
        desc:         "Weapon proc / Matriarch Macabre. Use during Maiden burst window."
    }

    ; Apply EfficientKiller modifier
    if Talents["EfficientKiller"] {
        for name, data in AbilityData {
            if data.energyCost > 0 {
                data.energyCost := Round(data.energyCost * 0.9)
            }
        }
        global MaxEnergy := 220
    }
}

; ── Cooldown tracking (last used timestamp per ability) ───────────────────
global LastUsedTime := Map()

InitializeLastUsed() {
    global LastUsedTime
    for ability in Keybinds {
        LastUsedTime[ability] := 0
    }
}

; ============================================================================
; STATISTICS
; ============================================================================
global AbilityStats := Map()
global ResourceStats := Map(
    "EnergyWasted",   0.0,
    "CPWasted",       0.0,
    "TotalCasts",     0,
    "TotalDamage",    0.0,
    "RotationTime",   0,
    "DPS",            0.0,
    "CPM",            0.0,
    "Uptime",         0.0,
    "StealthUses",    0,
    "GuileWindows",   0,
    "FinishersDuringGuile", 0
)
global RotationStartTime := 0

; ============================================================================
; UI GLOBALS
; ============================================================================
global MainGUI    := ""
global UIControls := Map()
global CurrentTheme := "DarkWidow"
global Themes := Map(
    "DarkWidow", {
        primary:    "2d1b4e",
        secondary:  "8b0000",
        accent:     "ffd700",
        background: "0a0a0a",
        panel:      "1a1a1a",
        text:       "ffffff",
        textDim:    "888888",
        stealth:    "8b00ff",    ; purple glow for stealth state
        guile:      "ff8c00",    ; orange for Guile window
        danger:     "ff2020"     ; red for warnings
    }
)

; ============================================================================
; INITIALIZATION
; ============================================================================
InitializeKeybinds() {
    global Keybinds := Map(
        "BroodingShadows",   "NumpadAdd",
        "WidowsBite",        "Numpad2",
        "HemorrhagingStrike","Numpad4",
        "Backstab",          "Numpad1",
        "ArachnidAssault",   "Numpad8",
        "QueensFang",        "Numpad5",
        "SkitteringBlades",  "Numpad3",
        "MaidenOfDeath",     "NumpadDiv",
        "WeaponAbility",     "Numpad9",
        "FinalStratagem",    "Numpad7",
        "StalkerStep",       "Right",
        "Kick",              "NumpadSub",
        "ShadowProtection",  "Numpad6"
    )
}

InitializeStats() {
    global AbilityStats := Map()
    for ability in Keybinds {
        AbilityStats[ability] := {
            used: 0, skipped: 0, damage: 0.0,
            cpSpent: 0, energySpent: 0,
            stealthCasts: 0, guileFinishers: 0
        }
    }
}

; ============================================================================
; ██████  MODULE 2: STEALTH ENGINE FUNCTIONS
; ============================================================================

; Called when BroodingShadows is successfully cast
EnterStealth() {
    global StealthState, StealthUsedTime, BroodingCharges, ResourceStats

    if BroodingCharges <= 0 {
        return false
    }

    BroodingCharges--
    StealthState    := "PENDING"
    StealthUsedTime := A_TickCount
    ResourceStats["StealthUses"]++

    LogDebug("🌑 STEALTH ENTERED — Brooding charges remaining: " BroodingCharges)
    return true
}

; Called at the start of UseAbility() for any builder cast
; Returns the poison name if stealth was consumed, "" if not in stealth
ConsumeStealthWith(ability) {
    global StealthState, StealthConsumedBy, LastPoisonApplied
    global StealthUsedTime, StealthWindowMs, AbilityData

    ; Check if stealth window has expired (>10s since Brooding cast)
    if StealthState = "PENDING" && (A_TickCount - StealthUsedTime) > StealthWindowMs {
        StealthState := "NONE"
        LogDebug("⚠️ Stealth window expired without cast!")
        return ""
    }

    if StealthState != "PENDING" {
        return ""
    }

    if !AbilityData.Has(ability) {
        return ""
    }

    ; Only builders consume stealth
    data := AbilityData[ability]
    if !data.isBuilder {
        return ""
    }

    poisonApplied      := data.stealthPoison
    StealthConsumedBy  := ability
    LastPoisonApplied  := poisonApplied
    StealthState       := "CONSUMED"

    LogDebug("🕷️ STEALTH CONSUMED by " ability " → " poisonApplied " Poison applied")
    return poisonApplied
}

; Clear CONSUMED state after the GCD resolves
ClearConsumedStealth() {
    global StealthState
    if StealthState = "CONSUMED" {
        StealthState := "NONE"
    }
}

; Is the bot currently in stealth (pending consumption)?
IsInStealth() {
    global StealthState, StealthUsedTime, StealthWindowMs
    if StealthState != "PENDING" {
        return false
    }
    ; Auto-expire
    if (A_TickCount - StealthUsedTime) > StealthWindowMs {
        global StealthState := "NONE"
        return false
    }
    return true
}

; ── Smart Brooding Decision ───────────────────────────────────────────────
; Should we use Brooding Shadows right now?
ShouldUseBrooding() {
    global BroodingCharges, StealthState, RotationType, TargetCount

    ; Don't enter stealth if already in stealth
    if StealthState = "PENDING" {
        return false
    }

    ; Need at least 1 charge
    if BroodingCharges <= 0 {
        return false
    }

    ; Module 4 preference: hold 1 charge for Seething reapply if it's expiring
    seethingRemaining := GetBuffRemaining("SeethingPoison")

    ; AOE: enter stealth when Volatile needs refreshing or we want mass AoE
    if RotationType = "AOE" && TargetCount >= 3 {
        ; Skittering Blades from stealth = Volatile on ALL enemies
        if !IsBuffActive("VolatilePoison") {
            return true
        }
        if seethingRemaining < 5 && BroodingCharges = 2 {
            return true   ; save 1 charge for Volatile, use 1 for Seething
        }
    }

    ; ST: standard Seething refresh cycle
    if seethingRemaining < 8 {
        return true       ; about to need Seething refresh
    }

    ; Guile window setup: use Brooding to empower a finisher sequence
    ; Only if we have CP to spend and Guile isn't already active
    if !IsBuffActive("AssassinsGuile") && CurrentCP >= 3 && BroodingCharges = 2 {
        return true
    }

    return false
}

; ── Which builder to cast FROM stealth? ──────────────────────────────────
GetStealthPreferredBuilder() {
    global RotationType, TargetCount, CurrentCP

    seethingRemaining := GetBuffRemaining("SeethingPoison")

    ; Priority 1: Seething Poison missing or < 5s → Widow's Bite
    if seethingRemaining < 5 {
        if IsAbilityReady("WidowsBite") {
            return "WidowsBite"
        }
    }

    ; Priority 2: AOE 3+ targets → Skittering Blades (Volatile on all)
    if RotationType = "AOE" && TargetCount >= 3 {
        if IsAbilityReady("SkitteringBlades") && CanAffordAbility("SkitteringBlades") {
            return "SkitteringBlades"
        }
    }

    ; Priority 3: CP at cap or near cap → Backstab (Caustic = instant 6CP bank)
    if CurrentCP >= 4 {
        return "Backstab"
    }

    ; Priority 4: Default Seething refresh
    if IsAbilityReady("WidowsBite") {
        return "WidowsBite"
    }

    ; Fallback
    return "Backstab"
}

; ============================================================================
; RESOURCE MANAGEMENT
; ============================================================================
UpdateEnergyRegen() {
    global CurrentEnergy, LastRegenTick, EnergyRegenRate, MaxEnergy
    global DeadlySchemeEnergy

    currentTime := A_TickCount
    if LastRegenTick = 0 {
        LastRegenTick := currentTime
        return
    }

    elapsed        := (currentTime - LastRegenTick) / 1000.0
    LastRegenTick  := currentTime

    regenRate := EnergyRegenRate

    ; Maiden of Death: +20% energy regen
    if IsBuffActive("Maiden") {
        regenRate *= 1.2
    }

    ; Seething Poison: Predator's Rush → +40% energy regen  (MODULE 1 FIX: was 1.4×, correct)
    if IsBuffActive("SeethingPoison") {
        regenRate *= 1.4
    }

    ; Hemorrhaging Strike bleed: +3 energy per tick (tick rate 3s, or 2.4s with Bloodrush)
    if IsBuffActive("Hemorrhage") {
        tickRate   := Talents["Bloodrush"] ? 2.4 : 3.0
        regenRate  += (3.0 / tickRate)
    }

    ; Venomous Delight: 10% chance per poison tick to restore 10 energy
    if Talents["VenomousDelight"] && (IsBuffActive("SeethingPoison") || IsBuffActive("VolatilePoison")) {
        if Random(1, 100) <= 10 {
            regenRate += (10.0 / elapsed)  ; approximate: inject 10 energy worth of rate
        }
    }

    oldEnergy      := CurrentEnergy
    energyGained   := regenRate * elapsed
    CurrentEnergy  := Min(MaxEnergy, CurrentEnergy + energyGained)

    ; Waste tracking
    if oldEnergy + energyGained > MaxEnergy {
        ResourceStats["EnergyWasted"] += (oldEnergy + energyGained - MaxEnergy)
    }

    ; Deadly Scheme accumulator
    if Talents["DeadlyScheme"] {
        global DeadlySchemeEnergy += energyGained
        if DeadlySchemeEnergy >= 200 && !IsBuffActive("DeadlyScheme") {
            BuffTimers["DeadlyScheme"] := A_TickCount + 12000
            global DeadlySchemeEnergy := 0
            ShowProcAlert("💀 DEADLY SCHEME", "Next finisher → 2× CRIT!")
        }
    }
}

UpdateBuffTimers() {
    ; Malevolence stack decay
    for finisher, timer in MalevolenceTimers {
        if timer > 0 && A_TickCount > timer {
            if MalevolenceStacks[finisher] > 0 {
                MalevolenceStacks[finisher]--
            }
            MalevolenceTimers[finisher] := 0
        }
    }

    ; Hemotoxin detonation window expiry warning
    if HemotoxinTimer > 0 && A_TickCount > HemotoxinTimer {
        global HemotoxinTimer  := 0
        global HemotoxinStacks := 0
        ShowProcAlert("⚠️ HEMOTOXIN EXPIRED", "Detonation window missed!")
    }

    ; ClearConsumedStealth each tick
    ClearConsumedStealth()
}

; ============================================================================
; ABILITY AVAILABILITY CHECKS
; ============================================================================
CanAffordAbility(ability) {
    if !AbilityData.Has(ability) {
        return true
    }
    data := AbilityData[ability]

    ; Energy check
    if data.energyCost > CurrentEnergy {
        return false
    }

    ; Finisher requires at least 1 CP
    if data.isFinisher && CurrentCP < 1 {
        return false
    }

    ; BroodingShadows needs a charge
    if ability = "BroodingShadows" && BroodingCharges <= 0 {
        return false
    }

    return true
}

IsAbilityReady(ability) {
    if !AbilityData.Has(ability) {
        return true
    }
    cd := AbilityData[ability].cooldownSec
    if cd = 0 {
        return true
    }
    if !LastUsedTime.Has(ability) || LastUsedTime[ability] = 0 {
        return true
    }
    elapsed := (A_TickCount - LastUsedTime[ability]) / 1000.0
    return elapsed >= cd
}

GetCooldownRemaining(ability) {
    if !AbilityData.Has(ability) {
        return 0
    }
    cd := AbilityData[ability].cooldownSec
    if cd = 0 {
        return 0
    }
    if !LastUsedTime.Has(ability) || LastUsedTime[ability] = 0 {
        return 0
    }
    elapsed   := (A_TickCount - LastUsedTime[ability]) / 1000.0
    remaining := cd - elapsed
    return Max(0, remaining)
}

IsBuffActive(buffName) {
    if !BuffTimers.Has(buffName) {
        return false
    }
    return BuffTimers[buffName] > A_TickCount
}

GetBuffRemaining(buffName) {
    ; Malevolence stacks have their own timer map
    if buffName = "MalevolenceQF" {
        if MalevolenceTimers["QueensFang"] = 0 {
            return 0
        }
        return Max(0, (MalevolenceTimers["QueensFang"] - A_TickCount) / 1000.0)
    }
    if buffName = "MalevolenceAA" {
        if MalevolenceTimers["ArachnidAssault"] = 0 {
            return 0
        }
        return Max(0, (MalevolenceTimers["ArachnidAssault"] - A_TickCount) / 1000.0)
    }
    if !BuffTimers.Has(buffName) {
        return 0
    }
    return Max(0, (BuffTimers[buffName] - A_TickCount) / 1000.0)
}

RecordAbilityUsed(ability) {
    if !AbilityData.Has(ability) {
        return
    }
    if AbilityData[ability].cooldownSec > 0 {
        LastUsedTime[ability] := A_TickCount
    }
}

; ============================================================================
; USE ABILITY — applies stealth engine and corrected mechanics
; ============================================================================
UseAbility(ability) {
    global CurrentEnergy, CurrentCP, MaxCP, MaxEnergy
    global BroodingCharges, FeedTheQueenStacks
    global MalevolenceStacks, MalevolenceTimers
    global HemotoxinStacks, HemotoxinTimer
    global ResourceStats

    if !AbilityData.Has(ability) {
        return
    }

    data := AbilityData[ability]

    ; ── Special: BroodingShadows ───────────────────────────────
    if ability = "BroodingShadows" {
        EnterStealth()
        RecordAbilityUsed("BroodingShadows")
        ; Brooding recharges are tracked by BroodingCharges counter
        ; A second charge is available after one full 15s CD
        ; (simplified: we track by BroodingCharges—max 2)
        return
    }

    ; ── Special: FinalStratagem ────────────────────────────────
    if ability = "FinalStratagem" {
        CurrentEnergy := MaxEnergy
        CurrentCP     := MaxCP
        for abilityName in LastUsedTime {
            if abilityName != "FinalStratagem" {
                LastUsedTime[abilityName] := 0
            }
        }
        BroodingCharges := BroodingMaxCharges
        ShowProcAlert("💥 FINAL STRATAGEM", "Full reset — GO NUCLEAR!")
        return
    }

    ; ── Special: MaidenOfDeath ────────────────────────────────
    if ability = "MaidenOfDeath" {
        BuffTimers["Maiden"] := A_TickCount + 10000   ; 10s window
        RecordAbilityUsed("MaidenOfDeath")
        ShowProcAlert("👑 MAIDEN OF DEATH", "10s burst — +20% dmg, all builders = 6 CP!")
        return
    }

    ; ── Special: ShadowProtection ─────────────────────────────
    if ability = "ShadowProtection" {
        BuffTimers["ShadowProtection"] := A_TickCount + 4000
        RecordAbilityUsed("ShadowProtection")
        ShowProcAlert("🛡️ SHADOW PROTECTION", "40% dmg reduction — 4s!")
        return
    }

    ; ── Special: StalkerStep ──────────────────────────────────
    if ability = "StalkerStep" {
        BuffTimers["StalkerStep"] := A_TickCount + 4000
        RecordAbilityUsed("StalkerStep")
        return
    }

    ; ── Special: WeaponAbility ────────────────────────────────
    if ability = "WeaponAbility" {
        RecordAbilityUsed("WeaponAbility")
        return
    }

    ; ── Special: Kick ─────────────────────────────────────────
    if ability = "Kick" {
        RecordAbilityUsed("Kick")
        return
    }

    ; ──────────────────────────────────────────────────────────
    ; MODULE 2: STEALTH CONSUMPTION — check before energy spend
    ; ──────────────────────────────────────────────────────────
    poisonApplied := ConsumeStealthWith(ability)
    inStealth     := (poisonApplied != "")

    ; Apply poison effects
    if inStealth {
        ApplyStealthPoison(ability, poisonApplied)
        AbilityStats[ability].stealthCasts++
    }

    ; ── Energy cost ───────────────────────────────────────────
    CurrentEnergy -= data.energyCost
    CurrentEnergy  := Max(0, CurrentEnergy)
    AbilityStats[ability].energySpent += data.energyCost

    ; Energy gain (Widow's Bite always generates 30)
    CurrentEnergy  := Min(MaxEnergy, CurrentEnergy + data.energyGain)

    ; ── BUILDERS ──────────────────────────────────────────────
    if data.isBuilder {
        ; MODULE 1 FIX: Maiden gives 6 CP to ALL builder casts (overrides normal cp gain)
        if IsBuffActive("Maiden") {
            cpGain := 6
        } else {
            ; Normal CP gain — check crit
            didCrit := (Random(1, 100) <= PlayerStats["Crit"])
            cpGain  := didCrit ? data.cpGainCrit : data.cpGain
        }

        ; MODULE 1 FIX: Backstab from stealth (Caustic Poison) grants 6 CP instantly
        ; This is handled in ApplyStealthPoison — cpGain is REPLACED here to avoid double-add
        if inStealth && ability = "Backstab" {
            cpGain := 6   ; Caustic Poison baseline is already 6 CP
        }

        ; Skittering Blades: 1 CP per enemy hit (2 on crit)
        if ability = "SkitteringBlades" {
            didCrit := (Random(1, 100) <= PlayerStats["Crit"])
            cpGain  := didCrit ? (data.cpGainCrit * TargetCount) : (data.cpGain * TargetCount)
            cpGain  := Min(cpGain, MaxCP)   ; cap at max CP

            if Talents["FeedTheQueen"] {
                global FeedTheQueenStacks := Min(6, FeedTheQueenStacks + 1)
            }
        }

        ; Assassin's Guile buff application — triggered by stealth builder
        if inStealth && Talents["AssassinsGuile"] {
            BuffTimers["AssassinsGuile"] := A_TickCount + 5000
            ResourceStats["GuileWindows"]++
            ShowProcAlert("⚡ ASSASSIN'S GUILE", "5s window — spam finishers NOW!")
        }

        oldCP     := CurrentCP
        CurrentCP := Min(MaxCP, CurrentCP + cpGain)

        if oldCP + cpGain > MaxCP {
            ResourceStats["CPWasted"] += (oldCP + cpGain - MaxCP)
        }

        RecordAbilityUsed(ability)
        return
    }

    ; ── FINISHERS ─────────────────────────────────────────────
    if data.isFinisher {
        spentCP   := CurrentCP
        CurrentCP := 0

        AbilityStats[ability].cpSpent += spentCP
        ResourceStats["TotalCasts"]++

        ; Track Guile finisher usage
        if IsBuffActive("AssassinsGuile") {
            AbilityStats[ability].guileFinishers++
            ResourceStats["FinishersDuringGuile"]++
        }

        ; Damage estimation
        agility     := PlayerStats["Agility"]
        baseDmgPct  := (ability = "QueensFang") ? 1.60
                     : (ability = "ArachnidAssault") ? 0.65
                     : (ability = "HemorrhagingStrike") ? 1.75
                     : 1.0

        cpBonus     := 0.20 * spentCP    ; +20% per CP (all 3 finishers scale identically)
        baseDmg     := agility * (baseDmgPct + cpBonus)

        ; Multipliers
        guileMult   := IsBuffActive("AssassinsGuile") ? 1.40 : 1.0
        maidenMult  := IsBuffActive("Maiden")         ? 1.20 : 1.0
        schemeMult  := IsBuffActive("DeadlyScheme")   ? 2.00 : 1.0

        malMult := 1.0
        if Talents["Malevolence"] {
            stacks := 0
            if ability = "QueensFang" {
                stacks := MalevolenceStacks["QueensFang"]
            } else if ability = "ArachnidAssault" {
                stacks := MalevolenceStacks["ArachnidAssault"]
            }
            if stacks > 0 {
                malMult := 1.0 + stacks   ; each stack = +100% (so 2 stacks = 3× total)
            }
        }

        ftqMult := 1.0
        if ability = "QueensFang" && FeedTheQueenStacks > 0 {
            ftqMult := 1.0 + (FeedTheQueenStacks * 0.15)
            global FeedTheQueenStacks := 0
        }

        totalDmg := baseDmg * guileMult * maidenMult * schemeMult * malMult * ftqMult

        AbilityStats[ability].damage       += totalDmg
        ResourceStats["TotalDamage"]       += totalDmg

        ; Clear Deadly Scheme after use
        if IsBuffActive("DeadlyScheme") {
            BuffTimers["DeadlyScheme"] := 0
        }

        ; Malevolence: add stack for repeated finisher use
        if Talents["Malevolence"] {
            if ability = "QueensFang" {
                MalevolenceStacks["QueensFang"] := Min(2, MalevolenceStacks["QueensFang"] + 1)
                MalevolenceTimers["QueensFang"] := A_TickCount + 20000
            } else if ability = "ArachnidAssault" {
                MalevolenceStacks["ArachnidAssault"] := Min(2, MalevolenceStacks["ArachnidAssault"] + 1)
                MalevolenceTimers["ArachnidAssault"] := A_TickCount + 20000
            }
        }

        ; HemorrhagingStrike: apply bleed
        if ability = "HemorrhagingStrike" {
            bleedDuration := 12 + (3 * spentCP)    ; base 12s + 3s per CP
            if Talents["Bloodrush"] {
                ; Ticks 20% faster — duration same but more ticks
            }
            BuffTimers["Hemorrhage"] := A_TickCount + (bleedDuration * 1000)

            ; Hemotoxin talent: each Hemorrhaging Strike applies Hemotoxin stacks
            if Talents["Hemotoxin"] {
                global HemotoxinStacks := Min(5, HemotoxinStacks + 1)
                global HemotoxinTimer  := A_TickCount + 9000   ; 9s detonation window
            }

            ; EfficientKiller: refund energy equal to CP spent
            if Talents["EfficientKiller"] {
                CurrentEnergy := Min(MaxEnergy, CurrentEnergy + spentCP)
            }
        }

        RecordAbilityUsed(ability)
    }
}

; Apply correct poison based on which builder was cast from stealth
ApplyStealthPoison(ability, poisonName) {
    global BuffTimers, CurrentCP, MaxCP

    if poisonName = "Caustic" {
        ; Caustic Poison: instant damage + 6 CP
        ; CP is applied in UseAbility builder section (cpGain := 6)
        BuffTimers["CausticPoison"] := A_TickCount + 2000   ; brief marker
        LogDebug("🟣 Caustic Poison — instant dmg + 6 CP")

    } else if poisonName = "Seething" {
        ; Seething Poison: +40% energy regen for 60s (Predator's Rush)
        BuffTimers["SeethingPoison"] := A_TickCount + 60000
        LogDebug("🟢 Seething Poison — Predator's Rush active (40% energy regen 60s)")

    } else if poisonName = "Volatile" {
        ; Volatile Poison: AoE DoT on ALL enemies hit, explodes on expiry
        ; Duration 6s base (Skittering from stealth: hits all targets)
        BuffTimers["VolatilePoison"] := A_TickCount + 6000
        LogDebug("🔴 Volatile Poison — AoE DoT on " TargetCount " targets (explosion on expiry)")
    }
}

; ============================================================================
; ██████  MODULE 4: PRIORITY LOGIC REWRITE
; ============================================================================
; Rotation follows Method.gg / Icy Veins confirmed priority ordering.
; Key windows that override normal priority:
;   1. FinalStratagem (custom reset macro) — use during Maiden if available
;   2. Maiden of Death burst window       — max finisher output for 10s
;   3. Assassin's Guile window            — 5s, MUST spam finishers here
;   4. Stealth sequence (Brooding ready)  — sets up Guile + poison
;   5. Hemotoxin detonation window        — 9s to detonate before stacks expire
;   6. Seething Poison maintenance        — highest sustain priority
;   7. Hemorrhage bleed upkeep            — maintain for 3 energy/tick
;   8. Finisher at 5–6 CP                 — never overcap
;   9. Brooding setup for next window     — when conditions are met
;  10. Backstab filler                    — default GCD fill

GetNextAbility() {
    UpdateEnergyRegen()
    UpdateBuffTimers()

    if RotationType = "ST" || TargetCount <= 2 {
        return GetSTPriority()
    } else {
        return GetAOEPriority()
    }
}

; ── Single Target Priority ────────────────────────────────────────────────
GetSTPriority() {

    ; ── P1: Final Stratagem during Maiden burst ───────────────
    if IsBuffActive("Maiden") && GetBuffRemaining("Maiden") > 2.0 {
        if IsAbilityReady("FinalStratagem") && CanAffordAbility("FinalStratagem") {
            return "FinalStratagem"
        }
    }

    ; ── P2: Maiden of Death — use immediately when off CD ─────
    ; Hold if FinalStratagem is <20s away (align them)
    if IsAbilityReady("MaidenOfDeath") && CanAffordAbility("MaidenOfDeath") {
        fsCD := GetCooldownRemaining("FinalStratagem")
        if fsCD = 0 || fsCD > 20 {
            return "MaidenOfDeath"
        }
    }

    ; ── P3: Weapon Ability — only inside Maiden window ────────
    if IsBuffActive("Maiden") && IsAbilityReady("WeaponAbility") && CanAffordAbility("WeaponAbility") {
        return "WeaponAbility"
    }

    ; ── P4: ASSASSIN'S GUILE WINDOW ──────────────────────────
    ; This is the highest DPS window — must pack 4 finishers in 5s.
    ; Priority: alternating QueensFang / ArachnidAssault for Malevolence stacks.
    if IsBuffActive("AssassinsGuile") {
        guileRemaining := GetBuffRemaining("AssassinsGuile")
        if guileRemaining > 0.3 && CurrentCP >= 4 {
            ; Spend Malevolence stacks on the correct finisher
            if Talents["Malevolence"] {
                if MalevolenceStacks["QueensFang"] < MalevolenceStacks["ArachnidAssault"] || MalevolenceStacks["ArachnidAssault"] >= 2 {
                    if CanAffordAbility("QueensFang") {
                        return "QueensFang"
                    }
                } else {
                    if CanAffordAbility("ArachnidAssault") {
                        return "ArachnidAssault"
                    }
                }
            }
            ; No Malevolence — just spam QueensFang
            if CanAffordAbility("QueensFang") {
                return "QueensFang"
            }
        }

        ; Inside Guile but low CP — build fast with Backstab
        if guileRemaining > 1.0 && CurrentCP < 4 && CurrentEnergy >= 20 {
            if CanAffordAbility("Backstab") {
                return "Backstab"
            }
        }
    }

    ; ── P5: HEMOTOXIN DETONATION (if Hemotoxin talented) ─────
    ; 9s window after Hemorrhaging Strike. Must cast detonate ability before expiry.
    ; (In Fellowship, Hemotoxin detonates via a follow-up cast on the target.
    ;  We model this as: cast QueensFang on Hemotoxin target when window is active.)
    if Talents["Hemotoxin"] && HemotoxinTimer > 0 {
        hemotoxinRemaining := Max(0, (HemotoxinTimer - A_TickCount) / 1000.0)
        ; If window is closing (<3s) and we have CP — detonate NOW
        if hemotoxinRemaining < 3.0 && hemotoxinRemaining > 0 && CurrentCP >= 3 {
            if CanAffordAbility("QueensFang") {
                return "QueensFang"
            }
        }
    }

    ; ── P6: SEETHING POISON UPKEEP ────────────────────────────
    ; This is the highest sustained priority. Seething = +40% energy regen.
    seethingRemaining := GetBuffRemaining("SeethingPoison")
    if seethingRemaining < 6.0 || !IsBuffActive("SeethingPoison") {
        if IsAbilityReady("BroodingShadows") && CanAffordAbility("BroodingShadows") && ShouldUseBrooding() {
            return "BroodingShadows"
        }
        ; If Brooding on CD but Widow's Bite is ready — use it without stealth
        if IsAbilityReady("WidowsBite") && CanAffordAbility("WidowsBite") {
            return "WidowsBite"
        }
    }

    ; ── P7: HEMORRHAGE BLEED MAINTENANCE ──────────────────────
    ; Keep bleed up for 3 energy/tick passive regen.
    hemorrhageRemaining := GetBuffRemaining("Hemorrhage")
    if hemorrhageRemaining < 3.0 && CurrentCP >= 3 {
        if IsAbilityReady("HemorrhagingStrike") && CanAffordAbility("HemorrhagingStrike") {
            return "HemorrhagingStrike"
        }
    }

    ; ── P8: BROODING SETUP for next Guile window ──────────────
    ; Enter stealth to set up next burst. Don't do this if Guile window just ended (<3s ago).
    ; Only when we have CP to spend soon after.
    if IsAbilityReady("BroodingShadows") && CanAffordAbility("BroodingShadows") {
        if ShouldUseBrooding() && !IsBuffActive("AssassinsGuile") {
            return "BroodingShadows"
        }
    }

    ; ── P9: EXECUTE STEALTH BUILDER (if pending) ──────────────
    ; If we're in stealth — cast the priority builder immediately
    if IsInStealth() {
        preferred := GetStealthPreferredBuilder()
        if preferred != "" && IsAbilityReady(preferred) && CanAffordAbility(preferred) {
            return preferred
        }
    }

    ; ── P10: FINISHER AT 6 CP (cap prevention) ────────────────
    if CurrentCP >= 6 {
        if Talents["Malevolence"] {
            if MalevolenceStacks["QueensFang"] < 2 && CanAffordAbility("QueensFang") {
                return "QueensFang"
            }
        }
        if CanAffordAbility("QueensFang") {
            return "QueensFang"
        }
    }

    ; ── P11: FINISHER AT 5 CP (optimal spend point) ───────────
    if CurrentCP >= 5 {
        if Talents["Malevolence"] && MalevolenceStacks["QueensFang"] < 2 {
            if CanAffordAbility("QueensFang") {
                return "QueensFang"
            }
        }
        if CanAffordAbility("QueensFang") {
            return "QueensFang"
        }
    }

    ; ── P12: WIDOW'S BITE — energy generation / off-CD refresh ─
    if IsAbilityReady("WidowsBite") && CanAffordAbility("WidowsBite") {
        ; Use if energy below threshold OR Seething getting low
        if CurrentEnergy < 80 || seethingRemaining < 10 {
            return "WidowsBite"
        }
    }

    ; ── P13: BACKSTAB FILLER ──────────────────────────────────
    if CurrentCP < 6 && CurrentEnergy >= 20 {
        if IsAbilityReady("Backstab") && CanAffordAbility("Backstab") {
            return "Backstab"
        }
    }

    ; ── P14: ENERGY DUMP — don't waste at cap ─────────────────
    if CurrentEnergy > (MaxEnergy - 25) {
        if IsAbilityReady("WidowsBite") && CanAffordAbility("WidowsBite") {
            return "WidowsBite"
        }
        if IsAbilityReady("Backstab") && CanAffordAbility("Backstab") {
            return "Backstab"
        }
    }

    ; ── P15: SPEND AT 4 CP rather than waste ──────────────────
    if CurrentCP >= 4 && CurrentEnergy < 60 {
        if CanAffordAbility("QueensFang") {
            return "QueensFang"
        }
    }

    return ""   ; nothing to do this GCD
}

; ── AOE Priority ──────────────────────────────────────────────────────────
GetAOEPriority() {

    ; P1–P3: Same as ST (Maiden/Weapon/FinalStratagem)
    if IsBuffActive("Maiden") && GetBuffRemaining("Maiden") > 2.0 {
        if IsAbilityReady("FinalStratagem") && CanAffordAbility("FinalStratagem") {
            return "FinalStratagem"
        }
    }
    if IsAbilityReady("MaidenOfDeath") && CanAffordAbility("MaidenOfDeath") {
        fsCD := GetCooldownRemaining("FinalStratagem")
        if fsCD = 0 || fsCD > 20 {
            return "MaidenOfDeath"
        }
    }
    if IsBuffActive("Maiden") && IsAbilityReady("WeaponAbility") && CanAffordAbility("WeaponAbility") {
        return "WeaponAbility"
    }

    ; P4: Guile window — AoE favours ArachnidAssault
    if IsBuffActive("AssassinsGuile") {
        guileRemaining := GetBuffRemaining("AssassinsGuile")
        if guileRemaining > 0.3 && CurrentCP >= 3 {
            if Talents["Malevolence"] {
                if MalevolenceStacks["ArachnidAssault"] < MalevolenceStacks["QueensFang"] || MalevolenceStacks["QueensFang"] >= 2 {
                    if CanAffordAbility("ArachnidAssault") {
                        return "ArachnidAssault"
                    }
                } else {
                    if CanAffordAbility("QueensFang") {
                        return "QueensFang"
                    }
                }
            }
            if CanAffordAbility("ArachnidAssault") {
                return "ArachnidAssault"
            }
        }
        if guileRemaining > 1.0 && CurrentCP < 3 {
            if TargetCount >= 3 && IsAbilityReady("SkitteringBlades") && CanAffordAbility("SkitteringBlades") {
                return "SkitteringBlades"
            }
        }
    }

    ; P5: Seething maintenance (same as ST)
    seethingRemaining := GetBuffRemaining("SeethingPoison")
    if seethingRemaining < 6.0 || !IsBuffActive("SeethingPoison") {
        if IsAbilityReady("BroodingShadows") && CanAffordAbility("BroodingShadows") && ShouldUseBrooding() {
            return "BroodingShadows"
        }
        if IsAbilityReady("WidowsBite") && CanAffordAbility("WidowsBite") {
            return "WidowsBite"
        }
    }

    ; P6: Volatile Poison refresh
    if !IsBuffActive("VolatilePoison") && TargetCount >= 3 {
        if IsAbilityReady("BroodingShadows") && CanAffordAbility("BroodingShadows") {
            return "BroodingShadows"   ; will use Skittering from stealth next GCD
        }
    }

    ; P7: Hemorrhage (AoE: higher CP threshold)
    hemorrhageRemaining := GetBuffRemaining("Hemorrhage")
    if hemorrhageRemaining < 3.0 && CurrentCP >= 5 {
        if IsAbilityReady("HemorrhagingStrike") && CanAffordAbility("HemorrhagingStrike") {
            return "HemorrhagingStrike"
        }
    }

    ; P8: Brooding setup
    if IsAbilityReady("BroodingShadows") && CanAffordAbility("BroodingShadows") {
        if ShouldUseBrooding() && !IsBuffActive("AssassinsGuile") {
            return "BroodingShadows"
        }
    }

    ; P9: Stealth builder (execute pending stealth)
    if IsInStealth() {
        preferred := GetStealthPreferredBuilder()
        if preferred != "" && IsAbilityReady(preferred) && CanAffordAbility(preferred) {
            return preferred
        }
    }

    ; P10: AoE finisher at threshold
    cpThreshold := Talents["FeedTheQueen"] ? 6 : 4
    if CurrentCP >= cpThreshold {
        if CanAffordAbility("ArachnidAssault") {
            return "ArachnidAssault"
        }
    }

    ; P11: Skittering Blades — main AoE builder
    if CurrentCP < 6 && CurrentEnergy >= 35 && TargetCount >= 3 {
        if IsAbilityReady("SkitteringBlades") && CanAffordAbility("SkitteringBlades") {
            return "SkitteringBlades"
        }
    }

    ; P12: Backstab filler when low targets or low energy
    if TargetCount <= 3 && CurrentCP < 6 && CurrentEnergy >= 20 {
        if IsAbilityReady("Backstab") && CanAffordAbility("Backstab") {
            return "Backstab"
        }
    }

    ; P13: Energy management
    if CurrentEnergy < 60 && IsAbilityReady("WidowsBite") && CanAffordAbility("WidowsBite") {
        return "WidowsBite"
    }
    if CurrentEnergy > (MaxEnergy - 25) {
        if IsAbilityReady("SkitteringBlades") && CanAffordAbility("SkitteringBlades") {
            return "SkitteringBlades"
        }
    }

    ; P14: Low CP AoE spend
    if CurrentCP >= 3 && CanAffordAbility("ArachnidAssault") {
        return "ArachnidAssault"
    }

    return ""
}

; ============================================================================
; UI — carried over from v5.0 with stealth state additions
; ============================================================================
CreateMainGUI() {
    global MainGUI, UIControls, AppVersion

    MainGUI := Gui("+AlwaysOnTop -DPIScale", "🕷️ Mara Ultimate v" AppVersion)
    MainGUI.BackColor := "0x0a0a0a"
    MainGUI.SetFont("s9", "Segoe UI")

    ; Header
    UIControls["HeaderBG"] := MainGUI.Add("Text", "x0 y0 w1020 h70 Background2d1b4e")
    MainGUI.SetFont("s16 bold cffd700")
    UIControls["Title"]    := MainGUI.Add("Text", "x20 y15 w280", "🕷️ MARA ULTIMATE v6.0")
    MainGUI.SetFont("s28 bold c00ff00")
    UIControls["DPSLive"]  := MainGUI.Add("Text", "x360 y10 w230 Center", "0 DPS")
    MainGUI.SetFont("s11 cWhite")
    UIControls["Timer"]    := MainGUI.Add("Text", "x620 y20 w140 Center", "⏱️ 0:00")
    MainGUI.SetFont("s12 bold c888888")
    UIControls["Status"]   := MainGUI.Add("Text", "x790 y18 w210 Center", "⚪ READY")
    MainGUI.SetFont("s8 c888888")
    MainGUI.Add("Text", "x20 y50 w980 Center",
        "MODULE 2: Stealth Engine  •  MODULE 1: Corrected Ability Data  •  MODULE 4: Priority Logic Overhaul")

    ; Resources
    CreateResourcePanel()

    ; Stealth State Panel (new in v6.0)
    CreateStealthPanel()

    ; Burst Windows
    CreateBurstPanel()

    ; Poison Tracker
    CreatePoisonPanel()

    ; Malevolence
    CreateMalevolencePanel()

    ; Ability Preview
    CreateAbilityPreview()

    ; Rotation Queue
    CreateRotationQueue()

    ; Performance
    CreatePerformancePanel()

    ; Config
    CreateConfigPanel()

    ; Controls
    CreateControlButtons()

    MainGUI.Show("w1020 h850")
    Log("✨ Mara Ultimate v" AppVersion " — Stealth Engine initialized!")
}

CreateResourcePanel() {
    UIControls["ResourcePanel"] := MainGUI.Add("GroupBox", "x20 y80 w310 h200 cWhite", "⚡ RESOURCES")
    MainGUI.SetFont("s36 bold c00ff00")
    UIControls["EnergyNum"] := MainGUI.Add("Text", "x30 y105 w290 h50 Center Background1a1a1a", CurrentEnergy)
    MainGUI.SetFont("s9 c888888")
    UIControls["EnergyMax"] := MainGUI.Add("Text", "x30 y158 w290 Center", "/ " MaxEnergy " Energy")
    MainGUI.SetFont("s11 cWhite")
    UIControls["EnergyPips"] := MainGUI.Add("Text", "x30 y175 w290 Center", GetEnergyPips())
    MainGUI.SetFont("s18 bold cffd700")
    UIControls["CPBox"] := MainGUI.Add("Text", "x90 y195 w140 h38 Center Border Background2d1b4e", CurrentCP " / 6 CP")
    MainGUI.SetFont("s9 cWhite")
    UIControls["BroodingLabel"] := MainGUI.Add("Text", "x30 y248 w140", "🌑 Brooding:")
    UIControls["BroodingValue"] := MainGUI.Add("Text", "x170 y248 w150 Right", "●● (ready)")
}

CreateStealthPanel() {
    ; MODULE 2: Stealth State visual — pulsing display of current state
    UIControls["StealthPanel"] := MainGUI.Add("GroupBox", "x340 y80 w310 h200 cWhite", "🌑 STEALTH ENGINE (Module 2)")

    MainGUI.SetFont("s22 bold c8b00ff")
    UIControls["StealthState"] := MainGUI.Add("Text", "x350 y105 w290 h45 Center Background1a1a1a", "NONE")

    MainGUI.SetFont("s9 cWhite")
    UIControls["StealthPoisonLabel"] := MainGUI.Add("Text", "x350 y158 w150", "Last Poison:")
    UIControls["StealthPoisonValue"] := MainGUI.Add("Text", "x500 y158 w140 Right c888888", "--")

    UIControls["StealthConsumedLabel"] := MainGUI.Add("Text", "x350 y178 w150", "Consumed By:")
    UIControls["StealthConsumedValue"] := MainGUI.Add("Text", "x500 y178 w140 Right c888888", "--")

    UIControls["StealthWindowLabel"] := MainGUI.Add("Text", "x350 y198 w150", "Window:")
    UIControls["StealthWindowValue"] := MainGUI.Add("Text", "x500 y198 w140 Right c888888", "--")

    MainGUI.SetFont("s9 cFFAA00")
    UIControls["StealthNextLabel"] := MainGUI.Add("Text", "x350 y220 w150", "Next stealth cast:")
    UIControls["StealthNextValue"] := MainGUI.Add("Text", "x500 y220 w140 Right cffd700", "--")

    MainGUI.SetFont("s8 c888888")
    UIControls["StealthGuileCount"] := MainGUI.Add("Text", "x350 y248 w290 Center", "Guile Windows: 0  |  Stealth Uses: 0")
}

CreateBurstPanel() {
    UIControls["BurstPanel"] := MainGUI.Add("GroupBox", "x660 y80 w340 h200 cWhite", "🔥 BURST WINDOWS")
    MainGUI.SetFont("s9 bold cWhite")

    UIControls["MaidenLabel"]  := MainGUI.Add("Text", "x670 y105 w100", "👑 Maiden:")
    UIControls["MaidenStatus"] := MainGUI.Add("Text", "x770 y105 w220 Right", "READY")
    UIControls["MaidenBar"]    := MainGUI.Add("Progress", "x670 y122 w320 h8 Background333333 c00ff00 Range0-10", 0)

    UIControls["WeaponLabel"]      := MainGUI.Add("Text", "x670 y135 w100", "⚔️ Weapon:")
    UIControls["MatriarchStatus"]  := MainGUI.Add("Text", "x770 y135 w220 Right", "90s")
    UIControls["WeaponBar"]        := MainGUI.Add("Progress", "x670 y150 w320 h8 Background333333 c00ff00 Range0-90", 0)

    UIControls["GuileLabel"]  := MainGUI.Add("Text", "x670 y163 w100", "⚡ Guile:")
    UIControls["GuileStatus"] := MainGUI.Add("Text", "x770 y163 w220 Right", "Inactive")
    UIControls["GuileBar"]    := MainGUI.Add("Progress", "x670 y178 w320 h8 Background333333 cFFAA00 Range0-5", 0)

    UIControls["HemotoxinLabel"]  := MainGUI.Add("Text", "x670 y191 w100", "🧪 Hemotoxin:")
    UIControls["HemotoxinStatus"] := MainGUI.Add("Text", "x770 y191 w220 Right", "0 stacks")
    UIControls["HemotoxinBar"]    := MainGUI.Add("Progress", "x670 y206 w320 h8 Background333333 cFF00FF Range0-9", 0)

    UIControls["FinalLabel"]  := MainGUI.Add("Text", "x670 y219 w100 cRed", "💥 ULTIMATE:")
    UIControls["FinalStatus"] := MainGUI.Add("Text", "x770 y219 w220 Right", "READY")
    UIControls["FinalBar"]    := MainGUI.Add("Progress", "x670 y234 w320 h8 Background333333 cRed Range0-180", 0)

    ; Maiden CD (FIXED: 60s)
    UIControls["MaidenCDLabel"] := MainGUI.Add("Text", "x670 y247 w320 Center c888888", "Maiden CD: 60s real | Was 90s (FIXED ✅)")
}

CreatePoisonPanel() {
    UIControls["PoisonPanel"] := MainGUI.Add("GroupBox", "x20 y292 w460 h155 cWhite", "☠️ POISON TRACKER")
    MainGUI.SetFont("s9 bold cWhite")

    UIControls["SeethingLabel"]  := MainGUI.Add("Text", "x30 y315 w120", "🟢 Seething:")
    UIControls["SeethingStatus"] := MainGUI.Add("Text", "x150 y315 w320 Right", "Inactive (Predator's Rush: OFF)")
    UIControls["SeethingBar"]    := MainGUI.Add("Progress", "x30 y333 w440 h12 Background333333 c00ff00 Range0-60", 0)

    UIControls["VolatileLabel"]  := MainGUI.Add("Text", "x30 y352 w120", "🔴 Volatile:")
    UIControls["VolatileStatus"] := MainGUI.Add("Text", "x150 y352 w320 Right", "Inactive")
    UIControls["VolatileBar"]    := MainGUI.Add("Progress", "x30 y368 w440 h12 Background333333 cFF0000 Range0-8", 0)

    UIControls["HemorrhageLabel"]  := MainGUI.Add("Text", "x30 y387 w120", "💉 Hemorrhage:")
    UIControls["HemorrhageStatus"] := MainGUI.Add("Text", "x150 y387 w320 Right", "Inactive")
    UIControls["HemorrhageBar"]    := MainGUI.Add("Progress", "x30 y403 w440 h12 Background333333 cAA0000 Range0-30", 0)

    MainGUI.SetFont("s8 c888888")
    UIControls["PoisonUptime"] := MainGUI.Add("Text", "x30 y425 w440 Center", "Poison Coverage: 0%")
}

CreateMalevolencePanel() {
    UIControls["MalPanel"] := MainGUI.Add("GroupBox", "x490 y292 w510 h155 cWhite", "⭐ MALEVOLENCE + STACKS")
    MainGUI.SetFont("s10 bold cWhite")

    UIControls["MalQFLabel"] := MainGUI.Add("Text", "x500 y315 w130", "👑 Queen's Fang:")
    UIControls["MalQF"]      := MainGUI.Add("Text", "x630 y315 w360 Right cffd700", "☆☆ (--)")
    UIControls["MalQFBar"]   := MainGUI.Add("Progress", "x500 y333 w490 h8 Background333333 cffd700 Range0-20", 0)

    UIControls["MalAALabel"] := MainGUI.Add("Text", "x500 y348 w130", "🕷️ Arachnid:")
    UIControls["MalAA"]      := MainGUI.Add("Text", "x630 y348 w360 Right cffd700", "☆☆ (--)")
    UIControls["MalAABar"]   := MainGUI.Add("Progress", "x500 y364 w490 h8 Background333333 cffd700 Range0-20", 0)

    UIControls["MalFTQLabel"] := MainGUI.Add("Text", "x500 y379 w130", "🌸 Feed Queen:")
    UIControls["MalFTQ"]      := MainGUI.Add("Text", "x630 y379 w360 Right cFF69B4", "0 stacks")
    UIControls["MalFTQBar"]   := MainGUI.Add("Progress", "x500 y395 w490 h8 Background333333 cFF69B4 Range0-6", 0)

    MainGUI.SetFont("s9 c00ff00")
    UIControls["MalMultiplier"] := MainGUI.Add("Text", "x500 y415 w490 Center", "Damage Multiplier: x1.0")
}

CreateAbilityPreview() {
    UIControls["PreviewPanel"] := MainGUI.Add("GroupBox", "x20 y460 w980 h130 cWhite", "🎯 NEXT ABILITY PREVIEW")

    MainGUI.SetFont("s42 cWhite")
    UIControls["AbilityIcon"] := MainGUI.Add("Text", "x40 y490 w80 h85 Center Background1a1a1a", "⚔️")

    MainGUI.SetFont("s14 bold cffd700")
    UIControls["NextAbility"] := MainGUI.Add("Text", "x140 y478 w850", "▶️ Waiting for action...")

    MainGUI.SetFont("s10 cWhite")
    UIControls["AbilityDamage"] := MainGUI.Add("Text", "x140 y508 w850", "Estimated Damage: --")

    MainGUI.SetFont("s9 c888888")
    UIControls["AbilityReason"] := MainGUI.Add("Text", "x140 y530 w850", "Priority Reason: Waiting...")

    MainGUI.SetFont("s9 cFFAA00")
    UIControls["AbilityCost"] := MainGUI.Add("Text", "x140 y552 w450", "Cost: --")

    MainGUI.SetFont("s9 c8b00ff")
    UIControls["StealthNote"] := MainGUI.Add("Text", "x600 y552 w390 Right", "")
}

CreateRotationQueue() {
    UIControls["QueuePanel"] := MainGUI.Add("GroupBox", "x20 y602 w980 h80 cWhite", "📜 ROTATION QUEUE — Next 5")
    MainGUI.SetFont("s10 bold cWhite")

    UIControls["Queue1"] := MainGUI.Add("Text", "x35 y625 w185 h45 Center Border Background2d1b4e cffd700", "1. --")
    MainGUI.Add("Text", "x225 y643 w20 Center", "→")
    UIControls["Queue2"] := MainGUI.Add("Text", "x250 y625 w185 h45 Center Border Background1a1a1a", "2. --")
    MainGUI.Add("Text", "x440 y643 w20 Center", "→")
    UIControls["Queue3"] := MainGUI.Add("Text", "x465 y625 w185 h45 Center Border Background1a1a1a", "3. --")
    MainGUI.Add("Text", "x655 y643 w20 Center", "→")
    UIControls["Queue4"] := MainGUI.Add("Text", "x680 y625 w155 h45 Center Border Background1a1a1a", "4. --")
    MainGUI.Add("Text", "x840 y643 w20 Center", "→")
    UIControls["Queue5"] := MainGUI.Add("Text", "x865 y625 w125 h45 Center Border Background1a1a1a", "5. --")
}

CreatePerformancePanel() {
    UIControls["PerfPanel"] := MainGUI.Add("GroupBox", "x20 y694 w980 h65 cWhite", "📊 PERFORMANCE")
    MainGUI.SetFont("s10 bold cWhite")

    UIControls["PerfDPSLabel"]   := MainGUI.Add("Text", "x35 y715 w60",  "DPS:")
    UIControls["PerfDPS"]        := MainGUI.Add("Text", "x95 y715 w90 Right c00ff00", "0")
    UIControls["PerfUptimeLabel"] := MainGUI.Add("Text", "x205 y715 w80",  "Uptime:")
    UIControls["PerfUptime"]     := MainGUI.Add("Text", "x285 y715 w80 Right c00ff00", "0%")
    UIControls["PerfCPMLabel"]   := MainGUI.Add("Text", "x385 y715 w60",  "CPM:")
    UIControls["PerfCPM"]        := MainGUI.Add("Text", "x445 y715 w80 Right cFFAA00", "0")
    UIControls["PerfWasteLabel"] := MainGUI.Add("Text", "x545 y715 w80",  "Waste:")
    UIControls["PerfWaste"]      := MainGUI.Add("Text", "x625 y715 w80 Right cFF8800", "0%")
    UIControls["PerfCastsLabel"] := MainGUI.Add("Text", "x725 y715 w70",  "Casts:")
    UIControls["PerfCasts"]      := MainGUI.Add("Text", "x795 y715 w60 Right cWhite", "0")
    UIControls["PerfGuileLabel"] := MainGUI.Add("Text", "x870 y715 w80",  "Guile:")
    UIControls["PerfGuile"]      := MainGUI.Add("Text", "x950 y715 w45 Right cFFAA00", "0")

    MainGUI.SetFont("s8 c888888")
    UIControls["EfficiencyLabel"] := MainGUI.Add("Text", "x35 y742 w100", "Efficiency:")
    UIControls["EfficiencyBar"]   := MainGUI.Add("Progress", "x140 y740 w855 h14 Background333333 c00ff00 Range0-100", 0)
}

CreateConfigPanel() {
    UIControls["ConfigPanel"] := MainGUI.Add("GroupBox", "x20 y770 w980 h45 cWhite", "⚙️ CONFIG")
    MainGUI.SetFont("s9 cWhite")

    MainGUI.Add("Text", "x35 y790 w100", "Target Count:")
    UIControls["TargetCount"] := MainGUI.Add("Edit", "x135 y787 w50 Center Background333333 cWhite", "1")
    MainGUI.Add("UpDown", "Range1-20", 1)
    MainGUI.Add("Text", "x195 y790 c888888", "(1-2=ST, 3+=AOE)")

    MainGUI.Add("Text", "x345 y790 w90", "Target HP %:")
    UIControls["TargetHP"] := MainGUI.Add("Edit", "x435 y787 w50 Center Background333333 cWhite", "100")
    MainGUI.Add("UpDown", "Range1-100", 100)

    UIControls["DebugCheck"] := MainGUI.Add("Checkbox", "x550 y787 w130 cWhite", "🐛 Debug Mode")
    UIControls["DebugCheck"].Value := DebugMode
    UIControls["DebugCheck"].OnEvent("Click", (*) => ToggleDebug())

    MainGUI.SetFont("s9 bold cFFAA00")
    UIControls["RotationTypeDisplay"] := MainGUI.Add("Text", "x730 y790 w260 Right", "Mode: Not Running")
}

CreateControlButtons() {
    MainGUI.SetFont("s9 bold")
    MainGUI.Add("Button", "x20 y825 w140 h60", "▶️ START`nST (F1)").OnEvent("Click", (*) => StartRotation("ST"))
    MainGUI.Add("Button", "x170 y825 w140 h60", "🌀 START`nAOE (F2)").OnEvent("Click", (*) => StartRotation("AOE"))
    MainGUI.Add("Button", "x320 y825 w100 h60", "⏸️`nPAUSE`n(F3)").OnEvent("Click", (*) => PauseRotation())
    MainGUI.Add("Button", "x430 y825 w100 h60", "⏹️`nSTOP`n(F4)").OnEvent("Click", (*) => StopRotation())
    MainGUI.Add("Button", "x540 y825 w110 h60", "🔄`nRESET`nRESOURCES").OnEvent("Click", (*) => ResetResources())

    MainGUI.SetFont("s9")
    MainGUI.Add("Button", "x665 y825 w100 h28", "⌨️ Keybinds (F5)").OnEvent("Click", (*) => ShowKeybindEditor())
    MainGUI.Add("Button", "x775 y825 w100 h28", "🎯 Talents (F6)").OnEvent("Click", (*) => ShowTalentEditor())
    MainGUI.Add("Button", "x885 y825 w115 h28", "📊 Analytics (F8)").OnEvent("Click", (*) => ShowAnalytics())
    MainGUI.Add("Button", "x665 y859 w100 h28", "📈 Stats").OnEvent("Click", (*) => ShowStatsEditor())
    MainGUI.Add("Button", "x775 y859 w100 h28", "💾 Save Config").OnEvent("Click", (*) => SaveConfig())
    MainGUI.Add("Button", "x885 y859 w115 h28", "❓ Help (F7)").OnEvent("Click", (*) => ShowHelp())
}

; ============================================================================
; GUI UPDATE
; ============================================================================
UpdateGUI() {
    if !IsObject(UIControls) {
        return
    }

    dps      := Round(ResourceStats["DPS"])
    dpsColor := (dps > 4000) ? "00ff00" : (dps > 3000) ? "ffaa00" : "ff0000"
    UIControls["DPSLive"].Value := dps " DPS"
    UIControls["DPSLive"].Opt("c" dpsColor)

    if RotationStartTime > 0 {
        elapsed := Round((A_TickCount - RotationStartTime) / 1000)
        min     := Floor(elapsed / 60)
        sec     := Mod(elapsed, 60)
        UIControls["Timer"].Value := "⏱️ " min ":" Format("{:02}", sec)
    }

    UIControls["Status"].Value := IsRunning ? "🔴 LIVE" : "⚪ READY"
    UIControls["Status"].Opt(IsRunning ? "cRed" : "c888888")

    UpdateResourceDisplay()
    UpdateStealthDisplay()
    UpdateBurstDisplay()
    UpdatePoisonDisplay()
    UpdateMalevolenceDisplay()
    UpdateAbilityPreview()
    UpdateRotationQueueDisplay()
    UpdatePerformanceDisplay()
}

UpdateResourceDisplay() {
    energyPct  := (CurrentEnergy / MaxEnergy) * 100
    energyColor := (energyPct > 75) ? "00ff00" : (energyPct > 40) ? "ffaa00" : "ff0000"
    UIControls["EnergyNum"].Value := Round(CurrentEnergy)
    UIControls["EnergyNum"].Opt("c" energyColor)
    UIControls["EnergyPips"].Value := GetEnergyPips()

    UIControls["CPBox"].Value := CurrentCP " / 6 CP"
    if CurrentCP = 6 {
        UIControls["CPBox"].Opt("Background8b0000 cffd700")
    } else {
        UIControls["CPBox"].Opt("Background2d1b4e cffd700")
    }

    ; Brooding charges
    if BroodingCharges >= 2 {
        UIControls["BroodingValue"].Value := "●● (2 charges)"
        UIControls["BroodingValue"].Opt("c00ff00")
    } else if BroodingCharges = 1 {
        cd := Round(GetCooldownRemaining("BroodingShadows"), 1)
        UIControls["BroodingValue"].Value := "●○ (1 — " cd "s)"
        UIControls["BroodingValue"].Opt("cFFAA00")
    } else {
        cd := Round(GetCooldownRemaining("BroodingShadows"), 1)
        UIControls["BroodingValue"].Value := "○○ (" cd "s)"
        UIControls["BroodingValue"].Opt("cRed")
    }
}

UpdateStealthDisplay() {
    ; MODULE 2: Stealth state visual
    switch StealthState {
        case "PENDING":
            windowRemaining := Max(0, (StealthWindowMs - (A_TickCount - StealthUsedTime)) / 1000.0)
            UIControls["StealthState"].Value := "🕷️ PENDING"
            UIControls["StealthState"].Opt("c8b00ff")
            UIControls["StealthWindowValue"].Value := Round(windowRemaining, 1) "s left"
            UIControls["StealthWindowValue"].Opt("c8b00ff")

            preferred := GetStealthPreferredBuilder()
            UIControls["StealthNextValue"].Value := preferred
            UIControls["StealthNextValue"].Opt("cffd700")

        case "CONSUMED":
            UIControls["StealthState"].Value := "✅ CONSUMED"
            UIControls["StealthState"].Opt("c00ff00")
            UIControls["StealthWindowValue"].Value := "Clearing..."
            UIControls["StealthWindowValue"].Opt("c888888")
            UIControls["StealthNextValue"].Value := StealthConsumedBy
            UIControls["StealthNextValue"].Opt("c00ff00")

        default:   ; NONE
            UIControls["StealthState"].Value := "○ NONE"
            UIControls["StealthState"].Opt("c888888")
            UIControls["StealthWindowValue"].Value := "--"
            UIControls["StealthWindowValue"].Opt("c888888")
            UIControls["StealthNextValue"].Value := "--"
            UIControls["StealthNextValue"].Opt("c888888")
    }

    UIControls["StealthPoisonValue"].Value := (LastPoisonApplied = "") ? "--" : LastPoisonApplied
    UIControls["StealthConsumedValue"].Value := (StealthConsumedBy = "") ? "--" : StealthConsumedBy

    UIControls["StealthGuileCount"].Value :=
        "Guile Windows: " ResourceStats["GuileWindows"] "  |  Stealth Uses: " ResourceStats["StealthUses"]
}

UpdateBurstDisplay() {
    ; Maiden (MODULE 1 FIX: real 60s CD)
    if IsBuffActive("Maiden") {
        remaining := Round(GetBuffRemaining("Maiden"), 1)
        UIControls["MaidenStatus"].Value := "ACTIVE (" remaining "s)"
        UIControls["MaidenStatus"].Opt("c00ff00")
        UIControls["MaidenBar"].Value := remaining
    } else if IsAbilityReady("MaidenOfDeath") {
        UIControls["MaidenStatus"].Value := "READY"
        UIControls["MaidenStatus"].Opt("c00ff00")
        UIControls["MaidenBar"].Value := 10
    } else {
        cd := Round(GetCooldownRemaining("MaidenOfDeath"))
        UIControls["MaidenStatus"].Value := cd "s (60s CD)"
        UIControls["MaidenStatus"].Opt("c888888")
        UIControls["MaidenBar"].Value := 0
    }

    ; Weapon
    weaponCD := Round(GetCooldownRemaining("WeaponAbility"))
    if weaponCD = 0 {
        UIControls["MatriarchStatus"].Value := "READY"
        UIControls["MatriarchStatus"].Opt("c00ff00")
        UIControls["WeaponBar"].Value := 90
    } else {
        UIControls["MatriarchStatus"].Value := weaponCD "s"
        UIControls["MatriarchStatus"].Opt("c888888")
        UIControls["WeaponBar"].Value := Max(0, 90 - weaponCD)
    }

    ; Guile
    if IsBuffActive("AssassinsGuile") {
        remaining := Round(GetBuffRemaining("AssassinsGuile"), 1)
        UIControls["GuileStatus"].Value := "⚡ ACTIVE — SPAM FINISHERS (" remaining "s)"
        UIControls["GuileStatus"].Opt("cFFAA00")
        UIControls["GuileBar"].Value := remaining
    } else {
        UIControls["GuileStatus"].Value := "Inactive (use Brooding to activate)"
        UIControls["GuileStatus"].Opt("c888888")
        UIControls["GuileBar"].Value := 0
    }

    ; Hemotoxin
    if HemotoxinTimer > 0 {
        htRemaining := Round(Max(0, (HemotoxinTimer - A_TickCount) / 1000.0), 1)
        UIControls["HemotoxinStatus"].Value := "⚠️ DETONATE! " htRemaining "s (" HemotoxinStacks " stacks)"
        UIControls["HemotoxinStatus"].Opt(htRemaining < 3 ? "cFF0000" : "cFF00FF")
        UIControls["HemotoxinBar"].Value := htRemaining
    } else {
        UIControls["HemotoxinStatus"].Value := HemotoxinStacks " stacks"
        UIControls["HemotoxinStatus"].Opt("c888888")
        UIControls["HemotoxinBar"].Value := HemotoxinStacks
    }

    ; Final Stratagem
    finalCD := Round(GetCooldownRemaining("FinalStratagem"))
    if finalCD = 0 {
        UIControls["FinalStatus"].Value := "READY!!!"
        UIControls["FinalStatus"].Opt("cFF0000")
        UIControls["FinalBar"].Value := 180
    } else {
        UIControls["FinalStatus"].Value := finalCD "s"
        UIControls["FinalStatus"].Opt("c888888")
        UIControls["FinalBar"].Value := Max(0, 180 - finalCD)
    }
}

UpdatePoisonDisplay() {
    ; Seething (with Predator's Rush indicator)
    if IsBuffActive("SeethingPoison") {
        remaining := Round(GetBuffRemaining("SeethingPoison"))
        UIControls["SeethingStatus"].Value := remaining "s — Predator's Rush: +40% Energy Regen"
        UIControls["SeethingStatus"].Opt("c00ff00")
        UIControls["SeethingBar"].Value := remaining
    } else {
        UIControls["SeethingStatus"].Value := "Inactive (Predator's Rush: OFF — DPS LOSS!)"
        UIControls["SeethingStatus"].Opt("cRed")
        UIControls["SeethingBar"].Value := 0
    }

    ; Volatile
    if IsBuffActive("VolatilePoison") {
        remaining := Round(GetBuffRemaining("VolatilePoison"), 1)
        UIControls["VolatileStatus"].Value := remaining "s — explosion on expiry"
        UIControls["VolatileStatus"].Opt("cFF8800")
        UIControls["VolatileBar"].Value := remaining
    } else {
        UIControls["VolatileStatus"].Value := "Inactive"
        UIControls["VolatileStatus"].Opt("c666666")
        UIControls["VolatileBar"].Value := 0
    }

    ; Hemorrhage
    if IsBuffActive("Hemorrhage") {
        remaining := Round(GetBuffRemaining("Hemorrhage"))
        UIControls["HemorrhageStatus"].Value := remaining "s — +3 Energy/tick"
        UIControls["HemorrhageStatus"].Opt("cAA0000")
        UIControls["HemorrhageBar"].Value := remaining
    } else {
        UIControls["HemorrhageStatus"].Value := "Inactive"
        UIControls["HemorrhageStatus"].Opt("c666666")
        UIControls["HemorrhageBar"].Value := 0
    }

    ; Coverage
    active := (IsBuffActive("SeethingPoison") ? 1 : 0)
            + (IsBuffActive("VolatilePoison")  ? 1 : 0)
            + (IsBuffActive("Hemorrhage")      ? 1 : 0)
    UIControls["PoisonUptime"].Value := "Poison Coverage: " Round((active / 3) * 100) "%  (" active "/3 active)"
}

UpdateMalevolenceDisplay() {
    if Talents["Malevolence"] {
        qfS := MalevolenceStacks["QueensFang"]
        aaS := MalevolenceStacks["ArachnidAssault"]

        qfStars := (qfS >= 2) ? "★★" : (qfS = 1) ? "★☆" : "☆☆"
        if qfS > 0 {
            qfTime := Round(GetBuffRemaining("MalevolenceQF"))
            UIControls["MalQF"].Value := qfStars " (" qfTime "s) — x" (1 + qfS) " next QF"
            UIControls["MalQF"].Opt("cffd700")
            UIControls["MalQFBar"].Value := qfTime
        } else {
            UIControls["MalQF"].Value := qfStars " (--)"
            UIControls["MalQF"].Opt("c666666")
            UIControls["MalQFBar"].Value := 0
        }

        aaStars := (aaS >= 2) ? "★★" : (aaS = 1) ? "★☆" : "☆☆"
        if aaS > 0 {
            aaTime := Round(GetBuffRemaining("MalevolenceAA"))
            UIControls["MalAA"].Value := aaStars " (" aaTime "s) — x" (1 + aaS) " next AA"
            UIControls["MalAA"].Opt("cffd700")
            UIControls["MalAABar"].Value := aaTime
        } else {
            UIControls["MalAA"].Value := aaStars " (--)"
            UIControls["MalAA"].Opt("c666666")
            UIControls["MalAABar"].Value := 0
        }

        totalMult := 1.0
        if qfS > 0 {
            totalMult *= (1.0 + qfS)
        }
        if aaS > 0 {
            totalMult *= (1.0 + aaS)
        }
        UIControls["MalMultiplier"].Value := "Damage Multiplier: x" Round(totalMult, 2)
    } else {
        UIControls["MalQF"].Value      := "Talent disabled"
        UIControls["MalAA"].Value      := "Talent disabled"
        UIControls["MalMultiplier"].Value := "Malevolence: Disabled"
    }

    UIControls["MalFTQ"].Value := FeedTheQueenStacks " stacks"
    UIControls["MalFTQBar"].Value := FeedTheQueenStacks
}

UpdateAbilityPreview() {
    nextAbility := GetNextAbility()

    abilityIcons := Map(
        "QueensFang",        "👑",
        "ArachnidAssault",   "🕷️",
        "HemorrhagingStrike","💀",
        "Backstab",          "🗡️",
        "WidowsBite",        "🕸️",
        "SkitteringBlades",  "🌀",
        "MaidenOfDeath",     "👸",
        "BroodingShadows",   "🌑",
        "WeaponAbility",     "⚔️",
        "FinalStratagem",    "💥",
        "ShadowProtection",  "🛡️",
        "StalkerStep",       "💨"
    )

    if nextAbility = "" {
        UIControls["NextAbility"].Value  := "⏸️ Waiting..."
        UIControls["AbilityDamage"].Value := "No ability queued"
        UIControls["AbilityReason"].Value := ""
        UIControls["AbilityCost"].Value   := ""
        UIControls["StealthNote"].Value   := ""
        UIControls["AbilityIcon"].Value   := "⏳"
        return
    }

    icon := abilityIcons.Has(nextAbility) ? abilityIcons[nextAbility] : "⚔️"
    UIControls["NextAbility"].Value := "▶️ " nextAbility
    UIControls["AbilityIcon"].Value := icon

    ; Stealth annotation
    if IsInStealth() && AbilityData.Has(nextAbility) && AbilityData[nextAbility].isBuilder {
        UIControls["StealthNote"].Value := "🌑 FROM STEALTH → " AbilityData[nextAbility].stealthPoison " POISON"
        UIControls["StealthNote"].Opt("c8b00ff")
    } else {
        UIControls["StealthNote"].Value := ""
    }

    ; Cost display
    if AbilityData.Has(nextAbility) {
        d := AbilityData[nextAbility]
        costParts := []
        if d.energyCost > 0 {
            costParts.Push(d.energyCost " Energy")
        }
        if d.isFinisher {
            costParts.Push(CurrentCP " CP (spends all)")
        }
        if d.energyGain > 0 {
            costParts.Push("+" d.energyGain " Energy")
        }
        if d.cpGain > 0 {
            costParts.Push("+" d.cpGain " CP")
        }
        UIControls["AbilityCost"].Value := "Cost: " (costParts.Length = 0 ? "Free" : ArrJoin(costParts, " | "))
    }

    ; Damage estimate for finishers
    if AbilityData.Has(nextAbility) && AbilityData[nextAbility].isFinisher {
        agility    := PlayerStats["Agility"]
        basePct    := (nextAbility = "QueensFang")         ? 1.60
                    : (nextAbility = "ArachnidAssault")    ? 0.65
                    : (nextAbility = "HemorrhagingStrike") ? 1.75
                    : 1.0
        cpBonus    := 0.20 * CurrentCP
        baseDmg    := agility * (basePct + cpBonus)

        mults := []
        totalM := 1.0
        if IsBuffActive("AssassinsGuile") {
            totalM *= 1.4
            mults.Push("Guile +40%")
        }
        if IsBuffActive("Maiden") {
            totalM *= 1.2
            mults.Push("Maiden +20%")
        }
        if IsBuffActive("DeadlyScheme") {
            totalM *= 2.0
            mults.Push("CRIT ×2")
        }
        if Talents["Malevolence"] {
            stacks := (nextAbility = "QueensFang")      ? MalevolenceStacks["QueensFang"]
                    : (nextAbility = "ArachnidAssault") ? MalevolenceStacks["ArachnidAssault"]
                    : 0
            if stacks > 0 {
                totalM *= (1.0 + stacks)
                mults.Push("Mal ×" (1 + stacks))
            }
        }

        estDmg := Round(baseDmg * totalM)
        buffTxt := mults.Length > 0 ? " [" ArrJoin(mults, " + ") "]" : ""
        UIControls["AbilityDamage"].Value := "Est. Damage: ~" estDmg buffTxt
    } else if AbilityData.Has(nextAbility) && AbilityData[nextAbility].isBuilder {
        UIControls["AbilityDamage"].Value := "Builder — generates CP"
    } else {
        UIControls["AbilityDamage"].Value := "Cooldown / Utility"
    }

    UIControls["AbilityReason"].Value := "Priority: " GetAbilityReason(nextAbility)
}

UpdateRotationQueueDisplay() {
    ; Save state
    savedEnergy   := CurrentEnergy
    savedCP       := CurrentCP
    savedBrooding := BroodingCharges
    savedStealth  := StealthState

    queue := []
    Loop 5 {
        next := GetNextAbility()
        if next = "" {
            break
        }
        queue.Push(next)

        ; Simulate minimal state change
        if AbilityData.Has(next) {
            d := AbilityData[next]
            CurrentEnergy -= d.energyCost
            CurrentEnergy  := Max(0, CurrentEnergy)
            CurrentEnergy  := Min(MaxEnergy, CurrentEnergy + d.energyGain)
            if d.isFinisher {
                CurrentCP := 0
            } else if d.isBuilder {
                CurrentCP := Min(MaxCP, CurrentCP + d.cpGain)
            }
        }

        if A_Index > 8 {
            break
        }
    }

    ; Restore state
    global CurrentEnergy   := savedEnergy
    global CurrentCP       := savedCP
    global BroodingCharges := savedBrooding
    global StealthState    := savedStealth

    shortNames := Map(
        "QueensFang",        "Queen's Fang",
        "ArachnidAssault",   "Arachnid",
        "HemorrhagingStrike","Hemorrhage",
        "Backstab",          "Backstab",
        "WidowsBite",        "Widow's",
        "SkitteringBlades",  "Skittering",
        "MaidenOfDeath",     "MAIDEN",
        "BroodingShadows",   "🌑Brooding",
        "WeaponAbility",     "Weapon",
        "FinalStratagem",    "FINAL"
    )

    Loop 5 {
        if A_Index <= queue.Length {
            ability := queue[A_Index]
            name    := shortNames.Has(ability) ? shortNames[ability] : ability
            UIControls["Queue" A_Index].Value := name
            UIControls["Queue" A_Index].Opt(A_Index = 1 ? "cffd700 Background2d1b4e" : "cWhite Background1a1a1a")
        } else {
            UIControls["Queue" A_Index].Value := "--"
            UIControls["Queue" A_Index].Opt("c666666 Background1a1a1a")
        }
    }
}

UpdatePerformanceDisplay() {
    dps      := Round(ResourceStats["DPS"])
    dpsColor := (dps > 4000) ? "00ff00" : (dps > 3000) ? "ffaa00" : "ff8800"
    UIControls["PerfDPS"].Value := dps
    UIControls["PerfDPS"].Opt("c" dpsColor)

    UIControls["PerfUptime"].Value := IsRunning ? "100%" : "0%"
    UIControls["PerfUptime"].Opt(IsRunning ? "c00ff00" : "cFFAA00")

    if ResourceStats["RotationTime"] > 0 {
        cpm := Round((ResourceStats["TotalCasts"] / ResourceStats["RotationTime"]) * 60)
        UIControls["PerfCPM"].Value := cpm
    }

    totalWaste := ResourceStats["EnergyWasted"] + ResourceStats["CPWasted"]
    if ResourceStats["TotalCasts"] > 0 {
        wastePct := Round((totalWaste / (ResourceStats["TotalCasts"] * 10)), 1)
        UIControls["PerfWaste"].Value := wastePct "%"
        UIControls["PerfWaste"].Opt(wastePct < 5 ? "c00ff00" : wastePct < 10 ? "cFFAA00" : "cFF0000")
    }

    UIControls["PerfCasts"].Value := ResourceStats["TotalCasts"]
    UIControls["PerfGuile"].Value := ResourceStats["GuileWindows"]

    if MaxEnergy > 0 {
        eff := Max(0, 100 - Round((ResourceStats["EnergyWasted"] / (MaxEnergy * 10)) * 100))
        UIControls["EfficiencyBar"].Value := Min(100, eff)
    }
}

; ============================================================================
; ABILITY REASON STRINGS (updated for Module 4)
; ============================================================================
GetAbilityReason(ability) {
    if ability = "FinalStratagem" {
        return "ULTIMATE — full reset during Maiden"
    }
    if ability = "MaidenOfDeath" {
        return "Burst cooldown — 60s CD (FIXED)"
    }
    if ability = "WeaponAbility" {
        return "Weapon burst — use inside Maiden window"
    }
    if ability = "BroodingShadows" {
        return IsBuffActive("SeethingPoison") ? "Setup next Guile window" : "Seething Poison expiring — refresh!"
    }
    if ability = "WidowsBite" {
        if GetBuffRemaining("SeethingPoison") < 6 {
            return "Seething < 6s — Predator's Rush at risk!"
        }
        if CurrentEnergy < 80 {
            return "Emergency energy gen (+30 Energy)"
        }
        return "Energy gen + 4 CP (6 on crit)"
    }
    if ability = "HemorrhagingStrike" {
        return "Bleed maintenance — 3 energy/tick | Hemotoxin window: " Round(Max(0, (HemotoxinTimer - A_TickCount) / 1000)) "s"
    }
    if ability = "QueensFang" {
        if IsBuffActive("AssassinsGuile") {
            return "⚡ GUILE WINDOW — " CurrentCP " CP × 1.4 Guile!"
        }
        if Talents["Hemotoxin"] && HemotoxinTimer > 0 {
            return "⚠️ Hemotoxin DETONATE — " Round(Max(0, (HemotoxinTimer - A_TickCount) / 1000)) "s left"
        }
        return CurrentCP " CP spend — " (CurrentCP >= 6 ? "CAP PREVENTION" : "optimal spend")
    }
    if ability = "ArachnidAssault" {
        if IsBuffActive("AssassinsGuile") {
            return "⚡ GUILE WINDOW — AoE finisher × 1.4"
        }
        return "AoE finisher — " CurrentCP " CP"
    }
    if ability = "Backstab" {
        if IsInStealth() {
            return "🌑 FROM STEALTH → Caustic Poison (+6 CP instant)"
        }
        return "CP filler — 2 CP (3 crit)"
    }
    if ability = "SkitteringBlades" {
        if IsInStealth() {
            return "🌑 FROM STEALTH → Volatile Poison on ALL " TargetCount " targets"
        }
        return "AoE builder — " TargetCount " CP (" TargetCount "× hits)"
    }
    return "Priority engine"
}

; ============================================================================
; HELPER FUNCTIONS
; ============================================================================
ArrJoin(arr, sep) {
    result := ""
    for item in arr {
        result .= (A_Index = 1 ? "" : sep) item
    }
    return result
}

GetEnergyPips() {
    pips := ""
    Loop 10 {
        pips .= (CurrentEnergy >= A_Index * (MaxEnergy / 10)) ? "●" : "○"
    }
    return pips
}

LogDebug(msg) {
    if DebugMode {
        OutputDebug(msg)
    }
}

Log(msg) {
    ; Placeholder for logging
}

ShowProcAlert(title, message) {
    if !DebugMode {
        return
    }
    alertGUI := Gui("+AlwaysOnTop -Caption +ToolWindow")
    alertGUI.BackColor := "8b0000"
    alertGUI.SetFont("s13 bold cWhite")
    alertGUI.Add("Text", "x10 y10 w310 Center", title)
    alertGUI.SetFont("s9 norm")
    alertGUI.Add("Text", "x10 y42 w310 Center", message)
    alertGUI.Show("w330 h75 NoActivate")
    SetTimer(() => alertGUI.Destroy(), -3000)
}

ToggleDebug() {
    global DebugMode := UIControls["DebugCheck"].Value
}

; ============================================================================
; ROTATION EXECUTION
; ============================================================================
StartRotation(type) {
    global IsRunning, RotationType, TargetCount, TargetHP, RotationStartTime

    if IsRunning {
        MsgBox("⚠️ Rotation already running!", "Warning", "Icon!")
        return
    }

    try {
        TargetCount := Integer(UIControls["TargetCount"].Value)
        TargetHP    := Integer(UIControls["TargetHP"].Value)
    } catch {
        TargetCount := 1
        TargetHP    := 100
    }

    RotationType     := type
    IsRunning        := true
    RotationStartTime := A_TickCount

    UIControls["RotationTypeDisplay"].Value := "Mode: " (type = "ST" ? "Single Target" : "AOE")

    SetTimer UpdateRotation, 100
}

UpdateRotation() {
    global IsRunning, LastGCDTime, GCDDelay

    if !IsRunning {
        SetTimer UpdateRotation, 0
        return
    }

    UpdateGUI()

    currentTime := A_TickCount
    if LastGCDTime > 0 && (currentTime - LastGCDTime) < GCDDelay {
        return
    }

    nextAbility := GetNextAbility()

    if nextAbility = "" {
        return
    }

    if !IsAbilityReady(nextAbility) {
        if AbilityStats.Has(nextAbility) {
            AbilityStats[nextAbility].skipped++
        }
        return
    }

    if !CanAffordAbility(nextAbility) {
        return
    }

    if !Keybinds.Has(nextAbility) {
        return
    }

    abilityKey := Keybinds[nextAbility]

    try {
        Send("{" abilityKey "}")

        UseAbility(nextAbility)
        if AbilityStats.Has(nextAbility) {
            AbilityStats[nextAbility].used++
        }
        ResourceStats["TotalCasts"]++

        if RotationStartTime > 0 {
            elapsedSec := (A_TickCount - RotationStartTime) / 1000
            ResourceStats["RotationTime"] := elapsedSec
            if elapsedSec > 0 {
                ResourceStats["DPS"] := ResourceStats["TotalDamage"] / elapsedSec
            }
        }

        LastGCDTime := A_TickCount

        hasteReduction := PlayerStats["Haste"] / 100
        global GCDDelay := Round(1500 * (1 - Min(hasteReduction, 0.15)))

    } catch as err {
        LogDebug("⚠️ Ability error: " err.Message)
    }
}

PauseRotation() {
    global IsRunning := false
    SetTimer UpdateRotation, 0
}

StopRotation() {
    global IsRunning := false
    SetTimer UpdateRotation, 0
}

ResetResources() {
    global CurrentEnergy      := MaxEnergy
    global CurrentCP          := 0
    global BroodingCharges    := BroodingMaxCharges
    global FeedTheQueenStacks := 0
    global HemotoxinStacks    := 0
    global HemotoxinTimer     := 0
    global DeadlySchemeEnergy := 0
    global RotationStartTime  := 0
    global StealthState       := "NONE"
    global StealthConsumedBy  := ""
    global LastPoisonApplied  := ""
    global StealthUsedTime    := 0

    MalevolenceStacks["QueensFang"]     := 0
    MalevolenceStacks["ArachnidAssault"] := 0
    MalevolenceTimers["QueensFang"]     := 0
    MalevolenceTimers["ArachnidAssault"] := 0

    for buff in BuffTimers {
        BuffTimers[buff] := 0
    }

    for ability in LastUsedTime {
        LastUsedTime[ability] := 0
    }

    for stat in ResourceStats {
        ResourceStats[stat] := 0
    }

    UpdateGUI()
}

; ============================================================================
; CONFIG EDITORS
; ============================================================================
ShowKeybindEditor() {
    KeyGUI := Gui("+Owner" MainGUI.Hwnd " +AlwaysOnTop", "⌨️ Keybinds")
    KeyGUI.BackColor := "0x1a1a1a"
    KeyGUI.SetFont("s9 cWhite")
    KeyGUI.Add("Text", "x10 y10 w420 Center cffd700", "Keybind Configuration").SetFont("s10 bold")
    yPos := 45
    edits := Map()
    for ability, key in Keybinds {
        KeyGUI.Add("Text", "x20 y" yPos " w220 cWhite", ability ":")
        edits[ability] := KeyGUI.Add("Edit", "x245 y" (yPos-3) " w90 Center Background333333 cWhite", key)
        yPos += 28
    }
    KeyGUI.Add("Button", "x10 y" (yPos+10) " w210 h35 Default", "💾 Save").OnEvent("Click", (*) => SaveKeybindsGUI(KeyGUI, edits))
    KeyGUI.Add("Button", "x230 y" (yPos+10) " w210 h35", "❌ Cancel").OnEvent("Click", (*) => KeyGUI.Destroy())
    KeyGUI.Show("w450 h" (yPos + 60))
}

SaveKeybindsGUI(gui, edits) {
    for ability, edit in edits {
        Keybinds[ability] := Trim(edit.Value)
    }
    MsgBox("✅ Keybinds saved!", "Success", "Iconi")
    gui.Destroy()
}

ShowTalentEditor() {
    TalentGUI := Gui("+Owner" MainGUI.Hwnd " +AlwaysOnTop", "🎯 Talents")
    TalentGUI.BackColor := "0x1a1a1a"
    TalentGUI.SetFont("s9 cWhite")
    TalentGUI.Add("Text", "x10 y10 w500 Center cffd700", "Talent Configuration").SetFont("s10 bold")
    yPos := 45
    checks := Map()

    talentDescs := Map(
        "Malevolence",     "Malevolence — repeated finisher stacks: +100% dmg/stack",
        "AssassinsGuile",  "Assassin's Guile — stealth opener → finishers +40% for 5s",
        "FeedTheQueen",    "Feed the Queen — Skittering stacks → Queen's Fang bonus",
        "Hemotoxin",       "Hemotoxin — Hemorrhaging Strike adds detonation DoT",
        "FromTheShadows",  "From the Shadows — stealth opener bonus damage",
        "Bloodrush",       "Bloodrush — Hemorrhaging Strike ticks 20% faster",
        "GushingBlood",    "Gushing Blood — Maiden: bleed spreads to 4 targets",
        "VenomousDelight", "Venomous Delight — poison 10% chance restore 10 Energy",
        "EfficientKiller", "Efficient Killer — 10% less energy cost, +10% max Energy",
        "Puncture",        "Puncture — Skittering Blades leaves ground poison pool",
        "DeadlyScheme",    "Deadly Scheme — every 200 Energy spent → next finisher 2× crit",
        "RedLedger",       "Red Ledger — Hemorrhaging Strike grants Attack Speed",
        "CorrosiveSpill",  "Corrosive Spill — 20% chance finishers leave poison pool"
    )

    for talent, enabled in Talents {
        desc := talentDescs.Has(talent) ? talentDescs[talent] : talent
        checks[talent] := TalentGUI.Add("Checkbox", "x20 y" yPos " w480 " (enabled ? "Checked" : "") " cWhite", desc)
        yPos += 24
    }
    TalentGUI.Add("Button", "x10 y" (yPos+10) " w245 h35 Default", "💾 Save").OnEvent("Click", (*) => SaveTalentsGUI(TalentGUI, checks))
    TalentGUI.Add("Button", "x265 y" (yPos+10) " w245 h35", "❌ Cancel").OnEvent("Click", (*) => TalentGUI.Destroy())
    TalentGUI.Show("w520 h" (yPos + 60))
}

SaveTalentsGUI(gui, checks) {
    for talent, check in checks {
        Talents[talent] := check.Value
    }
    InitializeAbilityData()
    MsgBox("✅ Talents saved!", "Success", "Iconi")
    gui.Destroy()
}

ShowStatsEditor() {
    StatsGUI := Gui("+Owner" MainGUI.Hwnd " +AlwaysOnTop", "📊 Player Stats")
    StatsGUI.BackColor := "0x1a1a1a"
    StatsGUI.SetFont("s9 cWhite")
    StatsGUI.Add("Text", "x10 y10 w410 Center cffd700", "Player Stats (from Icy Veins: aim 14% Haste, then Expertise+Crit)").SetFont("s9 bold")
    yPos := 45
    sliders := Map()
    texts   := Map()
    for stat, value in PlayerStats {
        StatsGUI.Add("Text", "x20 y" yPos " w100 cWhite", stat ":")
        sliders[stat] := StatsGUI.Add("Slider", "x130 y" yPos " w200 Range0-100 ToolTip", value)
        texts[stat]   := StatsGUI.Add("Text",   "x340 y" yPos " w70 cFFAA00", value)
        sliders[stat].OnEvent("Change", UpdateStatText.Bind(stat, texts[stat]))
        yPos += 30
    }
    StatsGUI.Add("Button", "x10 y" (yPos+10) " w200 h35 Default", "💾 Save").OnEvent("Click", (*) => SaveStatsGUI(StatsGUI, sliders))
    StatsGUI.Add("Button", "x220 y" (yPos+10) " w200 h35", "❌ Cancel").OnEvent("Click", (*) => StatsGUI.Destroy())
    StatsGUI.Show("w430 h" (yPos + 60))
}

UpdateStatText(stat, textCtrl, sliderCtrl, *) {
    textCtrl.Value := sliderCtrl.Value
}

SaveStatsGUI(gui, sliders) {
    for stat, slider in sliders {
        PlayerStats[stat] := slider.Value
    }
    MsgBox("✅ Stats saved!", "Success", "Iconi")
    gui.Destroy()
}

ShowAnalytics() {
    txt := "📈 MARA v6.0 — ROTATION ANALYTICS`n"
    txt .= "═══════════════════════════════════════════`n`n"
    txt .= "PERFORMANCE:`n"
    txt .= "  Total Damage : " Round(ResourceStats["TotalDamage"]) "`n"
    txt .= "  DPS          : " Round(ResourceStats["DPS"]) "`n"
    txt .= "  Duration     : " Round(ResourceStats["RotationTime"]) "s`n"
    txt .= "  Total Casts  : " ResourceStats["TotalCasts"] "`n`n"
    txt .= "STEALTH ENGINE (Module 2):`n"
    txt .= "  Stealth Uses  : " ResourceStats["StealthUses"] "`n"
    txt .= "  Guile Windows : " ResourceStats["GuileWindows"] "`n"
    txt .= "  Guile Finishers: " ResourceStats["FinishersDuringGuile"] "`n`n"
    txt .= "RESOURCE EFFICIENCY:`n"
    txt .= "  Energy Wasted : " Round(ResourceStats["EnergyWasted"]) "`n"
    txt .= "  CP Wasted     : " Round(ResourceStats["CPWasted"]) "`n`n"
    txt .= "ABILITY BREAKDOWN:`n"
    for ability, data in AbilityStats {
        if data.used > 0 {
            txt .= "  " ability ": " data.used " uses"
            if data.damage > 0 {
                txt .= " | " Round(data.damage) " dmg"
            }
            if data.stealthCasts > 0 {
                txt .= " | " data.stealthCasts " stealth"
            }
            if data.guileFinishers > 0 {
                txt .= " | " data.guileFinishers " guile"
            }
            txt .= "`n"
        }
    }
    MsgBox(txt, "Analytics", "Iconi")
}

SaveConfig() {
    try {
        for ability, key in Keybinds {
            IniWrite(key, ConfigFile, "Keybinds", ability)
        }
        for talent, enabled in Talents {
            IniWrite(enabled, ConfigFile, "Talents", talent)
        }
        for stat, value in PlayerStats {
            IniWrite(value, ConfigFile, "Stats", stat)
        }
        MsgBox("✅ Config saved!", "Success", "Iconi")
    } catch as err {
        MsgBox("❌ Error: " err.Message, "Error", "Icon!")
    }
}

LoadConfig() {
    if !FileExist(ConfigFile) {
        return
    }
    try {
        for ability in Keybinds {
            loaded := IniRead(ConfigFile, "Keybinds", ability, "")
            if loaded != "" {
                Keybinds[ability] := loaded
            }
        }
        for talent in Talents {
            loaded := IniRead(ConfigFile, "Talents", talent, "")
            if loaded != "" {
                Talents[talent] := Integer(loaded)
            }
        }
        for stat in PlayerStats {
            loaded := IniRead(ConfigFile, "Stats", stat, "")
            if loaded != "" {
                PlayerStats[stat] := Float(loaded)
            }
        }
    } catch {
        ; Silent fail
    }
}

ShowHelp() {
    help := "🕷️ MARA ULTIMATE v" AppVersion "`n"
    help .= "══════════════════════════════════════════`n`n"
    help .= "MODULE 2 — STEALTH STATE ENGINE`n"
    help .= "  States: NONE → PENDING → CONSUMED → NONE`n"
    help .= "  Brooding Shadows sets state to PENDING.`n"
    help .= "  Next builder cast CONSUMES stealth:`n"
    help .= "    Backstab     → Caustic Poison  (+6 CP instant)`n"
    help .= "    Widow's Bite → Seething Poison (+40% E Regen 60s)`n"
    help .= "    Skittering   → Volatile Poison (AoE DoT + explosion)`n"
    help .= "  Stealth window auto-expires after 10s.`n`n"
    help .= "MODULE 1 — DATA FIXES`n"
    help .= "  Maiden of Death CD: 60s (was 90s — FIXED)`n"
    help .= "  Widow's Bite: 4 CP base (2 per strike × 2 strikes)`n"
    help .= "  Backstab stealth: 6 CP (Caustic Poison)`n"
    help .= "  Seething Poison: +40% Energy Regen (Predator's Rush)`n"
    help .= "  Shadow Protection added to priority logic`n`n"
    help .= "MODULE 4 — PRIORITY LOGIC`n"
    help .= "  1. FinalStratagem during Maiden (custom macro)`n"
    help .= "  2. Maiden of Death off CD`n"
    help .= "  3. Weapon inside Maiden window`n"
    help .= "  4. Assassin's Guile window — SPAM FINISHERS`n"
    help .= "  5. Hemotoxin detonation window (< 3s left)`n"
    help .= "  6. Seething Poison upkeep (Predator's Rush)`n"
    help .= "  7. Hemorrhage bleed maintenance`n"
    help .= "  8. Brooding setup for next Guile window`n"
    help .= "  9. Execute stealth builder (if PENDING)`n"
    help .= " 10. Finisher at 6 CP (cap prevention)`n"
    help .= " 11. Finisher at 5 CP (optimal)`n"
    help .= " 12–15. Energy gen, fillers, dump`n`n"
    help .= "HOTKEYS:`n"
    help .= "  F1: ST  | F2: AOE  | F3: Pause  | F4: Stop`n"
    MsgBox(help, "Help", "Iconi")
}

; ============================================================================
; HOTKEYS
; ============================================================================
F1:: StartRotation("ST")
F2:: StartRotation("AOE")
F3:: PauseRotation()
F4:: StopRotation()

ESC:: {
    result := MsgBox("Exit Mara Ultimate?", "Confirm", "YesNo Icon?")
    if result = "Yes" {
        ExitApp()
    }
}

; ============================================================================
; STARTUP
; ============================================================================
try {
    InitializeKeybinds()
    InitializeAbilityData()
    InitializeLastUsed()
    InitializeStats()

    LoadConfig()

    global CurrentEnergy  := MaxEnergy
    global CurrentCP      := 0
    global LastRegenTick  := A_TickCount
    global BroodingCharges := BroodingMaxCharges

    CreateMainGUI()

    MsgBox(
        "🕷️ MARA ULTIMATE v" AppVersion "`n`n"
        "✅ MODULE 2: Stealth State Engine`n"
        "   NONE → PENDING → CONSUMED state machine`n"
        "   Smart poison routing by ability type`n`n"
        "✅ MODULE 1: Ability Data Accuracy`n"
        "   Maiden of Death: 60s CD (was 90s — FIXED)`n"
        "   Widow's Bite: 4 CP base (2 per strike)`n"
        "   Backstab stealth: 6 CP via Caustic Poison`n"
        "   Seething = +40% Energy Regen (Predator's Rush)`n`n"
        "✅ MODULE 4: Priority Logic Overhaul`n"
        "   15-step ST priority (Method.gg based)`n"
        "   Guile window forces finisher spam`n"
        "   Hemotoxin detonation countdown`n"
        "   Stealth engine wired into all decisions`n`n"
        "F1/F2 to start — check Talents first!",
        "Welcome",
        "Iconi T6"
    )

} catch as err {
    MsgBox("❌ FATAL: " err.Message "`nLine: " err.Line, "Fatal Error", "Icon!")
    ExitApp()
}
