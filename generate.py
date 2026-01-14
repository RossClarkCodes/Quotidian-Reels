"""
Quotidian Reel Video Generator

Replicates EXACT Quotidian gameplay - looks like a screen recording.
Slower timing, exact visual appearance.

Specifications:
- Resolution: 1080x1920 (9:16)
- Frame rate: 30 fps
- Codec: H.264
"""

from PIL import Image, ImageDraw, ImageFont
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
from pathlib import Path
import json
from datetime import datetime, timedelta
import subprocess
import random
import re


@dataclass
class Quote:
    id: int
    text: str
    author: str
    source: Optional[str] = None

    # Punctuation marks that are auto-filled (not in supply)
    PUNCTUATION_MARKS = {'.', ',', '!', '?', ';', ':', '"', "'"}

    def __init__(self, id: int, text: str, author: str, source: Optional[str] = None, **kwargs):
        # Accept any additional fields from JSON export without error
        self.id = id
        self.text = text
        self.author = author
        self.source = source

    @property
    def answer(self) -> str:
        """Get puzzle text without trailing punctuation (like puzzleUtils.ts getPuzzleText)"""
        text = self.text.strip()
        if text and text[-1] in {'.', '!', '?'}:
            return text[:-1].strip()
        return text


class QuoteLibrary:
    EPOCH_YEAR = 2026
    EPOCH_MONTH = 1
    EPOCH_DAY = 1
    LIBRARY_OFFSET = 0

    def __init__(self, shared_path: Optional[Path] = None):
        if shared_path is None:
            script_dir = Path(__file__).parent
            shared_path = script_dir / "shared" / "quotes.json"
        self.shared_path = shared_path
        self.quotes: List[Quote] = []
        self._load_quotes()

    def _load_quotes(self):
        if not self.shared_path.exists():
            raise FileNotFoundError(f"Run 'npm run export-quotes' from Quotidian directory first.")
        with open(self.shared_path, 'r') as f:
            data = json.load(f)
        self.quotes = [Quote(**q) for q in data]
        print(f"✓ Loaded {len(self.quotes)} quotes")

    def get_yesterday_quote(self) -> Quote:
        yesterday = datetime.now() - timedelta(days=1)
        return self.get_daily_quote(yesterday)

    def get_daily_quote(self, date: datetime) -> Quote:
        local_midnight = datetime(date.year, date.month, date.day)
        epoch_midnight = datetime(self.EPOCH_YEAR, self.EPOCH_MONTH, self.EPOCH_DAY)
        days_since_epoch = (local_midnight - epoch_midnight).days

        if days_since_epoch < 0:
            preview = self.quotes[-1]
            return Quote(id=0, text=preview.text, author=preview.author, source=preview.source)

        idx = (days_since_epoch + self.LIBRARY_OFFSET) % len(self.quotes)
        q = self.quotes[idx]
        return Quote(id=idx + 1, text=q.text, author=q.author, source=q.source)


class GameConfig:
    """EXACT Quotidian game colors from Board.tsx and tailwind"""

    # Light mode colors
    BG = (253, 251, 247)        # #FDFBF7 - paper
    INK = (28, 28, 30)          # #1C1C1E - black
    STONE_400 = (229, 229, 234) # #E5E5EA - grid border/gaps
    STONE_500 = (120, 113, 108) # #78716C - supply letters (stone-500)
    WHITE = (255, 255, 255)     # empty cells
    STONE_100 = (243, 244, 246) # #F3F4F6 - punctuation cells

    # Grid - slightly reduced from 85px
    GRID_COLS = 12
    CELL_SIZE = 80              # Balanced size
    GAP = 2                     # 2px gaps for visible grid lines
    PADDING = 1                 # p-[1px]

    # Supply area - MUST align with grid columns
    SUPPLY_CELL_SIZE = 48       # Balanced size
    SUPPLY_GAP_X = 2            # Same as grid gap
    SUPPLY_GAP_Y = 2            # gap-0.5 (2px)

    # Screen
    WIDTH = 1080
    HEIGHT = 1920
    FPS = 30


