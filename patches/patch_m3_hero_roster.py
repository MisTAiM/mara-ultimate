"""
patch_m3_hero_roster.py
========================
Module 3 — Full Hero Roster + Hero Switcher

What this patch does:
  1. Adds global ActiveHero variable (default "Mara")
  2. Injects HeroData Map for all 10 heroes into the AHK globals
  3. Adds GetNextAbility() routing — delegates to per-hero priority function
  4. Adds all hero priority functions:
       GetHelenaRotation(), GetMeikoRotation(), GetXavianRotation()
       GetSylvieRotation(), GetVigourRotation(), GetAeonaRotation()
       GetArdeoRotation(), GetRimeRotation(), GetTariqRotation(), GetElarionRotation()
     (Mara's priority already exists as GetSTPriority / GetAOEPriority)
  5. Adds CreateHeroRosterPanel() UI function
  6. Adds UpdateHeroRosterPanel() to the UpdateGUI() call chain
  7. Adds SwitchHero(heroName) function
  8. Widens GUI from 1020 to 1360 to accommodate side panel

Run: python patches/patch_m3_hero_roster.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from patcher import Patcher

TARGET = Path(__file__).parent.parent / "FellowshipUltimate.ahk"

# ─────────────────────────────────────────────────────────────────────────────
# NEW CODE BLOCKS TO INJECT
# ─────────────────────────────────────────────────────────────────────────────

GLOBALS_HERO = """\
; ============================================================================
; HERO ROSTER — MODULE 3
; ============================================================================
global ActiveHero    := "Mara"
global PartyComp     := ["Meiko", "Vigour", "Mara", "Elarion"]  ; default meta Anchor comp

; Per-hero resource tracking (mirrors real game resources)
global HeroResources := Map(
    "Helena",  {name: "Toughness",    current: 80,  max: 100, color: "4169e1"},
    "Meiko",   {name: "ComboStance",  current: 0,   max: 6,   color: "20b2aa"},
    "Xavian",  {name: "Mana",         current: 100, max: 100, color: "ffd700"},
    "Sylvie",  {name: "Flutterflies", current: 0,   max: 5,   color: "90ee90"},
    "Vigour",  {name: "RadiantRunes", current: 0,   max: 5,   color: "ffd700"},
    "Aeona",   {name: "Mana",         current: 100, max: 100, color: "87ceeb"},
    "Mara",    {name: "Energy",       current: 200, max: 200, color: "8b00ff"},
    "Ardeos",  {name: "BurningEmbers",current: 0,   max: 4,   color: "ff4500"},
    "Rime",    {name: "WinterOrbs",   current: 0,   max: 5,   color: "00bfff"},
    "Tariq",   {name: "Fury",         current: 0,   max: 100, color: "ffd700"},
    "Elarion", {name: "Focus",        current: 50,  max: 100, color: "9370db"}
)

