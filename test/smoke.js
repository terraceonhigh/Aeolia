#!/usr/bin/env node
/**
 * smoke.js — Headless DOM smoke test runner for Aeolia.
 *
 * Usage:
 *   bun test/smoke.js                         # run default test/actions/boot_strategy.json
 *   bun test/smoke.js test/actions/foo.json    # run a specific action file
 *   bun test/smoke.js --headed                 # visible browser (debug mode)
 *
 * Action file format (JSON array):
 *   [
 *     { "action": "click", "selector": "button", "text": "STRATEGY", "wait": 500 },
 *     { "action": "waitForSelector", "selector": ".some-class", "timeout": 5000 },
 *     { "action": "assert", "selector": "#root", "contains": "AEOLIA" },
 *     { "action": "screenshot", "path": "test/out/step3.png" },
 *     ...
 *   ]
 *
 * Supported actions:
 *   click           — click element matching selector (+ optional text filter)
 *   waitForSelector — wait for selector to appear in DOM
 *   wait            — pause for `ms` milliseconds
 *   assert          — check selector's textContent contains `contains` string
 *   assertNoError   — verify no crash report / console errors accumulated
 *   screenshot      — save screenshot to `path`
 *   type            — type `value` into input matching selector
 *
 * On failure: prints step index, action, error, and all captured console
 * errors/warnings, then exits with code 1.
 */

import puppeteer from 'puppeteer';
import { readFileSync, mkdirSync } from 'fs';
import { dirname, resolve } from 'path';

const args = process.argv.slice(2);
const headed = args.includes('--headed');
const widthArg = args.find(a => a.startsWith('--width='));
const heightArg = args.find(a => a.startsWith('--height='));
const vpWidth = widthArg ? parseInt(widthArg.split('=')[1]) : 1280;
const vpHeight = heightArg ? parseInt(heightArg.split('=')[1]) : 900;
const actionFile = args.find(a => !a.startsWith('--')) || 'test/actions/boot_strategy.json';
const baseUrl = process.env.AEOLIA_URL || 'http://localhost:5175';

// Read action file
let actions;
try {
  actions = JSON.parse(readFileSync(resolve(actionFile), 'utf-8'));
} catch (e) {
  console.error(`Failed to read action file: ${actionFile}\n${e.message}`);
  process.exit(2);
}

console.log(`\x1b[36msmoke\x1b[0m  ${actions.length} actions from ${actionFile}`);
console.log(`\x1b[36msmoke\x1b[0m  target: ${baseUrl}  headed: ${headed}`);

const browser = await puppeteer.launch({
  headless: headed ? false : 'shell',
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});

const page = await browser.newPage();
await page.setViewport({ width: vpWidth, height: vpHeight, deviceScaleFactor: vpWidth <= 500 ? 2 : 1 });

// Capture console errors and uncaught exceptions
const consoleErrors = [];
const pageErrors = [];

page.on('console', msg => {
  if (msg.type() === 'error' || msg.type() === 'warning') {
    consoleErrors.push({ type: msg.type(), text: msg.text() });
  }
});
page.on('pageerror', err => {
  pageErrors.push(err.toString());
});

// Navigate to app
try {
  await page.goto(baseUrl, { waitUntil: 'networkidle0', timeout: 15000 });
} catch (e) {
  console.error(`\x1b[31mFATAL\x1b[0m  Could not load ${baseUrl}: ${e.message}`);
  console.error('Is the dev server running?');
  await browser.close();
  process.exit(2);
}

console.log(`\x1b[32m  OK\x1b[0m  page loaded`);

