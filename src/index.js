/**
 * Quotidian Reel Generator - Main Entry Point
 *
 * Automated Instagram Reel generation for daily puzzles
 */

import { ReelGenerator } from './generators/video-generator.js';
import fs from 'fs';
import path from 'path';

// Sample quote for testing
const sampleQuote = {
  id: '2024-01-15',
  answer: 'Most people didnt',
  author: '',
  slots: null, // Will be auto-generated
};

async function main() {
  console.log('🎬 Quotidian Reel Generator\n');

  const generator = new ReelGenerator();
  const outputDir = 'output';
  fs.mkdirSync(outputDir, { recursive: true });

  const date = new Date().toISOString().split('T')[0];

  // Generate video
  const videoPath = path.join(outputDir, `quotidian-reel-${date}.mp4`);
  await generator.generate(sampleQuote, videoPath);

  // Generate cover
  const coverPath = path.join(outputDir, `quotidian-cover-${date}.png`);
  await generator.generateCover(sampleQuote, coverPath);

  console.log('\n✨ Done!');
}

main().catch(console.error);
