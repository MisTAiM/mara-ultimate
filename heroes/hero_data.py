"""
Fellowship Ultimate Bot — Hero Data Registry
============================================
Authoritative hero data sourced from:
  - Icy Veins (icy-veins.com/fellowship)
  - Method.gg  (method.gg/fellowship/heroes)
  - Fextralife Fellowship Wiki

Each hero entry contains:
  - role, stat, resource_name, resource_max
  - abilities: list of dicts with cooldown, cost, type, desc
  - priority: ordered list of priority steps (maps to AHK priority functions)
  - key_mechanics: dict of named mechanics specific to that hero
  - talents: list of known talents with effect descriptions
"""

HEROES = {

    # ══════════════════════════════════════════════════════════════
    # TANKS
    # ══════════════════════════════════════════════════════════════

    "Helena": {
        "role":          "Tank",
        "stat":          "Strength",
        "resource":      "Toughness",    # defense buffer, reduces incoming dmg
        "resource_max":  100,
        "icon":          "🛡️",
        "color":         "4169e1",       # royal blue
        "mechanic":      "VeteranOfWar", # casting abilities reduces other CDs
        "desc": (
            "Sword-and-board tank. Manages Toughness (damage mitigation buffer) "
            "through Veteran of War CDR cycling. Priority: keep Toughness >75%, "
            "Shields Up on CD, rotate Shield Slam / Shockwave for CDR."
        ),
        "abilities": [
            {"name": "ShieldsUp",      "cd": 0,    "cost": 0,  "type": "defense",  "desc": "Core mitigation. Apply when Toughness <40% or block buff expiring. Primary defensive CD."},
            {"name": "ShieldSlam",     "cd": 0,    "cost": 0,  "type": "builder",  "desc": "Main damage + CDR trigger for Veteran of War. Spam on CD."},
            {"name": "Shockwave",      "cd": 0,    "cost": 0,  "type": "cc",       "desc": "AoE stun. Feeds Veteran of War CDR twice. High priority for CDR."},
            {"name": "ShieldThrow",    "cd": 0,    "cost": 0,  "type": "ranged",   "desc": "Ranged threat + CDR. Cast on CD. Resets on Siegebreaker."},
            {"name": "SweepingStrike", "cd": 0,    "cost": 0,  "type": "aoe",      "desc": "AoE damage. Lower priority — skip if health/Toughness low."},
            {"name": "IronWall",       "cd": 30.0, "cost": 0,  "type": "defense",  "desc": "Prevents Toughness loss for duration. Use when Shields Up unavailable."},
            {"name": "GrandMelee",     "cd": 45.0, "cost": 0,  "type": "offense",  "desc": "Extended damage window. Rotate with Iron Wall to cover Shield Up gaps."},
            {"name": "Siegebreaker",   "cd": 90.0, "cost": 0,  "type": "ultimate", "desc": "ULTIMATE. 25% dmg reduction + 25% bonus dmg, double CDR from Veteran of War. Save for heavy damage phases."},
            {"name": "Charge",         "cd": 20.0, "cost": 0,  "type": "mobility", "desc": "Gap closer + stun. Use to open pulls or reposition."},
            {"name": "Kick",           "cd": 16.0, "cost": 0,  "type": "interrupt","desc": "Interrupt. 16s CD."},
        ],
        "priority_st": [
            "Siegebreaker if heavy damage phase",
            "ShieldsUp if Toughness <40% or block buff expiring",
            "IronWall if ShieldsUp on CD and Toughness dropping",
            "Shockwave on CD (double CDR)",
            "ShieldThrow on CD",
            "ShieldSlam filler",
            "SweepingStrike if healthy",
            "GrandMelee on CD",
        ],
        "priority_aoe": [
            "Same as ST — Shockwave gets higher priority for AoE stun",
            "SweepingStrike every pack for AoE threat",
        ],
        "key_mechanics": {
            "VeteranOfWar": "Each ability cast has chance to reduce Shields Up and other CD by 1-2s. Never sit idle — keep casting.",
            "Toughness":    "Damage mitigation buffer. Above 75% = max dmg reduction. Below 40% = use Shields Up NOW.",
        },
        "stat_priority": ["Strength (iLvl)", "Haste", "Spirit", "Crit"],
        "talents": [
            "ShieldMastery — tighter rotation timing",
            "Aftershock — supercharges pull opener",
            "ReinforcedSteel — flat magic reduction",
            "GleamingShield — survivability",
            "FrontLineDefender — survivability",
            "SkullCracker — add control",
            "RazorShrapnel — add control",
        ],
    },

    "Meiko": {
        "role":          "Tank",
        "stat":          "Agility",
        "resource":      "Stance",       # Wind/Earth stance swapping
        "resource_max":  0,              # no numeric resource — combo-based
        "icon":          "🥋",
        "color":         "20b2aa",       # teal
        "mechanic":      "ComboStance",  # Wind/Earth stance chains into finishers
        "desc": (
            "Martial artist tank. Combo-based using Palm, Kick, Fist sequences "
            "into finishers. Twin Souls for threat control. Wind stance = mobility "
            "and damage. Earth stance = defense and self-heal. 6 possible combos."
        ),
        "abilities": [
            {"name": "PalmStrike",    "cd": 0,    "cost": 0,  "type": "builder",  "desc": "Basic builder. Chains into combo sequences."},
            {"name": "Kick",          "cd": 16.0, "cost": 0,  "type": "interrupt","desc": "Interrupt. Also part of combo chain."},
            {"name": "FistSlam",      "cd": 0,    "cost": 0,  "type": "builder",  "desc": "Heavy builder. Part of Fist combo chain."},
            {"name": "SpiritedStrikes","cd": 0,   "cost": 0,  "type": "finisher", "desc": "Finisher from Wind stance combo. Maintain uptime."},
            {"name": "SpiritedVortex","cd": 0,    "cost": 0,  "type": "finisher", "desc": "AoE finisher from Earth stance combo."},
            {"name": "WindDash",      "cd": 12.0, "cost": 0,  "type": "mobility", "desc": "Dash + enter Wind stance. Repositioning."},
            {"name": "EarthStance",   "cd": 12.0, "cost": 0,  "type": "defense",  "desc": "Enter Earth stance. Self-heal + armor."},
            {"name": "TwinSouls",     "cd": 45.0, "cost": 0,  "type": "utility",  "desc": "UNIQUE: threat control + emergency save for party member."},
            {"name": "IronBody",      "cd": 60.0, "cost": 0,  "type": "defense",  "desc": "Major defensive CD. Use in spike damage."},
        ],
        "priority_st": [
            "IronBody if spiking",
            "TwinSouls for threat/emergency",
            "SpiritedStrikes uptime (Wind finisher)",
            "WindDash for Wind combo access",
            "PalmStrike / Kick / FistSlam builders",
            "SpiritedVortex for AoE",
        ],
        "key_mechanics": {
            "ComboChain": "Palm→Kick→Fist in correct order unlocks finishers. Spirited Strikes (ST) and Spirited Vortex (AoE).",
            "TwinSouls":  "Unique ability — redirect damage from ally to Meiko temporarily. Emergency save tool.",
        },
        "stat_priority": ["Agility (iLvl)", "Haste", "Vigor", "Focus", "Fortitude"],
        "talents": [
            "Vigor — self-buff potential",
            "Focus — skill effectiveness",
            "Fortitude — endurance balance",
        ],
    },

    "Xavian": {
        "role":          "Tank",
        "stat":          "Intellect",    # mana-based tank (unique)
        "resource":      "Mana",
        "resource_max":  100,
        "icon":          "✨",
        "color":         "ffd700",       # gold
        "mechanic":      "SwiftReprival", # stacks for powerful spells
        "desc": (
            "Mana-based paladin-style tank. High self-sustain via healing and shields. "
            "Aura of Solace permanently redirects party damage to Xavian. "
            "Swift Reprival stacks power damaging and healing abilities. "
            "Season 2 hero — Brilliant Flash and Shining Halo mechanics."
        ),
        "abilities": [
            {"name": "AuraOfSolace",   "cd": 0,    "cost": 0,    "type": "passive",  "desc": "PERMANENT aura. Redirects % of party damage to Xavian. Always active."},
            {"name": "BrilliantFlash", "cd": 0,    "cost": 20,   "type": "builder",  "desc": "Generates Swift Reprival stacks. Primary builder."},
            {"name": "ShiningHalo",    "cd": 0,    "cost": 15,   "type": "heal",     "desc": "Party-wide shield/heal. Uses Shining Halo charges."},
            {"name": "HolyStrike",     "cd": 0,    "cost": 25,   "type": "damage",   "desc": "Mana spender. Damage + self-heal."},
            {"name": "DivineBulwark",  "cd": 30.0, "cost": 0,    "type": "defense",  "desc": "Major shield CD. Absorbs damage for duration."},
            {"name": "RadiantBarrier", "cd": 20.0, "cost": 0,    "type": "defense",  "desc": "Party shield. Reduce incoming damage for group."},
            {"name": "Consecration",   "cd": 45.0, "cost": 40,   "type": "aoe",      "desc": "AoE damage + heal zone. Drop in melee range."},
            {"name": "Kick",           "cd": 16.0, "cost": 0,    "type": "interrupt","desc": "Interrupt."},
        ],
        "priority_st": [
            "DivineBulwark if spiking",
            "RadiantBarrier for party",
            "AuraOfSolace — always on (passive)",
            "BrilliantFlash for Swift Reprival stacks",
            "ShiningHalo for healing",
            "HolyStrike mana spender",
            "Consecration on CD",
        ],
        "key_mechanics": {
            "SwiftReprival": "Stacks from BrilliantFlash. Empower healing/damage spells at max stacks.",
            "AuraOfSolace":  "Permanent passive aura — NEVER disabled. Makes Xavian absorb party damage.",
        },
        "stat_priority": ["Intellect (iLvl)", "Haste", "Spirit", "Crit"],
        "talents": ["Self-sustain focused", "Party support", "Damage redirect"],
    },

    # ══════════════════════════════════════════════════════════════
    # HEALERS
    # ══════════════════════════════════════════════════════════════

    "Sylvie": {
        "role":          "Healer",
        "stat":          "Intellect",
        "resource":      "Flutterflies", # pet-based healing charges
        "resource_max":  5,
        "icon":          "🦋",
        "color":         "90ee90",       # light green
        "mechanic":      "FlutterflyHoT", # Flutterflies apply HoTs, detonate for heal
        "desc": (
            "Proactive HoT healer. Plants Flutterflies on allies for passive regen. "
            "Nettlebolt DPS reduces Life Petal CD. Heart Bloom converts overhealing "
            "to shields. Plant seeds, detonate when needed. Higher throughput than Vigour "
            "but less reactive burst."
        ),
        "abilities": [
            {"name": "Nettlebolt",    "cd": 0,    "cost": 10, "type": "damage",  "desc": "DPS ability. REDUCES Life Petal CD. Cast to maintain healing cooldown."},
            {"name": "LifePetal",     "cd": 8.0,  "cost": 20, "type": "heal",    "desc": "Primary direct heal. CD reduced by Nettlebolt casts."},
            {"name": "Flutterfly",    "cd": 0,    "cost": 15, "type": "hot",     "desc": "Deploy Flutterfly HoT on ally. Max 5 active. Stacks passive regen."},
            {"name": "HeartBloom",    "cd": 0,    "cost": 0,  "type": "passive", "desc": "PASSIVE: overhealing converts to shields on target."},
            {"name": "BloomBurst",    "cd": 12.0, "cost": 25, "type": "aoe",     "desc": "Detonate active Flutterflies for burst AoE heal."},
            {"name": "PollenCloud",   "cd": 20.0, "cost": 20, "type": "aoe",     "desc": "AoE HoT zone. Drop on party."},
            {"name": "NaturesMend",   "cd": 45.0, "cost": 0,  "type": "cooldown","desc": "Emergency major heal. Use for critical health."},
            {"name": "Rejuvenate",    "cd": 0,    "cost": 15, "type": "hot",     "desc": "Single target HoT. Maintain on tank."},
            {"name": "Kick",          "cd": 20.0, "cost": 0,  "type": "interrupt","desc": "Interrupt. Higher CD than DPS."},
        ],
        "priority_st": [
            "NaturesMend if tank critical",
            "BloomBurst if multiple Flutterflies active and party damaged",
            "LifePetal if tank below 60%",
            "Nettlebolt to reduce LifePetal CD",
            "Flutterfly maintenance on tank",
            "Rejuvenate on tank",
            "PollenCloud on CD",
        ],
        "priority_aoe": [
            "NaturesMend emergency",
            "PollenCloud for AoE HoT",
            "BloomBurst — detonate Flutterflies",
            "Flutterfly on lowest HP targets",
            "Nettlebolt for CDR",
        ],
        "key_mechanics": {
            "Nettlebolt_CDR": "Every Nettlebolt cast reduces LifePetal CD. Weave constantly to maximize healing uptime.",
            "Flutterflies":   "Deploy on all party members. BloomBurst detonates them for AoE heal.",
            "HeartBloom":     "Passive shield from overhealing — overheal intentionally on tanks.",
        },
        "stat_priority": ["Intellect (iLvl)", "Crit", "Expertise", "Spirit", "Haste"],
        "talents": [
            "Proactive HoT stacking",
            "Flutterfly count increases",
            "HeartBloom shield amplification",
        ],
    },

    "Vigour": {
        "role":          "Healer",
        "stat":          "Intellect",
        "resource":      "RadiantRunes", # generated by dealing damage
        "resource_max":  5,
        "icon":          "⚡",
        "color":         "ffd700",       # gold/yellow
        "mechanic":      "RadiantRunes", # deal damage → generate runes → spend on heals
        "desc": (
            "Reactive burst healer. Deals damage (RadiantBlast, DawnbreakerOrb) to "
            "generate Radiant Runes. Spends runes on empowered instant heals and "
            "shields. Overcharging spreads heals to multiple targets. Pairs with Meiko "
            "in meta Anchor comp. Weaker spot-heal, stronger burst + shields."
        ),
        "abilities": [
            {"name": "RadiantBlast",   "cd": 0,    "cost": 10, "type": "damage",  "desc": "Primary DPS. Generates Radiant Runes. Cast constantly."},
            {"name": "DawnbreakerOrb", "cd": 8.0,  "cost": 15, "type": "damage",  "desc": "AoE damage orb. Generates Runes faster on multi-hit."},
            {"name": "HolyMend",       "cd": 0,    "cost": 1,  "type": "heal",    "desc": "Rune spender. Instant direct heal. Empowered at max runes."},
            {"name": "ShieldOfLight",  "cd": 0,    "cost": 2,  "type": "shield",  "desc": "Rune spender. Absorb shield on target."},
            {"name": "Overcharge",     "cd": 0,    "cost": 3,  "type": "aoe",     "desc": "Spend 3 runes — Overcharge next heal to hit multiple targets."},
            {"name": "HealingWave",    "cd": 20.0, "cost": 0,  "type": "heal",    "desc": "Moderate direct heal. No rune cost."},
            {"name": "DivineSurge",    "cd": 60.0, "cost": 0,  "type": "cooldown","desc": "ULTIMATE. Major burst heal on party. Use for wipe prevention."},
            {"name": "ProtectiveAura", "cd": 30.0, "cost": 0,  "type": "defense", "desc": "Party damage reduction aura for duration."},
            {"name": "Kick",           "cd": 20.0, "cost": 0,  "type": "interrupt","desc": "Interrupt. Higher CD than DPS."},
        ],
        "priority_st": [
            "DivineSurge if wipe risk",
            "HolyMend at max runes if tank below 50%",
            "Overcharge + HolyMend for multi-target burst",
            "ShieldOfLight on tank preemptively",
            "DawnbreakerOrb for rune generation",
            "RadiantBlast filler for rune gen",
            "HealingWave if runes low and tank damaged",
            "ProtectiveAura on CD",
        ],
        "key_mechanics": {
            "RadiantRunes":  "Deal damage → generate runes. Runes → instant heals/shields. Never stop dealing damage.",
            "Overcharge":    "Spend 3 runes to make next heal AoE. Use during group damage phases.",
            "DamageToBridge": "The cadence: RadiantBlast → runes → HolyMend/Shield. Never purely defensive.",
        },
        "stat_priority": ["Intellect (iLvl)", "Crit", "Expertise", "Spirit", "Haste"],
        "talents": [
            "RadiantRune generation rate",
            "Overcharge range/targets",
            "DivineSurge cooldown reduction",
        ],
    },

    "Aeona": {
        "role":          "Healer",
        "stat":          "Intellect",
        "resource":      "Mana",
        "resource_max":  100,
        "icon":          "🌟",
        "color":         "87ceeb",       # sky blue
        "mechanic":      "DamageDelay",  # unique: delays incoming damage, boosts party EHP
        "desc": (
            "Season 2 healer. Unique mechanic delays incoming damage to party, "
            "boosting effective HP by up to 50%. Powerful single-target damage output. "
            "Mana management issues early, lacks throughput on sustained damage. "
            "Best when burst mitigation matters over sustained HPS."
        ),
        "abilities": [
            {"name": "DelayedImpact",  "cd": 0,    "cost": 15, "type": "unique",  "desc": "UNIQUE: delay incoming damage on target, increasing effective HP window."},
            {"name": "ArcaneBlast",    "cd": 0,    "cost": 20, "type": "damage",  "desc": "Primary DPS + healing contribution."},
            {"name": "HealingLight",   "cd": 0,    "cost": 25, "type": "heal",    "desc": "Direct heal. Main restore ability."},
            {"name": "StarShield",     "cd": 15.0, "cost": 20, "type": "shield",  "desc": "Large absorb shield. Use before spike damage."},
            {"name": "CosmicMend",     "cd": 30.0, "cost": 0,  "type": "heal",    "desc": "Major group heal CD."},
            {"name": "TimeWarp",       "cd": 90.0, "cost": 0,  "type": "cooldown","desc": "ULTIMATE. Party-wide EHP boost for duration."},
            {"name": "Kick",           "cd": 20.0, "cost": 0,  "type": "interrupt","desc": "Interrupt."},
        ],
        "priority_st": [
            "TimeWarp for critical phases",
            "DelayedImpact on tank before spike",
            "StarShield preemptively",
            "CosmicMend for group damage",
            "HealingLight if tank low",
            "ArcaneBlast filler",
        ],
        "key_mechanics": {
            "DelayedImpact": "Core unique — delays dmg to tank. Pre-cast before known spikes for max EHP.",
            "ManaManagement": "Aeona runs OOM quickly. Monitor mana — Spirit stat helps.",
        },
        "stat_priority": ["Intellect (iLvl)", "Spirit", "Crit", "Expertise"],
        "talents": ["Delay duration", "Shield size", "Mana efficiency"],
    },

    # ══════════════════════════════════════════════════════════════
    # DPS
    # ══════════════════════════════════════════════════════════════

    "Mara": {
        "role":          "DPS",
        "stat":          "Agility",
        "resource":      "Energy",
        "resource_max":  200,
        "icon":          "🕷️",
        "color":         "8b00ff",       # purple
        "mechanic":      "StealthPoison", # stealth → poison → combo points → finisher
        "desc": (
            "Stealth rogue assassin. Builder/spender around combo points and energy. "
            "Brooding Shadows → stealth → poison application → Assassin's Guile window. "
            "Three finishers: Queen's Fang (ST), Arachnid Assault (AoE), Hemorrhaging Strike (bleed)."
            "See MaraUltimate_v6.ahk for full Module 1/2/4 implementation."
        ),
        "stat_priority": ["Agility (iLvl)", "Haste ~14%", "Expertise", "Crit"],
        "implemented":   True,           # already has full AHK module
    },

    "Ardeos": {
        "role":          "DPS",
        "stat":          "Intellect",
        "resource":      "Cinders",      # DoT ticks generate Cinders → Burning Embers
        "resource_max":  4,              # max 4 Burning Embers
        "icon":          "🔥",
        "color":         "ff4500",       # orange-red
        "mechanic":      "BurningEmbers", # Cinders (0-100) → Burning Embers (0-4) → Detonate
        "desc": (
            "Fire DoT mage. Cinders accumulate from DoT abilities to 100, "
            "converting to a Burning Ember (max 4). Detonate consumes Embers for burst "
            "based on active DoTs. Balance spending Embers vs saving for burst windows. "
            "Rotation similar in ST and AoE — easy to learn."
        ),
        "abilities": [
            {"name": "SearingBlaze",   "cd": 0,    "cost": 0,    "type": "dot",      "desc": "Primary DoT. Generates Cinders per tick. Always maintain."},
            {"name": "FireBall",       "cd": 0,    "cost": 0,    "type": "direct",   "desc": "Direct damage. Extends SearingBlaze with SlowBurn talent."},
            {"name": "EngulfingFlames","cd": 0,    "cost": 0,    "type": "dot",      "desc": "Second DoT. Stack with SearingBlaze before Detonate."},
            {"name": "InfernalWave",   "cd": 0,    "cost": 0,    "type": "aoe",      "desc": "AoE fire wave. Applies DoT to multiple targets."},
            {"name": "Detonate",       "cd": 0,    "cost": 1,    "type": "finisher", "desc": "SPEND Burning Embers. Damage scales with active DoTs on target. Never use with 0 DoTs."},
            {"name": "Pyromania",      "cd": 20.0, "cost": 0,    "type": "cooldown", "desc": "Burst window. Increases Cinder generation rate. Back-to-back in Season 2."},
            {"name": "Combustion",     "cd": 60.0, "cost": 0,    "type": "cooldown", "desc": "MAJOR burst CD. Massively increases fire damage. Align with Detonate stack."},
            {"name": "Kick",           "cd": 20.0, "cost": 0,    "type": "interrupt","desc": "Interrupt. Higher CD — coordinate with party."},
        ],
        "priority_st": [
            "Combustion if 4 Embers and DoTs active",
            "Detonate at 4 Embers OR if Combustion active",
            "SearingBlaze — maintain DoT (never let drop)",
            "EngulfingFlames — maintain DoT",
            "Pyromania on CD",
            "FireBall filler",
            "InfernalWave for AoE DoT application",
        ],
        "priority_aoe": [
            "InfernalWave to apply DoTs to all targets",
            "Detonate when multiple targets have DoTs (huge multiplier)",
            "Combustion + Detonate burst",
            "SearingBlaze / EngulfingFlames on primary",
        ],
        "key_mechanics": {
            "Cinders":       "DoT ticks generate Cinders (0→100). At 100 = 1 Burning Ember.",
            "BurningEmbers": "Max 4 stacks. Detonate damage multiplied by number of active DoTs.",
            "DetonateRule":  "NEVER Detonate with 0 DoTs active — wasted. Always have 2+ DoTs first.",
        },
        "stat_priority": ["Intellect (iLvl)", "Crit", "Expertise", "Haste"],
        "talents": [
            "SlowBurn (1A) — FireBall extends SearingBlaze",
            "CorrosiveSpill — finisher AoE DoT pool",
            "Pyromania CDR",
            "InfernalWave DoT extension",
        ],
    },

    "Rime": {
        "role":          "DPS",
        "stat":          "Intellect",
        "resource":      "Anima",        # generates Winter Orbs
        "resource_max":  100,            # Anima pools → Winter Orbs (burst resource)
        "icon":          "❄️",
        "color":         "00bfff",       # deep sky blue
        "mechanic":      "WinterOrbs",   # Anima → Winter Orbs → burst spending
        "desc": (
            "Frost mage with builder/spender mechanic. Channels Anima into Winter Orbs "
            "for burst windows. FreezingTorrent builder → ColdSnap → GlacialBlast / IceComet "
            "spenders. Winter's Blessing provides group healing support. "
            "Simple rotation — avoid overcapping Anima during cooldowns."
        ),
        "abilities": [
            {"name": "FreezingTorrent","cd": 0,    "cost": 0,    "type": "builder",  "desc": "Primary builder. Generates Anima. Spam on CD."},
            {"name": "ColdSnap",       "cd": 0,    "cost": 20,   "type": "builder",  "desc": "Second builder. Generates Winter Orbs faster."},
            {"name": "GlacialBlast",   "cd": 0,    "cost": 1,    "type": "spender",  "desc": "Winter Orb spender. Primary ST spender."},
            {"name": "IceComet",       "cd": 0,    "cost": 2,    "type": "spender",  "desc": "Winter Orb spender. AoE / higher cost."},
            {"name": "FrostNova",      "cd": 20.0, "cost": 0,    "type": "cc",       "desc": "Freeze / root in place. CC + minor damage."},
            {"name": "WinterBlessing", "cd": 30.0, "cost": 0,    "type": "support",  "desc": "Party heal burst. GROUP SUPPORT — use when party damaged."},
            {"name": "IceAge",         "cd": 90.0, "cost": 0,    "type": "cooldown", "desc": "ULTIMATE. Major frost damage burst. Use at max Orbs."},
            {"name": "Kick",           "cd": 20.0, "cost": 0,    "type": "interrupt","desc": "Interrupt."},
        ],
        "priority_st": [
            "IceAge at max Orbs (burst window)",
            "GlacialBlast — spend Orbs before overcap",
            "ColdSnap on CD",
            "FreezingTorrent filler",
            "WinterBlessing when party low",
            "FrostNova for CC",
        ],
        "priority_aoe": [
            "IceComet for AoE Orb spend",
            "IceAge burst",
            "FreezingTorrent for Anima gen",
            "WinterBlessing party healing",
        ],
        "key_mechanics": {
            "WinterOrbs":    "Generated from Anima. Spend on GlacialBlast or IceComet. Never overcap.",
            "Overcap_Risk":  "Fast generation during IceAge causes quick overcap. Pre-spend Orbs before IceAge.",
        },
        "stat_priority": ["Intellect (iLvl)", "Crit", "Haste", "Expertise"],
        "talents": [
            "IcyFlowBuild — balanced ST/AoE (Freezing Torrent + GlacialBlast focus)",
            "IceComet amplification",
            "WinterBlessing healing amp",
        ],
    },

    "Tariq": {
        "role":          "DPS",
        "stat":          "Strength",
        "resource":      "Fury",         # build Fury → spend in burst windows
        "resource_max":  100,
        "icon":          "⚡",
        "color":         "ffd700",       # gold
        "mechanic":      "SwingTimer",   # precise timing maximizes damage uptime
        "desc": (
            "Thunder berserker. Builds Fury with attacks, spends in burst windows. "
            "Swing Timer mechanic — hit abilities at correct intervals to maximize uptime. "
            "Two builds: Lightning (Thunder Call burst) and Schism (alternate heavy hits). "
            "High APM — rewards precision. Melee positioning required."
        ),
        "abilities": [
            {"name": "HammerStrike",  "cd": 0,    "cost": 0,   "type": "builder",  "desc": "Basic attack. Generates Fury. Swing Timer anchor."},
            {"name": "ThunderClap",   "cd": 0,    "cost": 0,   "type": "builder",  "desc": "AoE builder. Applies lightning DoT."},
            {"name": "ThunderCall",   "cd": 0,    "cost": 30,  "type": "spender",  "desc": "Fury spender. Calls lightning strike. Main ST spender (Lightning Build)."},
            {"name": "Schism",        "cd": 0,    "cost": 40,  "type": "spender",  "desc": "Heavy Fury spender (Schism Build). Massive single hit."},
            {"name": "LightningBolt", "cd": 8.0,  "cost": 0,   "type": "proc",     "desc": "Lightning proc off Thunder DoT. Use immediately on proc."},
            {"name": "BerserkerRage", "cd": 30.0, "cost": 0,   "type": "cooldown", "desc": "Increases Fury generation rate + attack speed."},
            {"name": "StormBreaker",  "cd": 60.0, "cost": 0,   "type": "cooldown", "desc": "Major burst CD. Doubles Fury spend effects."},
            {"name": "Kick",          "cd": 16.0, "cost": 0,   "type": "interrupt","desc": "Interrupt. Lower CD than ranged."},
        ],
        "priority_st": [
            "StormBreaker at 80+ Fury",
            "ThunderCall (Lightning) or Schism at 70+ Fury",
            "LightningBolt proc — use immediately",
            "BerserkerRage on CD",
            "ThunderClap for DoT application",
            "HammerStrike filler",
        ],
        "priority_aoe": [
            "ThunderClap for AoE DoT on all",
            "ThunderCall AoE lightning at 70+ Fury",
            "StormBreaker burst",
            "HammerStrike filler",
        ],
        "key_mechanics": {
            "SwingTimer":    "Space abilities to hit on cooldown exactly. Lost GCDs = big DPS loss.",
            "FuryManagement":"Never sit at 100 Fury — spend before cap. Build during filler windows.",
            "LightningProc": "Instant use when it procs. Never delay.",
        },
        "stat_priority": ["Strength (iLvl)", "Haste", "Crit", "Expertise"],
        "talents": [
            "LightningBuild — Thunder Call focus",
            "SchismBuild — massive hit alternate",
            "GodOfThunder — lightning damage amp",
        ],
    },

    "Elarion": {
        "role":          "DPS",
        "stat":          "Agility",
        "resource":      "Focus",        # passive regen resource
        "resource_max":  100,
        "icon":          "🏹",
        "color":         "9370db",       # medium purple
        "mechanic":      "LunarMark",    # place marks → trigger for burst explosion
        "desc": (
            "Ranged marksman. Focus resource (passive regen). Places Lunarlight Marks "
            "on enemies, triggered by specific abilities for burst damage. "
            "Heartseeker Barrage procs Marks. Mass Grip utility. Can cast while moving. "
            "Very high priority-target damage. Rotation is AoE-efficient by default."
        ),
        "abilities": [
            {"name": "ArrowStrike",     "cd": 0,    "cost": 10, "type": "builder",  "desc": "Basic Focus generator. Cast constantly."},
            {"name": "PiercingShot",    "cd": 0,    "cost": 20, "type": "damage",   "desc": "Primary Focus spender. High ST damage."},
            {"name": "LunarlightMark",  "cd": 0,    "cost": 15, "type": "utility",  "desc": "Apply mark to target. Detonates for burst when triggered."},
            {"name": "HeartseekerBarrage","cd": 0,  "cost": 30, "type": "burst",    "desc": "Triggers Lunarlight Marks. HIGH priority when marks are active."},
            {"name": "StarfallArrow",   "cd": 8.0,  "cost": 25, "type": "aoe",      "desc": "AoE arrow rain. Apply Marks to multiple targets."},
            {"name": "MassGrip",        "cd": 30.0, "cost": 0,  "type": "utility",  "desc": "UNIQUE: pulls multiple enemies together. Party utility."},
            {"name": "CelestialVolley", "cd": 45.0, "cost": 0,  "type": "cooldown", "desc": "Major burst CD. Rapid fire sequence."},
            {"name": "Impend",          "cd": 20.0, "cost": 0,  "type": "debuff",   "desc": "Vulnerability debuff on target. Increases party damage."},
            {"name": "Kick",            "cd": 20.0, "cost": 0,  "type": "interrupt","desc": "Interrupt."},
        ],
        "priority_st": [
            "HeartseekerBarrage if LunarlightMark active",
            "CelestialVolley burst window",
            "LunarlightMark on target (keep up)",
            "Impend for vulnerability debuff",
            "PiercingShot Focus spender at 70+",
            "StarfallArrow on CD",
            "ArrowStrike filler",
            "MassGrip for party utility",
        ],
        "priority_aoe": [
            "StarfallArrow — mark all targets",
            "HeartseekerBarrage — trigger all marks",
            "MassGrip to group enemies",
            "CelestialVolley burst",
            "ArrowStrike filler",
        ],
        "key_mechanics": {
            "LunarlightMark":    "Apply mark → trigger with HeartseekerBarrage for burst. Mark first, then Barrage.",
            "MassGrip":          "Pulls enemies together — coordinate with tank. Major party utility.",
            "MobileAttacks":     "Can cast nearly all abilities while moving. Use dodge rolls during casts.",
        },
        "stat_priority": ["Agility (iLvl)", "Crit", "Expertise", "Haste"],
        "talents": [
            "Lunarlight Mark triggers on Heartseeker",
            "Increased Barrage Mark chance (Season 2)",
            "Impend duration/potency",
            "Sapphire gem track (Season 2 — high priority)",
        ],
    },
}

# ── Hero role groups for easy lookup ──────────────────────────────────────
TANKS   = [h for h, d in HEROES.items() if d["role"] == "Tank"]
HEALERS = [h for h, d in HEROES.items() if d["role"] == "Healer"]
DPS     = [h for h, d in HEROES.items() if d["role"] == "DPS"]

# ── Meta comps (from tier lists) ──────────────────────────────────────────
META_COMPS = {
    "Anchor (High-End Eternal)": ["Meiko", "Vigour", "Mara", "Elarion"],
    "Trash Clear Speed":         ["Meiko", "Sylvie", "Rime", "Ardeos"],
    "Safe Climb":                ["Helena", "Vigour", "Rime", "Elarion"],
    "Budget Carry":              ["Helena", "Sylvie", "Mara", "Tariq"],
}

if __name__ == "__main__":
    print(f"Fellowship Hero Registry — {len(HEROES)} heroes loaded")
    print(f"  Tanks:   {TANKS}")
    print(f"  Healers: {HEALERS}")
    print(f"  DPS:     {DPS}")
    print(f"\nMeta Comps:")
    for name, comp in META_COMPS.items():
        print(f"  {name}: {' + '.join(comp)}")
