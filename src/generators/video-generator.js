/**
 * Quotidian Reel Video Generator
 *
 * Specifications:
 * - Resolution: 1080x1920 (9:16)
 * - Frame rate: 30 fps
 * - Codec: H.264
 * - Duration: 6.9-7.6s (target ~7.3s)
 */

import fs from 'fs';
import path from 'path';
import { createCanvas } from 'canvas';
import ffmpeg from 'fluent-ffmpeg';

// Video Configuration
const CONFIG = {
  width: 1080,
  height: 1920,
  fps: 30,
  bgColor: '#0a0a0a',
  gridColor: '#2a2a2a',
  letterColor: '#f5f5f5',
  filledLetterColor: '#ffffff',
  brandColor: '#666666',
  fontFamily: 'Arial, sans-serif',
  safeZone: 0.6, // Central 60% vertical zone
};

// Timeline Configuration (in seconds)
const TIMELINE = {
  letterBankFadeIn: 0.30,
  microBreath: 0.55,
  solveWindow: 3.2,
  transitionDuration: 0.40,
  quoteReveal: 2.60,
  loopReset: 0.40,
};

export class ReelGenerator {
  constructor(options = {}) {
    this.config = { ...CONFIG, ...options };
    this.frames = [];
  }

  /**
   * Calculate timing based on quote length
   * per_letter_delay = solve_window / character_count (clamped 40-120ms)
   */
  calculateLetterTiming(characterCount) {
    const solveWindow = TIMELINE.solveWindow;
    let perLetterDelay = (solveWindow / characterCount) * 1000; // Convert to ms
    perLetterDelay = Math.max(40, Math.min(120, perLetterDelay));
    return perLetterDelay;
  }

  /**
   * Generate frame at specific time
   */
  generateFrame(quote, time, state) {
    const canvas = createCanvas(this.config.width, this.config.height);
    const ctx = canvas.getContext('2d');

    // Background
    ctx.fillStyle = this.config.bgColor;
    ctx.fillRect(0, 0, this.config.width, this.config.height);

    // Determine what to show based on timeline
    const phase = this.getPhase(time);

    switch (phase) {
      case 'initial':
        this.drawInitialState(ctx, quote);
        break;
      case 'letterBankFadeIn':
        this.drawLetterBankFadeIn(ctx, quote, time);
        break;
      case 'microBreath':
        this.drawMicroBreath(ctx, quote, time);
        break;
      case 'autoSolve':
        this.drawAutoSolve(ctx, quote, time, state);
        break;
      case 'transition':
        this.drawTransition(ctx, quote, time);
        break;
      case 'quoteReveal':
        this.drawQuoteReveal(ctx, quote, time);
        break;
      case 'loopReset':
        this.drawLoopReset(ctx, quote, time);
        break;
    }

    return canvas;
  }

  /**
   * Determine current phase based on time
   */
  getPhase(time) {
    const letterBankFadeEnd = TIMELINE.letterBankFadeIn;
    const microBreathEnd = TIMELINE.microBreath;
    const autoSolveEnd = microBreathEnd + TIMELINE.solveWindow;
    const transitionEnd = autoSolveEnd + TIMELINE.transitionDuration;
    const quoteRevealEnd = transitionEnd + TIMELINE.quoteReveal;

    if (time < letterBankFadeEnd) return 'letterBankFadeIn';
    if (time < microBreathEnd) return 'microBreath';
    if (time < autoSolveEnd) return 'autoSolve';
    if (time < transitionEnd) return 'transition';
    if (time < quoteRevealEnd) return 'quoteReveal';
    return 'loopReset';
  }

  /**
   * Draw initial state (0.00s) - Grid visible, blank slots, no letter bank
   */
  drawInitialState(ctx, quote) {
    const { width, height, gridColor, safeZone } = this.config;

    // Calculate grid positioning (centered in safe 60% vertical zone)
    const safeHeight = height * safeZone;
    const safeTop = (height - safeHeight) / 2;

    // Draw puzzle grid with blank slots
    this.drawGrid(ctx, quote, width / 2, safeTop + safeHeight / 2);
  }

  /**
   * Draw letter bank fade in (0.00-0.30s)
   */
  drawLetterBankFadeIn(ctx, quote, time) {
    this.drawInitialState(ctx, quote);

    // Fade in letter bank
    const progress = Math.min(1, time / TIMELINE.letterBankFadeIn);
    this.drawLetterBank(ctx, quote, progress);
  }

  /**
   * Draw micro-breath phase (0.30-0.55s)
   */
  drawMicroBreath(ctx, quote, time) {
    const relativeTime = time - TIMELINE.microBreath;

    // Gentle float motion (1% scale or less)
    const floatAmount = Math.sin(relativeTime * 2) * 0.005;
    this.drawGrid(ctx, quote, this.config.width / 2, this.config.height / 2, 1 + floatAmount);
    this.drawLetterBank(ctx, quote, 1);
  }