// Execute actions
let stepIdx = 0;
for (const step of actions) {
  stepIdx++;
  const label = `[${stepIdx}/${actions.length}] ${step.action}`;
  try {
    switch (step.action) {
      case 'click': {
        if (step.text) {
          // Find element by selector + text content
          const clicked = await page.evaluate((sel, txt) => {
            const els = [...document.querySelectorAll(sel)];
            const match = els.find(el => el.textContent.includes(txt));
            if (match) { match.click(); return true; }
            return false;
          }, step.selector, step.text);
          if (!clicked) throw new Error(`No "${step.selector}" with text "${step.text}" found`);
        } else {
          await page.click(step.selector);
        }
        if (step.wait) await new Promise(r => setTimeout(r, step.wait));
        console.log(`\x1b[32m  OK\x1b[0m  ${label} — ${step.selector}${step.text ? ` "${step.text}"` : ''}`);
        break;
      }
      case 'waitForSelector': {
        await page.waitForSelector(step.selector, { timeout: step.timeout || 10000 });
        console.log(`\x1b[32m  OK\x1b[0m  ${label} — ${step.selector}`);
        break;
      }
      case 'wait': {
        await new Promise(r => setTimeout(r, step.ms || 1000));
        console.log(`\x1b[32m  OK\x1b[0m  ${label} — ${step.ms || 1000}ms`);
        break;
      }
      case 'assert': {
        const text = await page.evaluate(sel => {
          const el = document.querySelector(sel);
          return el ? el.textContent : null;
        }, step.selector);
        if (text === null) throw new Error(`Selector "${step.selector}" not found`);
        if (step.contains && !text.includes(step.contains)) {
          throw new Error(`"${step.selector}" text does not contain "${step.contains}"\n  Got: "${text.slice(0, 200)}"`);
        }
        if (step.notContains && text.includes(step.notContains)) {
          throw new Error(`"${step.selector}" text unexpectedly contains "${step.notContains}"`);
        }
        console.log(`\x1b[32m  OK\x1b[0m  ${label} — ${step.selector} ${step.contains ? `contains "${step.contains}"` : 'exists'}`);
        break;
      }
      case 'assertNoError': {
        // Check for React error boundary crash report
        const crashText = await page.evaluate(() => {
          const body = document.body.textContent || '';
          if (body.includes('CRASH REPORT')) {
            return body.slice(body.indexOf('CRASH REPORT'), body.indexOf('CRASH REPORT') + 500);
          }
          return null;
        });
        if (crashText) throw new Error(`Crash report on screen:\n${crashText}`);
        if (pageErrors.length > 0) throw new Error(`Uncaught page errors:\n${pageErrors.join('\n')}`);
        console.log(`\x1b[32m  OK\x1b[0m  ${label} — no errors (${consoleErrors.length} console warnings)`);
        break;
      }
      case 'screenshot': {
        const outPath = resolve(step.path || `test/out/step_${stepIdx}.png`);
        mkdirSync(dirname(outPath), { recursive: true });
        await page.screenshot({ path: outPath, fullPage: step.fullPage || false });
        console.log(`\x1b[32m  OK\x1b[0m  ${label} — ${outPath}`);
        break;
      }
      case 'eval': {
        // Run arbitrary JS in page context — for tricky selectors
        const result = await page.evaluate(step.js);
        if (step.wait) await new Promise(r => setTimeout(r, step.wait));
        console.log(`\x1b[32m  OK\x1b[0m  ${label} — ${step.js.slice(0, 60)}${result !== undefined ? ` → ${JSON.stringify(result).slice(0, 60)}` : ''}`);
        break;
      }
      case 'type': {
        await page.click(step.selector);
        await page.type(step.selector, String(step.value));
        console.log(`\x1b[32m  OK\x1b[0m  ${label} — ${step.selector} "${step.value}"`);
        break;
      }
      default:
        console.warn(`\x1b[33mSKIP\x1b[0m  ${label} — unknown action "${step.action}"`);
    }
  } catch (err) {
    console.error(`\n\x1b[31mFAIL\x1b[0m  ${label}`);
    console.error(`  Action: ${JSON.stringify(step)}`);
    console.error(`  Error:  ${err.message}`);
    if (consoleErrors.length > 0) {
      console.error(`\n  Console errors/warnings (${consoleErrors.length}):`);
      for (const ce of consoleErrors.slice(-10)) {
        console.error(`    [${ce.type}] ${ce.text.slice(0, 200)}`);
      }
    }
    if (pageErrors.length > 0) {
      console.error(`\n  Uncaught page errors (${pageErrors.length}):`);
      for (const pe of pageErrors.slice(-5)) {
        console.error(`    ${pe.slice(0, 300)}`);
      }
    }
    // Take failure screenshot
    const failPath = resolve(`test/out/fail_step_${stepIdx}.png`);
    mkdirSync(dirname(failPath), { recursive: true });
    await page.screenshot({ path: failPath, fullPage: true }).catch(() => {});
    console.error(`  Screenshot: ${failPath}`);

    await browser.close();
    process.exit(1);
  }
}

// Summary
console.log(`\n\x1b[32mPASS\x1b[0m  All ${actions.length} steps completed`);
if (consoleErrors.length > 0) {
  console.log(`\x1b[33mWARN\x1b[0m  ${consoleErrors.length} console warnings accumulated:`);
  for (const ce of consoleErrors.slice(-5)) {
    console.log(`  [${ce.type}] ${ce.text.slice(0, 150)}`);
  }
}

await browser.close();
process.exit(0);
