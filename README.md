# 🕷️ Mara Ultimate — Fellowship MMORPG Rotation Bot

> AutoHotkey v2.0 priority rotation assistant for **Mara** (Rogue Assassin) in [Fellowship](https://store.steampowered.com/app/fellowship)

---

## Current Version: v6.0 — Spider's Web Edition

### Modules Implemented

| Module | Status | Description |
|--------|--------|-------------|
| **Module 2** | ✅ Complete | Stealth State Engine — `NONE → PENDING → CONSUMED` state machine |
| **Module 1** | ✅ Complete | Ability Data Accuracy — real numbers from Icy Veins / Method.gg |
| **Module 4** | ✅ Complete | Priority Logic Overhaul — 15-step ST + 14-step AOE |
| **Module 3** | 🔜 Planned | Hero Roster Panel — full party composition UI |
| **Module 5** | 🔜 Planned | UI Polish & Cosmetics — animated stealth glow, arc bars |
| **Module 6** | 🔜 Planned | Hemotoxin Build — full detonation window tracking |

---

## Features

### 🌑 Stealth Engine (Module 2)
- Three-state machine: **NONE → PENDING → CONSUMED**
- `BroodingShadows` sets state to `PENDING`, timestamps the 10s window
- Next builder cast **consumes stealth** and routes the correct poison:
  - `Backstab` → **Caustic Poison** (instant 6 CP)
  - `Widow's Bite` → **Seething Poison** (+40% Energy Regen for 60s — Predator's Rush)
  - `Skittering Blades` → **Volatile Poison** (AoE DoT on ALL targets + explosion on expiry)
- Smart `ShouldUseBrooding()` — won't waste a charge if Seething has >15s remaining
- `GetStealthPreferredBuilder()` — picks Seething refresh vs Volatile vs Caustic based on context

### ⚡ Real Ability Data (Module 1)
| Fix | Old | Corrected |
|-----|-----|-----------|
| Maiden of Death CD | 90s | **60s** |
| Widow's Bite CP | 2 base | **4 base** (2 per strike × 2 strikes) |
| Backstab stealth CP | vague | **6 CP** (Caustic Poison) |
| Seething Poison regen | 40% | **+40% (Predator's Rush)** — now labeled correctly |
| Shadow Protection | unused | Added to priority + proc alert |

### 🎯 Priority Logic (Module 4)
**Single Target (15 steps):**
1. FinalStratagem during Maiden burst (custom macro)
2. Maiden of Death off CD (60s)
3. Weapon inside Maiden window
4. **Assassin's Guile window** — forces finisher spam (4 GCDs in 5s)
5. Hemotoxin detonation (< 3s panic mode)
6. Seething Poison maintenance (Predator's Rush upkeep)
7. Hemorrhage bleed maintenance (+3 energy/tick)
8. Brooding setup for next Guile window
9. Execute pending stealth builder
10. Finisher at 6 CP (cap prevention)
11. Finisher at 5 CP (optimal spend)
12–15. Energy gen, fillers, energy dump

**AOE (14 steps):** Same structure, swaps Queen's Fang priority for Arachnid Assault, adds Volatile Poison refresh via Skittering from stealth.

---

## UI Panels

- **⚡ Resources** — Live energy (color-coded), CP display, Brooding charges
- **🌑 Stealth Engine** — Real-time state display (NONE/PENDING/CONSUMED), last poison applied, stealth window countdown
- **🔥 Burst Windows** — Maiden, Weapon, Assassin's Guile, Hemotoxin, Final Stratagem with progress bars
- **☠️ Poison Tracker** — Seething (Predator's Rush indicator), Volatile, Hemorrhage with uptime %
- **⭐ Malevolence** — Stack timers for QF and AA, Feed the Queen stacks, damage multiplier display
- **🎯 Next Ability Preview** — Icon, estimated damage with all active multipliers, stealth annotation
- **📜 Rotation Queue** — Next 5 abilities simulated
- **📊 Performance** — DPS, CPM, waste %, efficiency bar, Guile window counter

---

## Installation

1. Install [AutoHotkey v2.0](https://www.autohotkey.com/)
2. Download `MaraUltimate_v6.ahk`
3. Double-click to run
4. Configure Talents to match your in-game build (F6)
5. Set keybinds to match your in-game layout (F5)
6. Press **F1** (Single Target) or **F2** (AOE) to start

---

## Hotkeys

| Key | Action |
|-----|--------|
| `F1` | Start Single Target rotation |
| `F2` | Start AOE rotation |
| `F3` | Pause |
| `F4` | Stop |
| `F5` | Keybind editor |
| `F6` | Talent editor |
| `F7` | Help |
| `F8` | Analytics |
| `ESC` | Exit |

---

## Stat Priority (from Method.gg)

> Aim for **~14% Haste**, then balance **Expertise** and **Crit** equally. Avoid overstacking Spirit.

- Finisher build: Expertise = Crit > Haste (~10%) > Spirit (0–20%)
- Hemotoxin build: Expertise = Crit > Haste (~10% lower than Exp/Crit)

---

## Hero Roster (Fellowship)

| Role | Heroes |
|------|--------|
| Tank | Helena, Meiko, Xavian |
| Healer | Aeona, Sylvie, Vigour |
| DPS | **Mara**, Ardeos, Elarion, Rime, Tariq |

---

## Credits

- **Morpheus** (MisTAiM) — Developer / Black Bulls Den
- Ability data sourced from [Icy Veins](https://www.icy-veins.com/fellowship/news/mara-hero-dps-guide/) and [Method.gg](https://www.method.gg/fellowship/heroes/mara)