  /**
   * Draw auto-solve phase (0.55-3.80s)
   */
  drawAutoSolve(ctx, quote, time, state) {
    const relativeTime = time - TIMELINE.microBreath;
    const letterDelay = this.calculateLetterTiming(quote.answer.length);
    const lettersPlaced = Math.floor(relativeTime / (letterDelay / 1000));

    this.drawGrid(ctx, quote, this.config.width / 2, this.config.height / 2, 1, lettersPlaced);
    this.drawLetterBank(ctx, quote, 1);
  }

  /**
   * Draw transition phase (~3.80-4.20s)
   */
  drawTransition(ctx, quote, time) {
    const relativeTime = time - (TIMELINE.microBreath + TIMELINE.solveWindow);
    const progress = Math.min(1, relativeTime / TIMELINE.transitionDuration);

    // Grid fades out, quote fades in
    this.drawGrid(ctx, quote, this.config.width / 2, this.config.height / 2, 1, quote.answer.length, 1 - progress);

    // Quote starts fading in
    this.drawQuote(ctx, quote, progress);
  }

  /**
   * Draw quote reveal phase (4.20-6.80s)
   */
  drawQuoteReveal(ctx, quote, time) {
    const relativeTime = time - (TIMELINE.microBreath + TIMELINE.solveWindow + TIMELINE.transitionDuration);
    const progress = Math.min(1, relativeTime / 0.5); // Fast fade in

    this.drawQuote(ctx, quote, 1);
    this.drawBrandMark(ctx, quote, progress);
  }

  /**
   * Draw loop reset phase (6.80-7.20s)
   */
  drawLoopReset(ctx, quote, time) {
    const relativeTime = time - (
      TIMELINE.microBreath +
      TIMELINE.solveWindow +
      TIMELINE.transitionDuration +
      TIMELINE.quoteReveal
    );
    const progress = Math.min(1, relativeTime / TIMELINE.loopReset);

    // Cross-dissolve: quote fades out, grid fades in
    this.drawQuote(ctx, quote, 1 - progress);
    this.drawGrid(ctx, quote, this.config.width / 2, this.config.height / 2, 1, 0, progress);
  }

  /**
   * Draw the puzzle grid
   */
  drawGrid(ctx, quote, centerX, centerY, scale = 1, filledCount = 0, opacity = 1) {
    ctx.save();
    ctx.globalAlpha = opacity;
    ctx.translate(centerX, centerY);
    ctx.scale(scale, scale);

    // Calculate grid dimensions based on quote length
    const slots = quote.slots || this.createSlots(quote.answer);
    const slotSize = 60;
    const gap = 12;
    const gridWidth = slots.length * (slotSize + gap) - gap;
    const startX = -gridWidth / 2;
    const startY = 0;

    // Draw slots
    slots.forEach((slot, index) => {
      const x = startX + index * (slotSize + gap);

      // Slot background
      ctx.strokeStyle = this.config.gridColor;
      ctx.lineWidth = 2;
      ctx.strokeRect(x - slotSize / 2, startY - slotSize / 2, slotSize, slotSize);

      // Letter if filled
      if (index < filledCount) {
        ctx.fillStyle = this.config.filledLetterColor;
        ctx.font = `bold 36px ${this.config.fontFamily}`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(quote.answer[index], x, startY);
      }
    });

    ctx.restore();
  }

  /**
   * Draw letter bank
   */
  drawLetterBank(ctx, quote, opacity) {
    ctx.save();
    ctx.globalAlpha = opacity;

    const letters = this.shuffleLetters(quote.answer);
    const letterSize = 50;
    const gap = 10;
    const bankWidth = letters.length * (letterSize + gap) - gap;
    const startX = (this.config.width - bankWidth) / 2;
    const startY = this.config.height * 0.75;

    ctx.font = `bold 32px ${this.config.fontFamily}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    letters.forEach((letter, index) => {
      const x = startX + index * (letterSize + gap) + letterSize / 2;
      ctx.fillStyle = this.config.letterColor;
      ctx.fillText(letter, x, startY);
    });

    ctx.restore();
  }

  /**
   * Draw the revealed quote
   */
  drawQuote(ctx, quote, opacity) {
    ctx.save();
    ctx.globalAlpha = opacity;

    const centerX = this.config.width / 2;
    const centerY = this.config.height / 2;

    ctx.fillStyle = this.config.filledLetterColor;
    ctx.font = `bold 42px ${this.config.fontFamily}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    // Wrap text if needed
    const maxWidth = this.config.width * 0.8;
    const lines = this.wrapText(ctx, quote.answer, maxWidth);

    const lineHeight = 56;
    const totalHeight = lines.length * lineHeight;
    const startY = centerY - totalHeight / 2;

    lines.forEach((line, index) => {
      ctx.fillText(line.trim(), centerX, startY + index * lineHeight);
    });

    ctx.restore();
  }

