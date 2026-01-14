# Quotidian Reel Generator

Automated Instagram Reel generation for Quotidian daily puzzles.

## Overview

This tool generates Instagram Reels from daily puzzle data. Each reel:

- Demonstrates the puzzle being auto-solved
- Reveals the completed quote
- Loops seamlessly for replay value
- Creates curiosity without CTAs

**Important**: Generates reels for **yesterday's** puzzle to avoid spoiling today's game.

## Features

- ✅ Shared puzzle data with main Quotidian codebase
- ✅ Dynamic letter timing based on quote length
- ✅ Audio: Music track + letter impact SFX
- ✅ Cover image generation (matches reel reveal frame)
- ✅ No stats/streaks - for official Instagram page

## Quick Start

```bash
cd Quotidian-reel
./generate-with-export.sh
```

## Manual Workflow

### 1. Export Quotes (when adding new quotes to database)

From the Quotidian directory:
```bash
cd ../Quotidian
npm run export-quotes
```

This exports the quotes library to `Quotidian-reel/shared/quotes.json`.

### 2. Generate Reel

From the Quotidian-reel directory:
```bash
cd Quotidian-reel
python3 generate.py
```

## Output Files

```
output/
├── quotidian-reel-2026-01-12.mp4  # Video reel
└── quotidian-cover-2026-01-12.png # Cover image
```

Files are dated for **yesterday's** puzzle (to avoid spoilers).

## Audio

### Custom Music

Place your music track at `assets/music.mp3`.

**Requirements:**
- Format: MP3
- Target loudness: ~-16 LUFS
- Style: Ambient, minimal
- Duration: ≥8 seconds

### Letter SFX

Generated automatically - subtle clicks/thuds timed to letter placements with slight randomization for ASMR effect.

## Video Specifications

| Property | Value |
|----------|-------|
| Format | MP4 (H.264) |
| Resolution | 1080 × 1920 (9:16) |
| Frame Rate | 30 fps |
| Duration | ~7.1 seconds |
| Audio | AAC, 48 kHz, 192 kbps |

## Visual Timeline

| Time | Phase |
|------|-------|
| 0.00-0.30s | Letter bank materializes |
| 0.30-0.55s | Micro-breath (subtle motion) |
| 0.55-3.80s | Auto-solve (dynamic timing) |
| 3.80-4.20s | Transition |
| 4.20-6.80s | Quote reveal + brand mark |
| 6.80-7.20s | Loop reset (cross-dissolve) |

## Cover Image

The cover image matches the final quote reveal frame:
- Faint grid lines (8% opacity)
- Full quote with same typography
- Prominent "Quotidian" wordmark
- "A daily puzzle" subtitle
- No stats, no streaks

## Updating Quotes

When you add new quotes to the main Quotidian codebase (`constants.ts`):

1. Run `npm run export-quotes` from the Quotidian directory
2. The reel generator will automatically use the updated data

The date calculation logic is identical between the main app and reel generator, ensuring both use the same daily puzzle.

## Project Structure

```
Quotidian-reel/
├── generate.py              # Main Python video generator
├── generate-with-export.sh  # Full workflow script
├── requirements.txt         # Python dependencies
├── assets/
│   ├── README.md           # Audio specifications
│   └── music.mp3           # (optional) Custom music track
├── shared/
│   └── quotes.json         # Exported from main codebase
├── output/                 # Generated videos and covers
└── tmp/                    # Temporary frames
```

## Dependencies

- Python 3.8+
- Pillow (image generation)
- numpy (audio generation)
- ffmpeg (video encoding)

Install:
```bash
pip3 install -r requirements.txt
```