; Per-hero cooldown tracking maps (separate from Mara's existing LastUsedTime)
global HeroLastUsed := Map()
"""

HERO_SWITCHER_FUNC = """\
; ============================================================================
; HERO SWITCHER — MODULE 3
; ============================================================================
SwitchHero(heroName) {
    global ActiveHero, RotationType

    validHeroes := ["Helena","Meiko","Xavian","Sylvie","Vigour","Aeona",
                    "Mara","Ardeos","Rime","Tariq","Elarion"]
    isValid := false
    for h in validHeroes {
        if h = heroName {
            isValid := true
        }
    }

    if !isValid {
        MsgBox("❌ Unknown hero: " heroName, "Error", "Icon!")
        return
    }

    ActiveHero := heroName

    ; Auto-set rotation type by role
    tankHeroes   := ["Helena","Meiko","Xavian"]
    healerHeroes := ["Sylvie","Vigour","Aeona"]
    for h in tankHeroes {
        if h = heroName {
            global RotationType := "TANK"
        }
    }
    for h in healerHeroes {
        if h = heroName {
            global RotationType := "HEAL"
        }
    }

    ResetResources()

    if UIControls.Has("HeroActiveLabel") {
        UIControls["HeroActiveLabel"].Value := GetHeroIcon(heroName) " " heroName
    }

    LogDebug("🔄 Switched to hero: " heroName " | Mode: " RotationType)
}

GetHeroIcon(heroName) {
    icons := Map(
        "Helena",  "🛡️",
        "Meiko",   "🥋",
        "Xavian",  "✨",
        "Sylvie",  "🦋",
        "Vigour",  "⚡",
        "Aeona",   "🌟",
        "Mara",    "🕷️",
        "Ardeos",  "🔥",
        "Rime",    "❄️",
        "Tariq",   "⚡",
        "Elarion", "🏹"
    )
    return icons.Has(heroName) ? icons[heroName] : "❓"
}

GetHeroRole(heroName) {
    tanks   := ["Helena","Meiko","Xavian"]
    healers := ["Sylvie","Vigour","Aeona"]
    for h in tanks   { if h = heroName { return "Tank"   } }
    for h in healers { if h = heroName { return "Healer" } }
    return "DPS"
}
"""

HERO_ROTATION_DISPATCH = """\
; ============================================================================
; HERO ROTATION DISPATCH — MODULE 3
; Routes GetNextAbility() to the correct hero priority function
; ============================================================================
GetNextAbilityForHero() {
    global ActiveHero, RotationType

    UpdateEnergyRegen()
    UpdateBuffTimers()

    switch ActiveHero {
        case "Helena":  return GetHelenaRotation()
        case "Meiko":   return GetMeikoRotation()
        case "Xavian":  return GetXavianRotation()
        case "Sylvie":  return GetSylvieRotation()
        case "Vigour":  return GetVigourRotation()
        case "Aeona":   return GetAeonaRotation()
        case "Mara":
            if RotationType = "AOE" || TargetCount > 2 {
                return GetAOEPriority()
            }
            return GetSTPriority()
        case "Ardeos":  return GetArdeoRotation()
        case "Rime":    return GetRimeRotation()
        case "Tariq":   return GetTariqRotation()
        case "Elarion": return GetElarionRotation()
        default:        return GetSTPriority()
    }
}
"""

HELENA_ROTATION = """\
; ── HELENA rotation (Toughness management + Veteran of War CDR) ──────────
GetHelenaRotation() {
    ; P1: Siegebreaker — heavy damage phase
    if IsAbilityReady("Siegebreaker") {
        ; Use if Toughness < 60 (incoming heavy damage) or on pull
        toughness := HeroResources["Helena"].current
        if toughness < 60 || ResourceStats["TotalCasts"] < 3 {
            return "Siegebreaker"
        }
    }

    ; P2: ShieldsUp — Toughness management (core defensive)
    toughness := HeroResources["Helena"].current
    if toughness < 40 && IsAbilityReady("ShieldsUp") {
        return "ShieldsUp"
    }

    ; P3: IronWall — cover Shield Up gaps
    if toughness < 55 && IsAbilityReady("IronWall") {
        return "IronWall"
    }

    ; P4: ShieldsUp proactive (approaching threshold)
    if toughness < 75 && IsAbilityReady("ShieldsUp") {
        return "ShieldsUp"
    }

    ; P5: Shockwave — double CDR from Veteran of War, AoE stun
    if IsAbilityReady("Shockwave") {
        return "Shockwave"
    }

    ; P6: GrandMelee — damage window CD
    if IsAbilityReady("GrandMelee") {
        return "GrandMelee"
    }

    ; P7: ShieldThrow — ranged threat + CDR
    if IsAbilityReady("ShieldThrow") {
        return "ShieldThrow"
    }

    ; P8: SweepingStrike — AoE DPS if healthy
    if toughness > 60 && IsAbilityReady("SweepingStrike") {
        return "SweepingStrike"
    }

    ; P9: ShieldSlam — filler builder + CDR
    if IsAbilityReady("ShieldSlam") {
        return "ShieldSlam"
    }

    return ""
}
"""

MEIKO_ROTATION = """\
; ── MEIKO rotation (Combo chains → finishers, stance swapping) ──────────
GetMeikoRotation() {
    ; P1: IronBody — defensive spike CD
    if IsAbilityReady("IronBody") {
        if HeroResources["Meiko"].current < 30 {
            return "IronBody"
        }
    }

    ; P2: TwinSouls — threat/emergency
    if IsAbilityReady("TwinSouls") {
        return "TwinSouls"
    }

    ; P3: SpiritedStrikes — finisher (Wind stance combo)
    if IsAbilityReady("SpiritedStrikes") {
        return "SpiritedStrikes"
    }

    ; P4: SpiritedVortex — AoE finisher
    if TargetCount >= 3 && IsAbilityReady("SpiritedVortex") {
        return "SpiritedVortex"
    }

    ; P5: WindDash — stance access + mobility
    if IsAbilityReady("WindDash") {
        return "WindDash"
    }

    ; P6: EarthStance — defense + self-heal
    if IsAbilityReady("EarthStance") {
        if HeroResources["Meiko"].current < 50 {
            return "EarthStance"
        }
    }

    ; P7: Kick — interrupt
    if IsAbilityReady("Kick") {
        return "Kick"
    }

    ; P8: FistSlam / PalmStrike builders
    if IsAbilityReady("FistSlam") {
        return "FistSlam"
    }
    if IsAbilityReady("PalmStrike") {
        return "PalmStrike"
    }

    return ""
}
"""

XAVIAN_ROTATION = """\
; ── XAVIAN rotation (Mana + Swift Reprival stacks + AuraOfSolace) ───────
GetXavianRotation() {
    mana := HeroResources["Xavian"].current

    ; P1: DivineBulwark — major defensive spike
    if IsAbilityReady("DivineBulwark") && mana < 30 {
        return "DivineBulwark"
    }

    ; P2: RadiantBarrier — party protection
    if IsAbilityReady("RadiantBarrier") {
        return "RadiantBarrier"
    }

    ; P3: BrilliantFlash — Swift Reprival stacks
    if IsAbilityReady("BrilliantFlash") && mana > 20 {
        return "BrilliantFlash"
    }

    ; P4: ShiningHalo — party heal
    if IsAbilityReady("ShiningHalo") && mana > 15 {
        return "ShiningHalo"
    }

    ; P5: HolyStrike — damage + self-heal
    if IsAbilityReady("HolyStrike") && mana > 25 {
        return "HolyStrike"
    }

    ; P6: Consecration — AoE damage/heal zone
    if IsAbilityReady("Consecration") && mana > 40 {
        return "Consecration"
    }

    ; P7: DivineBulwark proactive
    if IsAbilityReady("DivineBulwark") {
        return "DivineBulwark"
    }

    return ""
}
"""

SYLVIE_ROTATION = """\
; ── SYLVIE rotation (Flutterfly HoTs + Nettlebolt CDR + BloomBurst) ─────
GetSylvieRotation() {
    flutterflies := HeroResources["Sylvie"].current

    ; P1: NaturesMend — emergency
    if IsAbilityReady("NaturesMend") {
        ; Emergency only — check if tank critical
        return "NaturesMend"
    }

    ; P2: BloomBurst — detonate if max Flutterflies and party damaged
    if flutterflies >= 4 && IsAbilityReady("BloomBurst") {
        return "BloomBurst"
    }

    ; P3: LifePetal — direct heal if tank low
    if IsAbilityReady("LifePetal") {
        return "LifePetal"
    }

    ; P4: Nettlebolt — DPS for LifePetal CDR (MOST IMPORTANT sustain tool)
    if IsAbilityReady("Nettlebolt") {
        return "Nettlebolt"
    }

    ; P5: Flutterfly deploy — maintain HoTs
    if flutterflies < 4 && IsAbilityReady("Flutterfly") {
        return "Flutterfly"
    }

    ; P6: PollenCloud — AoE HoT zone
    if IsAbilityReady("PollenCloud") {
        return "PollenCloud"
    }

    ; P7: Rejuvenate on tank
    if IsAbilityReady("Rejuvenate") {
        return "Rejuvenate"
    }

    return ""
}
"""

VIGOUR_ROTATION = """\
; ── VIGOUR rotation (Damage → RadiantRunes → Heals + Shields) ───────────
GetVigourRotation() {
    runes := HeroResources["Vigour"].current

    ; P1: DivineSurge — wipe prevention
    if IsAbilityReady("DivineSurge") {
        return "DivineSurge"
    }

    ; P2: Overcharge + HolyMend at max runes if party damaged
    if runes >= 4 && IsAbilityReady("HolyMend") {
        if IsAbilityReady("Overcharge") {
            return "Overcharge"
        }
        return "HolyMend"
    }

    ; P3: ShieldOfLight — preemptive tank shield
    if runes >= 2 && IsAbilityReady("ShieldOfLight") {
        return "ShieldOfLight"
    }

    ; P4: ProtectiveAura — party CD
    if IsAbilityReady("ProtectiveAura") {
        return "ProtectiveAura"
    }

    ; P5: DawnbreakerOrb — AoE rune gen
    if IsAbilityReady("DawnbreakerOrb") {
        return "DawnbreakerOrb"
    }

    ; P6: HealingWave — rune-free heal if runes low and tank hurt
    if runes < 2 && IsAbilityReady("HealingWave") {
        return "HealingWave"
    }

    ; P7: RadiantBlast filler — rune generation
    if IsAbilityReady("RadiantBlast") {
        return "RadiantBlast"
    }

    return ""
}
"""

AEONA_ROTATION = """\
; ── AEONA rotation (Delayed damage + shields + mana management) ─────────
GetAeonaRotation() {
    mana := HeroResources["Aeona"].current

    ; P1: TimeWarp — major EHP phase
    if IsAbilityReady("TimeWarp") && mana > 0 {
        return "TimeWarp"
    }

    ; P2: DelayedImpact — pre-cast before spike
    if IsAbilityReady("DelayedImpact") && mana > 15 {
        return "DelayedImpact"
    }

    ; P3: StarShield — absorb before damage
    if IsAbilityReady("StarShield") && mana > 20 {
        return "StarShield"
    }

    ; P4: CosmicMend — group heal CD
    if IsAbilityReady("CosmicMend") {
        return "CosmicMend"
    }

    ; P5: HealingLight — direct heal
    if IsAbilityReady("HealingLight") && mana > 25 {
        return "HealingLight"
    }

    ; P6: ArcaneBlast filler (watch mana)
    if IsAbilityReady("ArcaneBlast") && mana > 20 {
        return "ArcaneBlast"
    }

    return ""
}
"""

ARDEOS_ROTATION = """\
; ── ARDEOS rotation (DoTs → Cinders → BurningEmbers → Detonate) ─────────
GetArdeoRotation() {
    embers := HeroResources["Ardeos"].current

    ; P1: Combustion at 4 embers — major burst
    if embers >= 4 && IsAbilityReady("Combustion") {
        return "Combustion"
    }

    ; P2: Detonate — spend embers (never with 0 DoTs)
    ; Only Detonate if at least SearingBlaze is active
    if embers >= 3 && IsBuffActive("SearingBlazeDoT") {
        if IsAbilityReady("Detonate") {
            return "Detonate"
        }
    }

    ; P3: Detonate during Combustion window
    if embers >= 1 && IsAbilityReady("Combustion") && IsBuffActive("SearingBlazeDoT") {
        if IsAbilityReady("Detonate") {
            return "Detonate"
        }
    }

    ; P4: SearingBlaze — primary DoT (NEVER let drop)
    if !IsBuffActive("SearingBlazeDoT") || GetBuffRemaining("SearingBlazeDoT") < 3 {
        if IsAbilityReady("SearingBlaze") {
            return "SearingBlaze"
        }
    }

    ; P5: EngulfingFlames — second DoT
    if !IsBuffActive("EngulfingFlamesDoT") || GetBuffRemaining("EngulfingFlamesDoT") < 3 {
        if IsAbilityReady("EngulfingFlames") {
            return "EngulfingFlames"
        }
    }

    ; P6: Pyromania on CD
    if IsAbilityReady("Pyromania") {
        return "Pyromania"
    }

    ; P7: InfernalWave for AoE
    if TargetCount >= 3 && IsAbilityReady("InfernalWave") {
        return "InfernalWave"
    }

    ; P8: Detonate at 2+ embers with DoTs
    if embers >= 2 && IsBuffActive("SearingBlazeDoT") && IsAbilityReady("Detonate") {
        return "Detonate"
    }

    ; P9: FireBall filler
    if IsAbilityReady("FireBall") {
        return "FireBall"
    }

    return ""
}
"""

RIME_ROTATION = """\
; ── RIME rotation (Anima → WinterOrbs → Burst spenders) ─────────────────
GetRimeRotation() {
    orbs := HeroResources["Rime"].current

    ; P1: IceAge at near-max Orbs — major burst
    if orbs >= 4 && IsAbilityReady("IceAge") {
        return "IceAge"
    }

    ; P2: GlacialBlast — spend orbs before overcap (ST)
    if orbs >= 3 && TargetCount <= 2 && IsAbilityReady("GlacialBlast") {
        return "GlacialBlast"
    }

    ; P3: IceComet — AoE spender
    if orbs >= 3 && TargetCount >= 3 && IsAbilityReady("IceComet") {
        return "IceComet"
    }

    ; P4: WinterBlessing — group healing
    if IsAbilityReady("WinterBlessing") {
        ; Use if party is damaged (simplified: cast on CD as utility)
        return "WinterBlessing"
    }

    ; P5: ColdSnap on CD
    if IsAbilityReady("ColdSnap") {
        return "ColdSnap"
    }

    ; P6: FrostNova for CC
    if IsAbilityReady("FrostNova") && TargetCount >= 3 {
        return "FrostNova"
    }

    ; P7: GlacialBlast at 2+ orbs to avoid cap
    if orbs >= 2 && IsAbilityReady("GlacialBlast") {
        return "GlacialBlast"
    }

    ; P8: FreezingTorrent filler
    if IsAbilityReady("FreezingTorrent") {
        return "FreezingTorrent"
    }

    return ""
}
"""

TARIQ_ROTATION = """\
; ── TARIQ rotation (Fury build → spend + Swing Timer + LightningProc) ───
GetTariqRotation() {
    fury := HeroResources["Tariq"].current

    ; P1: StormBreaker at 80+ Fury — major burst
    if fury >= 80 && IsAbilityReady("StormBreaker") {
        return "StormBreaker"
    }

    ; P2: ThunderCall (Lightning build) / Schism — spend at 70+
    if fury >= 70 {
        if IsAbilityReady("ThunderCall") {
            return "ThunderCall"
        }
        if IsAbilityReady("Schism") {
            return "Schism"
        }
    }

    ; P3: LightningBolt proc — use IMMEDIATELY
    if IsAbilityReady("LightningBolt") {
        ; Check if proc is active (simplified: CD resets on proc)
        return "LightningBolt"
    }

    ; P4: BerserkerRage on CD
    if IsAbilityReady("BerserkerRage") {
        return "BerserkerRage"
    }

    ; P5: ThunderClap — AoE DoT application
    if IsAbilityReady("ThunderClap") {
        return "ThunderClap"
    }

    ; P6: Spend at 50+ to avoid cap drift
    if fury >= 50 {
        if IsAbilityReady("ThunderCall") {
            return "ThunderCall"
        }
    }

    ; P7: HammerStrike filler
    if IsAbilityReady("HammerStrike") {
        return "HammerStrike"
    }

    return ""
}
"""

ELARION_ROTATION = """\
; ── ELARION rotation (Focus + LunarlightMark + HeartseekerBarrage) ──────
GetElarionRotation() {
    focus := HeroResources["Elarion"].current

    ; P1: CelestialVolley — burst CD
    if IsAbilityReady("CelestialVolley") {
        return "CelestialVolley"
    }

    ; P2: HeartseekerBarrage — trigger Lunarlight Marks (HIGHEST PRIORITY when marks up)
    if IsBuffActive("LunarlightMarkActive") && IsAbilityReady("HeartseekerBarrage") {
        return "HeartseekerBarrage"
    }

    ; P3: LunarlightMark — apply mark (must have mark before Barrage)
    if !IsBuffActive("LunarlightMarkActive") && IsAbilityReady("LunarlightMark") && focus >= 15 {
        return "LunarlightMark"
    }

    ; P4: Impend — vulnerability debuff (party DPS increase)
    if IsAbilityReady("Impend") {
        return "Impend"
    }

    ; P5: StarfallArrow — AoE mark application
    if TargetCount >= 3 && IsAbilityReady("StarfallArrow") && focus >= 25 {
        return "StarfallArrow"
    }

    ; P6: HeartseekerBarrage on CD (even without marks for Barrage itself)
    if IsAbilityReady("HeartseekerBarrage") && focus >= 30 {
        return "HeartseekerBarrage"
    }

    ; P7: PiercingShot — Focus spender at 70+
    if focus >= 70 && IsAbilityReady("PiercingShot") {
        return "PiercingShot"
    }

    ; P8: StarfallArrow on CD
    if IsAbilityReady("StarfallArrow") && focus >= 25 {
        return "StarfallArrow"
    }

    ; P9: MassGrip — party utility (coordinate)
    if IsAbilityReady("MassGrip") && TargetCount >= 3 {
        return "MassGrip"
    }

    ; P10: ArrowStrike filler
    if IsAbilityReady("ArrowStrike") {
        return "ArrowStrike"
    }

    return ""
}
"""

HERO_ROSTER_UI = """\
; ============================================================================
; HERO ROSTER PANEL — MODULE 3 UI
; ============================================================================
CreateHeroRosterPanel() {
    global MainGUI, UIControls

    UIControls["RosterPanel"] := MainGUI.Add("GroupBox", "x1040 y0 w310 h850 cWhite", "🎮 FELLOWSHIP ROSTER")

    MainGUI.SetFont("s9 bold cWhite")

    ; Active hero display
    MainGUI.SetFont("s12 bold cffd700")
    UIControls["HeroActiveLabel"] := MainGUI.Add("Text", "x1055 y25 w280 Center Background2d1b4e", "🕷️ Mara")

    MainGUI.SetFont("s8 c888888")
    MainGUI.Add("Text", "x1055 y52 w280 Center", "Active Hero")

    ; ── TANKS ───────────────────────────────────────────────
    MainGUI.SetFont("s8 bold c4169e1")
    MainGUI.Add("Text", "x1055 y75 w280 Center", "━━━━━━━ TANKS ━━━━━━━")

    CreateHeroButton("Helena", "🛡️", "x1055 y92 w88 h55",  "4169e1")
    CreateHeroButton("Meiko",  "🥋", "x1151 y92 w88 h55",  "20b2aa")
    CreateHeroButton("Xavian", "✨", "x1247 y92 w88 h55",  "ffd700")

    ; Toughness bar for Helena
    MainGUI.SetFont("s7 c888888")
    MainGUI.Add("Text", "x1055 y152 w90", "Toughness:")
    UIControls["HelenaToughnessBar"] := MainGUI.Add("Progress", "x1055 y163 w280 h6 Background333333 c4169e1 Range0-100", 80)

    ; ── HEALERS ─────────────────────────────────────────────
    MainGUI.SetFont("s8 bold c90ee90")
    MainGUI.Add("Text", "x1055 y180 w280 Center", "━━━━━━ HEALERS ━━━━━━")

    CreateHeroButton("Sylvie", "🦋", "x1055 y197 w88 h55", "90ee90")
    CreateHeroButton("Vigour", "⚡", "x1151 y197 w88 h55", "ffd700")
    CreateHeroButton("Aeona",  "🌟", "x1247 y197 w88 h55", "87ceeb")

    ; Resource bars for healers
    MainGUI.SetFont("s7 c888888")
    MainGUI.Add("Text", "x1055 y257 w90", "Flutterflies:")
    UIControls["SylvieResourceBar"] := MainGUI.Add("Progress", "x1055 y268 w280 h6 Background333333 c90ee90 Range0-5", 0)
    MainGUI.Add("Text", "x1055 y278 w90", "Radiant Runes:")
    UIControls["VigourResourceBar"] := MainGUI.Add("Progress", "x1055 y289 w280 h6 Background333333 cffd700 Range0-5", 0)

    ; ── DPS ─────────────────────────────────────────────────
    MainGUI.SetFont("s8 bold cff4500")
    MainGUI.Add("Text", "x1055 y305 w280 Center", "━━━━━━━━ DPS ━━━━━━━━")

    CreateHeroButton("Mara",    "🕷️", "x1055 y322 w88 h55", "8b00ff")
    CreateHeroButton("Ardeos",  "🔥", "x1151 y322 w88 h55", "ff4500")
    CreateHeroButton("Rime",    "❄️", "x1247 y322 w88 h55", "00bfff")

    CreateHeroButton("Tariq",   "⚡", "x1055 y385 w88 h55", "ffd700")
    CreateHeroButton("Elarion", "🏹", "x1151 y385 w88 h55", "9370db")

    ; DPS resource bars
    MainGUI.SetFont("s7 c888888")
    MainGUI.Add("Text", "x1055 y445 w90", "Embers/Orbs/Fury:")
    UIControls["DPSResourceBar"] := MainGUI.Add("Progress", "x1055 y456 w280 h6 Background333333 cff4500 Range0-100", 0)

    ; ── META COMPS ──────────────────────────────────────────
    MainGUI.SetFont("s8 bold cFFAA00")
    MainGUI.Add("Text", "x1055 y475 w280 Center", "━━━━━ META COMPS ━━━━")

    MainGUI.SetFont("s8 cWhite")
    UIControls["MetaComp1"] := MainGUI.Add("Button", "x1055 y492 w280 h28",
        "Anchor: Meiko+Vigour+Mara+Elarion").OnEvent("Click",
        (*) => SetPartyComp(["Meiko","Vigour","Mara","Elarion"]))

    UIControls["MetaComp2"] := MainGUI.Add("Button", "x1055 y525 w280 h28",
        "Trash: Meiko+Sylvie+Rime+Ardeos").OnEvent("Click",
        (*) => SetPartyComp(["Meiko","Sylvie","Rime","Ardeos"]))

    UIControls["MetaComp3"] := MainGUI.Add("Button", "x1055 y558 w280 h28",
        "Safe: Helena+Vigour+Rime+Elarion").OnEvent("Click",
        (*) => SetPartyComp(["Helena","Vigour","Rime","Elarion"]))

    ; ── PARTY DISPLAY ───────────────────────────────────────
    MainGUI.SetFont("s8 bold cWhite")
    MainGUI.Add("Text", "x1055 y598 w280 Center", "━━━━━ PARTY COMP ━━━━")

    UIControls["Party1"] := MainGUI.Add("Text", "x1055 y615 w280 h22 Center Background1a1a1a", "⟨ select comp above ⟩")
    UIControls["Party2"] := MainGUI.Add("Text", "x1055 y640 w280 h22 Center Background1a1a1a", "")
    UIControls["Party3"] := MainGUI.Add("Text", "x1055 y665 w280 h22 Center Background1a1a1a", "")
    UIControls["Party4"] := MainGUI.Add("Text", "x1055 y690 w280 h22 Center Background1a1a1a", "")

    ; ── ROTATION NOTES ──────────────────────────────────────
    MainGUI.SetFont("s8 bold cWhite")
    MainGUI.Add("Text", "x1055 y720 w280 Center", "━━━ HERO NOTES ━━━")
    MainGUI.SetFont("s8 c888888")
    UIControls["HeroNotes"] := MainGUI.Add("Text", "x1055 y738 w280 h100 Wrap", "Select a hero to see rotation notes.")
}

CreateHeroButton(heroName, icon, pos, color) {
    global MainGUI, UIControls
    MainGUI.SetFont("s10 bold c" color)
    btn := MainGUI.Add("Button", pos, icon "`n" heroName)
    btn.OnEvent("Click", SwitchHeroCallback.Bind(heroName))
    UIControls["HeroBtn_" heroName] := btn
}

SwitchHeroCallback(heroName, *) {
    SwitchHero(heroName)
    UpdateHeroRosterPanel()
}

SetPartyComp(comp) {
    global PartyComp := comp
    UpdatePartyDisplay()
}

UpdatePartyDisplay() {
    global PartyComp, UIControls
    roles := ["Tank", "Healer", "DPS", "DPS"]
    Loop Min(PartyComp.Length, 4) {
        hero := PartyComp[A_Index]
        icon := GetHeroIcon(hero)
        UIControls["Party" A_Index].Value := icon " " hero " [" GetHeroRole(hero) "]"
    }
}

UpdateHeroRosterPanel() {
    global UIControls, ActiveHero, HeroResources

    if !UIControls.Has("HeroActiveLabel") {
        return
    }

    UIControls["HeroActiveLabel"].Value := GetHeroIcon(ActiveHero) " " ActiveHero

    ; Update hero-specific resource bars
    if HeroResources.Has("Helena") {
        UIControls["HelenaToughnessBar"].Value := HeroResources["Helena"].current
    }
    if HeroResources.Has("Sylvie") {
        UIControls["SylvieResourceBar"].Value := HeroResources["Sylvie"].current
    }
    if HeroResources.Has("Vigour") {
        UIControls["VigourResourceBar"].Value := HeroResources["Vigour"].current
    }

    ; DPS resource bar — show active hero's resource
    dpsHeroes := ["Ardeos","Rime","Tariq","Elarion"]
    for h in dpsHeroes {
        if h = ActiveHero && HeroResources.Has(h) {
            UIControls["DPSResourceBar"].Value := HeroResources[h].current
        }
    }

    ; Hero rotation notes
    heroNotes := Map(
        "Helena",  "Priority: Shields Up when Toughness <40%. Shockwave for double CDR. Siegebreaker for heavy phases.",
        "Meiko",   "Combo chain: Palm→Kick→Fist→Finisher. Maintain Spirited Strikes uptime. TwinSouls for emergency.",
        "Xavian",  "AuraOfSolace always active. Stack Swift Reprival. ShiningHalo for party heals.",
        "Sylvie",  "Weave Nettlebolt → LifePetal CDR. Deploy Flutterflies. BloomBurst at 4+ stacks.",
        "Vigour",  "Deal damage → generate Runes → heal. Overcharge for AoE burst healing. Never purely defensive.",
        "Aeona",   "DelayedImpact before spikes. Watch mana. StarShield preemptively.",
        "Mara",    "Brooding→stealth→poison→Guile window. Seething uptime critical (+40% Energy Regen).",
        "Ardeos",  "Stack DoTs FIRST, then Detonate. Never Detonate with 0 DoTs. Save Embers for Combustion.",
        "Rime",    "Don't overcap Orbs during IceAge. Pre-spend before burst. WinterBlessing for group heal.",
        "Tariq",   "Swing Timer — never idle. LightningBolt proc = instant use. Build to 70+ before ThunderCall.",
        "Elarion", "Mark → Barrage to trigger. Impend for party buff. MassGrip to group enemies for AoE."
    )

    if heroNotes.Has(ActiveHero) {
        UIControls["HeroNotes"].Value := heroNotes[ActiveHero]
    }
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# RUN THE PATCH
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Module 3 — Hero Roster Patch")
    print("=" * 60)

    p = Patcher(str(TARGET))

    # 1. Inject hero globals after the existing TARGETING globals block
    p.insert_after(
        "global TargetHP    := 100",
        GLOBALS_HERO
    )

    # 2. Inject hero switcher utility functions before hotkeys
    p.append_function(HERO_SWITCHER_FUNC, before_anchor="F1:: StartRotation")

    # 3. Inject dispatch function
    p.append_function(HERO_ROTATION_DISPATCH, before_anchor="F1:: StartRotation")

    # 4. Inject all hero rotation functions
    for block in [
        HELENA_ROTATION, MEIKO_ROTATION, XAVIAN_ROTATION,
        SYLVIE_ROTATION, VIGOUR_ROTATION, AEONA_ROTATION,
        ARDEOS_ROTATION, RIME_ROTATION, TARIQ_ROTATION, ELARION_ROTATION
    ]:
        p.append_function(block, before_anchor="F1:: StartRotation")

    # 5. Inject hero roster UI function
    p.append_function(HERO_ROSTER_UI, before_anchor="F1:: StartRotation")

    # 6. Patch CreateMainGUI to call CreateHeroRosterPanel and widen to 1360
    p.replace_exact(
        'MainGUI.Show("w1020 h850")',
        'CreateHeroRosterPanel()\n    UpdatePartyDisplay()\n    MainGUI.Show("w1360 h850")'
    )

    # 7. Patch UpdateGUI to call UpdateHeroRosterPanel
    p.replace_exact(
        "    UpdatePerformanceDisplay()",
        "    UpdatePerformanceDisplay()\n    UpdateHeroRosterPanel()"
    )

    # 8. Route GetNextAbility to the dispatch
    p.replace_exact(
        "GetNextAbility() {",
        "GetNextAbility() {\n    return GetNextAbilityForHero()\n}\n\nGetNextAbilityForHero_UNUSED() {"
    )

    # 9. Verify
    p.verify([
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
        "ActiveHero",
        "w1360",
    ])

    p.print_ops()
    p.save()

    print("\n✅ Module 3 patch complete!")
    print("   Run FellowshipUltimate.ahk to see the full hero roster panel.")


if __name__ == "__main__":
    main()