  /**
   * Draw subtle brand mark
   */
  drawBrandMark(ctx, quote, opacity) {
    ctx.save();
    ctx.globalAlpha = opacity * 0.5;

    const fontSize = 28;
    ctx.font = `${fontSize}px ${this.config.fontFamily}`;
    ctx.fillStyle = this.config.brandColor;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';

    ctx.fillText('Quotidian', this.config.width / 2, this.config.height - 100);

    ctx.restore();
  }

  /**
   * Helper: Wrap text to fit width
   */
  wrapText(ctx, text, maxWidth) {
    const words = text.split(' ');
    const lines = [];
    let currentLine = '';

    words.forEach(word => {
      const testLine = currentLine + (currentLine ? ' ' : '') + word;
      const metrics = ctx.measureText(testLine);

      if (metrics.width > maxWidth && currentLine) {
        lines.push(currentLine);
        currentLine = word;
      } else {
        currentLine = testLine;
      }
    });

    if (currentLine) lines.push(currentLine);
    return lines;
  }

  /**
   * Helper: Create slots array from answer
   */
  createSlots(answer) {
    return answer.split('').map(char => ({ letter: char, filled: false }));
  }

  /**
   * Helper: Shuffle letters for bank
   */
  shuffleLetters(answer) {
    const letters = answer.split('');
    // Fisher-Yates shuffle
    for (let i = letters.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [letters[i], letters[j]] = [letters[j], letters[i]];
    }
    return letters;
  }

  /**
   * Generate complete reel video
   */
  async generate(quote, outputPath) {
    const totalDuration =
      TIMELINE.microBreath +
      TIMELINE.solveWindow +
      TIMELINE.transitionDuration +
      TIMELINE.quoteReveal +
      TIMELINE.loopReset;

    const totalFrames = Math.floor(totalDuration * this.config.fps);
    const frameDir = path.join('tmp', `frames-${Date.now()}`);
    fs.mkdirSync(frameDir, { recursive: true });

    console.log(`Generating ${totalFrames} frames...`);

    for (let frame = 0; frame < totalFrames; frame++) {
      const time = frame / this.config.fps;
      const canvas = this.generateFrame(quote, time, {});
      const framePath = path.join(frameDir, `frame${frame.toString().padStart(5, '0')}.png`);
      const buffer = canvas.toBuffer('image/png');
      fs.writeFileSync(framePath, buffer);

      if (frame % 30 === 0) {
        console.log(`  Frame ${frame}/${totalFrames}`);
      }
    }

    console.log('Encoding video...');
    await this.encodeVideo(frameDir, outputPath, totalDuration);

    // Cleanup
    fs.rmSync(frameDir, { recursive: true, force: true });

    console.log(`✓ Video generated: ${outputPath}`);
    return outputPath;
  }

  /**
   * Encode video from frames using ffmpeg
   */
  async encodeVideo(frameDir, outputPath, duration) {
    return new Promise((resolve, reject) => {
      ffmpeg()
        .input(path.join(frameDir, 'frame%05d.png'))
        .inputFPS(this.config.fps)
        .videoCodec('libx264')
        .size(`${this.config.width}x${this.config.height}`)
        .outputOptions([
          '-preset slow',
          '-crf 18',
          '-pix_fmt yuv420p',
          '-tune film',
        ])
        .audioCodec('aac')
        .audioFrequency(48000)
        .outputOptions('-shortest')
        .on('end', () => resolve())
        .on('error', (err) => reject(err))
        .save(outputPath);
    });
  }

  /**
   * Generate cover image
   */
  async generateCover(quote, outputPath) {
    const canvas = createCanvas(this.config.width, this.config.height);
    const ctx = canvas.getContext('2d');

    // Background
    ctx.fillStyle = this.config.bgColor;
    ctx.fillRect(0, 0, this.config.width, this.config.height);

    // Faint grid lines
    ctx.save();
    ctx.globalAlpha = 0.05;
    this.drawGrid(ctx, quote, this.config.width / 2, this.config.height / 2);
    ctx.restore();

    // Quote
    this.drawQuote(ctx, quote, 1);

    // Brand mark
    this.drawBrandMark(ctx, quote, 1);

    // Save
    const buffer = canvas.toBuffer('image/png');
    fs.writeFileSync(outputPath, buffer);

    console.log(`✓ Cover generated: ${outputPath}`);
    return outputPath;
  }
}