def get_font(size: int, bold: bool = False, family: str = "serif", italic: bool = False):
    """Get serif/sans fonts like the game uses"""
    if family == "sans":
        if bold and italic:
            paths = [
                "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf",
                "/System/Library/Fonts/Supplemental/Helvetica Bold Oblique.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
            ]
        elif bold:
            paths = [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
            ]
        elif italic:
            paths = [
                "/System/Library/Fonts/Supplemental/Arial Italic.ttf",
                "/System/Library/Fonts/Supplemental/Helvetica Oblique.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
            ]
        else:
            paths = [
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
            ]
    else:
        if bold and italic:
            paths = [
                "/System/Library/Fonts/Supplemental/Georgia Bold Italic.ttf",
                "/System/Library/Fonts/Supplemental/Times New Roman Bold Italic.ttf",
                "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
                "/System/Library/Fonts/Supplemental/Georgia.ttf",
            ]
        elif bold:
            paths = [
                "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
                "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
                "/System/Library/Fonts/Supplemental/Georgia.ttf",
                "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
            ]
        elif italic:
            paths = [
                "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
                "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf",
                "/System/Library/Fonts/Supplemental/Georgia.ttf",
                "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
            ]
        else:
            paths = [
                "/System/Library/Fonts/Supplemental/Georgia.ttf",
                "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
            ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except:
            continue
    return ImageFont.load_default()


def measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


class GameState:
    """
    Replicate EXACT game state from puzzleUtils.ts and Board.tsx
    """

    def __init__(self, quote: Quote):
        self.quote = quote
        self.config = GameConfig()
        self.rows = []
        self.supply = [[] for _ in range(self.config.GRID_COLS)]
        self.letter_positions = []  # List of (row, col) positions for each letter in answer
        self.placed_supply_letters = []  # Actual letters taken from supply (in order of placement)
        self.placed_count = 0  # How many letters have been placed
        self.used_supply_indices = []  # Track which supply letters have been used (col_idx, letter_idx)

        # Build grid (from puzzleUtils.ts buildRows + initializeGame)
        self._build_grid()
        # Build supply
        self._build_supply()
        # Build letter positions mapping
        self._build_letter_positions()

    def _build_grid(self):
        """
        From puzzleUtils.ts buildRows + initializeGame functions.
        Builds rows with word wrapping, then centers each row in the 12-column grid.
        """
        puzzle_text = self.quote.answer
        words = puzzle_text.split(' ')
        lines = []
        current_line = []
        current_length = 0

        # Step 1: Build lines (words grouped with # for spaces)
        for word in words:
            if not word:
                continue
            space_cost = 1 if current_line else 0
            word_cost = len(word)

            if current_length + space_cost + word_cost <= self.config.GRID_COLS:
                if current_line:
                    current_line.append('#')  # Space represented as block
                    current_length += 1
                current_line.extend(list(word))
                current_length += word_cost
            else:
                lines.append(current_line)
                current_line = list(word)
                current_length = word_cost

        if current_line:
            lines.append(current_line)

        # Step 2: Convert lines to centered grid rows (like initializeGame)
        for line_chars in lines:
            # Calculate centering padding
            empty_spots = self.config.GRID_COLS - len(line_chars)
            left_pad = empty_spots // 2

            # Build centered row
            row = ['#'] * self.config.GRID_COLS  # Start with all blocks
            for i, char in enumerate(line_chars):
                row[left_pad + i] = char

            self.rows.append(row)

    def _build_supply(self):
        """
        From puzzleUtils.ts initializeGame function.
        Supply is built from grid positions - letters appear in their column positions.
        Punctuation marks are NOT added to supply (they're auto-filled).
        """
        # Find all letter positions (not blocks, not punctuation)
        for r, row in enumerate(self.rows):
            for c, char in enumerate(row):
                if char != '#' and char not in self.quote.PUNCTUATION_MARKS:
                    # This is a letter that goes in supply at column c
                    self.supply[c].append(char)

        # Shuffle each column (deterministic like game)
        random.seed(self.quote.id)
        for col in self.supply:
            random.shuffle(col)

    def _build_letter_positions(self):
        """Build list of (row, col) positions for each letter in the answer (in order)"""
        answer_without_spaces = self.quote.answer.replace(' ', '')
        letter_idx = 0

        for r, row in enumerate(self.rows):
            for c, char in enumerate(row):
                if char != '#' and char not in self.quote.PUNCTUATION_MARKS:
                    if letter_idx < len(answer_without_spaces):
                        self.letter_positions.append((r, c))
                        letter_idx += 1

    def get_letter_at_position(self, row: int, col: int) -> Optional[str]:
        """Get the actual placed letter at a given grid position (from supply, not necessarily correct)"""
        # Find the index of this position in letter_positions
        try:
            idx = self.letter_positions.index((row, col))
            if idx < self.placed_count and idx < len(self.placed_supply_letters):
                return self.placed_supply_letters[idx]
        except ValueError:
            pass
        return None

    def place_next_letter(self) -> bool:
        """
        Place the next letter in the grid.
        - Places the CORRECT answer letter in the grid
        - Removes that SPECIFIC letter from the shuffled supply (wherever it is)
        This creates the illusion of someone playing correctly.
        """
        if self.placed_count >= len(self.letter_positions):
            return False

        # Find the position for the next letter
        pos_idx = self.placed_count
        if pos_idx >= len(self.letter_positions):
            return False

        row, col = self.letter_positions[pos_idx]

        # Get the CORRECT letter from the answer
        answer_without_spaces = self.quote.answer.replace(' ', '')
        correct_letter = answer_without_spaces[pos_idx]

        # Find and remove this specific letter from the shuffled supply for this column
        if col < len(self.supply):
            # Search through the supply column to find the matching letter
            # Skip letters that are already used
            for i, supply_letter in enumerate(self.supply[col]):
                # Check if this supply index is already used
                already_used = any(used_col == col and used_idx == i for used_col, used_idx in self.used_supply_indices)
                if not already_used and supply_letter == correct_letter:
                    # Found it! Mark this supply letter as used
                    self.used_supply_indices.append((col, i))
                    break

        self.placed_supply_letters.append(correct_letter)
        self.placed_count += 1
        return True

    def get_total_letters(self) -> int:
        """Get total number of letters to place"""
        return len(self.letter_positions)


class GameplayRenderer:
    """Render EXACT gameplay visuals from Board.tsx"""

    def __init__(self, config: GameConfig = None):
        self.config = config or GameConfig()

    def _calculate_layout(self, state: GameState):
        # Calculate grid dimensions
        grid_width = self.config.GRID_COLS * self.config.CELL_SIZE + (self.config.GRID_COLS - 1) * self.config.GAP
        grid_height = len(state.rows) * self.config.CELL_SIZE + (len(state.rows) - 1) * self.config.GAP

        # Calculate max supply height
        max_supply_height = max(len(col) for col in state.supply) if state.supply else 0
        supply_height = max_supply_height * (self.config.SUPPLY_CELL_SIZE + self.config.SUPPLY_GAP_Y)

        # Total puzzle height (supply + divider + grid)
        total_puzzle_height = supply_height + 20 + grid_height  # 20px for divider + spacing

        # Vertically center the entire puzzle on screen
        puzzle_start_y = (self.config.HEIGHT - total_puzzle_height) // 2

        # Center the grid horizontally - BOTH grid and supply use same x position
        grid_x = (self.config.WIDTH - grid_width) // 2

        # Position grid below supply
        grid_y = puzzle_start_y + supply_height + 20

        # Supply bottom y (letters stack from bottom)
        supply_bottom_y = grid_y - 10

        return grid_x, grid_y, supply_bottom_y, grid_width, grid_height

    def render(self, state: GameState, dissolve_progress: float = 0.0) -> Image.Image:
        """Render a frame of gameplay"""
        img = Image.new('RGB', (self.config.WIDTH, self.config.HEIGHT), self.config.BG)
        draw = ImageDraw.Draw(img, 'RGB')

        grid_x, grid_y, supply_bottom_y, grid_width, grid_height = self._calculate_layout(state)

        # Draw supply area - supply columns align with grid columns
        self._draw_supply(draw, state, grid_x, supply_bottom_y)

        # Draw divider line (border-b border-ink)
        divider_y = supply_bottom_y + 5
        draw.rectangle([grid_x, divider_y, grid_x + grid_width, divider_y + 1],
                      fill=self.config.INK)

        # Draw grid
        self._draw_grid(draw, state, grid_x, grid_y, dissolve_progress)

        # Draw Quotidian wordmark (halfway between grid bottom and screen bottom)
        grid_bottom_y = grid_y + grid_height
        logo_y = (grid_bottom_y + self.config.HEIGHT) // 2
        font = get_font(24, bold=True)
        draw.text((self.config.WIDTH // 2, logo_y), "Quotidian",
                  fill=self.config.STONE_500, font=font, anchor="mm")

        return img

    def render_won(self, state: GameState) -> Image.Image:
        """Render the post-check reveal state (letters only)"""
        img = Image.new('RGB', (self.config.WIDTH, self.config.HEIGHT), self.config.BG)
        draw = ImageDraw.Draw(img, 'RGB')

        grid_x, grid_y, _supply_bottom_y, grid_width, grid_height = self._calculate_layout(state)
        self._draw_won_grid(draw, state, grid_x, grid_y)

        grid_bottom_y = grid_y + grid_height
        logo_y = (grid_bottom_y + self.config.HEIGHT) // 2
        font = get_font(24, bold=True)
        draw.text((self.config.WIDTH // 2, logo_y), "Quotidian",
                  fill=self.config.STONE_500, font=font, anchor="mm")

        return img

    def render_reveal(self, state: GameState, progress: float) -> Image.Image:
        """Crossfade from gameplay grid to the reveal state"""
        progress = max(0.0, min(1.0, progress))
        if progress <= 0.0:
            return self.render(state, dissolve_progress=0.0)
        if progress >= 1.0:
            return self.render_won(state)

        base = self.render(state, dissolve_progress=0.0)
        won = self.render_won(state)
        return Image.blend(base, won, progress)

    def _draw_won_grid(self, draw: ImageDraw.ImageDraw, state: GameState, grid_x: int, grid_y: int):
        letter_font_size = int(self.config.CELL_SIZE * 0.78)
        letter_font = get_font(letter_font_size, family="serif")
        punctuation_font = get_font(int(letter_font_size * 0.85), family="serif")

        def draw_centered(text: str, cell_x: int, cell_y: int, font: ImageFont.FreeTypeFont):
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            text_top_offset = bbox[1]
            draw.text((cell_x + (self.config.CELL_SIZE - text_w) // 2,
                       cell_y + (self.config.CELL_SIZE - text_h) // 2 - text_top_offset),
                      text, fill=self.config.INK, font=font)

        for r, row in enumerate(state.rows):
            for c, char in enumerate(row):
                if char == '#':
                    continue
                cell_x = grid_x + c * (self.config.CELL_SIZE + self.config.GAP)
                cell_y = grid_y + r * (self.config.CELL_SIZE + self.config.GAP)
                draw_centered(char, cell_x, cell_y, letter_font)

        trimmed = state.quote.text.strip()
        if trimmed and trimmed[-1] in {'.', '!', '?'} and state.letter_positions:
            trailing_char = trimmed[-1]
            row, col = state.letter_positions[-1]
            cell_x = grid_x + col * (self.config.CELL_SIZE + self.config.GAP)
            cell_y = grid_y + row * (self.config.CELL_SIZE + self.config.GAP)

            letter_char = state.rows[row][col]
            letter_bbox = draw.textbbox((0, 0), letter_char, font=letter_font)
            letter_w = letter_bbox[2] - letter_bbox[0]
            letter_h = letter_bbox[3] - letter_bbox[1]
            letter_top_offset = letter_bbox[1]
            letter_x = cell_x + (self.config.CELL_SIZE - letter_w) // 2
            letter_y = cell_y + (self.config.CELL_SIZE - letter_h) // 2 - letter_top_offset

            punct_bbox = draw.textbbox((0, 0), trailing_char, font=punctuation_font)
            punct_w = punct_bbox[2] - punct_bbox[0]
            punct_h = punct_bbox[3] - punct_bbox[1]
            punct_x = letter_x + letter_w + int(punct_w * 0.1)
            punct_y = letter_y + letter_h - int(punct_h * 0.85)
            draw.text((punct_x, punct_y), trailing_char, fill=self.config.INK, font=punctuation_font)

    def _draw_supply(self, draw: ImageDraw.ImageDraw, state: GameState, grid_x: int, supply_bottom_y: int):
        """
        Draw supply area - letters stacked from bottom (justify-end).
        KEY: Supply column N aligns with grid column N.
        Letters disappear as they are placed (the specific letter used is removed).
        """
        for col_idx, column in enumerate(state.supply):
            # Calculate x position: grid_x + (column width with gaps up to this column)
            # This ensures supply column aligns exactly with grid column
            col_x = grid_x + col_idx * (self.config.CELL_SIZE + self.config.GAP)

            # Center the supply cell within the grid column
            cell_offset = (self.config.CELL_SIZE - self.config.SUPPLY_CELL_SIZE) // 2
            supply_cell_x = col_x + cell_offset

            # Find which letters in this column are still available (not used)
            available_letters = []
            for i, letter in enumerate(column):
                # Check if this supply letter is used
                is_used = any(used_col == col_idx and used_idx == i for used_col, used_idx in state.used_supply_indices)
                if not is_used:
                    available_letters.append((i, letter))

            # Draw available letters stacked from bottom (justify-end)
            # Reverse so the first element is at the bottom
            for display_idx, (original_idx, letter) in enumerate(reversed(available_letters)):
                # Stack upward from bottom
                letter_y = supply_bottom_y - (display_idx + 1) * (self.config.SUPPLY_CELL_SIZE + self.config.SUPPLY_GAP_Y)

                # Cell background (white like empty cells)
                draw.rectangle([supply_cell_x, letter_y,
                              supply_cell_x + self.config.SUPPLY_CELL_SIZE,
                              letter_y + self.config.SUPPLY_CELL_SIZE],
                              fill=self.config.WHITE)

                # Letter (stone-500 color)
                font = get_font(int(self.config.SUPPLY_CELL_SIZE * 0.72), bold=True)
                bbox = draw.textbbox((0, 0), letter, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                draw.text((supply_cell_x + (self.config.SUPPLY_CELL_SIZE - text_w) // 2,
                         letter_y + (self.config.SUPPLY_CELL_SIZE - text_h) // 2),
                        letter, fill=self.config.STONE_500, font=font)

    def _draw_grid(self, draw: ImageDraw.ImageDraw, state: GameState, grid_x: int, grid_y: int, dissolve_progress: float = 0.0):
        """Draw the puzzle grid with optional dissolve effect"""
        # Calculate full grid dimensions including outer border
        grid_width = self.config.GRID_COLS * self.config.CELL_SIZE + (self.config.GRID_COLS - 1) * self.config.GAP
        grid_height = len(state.rows) * self.config.CELL_SIZE + (len(state.rows) - 1) * self.config.GAP

        # Helper function to interpolate colors
        def lerp_color(c1, c2, t):
            return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

        # Draw grid border/background (stone-400 shows as gaps between cells)
        # When dissolving, this fades to BG (transparent effect)
        border_color = lerp_color(self.config.STONE_400, self.config.BG, dissolve_progress)
        border_x = grid_x - self.config.PADDING
        border_y = grid_y - self.config.PADDING
        border_w = grid_width + self.config.PADDING * 2
        border_h = grid_height + self.config.PADDING * 2

        draw.rectangle([border_x, border_y, border_x + border_w, border_y + border_h],
                      fill=border_color)

        # Draw cells
        for r, row in enumerate(state.rows):
            for c, char in enumerate(row):
                cell_x = grid_x + c * (self.config.CELL_SIZE + self.config.GAP)
                cell_y = grid_y + r * (self.config.CELL_SIZE + self.config.GAP)

                if char == '#':
                    # Block cell - black (bg-ink)
                    # When dissolving, fades to BG (transparent effect)
                    block_color = lerp_color(self.config.INK, self.config.BG, dissolve_progress)
                    draw.rectangle([cell_x, cell_y,
                                  cell_x + self.config.CELL_SIZE,
                                  cell_y + self.config.CELL_SIZE],
                                  fill=block_color)
                elif char in state.quote.PUNCTUATION_MARKS:
                    # Punctuation cell - subdued (bg-stone-100, text-stone-400)
                    draw.rectangle([cell_x, cell_y,
                                  cell_x + self.config.CELL_SIZE,
                                  cell_y + self.config.CELL_SIZE],
                                  fill=self.config.STONE_100)
                    font = get_font(int(self.config.CELL_SIZE * 0.5))
                    bbox = draw.textbbox((0, 0), char, font=font)
                    text_w = bbox[2] - bbox[0]
                    text_h = bbox[3] - bbox[1]
                    # Punctuation is stone-400
                    punctuation_color = (163, 177, 198)  # Approximate stone-400
                    draw.text((cell_x + (self.config.CELL_SIZE - text_w) // 2,
                             cell_y + (self.config.CELL_SIZE - text_h) // 2),
                            char, fill=punctuation_color, font=font)
                else:
                    # Letter cell - white background
                    draw.rectangle([cell_x, cell_y,
                                  cell_x + self.config.CELL_SIZE,
                                  cell_y + self.config.CELL_SIZE],
                                  fill=self.config.WHITE)

                    # Check if this position has a letter placed
                    letter = state.get_letter_at_position(r, c)
                    if letter:
                        font = get_font(int(self.config.CELL_SIZE * 0.72), bold=True)
                        # Use textbbox for accurate bounding box
                        bbox = draw.textbbox((0, 0), letter, font=font)
                        text_w = bbox[2] - bbox[0]
                        text_h = bbox[3] - bbox[1]
                        # Center vertically using the actual text bounding box
                        # textbbox returns (left, top, right, bottom), so we need to account for the top offset
                        text_top_offset = bbox[1]  # Distance from top of bbox to top of actual text
                        draw.text((cell_x + (self.config.CELL_SIZE - text_w) // 2,
                                 cell_y + (self.config.CELL_SIZE - text_h) // 2 - text_top_offset),
                                letter, fill=self.config.INK, font=font)


def render_splash_screen(config: GameConfig) -> Image.Image:
    """Render the splash screen with curtain opening animation"""
    img = Image.new('RGB', (config.WIDTH, config.HEIGHT), (28, 28, 30))  # Dark background
    draw = ImageDraw.Draw(img, 'RGB')

    # Draw "Quotidian" text in center
    font = get_font(120, bold=True)
    text = "Quotidian"
    draw.text((config.WIDTH // 2, config.HEIGHT // 2), text,
              fill=(253, 251, 247), font=font, anchor="mm")

    # Draw the opening curtains (two panels sliding apart)
    # At full open state, curtains are off-screen
    curtain_width = int(config.WIDTH * 0.5)
    curtain_x_left = -curtain_width // 2  # Off-screen to the left
    curtain_x_right = config.WIDTH + curtain_width // 2  # Off-screen to the right

    # Left curtain
    draw.rectangle([curtain_x_left, 0, curtain_x_left + curtain_width + 100, config.HEIGHT],
                  fill=(253, 251, 247))  # Paper color

    # Right curtain
    draw.rectangle([curtain_x_right - curtain_width - 100, 0, curtain_x_right, config.HEIGHT],
                  fill=(253, 251, 247))  # Paper color

    return img


def render_splash_screen_mid_open(config: GameConfig, progress: float) -> Image.Image:
    """
    Render splash screen with curtains partially open.
    progress: 0.0 = closed, 1.0 = fully open
    """
    img = Image.new('RGB', (config.WIDTH, config.HEIGHT), (28, 28, 30))  # Dark background
    draw = ImageDraw.Draw(img, 'RGB')

    # Draw "Quotidian" text in center
    font = get_font(120, bold=True)
    text = "Quotidian"
    draw.text((config.WIDTH // 2, config.HEIGHT // 2), text,
              fill=(253, 251, 247), font=font, anchor="mm")

    # Draw the curtains sliding apart
    curtain_width = int(config.WIDTH * 0.5)
    offset = int(curtain_width * progress)  # How far they've moved

    # Left curtain (slides left)
    curtain_x_left = -offset
    draw.rectangle([curtain_x_left, 0, curtain_x_left + curtain_width, config.HEIGHT],
                  fill=(253, 251, 247))

    # Right curtain (slides right)
    curtain_x_right = config.WIDTH - curtain_width + offset
    draw.rectangle([curtain_x_right, 0, curtain_x_right + curtain_width, config.HEIGHT],
                  fill=(253, 251, 247))

    return img


class ReelGenerator:
    """Generate reel that looks like screen recording of gameplay"""

    def __init__(self):
        self.config = GameConfig()
        self.frames_dir = Path("tmp/frames")
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.tmp_dir = Path("tmp")
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

        # Audio setup
        quotidian_path = Path(__file__).parent.parent / "Quotidian"
        audio_dir = quotidian_path / "public" / "audio"
        self.letter_sfx = audio_dir / "sfx" / "letter_place.mp3"
        self.win_fanfare = audio_dir / "music" / "win_fanfare.mp3"
        self.background_music = audio_dir / "music" / "music.mp3"

    def _get_audio_duration(self, path: Path) -> Optional[float]:
        if not path.exists():
            return None

        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=nokey=1:noprint_wrappers=1",
                    str(path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            duration = result.stdout.strip()
            if duration:
                return float(duration)
        except Exception:
            pass

        try:
            result = subprocess.run(
                ["ffmpeg", "-i", str(path)],
                capture_output=True,
                text=True,
            )
            match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", result.stderr)
            if match:
                hours = int(match.group(1))
                minutes = int(match.group(2))
                seconds = float(match.group(3))
                return (hours * 3600) + (minutes * 60) + seconds
        except Exception:
            pass

        return None

    def generate_video(self, quote: Quote, output_path: str):
        """Generate gameplay reel - balanced timing"""

        state = GameState(quote)
        renderer = GameplayRenderer(self.config)

        # Timing targets
        pause_before_start = 0.2
        max_solve_time = 7.0
        max_time_per_letter = 0.12

        total_letters = len(state.letter_positions)
        if total_letters > 0:
            available = max(0.0, max_solve_time - pause_before_start)
            time_per_letter = min(available / total_letters, max_time_per_letter) if available > 0 else 0.0
        else:
            time_per_letter = 0.0

        solve_duration = pause_before_start + (total_letters * time_per_letter)

        # Reveal phase (dissolve to letters)
        reveal_fade_duration = 1.0
        win_fanfare_duration = self._get_audio_duration(self.win_fanfare)
        if win_fanfare_duration is not None:
            reveal_hold_duration = max(0.0, win_fanfare_duration - reveal_fade_duration)
        else:
            reveal_hold_duration = 1.0

        total_duration = solve_duration + reveal_fade_duration + reveal_hold_duration

        # Calculate frame counts for each phase
        solve_frames = int(solve_duration * self.config.FPS)
        reveal_fade_frames = int(reveal_fade_duration * self.config.FPS)
        reveal_hold_frames = int(reveal_hold_duration * self.config.FPS)

        total_frames = solve_frames + reveal_fade_frames + reveal_hold_frames

        print(f"Generating {total_frames} frames ({total_duration:.1f}s)...")

        frame_offset = 0

        # Phase 1: Generate puzzle frames (letter placement)
        print("  Phase 1: Letter placement...")
        for frame in range(solve_frames):
            time = frame / self.config.FPS

            # Determine how many letters should be placed
            target_placed = 0
            if frame == solve_frames - 1:
                target_placed = total_letters
            elif time > pause_before_start and time_per_letter > 0:
                elapsed = time - pause_before_start
                target_placed = min(total_letters, int(elapsed / time_per_letter))

            # Update state by placing letters from supply (not just setting count)
            while state.placed_count < target_placed:
                if not state.place_next_letter():
                    break  # No more letters to place

            # Render frame (no dissolve yet)
            img = renderer.render(state, dissolve_progress=0.0)
            img.save(self.frames_dir / f"frame{frame:05d}.png")

            if frame % 30 == 0:
                print(f"    Frame {frame}/{solve_frames} ({state.placed_count}/{total_letters} letters)")

        frame_offset += solve_frames
        print(f"  Letter placement complete at frame {frame_offset}")

        # Phase 2: Reveal dissolve (fade to letters-only state)
        print("  Phase 2: Reveal dissolve...")
        for i in range(reveal_fade_frames):
            progress = (i + 1) / max(reveal_fade_frames, 1)
            img = renderer.render_reveal(state, progress=progress)
            img.save(self.frames_dir / f"frame{frame_offset + i:05d}.png")

        frame_offset += reveal_fade_frames
        print(f"  Reveal complete at frame {frame_offset}")

        # Phase 3: Hold reveal briefly
        print("  Phase 3: Hold reveal...")
        for i in range(reveal_hold_frames):
            img = renderer.render_reveal(state, progress=1.0)
            img.save(self.frames_dir / f"frame{frame_offset + i:05d}.png")

        frame_offset += reveal_hold_frames
        print(f"  Total frames: {frame_offset}")

        # Verify frame count matches expected
        actual_frames = len(list(self.frames_dir.glob("frame*.png")))
        print(f"  Actual frames generated: {actual_frames}")

        # Encode with audio
        print("\nEncoding video...")
        # Calculate actual letter count (not including spaces)
        actual_letter_count = len(state.letter_positions)
        self._encode(
            output_path,
            frame_offset / self.config.FPS,
            actual_letter_count,
            time_per_letter,
            pause_before_start,
            solve_duration,
            solve_duration
        )

        # Cleanup
        for f in self.frames_dir.glob("*.png"):
            f.unlink()
        for f in self.tmp_dir.glob("*.wav"):
            f.unlink()

        print(f"✓ Video: {output_path}")
        return output_path

    def _encode(
        self,
        output_path: str,
        duration: float,
        total_letters: int,
        letter_time: float,
        start_delay: float,
        win_delay: float,
        reveal_start: float
    ):
        """Encode video with audio"""
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(self.config.FPS),
            "-i", str(self.frames_dir / "frame%05d.png"),
        ]

        # Add audio files
        audio_inputs = []

        filter_parts = []
        labels = []
        stream_map = ["0:v"]

        input_index = 1

        if self.background_music.exists():
            audio_inputs.append(str(self.background_music))
            if reveal_start > 0:
                fade_end = reveal_start + 1.0
                filter_parts.append(
                    f"[{input_index}:a]volume=1.2,afade=t=out:st={reveal_start:.3f}:d=1.0,atrim=0:{fade_end:.3f}[music]"
                )
            else:
                filter_parts.append(f"[{input_index}:a]volume=1.2[music]")
            labels.append("music")
            input_index += 1

        if self.letter_sfx.exists():
            # Create SFX track with letter timing
            self._create_sfx_track(total_letters, letter_time, start_delay, self.tmp_dir / "sfx.wav")
            audio_inputs.append(str(self.tmp_dir / "sfx.wav"))
            filter_parts.append(f"[{input_index}:a]volume=0.08[sfx]")
            labels.append("sfx")
            input_index += 1

        if self.win_fanfare.exists():
            wav = self.tmp_dir / "win.wav"
            subprocess.run(["ffmpeg", "-y", "-i", str(self.win_fanfare), "-ar", "48000", str(wav)],
                          capture_output=True)
            audio_inputs.append(str(wav))
            delay_ms = max(0, int(win_delay * 1000))
            filter_parts.append(f"[{input_index}:a]adelay={delay_ms}|{delay_ms},volume=0.7[win]")
            labels.append("win")
            input_index += 1

        for audio in audio_inputs:
            cmd.extend(["-i", audio])

        if filter_parts:
            if len(labels) > 1:
                mix_inputs = "".join(f"[{label}]" for label in labels)
                filter_parts.append(f"{mix_inputs}amix=inputs={len(labels)}[aout]")
                stream_map.append("[aout]")
            elif labels:
                stream_map.append(f"[{labels[0]}]")

            cmd.extend(["-filter_complex", ";".join(filter_parts)])
        elif audio_inputs:
            stream_map.append("1:a")

        for s in stream_map:
            cmd.extend(["-map", s])

        cmd.extend([
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-shortest",
            output_path
        ])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            raise RuntimeError("Encoding failed")

    def _create_sfx_track(self, total_letters: int, letter_time: float, start_delay: float, output_path: str):
        """Create SFX track with letter_place.mp3 at each placement"""
        subprocess.run([
            "ffmpeg", "-y", "-i", str(self.letter_sfx),
            "-ar", "48000", str(self.tmp_dir / "letter.wav")
        ], capture_output=True, check=True)

        import wave
        with wave.open(str(self.tmp_dir / "letter.wav"), 'r') as wf:
            sfx_data = wf.readframes(wf.getnframes())
            sfx_audio = np.frombuffer(sfx_data, dtype=np.int16).astype(np.float32) / 32767
            if wf.getnchannels() == 2:
                sfx_audio = sfx_audio.reshape(-1, 2).mean(axis=1)

        # Use actual puzzle timing parameters
        actual_solve_duration = start_delay + (total_letters * letter_time)

        # Add small buffer at end
        duration = actual_solve_duration + 1.0
        samples = int(duration * 48000)
        track = np.zeros(samples, dtype=np.float32)

        # Place SFX at correct timing (matching when letters appear in video)
        for i in range(total_letters):
            click_time = start_delay + (i * letter_time)
            start = int(click_time * 48000)
            end = min(start + len(sfx_audio), samples)
            available = min(len(sfx_audio), end - start)
            if available > 0:
                track[start:start + available] += sfx_audio[:available] * 0.5

        track = np.clip(track, -1, 1)
        track_int16 = (track * 32767).astype(np.int16)

        with wave.open(str(output_path), 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(track_int16.tobytes())


def main():
    print("🎬 Quotidian Reel Generator - Gameplay Style\n")

    library = QuoteLibrary()
    quote = library.get_yesterday_quote()
    print(f"\n📝 #{quote.id}: \"{quote.answer}\"\n")

    generator = ReelGenerator()
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    video_path = output_dir / f"quotidian-reel-{date_str}.mp4"
    generator.generate_video(quote, str(video_path))

    print("\n✨ Done!")


if __name__ == "__main__":
    main()
