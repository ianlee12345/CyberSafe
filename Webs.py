"""Serve the local Cyber Sleuth training arcade and optional LAN race rooms."""

import json
import os
from contextlib import closing
import hashlib
import random
import secrets
from pathlib import Path
import sqlite3
import socket
import threading
import time
from urllib.parse import parse_qs, urlparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))
QUESTION_HISTORY = Path(__file__).with_name("cyber-safe-question-history.sqlite3")
SCENARIO_IDS = [
    "delivery",
    "bank",
    "voice",
    "support",
    "job",
    "romance",
    "ceo",
    "code",
    "library",
    "clinic",
    "coworker",
    "codehelp",
]
ROOMS: dict[str, dict] = {}
ROOM_LOCK = threading.Lock()

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0A0A0C"><title>Cyber Safe — Cyber Sleuth Academy</title>
<style>
:root {
  color-scheme: dark;
  --bg: #0A0A0C;
  --panel: #16171B;
  --panel-raised: #1D1F24;
  --line: #2A2C33;
  --silver: #B8BCC6;
  --ink: #E6E8EE;
  --muted: #8A8F9C;
  --danger: #FF5C6C;
  --success: #4ADE80;
  --warning: #FFC857;
  --halo: rgba(184,188,198,.11);
  --finish-start: var(--muted);
  --finish-end: var(--ink);
  --finish-edge: var(--line);
  --shadow: 0 18px 48px rgba(0,0,0,.22);
}
* { box-sizing: border-box; }
[hidden], .hidden { display: none !important; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
.svg-defs { position: absolute; width: 0; height: 0; overflow: hidden; }
html { scrollbar-color: #555963 var(--bg); }
body { margin: 0; min-height: 100vh; background: var(--bg); color: var(--silver); font: 15px/1.6 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }
body[data-theme="sunset"] { --halo: rgba(255,200,87,.13); --finish-end: var(--warning); --finish-edge: #725B2A; }
body[data-theme="ice"] { --halo: rgba(184,188,198,.22); --finish-start: var(--silver); --finish-edge: var(--muted); }
h1, h2, h3, strong { color: var(--ink); }
button, input { font: inherit; }
button { min-height: 44px; min-width: 44px; cursor: pointer; color: inherit; transition: background-color .18s ease, border-color .18s ease, color .18s ease, transform .18s ease, box-shadow .18s ease; }
button:focus-visible, input:focus-visible { outline: 3px solid var(--warning); outline-offset: 3px; }
main:focus { outline: none; }
button:active:not(:disabled) { transform: translateY(1px); }
button:disabled { cursor: not-allowed; }
.top { position: sticky; top: 0; z-index: 5; padding: 14px clamp(18px,4vw,48px) 13px; background: rgba(10,10,12,.96); border-bottom: 1px solid var(--line); backdrop-filter: blur(18px); }
.toprow, .xpwrap { max-width: 1400px; margin: auto; }
.toprow { display: flex; align-items: center; gap: 24px; }
.brand { display: flex; align-items: center; gap: 11px; color: var(--ink); font-weight: 900; line-height: 1.1; letter-spacing: .13em; white-space: nowrap; }
.logo { width: 46px; height: 46px; flex: 0 0 46px; display: grid; place-items: center; border: 1px solid var(--finish-edge); border-radius: 13px; background: var(--panel); }
.lock-svg { display: block; width: 100%; height: 100%; }
.logo .lock-svg { width: 31px; height: 31px; }
.brand-name span, .splash-brand h1 span { color: var(--silver); }
.brand small { display: block; margin-top: 5px; color: var(--muted); font-weight: 700; font-size: 9px; letter-spacing: .15em; }
.stats { margin-left: auto; display: flex; align-items: center; flex-wrap: wrap; justify-content: flex-end; gap: 8px; font-size: 12px; }
.header-actions { display: flex; align-items: center; gap: 8px; }
.toggle-short { display: none; }
.agent-block { display: grid; gap: 1px; min-width: 0; padding: 0 12px; }
.stat-label { color: var(--muted); font-size: 10px; font-weight: 800; letter-spacing: .09em; line-height: 1.2; text-transform: uppercase; }
.agent-name { max-width: 16ch; overflow-wrap: anywhere; color: var(--ink); font-weight: 800; line-height: 1.3; }
.rankchip, .header-stat { display: flex; align-items: center; gap: 8px; min-height: 44px; border-left: 1px solid var(--line); padding: 0 11px; }
.rankchip strong, .header-stat strong { display: block; color: var(--ink); line-height: 1.2; white-space: nowrap; }
.header-stat { gap: 6px; }
.header-stat .stat-icon { color: var(--silver); font-size: 16px; }
.rankbadge { width: 38px; height: 38px; flex: 0 0 38px; display: grid; place-items: center; }
.rankbadge svg { display: block; width: 36px; height: 36px; overflow: visible; }
.xpwrap { margin-top: 12px; display: grid; grid-template-columns: auto minmax(0,1fr) auto; gap: 12px; align-items: center; color: var(--muted); font-size: 11px; font-weight: 700; }
.xpbar, .meter { height: 6px; border-radius: 99px; background: var(--line); overflow: hidden; }
.xpbar span, .meter span { height: 100%; display: block; width: 0; border-radius: inherit; background: linear-gradient(90deg,var(--finish-start),var(--finish-end)); transition: width .55s ease; }
.layout { max-width: 1400px; margin: 28px auto; padding: 0 clamp(18px,4vw,48px); display: grid; grid-template-columns: 205px minmax(0,1fr); gap: 26px; }
.side { display: grid; align-content: start; gap: 5px; position: sticky; top: 120px; height: max-content; }
.nav-label { padding: 5px 12px 9px; color: var(--muted); font-size: 10px; font-weight: 900; letter-spacing: .14em; }
.navbtn { position: relative; display: flex; align-items: center; gap: 10px; background: transparent; border: 1px solid transparent; text-align: left; padding: 10px 12px; border-radius: 10px; color: var(--silver); font-weight: 700; }
.nav-icon { display: grid; place-items: center; width: 22px; height: 22px; flex: 0 0 22px; color: var(--muted); font-size: 17px; }
.navbtn:hover, .navbtn.active { color: var(--ink); background: var(--panel); border-color: var(--line); }
.navbtn.active:before { content: ""; position: absolute; left: -1px; top: 10px; bottom: 10px; width: 3px; border-radius: 4px; background: var(--ink); }
.navbtn.active .nav-icon { color: var(--ink); }
.side-note { margin-top: 20px; padding: 16px 13px; border: 1px solid var(--line); border-radius: 13px; background: var(--panel); color: var(--muted); font-size: 12px; }
.side-note strong { display: block; margin-bottom: 6px; font-size: 11px; letter-spacing: .08em; }
main { min-width: 0; overflow-wrap: anywhere; }
main.screen-enter { animation: screen-in .3s ease both; }
.eyebrow { color: var(--silver); font-size: 10px; font-weight: 900; letter-spacing: .16em; text-transform: uppercase; }
.hero { position: relative; display: grid; grid-template-columns: minmax(0,1.2fr) minmax(200px,.8fr); gap: 20px; align-items: center; min-height: 355px; overflow: hidden; border: 1px solid var(--line); border-radius: 20px; padding: clamp(24px,4vw,46px); background: radial-gradient(circle at 79% 45%,var(--halo),transparent 34%),var(--panel); box-shadow: var(--shadow); }
.hero:before { content: ""; position: absolute; inset: 0; opacity: .14; background-image: linear-gradient(#B8BCC6 1px,transparent 1px),linear-gradient(90deg,#B8BCC6 1px,transparent 1px); background-size: 44px 44px; mask-image: linear-gradient(90deg,transparent 30%,#000 100%); pointer-events: none; }
.hero-copy, .hero-art { position: relative; z-index: 1; }
.hero-kicker { display: inline-flex; align-items: center; gap: 8px; padding: 6px 10px; border: 1px solid #3B3D45; border-radius: 99px; background: rgba(10,10,12,.45); }
.status-dot { width: 7px; height: 7px; flex: 0 0 7px; border-radius: 50%; background: var(--silver); box-shadow: 0 0 10px rgba(184,188,198,.45); }
.greeting { margin: 20px 0 0; color: var(--silver); font-size: 14px; font-weight: 700; }
.hero h1 { max-width: 660px; margin: 9px 0 16px; color: var(--ink); font-size: clamp(39px,5.6vw,66px); line-height: 1.03; letter-spacing: -.055em; }
.hero h1 em { color: var(--silver); font-style: normal; }
.hero-description { max-width: 580px; margin: 0; color: var(--silver); font-size: 15px; }
.hero-note { display: flex; flex-wrap: wrap; gap: 7px 15px; margin-top: 21px; color: var(--muted); font-size: 11px; font-weight: 700; }
.hero-note span { display: inline-flex; align-items: center; gap: 6px; }
.hero-note b { color: var(--silver); }
.hero-art { display: grid; justify-items: center; gap: 13px; }
.radar { position: relative; width: min(100%,245px); aspect-ratio: 1; display: grid; place-items: center; border: 1px solid #3B3D45; border-radius: 50%; background: radial-gradient(circle,rgba(184,188,198,.09),transparent 65%); box-shadow: inset 0 0 45px rgba(0,0,0,.22),0 0 60px var(--halo); }
.radar:before, .radar:after { content: ""; position: absolute; border: 1px solid #3B3D45; border-radius: 50%; }
.radar:before { inset: 15%; }
.radar:after { inset: 30%; }
.radar-cross { position: absolute; inset: 0; background: linear-gradient(90deg,transparent calc(50% - .5px),#3B3D45 50%,transparent calc(50% + .5px)),linear-gradient(transparent calc(50% - .5px),#3B3D45 50%,transparent calc(50% + .5px)); opacity: .7; border-radius: 50%; }
.radar-lock { z-index: 1; width: 86px; height: 86px; display: grid; place-items: center; border: 1px solid #3B3D45; border-radius: 24px; background: var(--panel); box-shadow: 0 14px 40px rgba(0,0,0,.5); }
.radar-lock .lock-svg { width: 62px; height: 62px; }
.hero-art-label { color: var(--muted); font-size: 10px; font-weight: 800; letter-spacing: .16em; text-align: center; }
.actions { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; margin-top: 22px; }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; border: 1px solid var(--ink); border-radius: 10px; background: var(--ink); color: var(--bg); padding: 10px 16px; font-weight: 800; line-height: 1.3; }
.btn:hover:not(:disabled) { background: #fff; border-color: #fff; box-shadow: 0 7px 22px rgba(184,188,198,.16); transform: translateY(-1px); }
.btn.alt { background: transparent; color: var(--ink); border-color: #555963; }
.btn.alt:hover:not(:disabled) { background: var(--panel-raised); border-color: var(--silver); }
.btn.danger { background: #2A181D; color: var(--danger); border-color: #82404A; }
.btn.danger:hover:not(:disabled) { background: #3A2027; border-color: var(--danger); }
.btn.small { padding: 8px 13px; font-size: 12px; }
.btn:disabled { background: var(--panel-raised); color: var(--muted); border-color: var(--line); box-shadow: none; }
.btn.correct:disabled { border-color: var(--success); background: #14251B; color: var(--ink); }
.btn.wrong:disabled { border-color: var(--danger); background: #2A181D; color: var(--ink); }
.grid { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 12px; margin: 14px 0; }
.card, .zonecard, .gamecard { border: 1px solid var(--line); background: var(--panel); border-radius: 15px; padding: 19px; box-shadow: var(--shadow); }
.card { min-height: 140px; }
.metric-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.metric-icon { color: var(--muted); font-size: 18px; }
.card h3 { margin: 12px 0 4px; font-size: 21px; line-height: 1.2; letter-spacing: -.02em; }
.card p, .muted { color: var(--muted); font-size: 13px; margin: 0; }
.field-note { display: flex; align-items: center; gap: 14px; margin: 14px 0; padding: 16px 18px; border: 1px solid var(--line); border-radius: 14px; background: #111216; }
.field-note-icon { display: grid; place-items: center; width: 42px; height: 42px; flex: 0 0 42px; border: 1px solid var(--line); border-radius: 12px; color: var(--ink); font-size: 19px; }
.field-note strong { display: block; margin: 2px 0; }
.field-note p { color: var(--muted); font-size: 12px; margin: 0; }
.sectionhead { margin: 32px 0 14px; display: flex; justify-content: space-between; align-items: end; gap: 12px; }
.sectionhead h2 { margin: 3px 0 0; font-size: 22px; letter-spacing: -.02em; }
.zones { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 12px; }
.muted + .zones { margin-top: 20px; }
.zonecard { position: relative; display: flex; flex-direction: column; min-width: 0; transition: border-color .2s ease, transform .2s ease; }
.zonecard:not(.locked):hover { border-color: #60636C; transform: translateY(-2px); }
.zonecard.locked { background: #111216; box-shadow: none; }
.zonecard h3 { margin: 17px 0 4px; font-size: 18px; }
.zonecard p { margin: 0 0 15px; color: var(--muted); font-size: 13px; }
.zone-top, .zone-identity { display: flex; align-items: center; gap: 10px; }
.zone-top { justify-content: space-between; }
.zone-icon { display: grid; place-items: center; width: 42px; height: 42px; flex: 0 0 42px; border: 1px solid var(--line); border-radius: 12px; background: var(--panel-raised); color: var(--silver); font-size: 20px; }
.zone-index { color: var(--muted); font-size: 10px; font-weight: 900; letter-spacing: .12em; white-space: nowrap; }
.zone-status { display: inline-flex; align-items: center; gap: 6px; color: var(--success); font-size: 10px; font-weight: 900; letter-spacing: .07em; }
.zone-status:before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.locked .zone-status { color: var(--muted); }
.zone-details { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: auto; }
.stars { color: var(--warning); letter-spacing: 3px; white-space: nowrap; }
.stars .off { color: var(--muted); }
.pill { font-size: 11px; font-weight: 700; border: 1px solid var(--line); border-radius: 99px; padding: 4px 9px; color: var(--silver); }
.zonecard .actions { margin-top: 17px; padding-top: 16px; border-top: 1px solid var(--line); }
.screen-title { color: var(--ink); font-size: clamp(28px,4vw,38px); line-height: 1.1; letter-spacing: -.04em; margin: 6px 0 12px; }
.gamecard { padding: clamp(20px,4vw,34px); margin-top: 14px; }
.gamehead { display: flex; justify-content: space-between; align-items: center; color: var(--silver); font-size: 12px; font-weight: 800; letter-spacing: .04em; gap: 12px; }
.timer { color: var(--warning); background: #282117; border: 1px solid #725B2A; border-radius: 9px; padding: 7px 11px; font-weight: 900; white-space: nowrap; }
.timer.low { color: var(--warning); background: #352A18; border-color: var(--warning); box-shadow: 0 0 0 2px rgba(255,200,87,.14); }
.meter { margin-top: 12px; }
.message { margin: 20px 0; padding: 18px; border: 1px solid var(--line); background: #101115; border-radius: 14px; }
.message.text, .message.chat { max-width: 93%; border-radius: 16px 16px 16px 4px; background: #1D1F24; }
.message.email { border-radius: 10px; background: #101115; }
.message.call { border-radius: 14px; border-left: 4px solid var(--silver); }
.message.screen { border-radius: 10px; border-top: 4px solid var(--danger); }
.sender { padding-bottom: 10px; border-bottom: 1px solid var(--line); color: var(--silver); font-size: 11px; font-weight: 900; letter-spacing: .08em; }
.prompt { color: var(--ink); font-size: clamp(17px,2.4vw,21px); line-height: 1.5; margin: 14px 0 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.question-prompt { margin: 22px 0 0; color: var(--ink); font-size: clamp(18px,2.4vw,22px); line-height: 1.35; letter-spacing: -.02em; }
.answers { display: grid; gap: 9px; margin-top: 15px; }
.answer { display: flex; align-items: center; gap: 12px; width: 100%; border: 1px solid #3B3D45; background: #111216; color: var(--ink); padding: 14px 15px; border-radius: 10px; text-align: left; overflow-wrap: anywhere; }
.answer:hover:not(:disabled) { border-color: var(--silver); background: var(--panel-raised); }
.answer.correct, .btn.correct { border-color: var(--success); background: #14251B; color: var(--ink); }
.answer.wrong, .btn.wrong { border-color: var(--danger); background: #2A181D; color: var(--ink); }
.choice-icon { display: grid; place-items: center; width: 28px; height: 28px; flex: 0 0 28px; border: 1px solid currentColor; border-radius: 8px; font-weight: 900; }
.choice-icon.scam, .verdict.scam { color: var(--danger); }
.choice-icon.safe, .verdict.safe { color: var(--success); }
.feedback { border-left: 4px solid var(--success); background: #112119; padding: 16px; margin-top: 16px; border-radius: 0 10px 10px 0; animation: correct-pulse .65s ease; }
.feedback.bad { border-color: var(--danger); background: #29171C; animation: soft-shake .35s ease; }
.feedback > b { display: block; margin-bottom: 5px; color: var(--success); }
.feedback.bad > b { color: var(--danger); }
.feedback p { margin: 6px 0; color: var(--silver); font-size: 13px; }
.flags { display: flex; gap: 8px; flex-wrap: wrap; margin: 15px 0; }
.flag { border: 1px dashed #626671; background: #111216; padding: 9px 12px; border-radius: 9px; color: var(--silver); }
.flag:hover:not(:disabled) { border-color: var(--silver); background: var(--panel-raised); }
.flag.selected { border: 1px solid var(--warning); background: #282117; color: var(--ink); }
.row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.combo { color: var(--silver); font-weight: 800; font-size: 13px; }
.box { border: 1px solid var(--line); background: var(--panel); padding: 18px; border-radius: 14px; margin: 12px 0; }
.list { display: grid; gap: 10px; }
.listrow { display: flex; justify-content: space-between; align-items: center; gap: 14px; }
.badge { font-size: 22px; }
.shopitem { display: grid; grid-template-columns: auto minmax(0,1fr) auto; gap: 12px; align-items: center; }
.toast { position: fixed; z-index: 20; bottom: 22px; left: 50%; width: max-content; max-width: calc(100vw - 30px); transform: translateX(-50%); border: 1px solid #555963; border-radius: 12px; padding: 12px 18px; background: var(--panel-raised); color: var(--ink); box-shadow: var(--shadow); animation: toast-in .3s; }
.overlay { position: fixed; inset: 0; z-index: 7; background: rgba(0,0,0,.78); display: grid; place-items: center; padding: 15px; }
.modal, .progress-modal { width: min(520px,100%); max-height: 92vh; overflow: auto; background: var(--panel); border: 1px solid #555963; border-radius: 20px; padding: clamp(20px,4vw,32px); box-shadow: 0 25px 80px rgba(0,0,0,.65); text-align: center; }
.modal h2 { font-size: 32px; margin: 7px; }
.confetti { position: fixed; top: -15px; width: 8px; height: 13px; z-index: 9; pointer-events: none; animation: fall 2.8s linear forwards; }
.toggle { background: var(--panel); border: 1px solid var(--line); border-radius: 9px; padding: 8px 11px; font-size: 11px; font-weight: 800; color: var(--ink); }
.toggle:hover { background: var(--panel-raised); border-color: #626671; }
.footer { padding: 30px 0 10px; color: var(--muted); font-size: 11px; text-align: center; }
.progress-modal { width: min(920px,100%); text-align: left; }
.progress-modal-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 15px; }
.progress-modal h2 { font-size: clamp(27px,4vw,38px); line-height: 1.05; margin: 5px 0; }
.progress-modal .close { border: 1px solid #555963; border-radius: 50%; background: var(--panel-raised); color: var(--ink); font-size: 22px; }
.journey-summary { display: grid; grid-template-columns: auto minmax(0,1fr) auto; align-items: center; gap: 14px; padding: 15px; margin: 18px 0; background: #101115; border: 1px solid var(--line); border-radius: 15px; }
.journey-summary .rankbadge { width: 50px; height: 50px; flex-basis: 50px; }
.journey-summary .rankbadge svg { width: 48px; height: 48px; }
.journey-percent { color: var(--ink); font-size: 24px; font-weight: 900; }
.journey-track { height: 9px; background: var(--line); border-radius: 20px; overflow: hidden; margin: 8px 0; }
.journey-track span { display: block; height: 100%; border-radius: 20px; background: linear-gradient(90deg,var(--muted),var(--ink)); transition: width .5s; }
.journey-ends { display: flex; justify-content: space-between; gap: 10px; color: var(--muted); font-size: 11px; font-weight: 800; }
.rank-road { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 11px; }
.rank-stop { background: #101115; border: 1px solid var(--line); border-radius: 14px; padding: 12px; min-width: 0; }
.rank-stop.done { background: var(--panel-raised); }
.rank-stop.active { border: 2px solid var(--silver); box-shadow: 0 7px 22px rgba(0,0,0,.24); }
.rank-stop.future { background: #111216; }
.rank-stop-head { display: flex; align-items: center; gap: 8px; margin-bottom: 7px; }
.rank-stop-head .rankbadge { width: 34px; height: 34px; flex-basis: 34px; }
.rank-stop-head .rankbadge svg { width: 32px; height: 32px; }
.rank-stop-head strong { display: block; font-size: 13px; line-height: 1.1; }
.rank-stop-head small { display: block; color: var(--muted); font-size: 10px; margin-top: 3px; }
.rank-tiers { display: grid; grid-template-columns: repeat(3,1fr); gap: 5px; }
.rank-tier { border: 1px solid var(--line); background: var(--panel); border-radius: 8px; text-align: center; padding: 5px 2px; font-size: 10px; color: var(--silver); font-weight: 800; }
.rank-tier.done { background: var(--panel-raised); color: var(--ink); }
.rank-tier.active { background: var(--ink); border-color: var(--ink); color: var(--bg); }
.journey-hint { font-size: 12px; color: var(--muted); margin: 14px 2px 0; }
.launch { position: fixed; inset: 0; z-index: 10; display: grid; place-items: center; padding: 24px; background: radial-gradient(circle at 50% 40%,rgba(184,188,198,.08),transparent 42%),var(--bg); overflow: auto; }
.launch-stage { width: min(560px,100%); text-align: center; }
.splash-brand { animation: splash-in .7s ease both; }
.splash-logo { position: relative; width: 112px; height: 112px; margin: 0 auto 23px; border: 1px solid var(--line); border-radius: 28px; display: grid; place-items: center; background: var(--panel); overflow: hidden; box-shadow: 0 18px 50px rgba(0,0,0,.5),0 0 50px rgba(184,188,198,.07); }
.splash-logo .lock-svg { width: 76px; height: 76px; }
.splash-logo:after { content: ""; position: absolute; inset: -50%; background: linear-gradient(110deg,transparent 42%,rgba(230,232,238,.15) 50%,transparent 58%); animation: sweep 1.6s ease .4s both; }
.splash-brand h1 { color: var(--ink); font-size: clamp(29px,6vw,42px); letter-spacing: .14em; margin: 0; }
.splash-brand p { color: var(--muted); font-size: 10px; letter-spacing: .25em; font-weight: 800; }
.launch.leaving .splash-brand { animation: fade-out .35s ease forwards; }
.boot-panel { text-align: left; border: 1px solid #3B3D45; border-radius: 18px; padding: clamp(22px,5vw,32px); background: var(--panel); box-shadow: var(--shadow); animation: screen-in .3s ease both; }
.boot-title { color: var(--ink); font-weight: 900; letter-spacing: .12em; font-size: 12px; }
.boot-lines { min-height: 160px; margin: 18px 0; color: var(--silver); font: 13px/1.7 ui-monospace, Consolas, monospace; overflow-wrap: anywhere; }
.boot-line:before { content: "> "; color: var(--muted); font-weight: 900; }
.boot-progress { margin: 14px 0 0; }
.skip { position: fixed; top: 20px; right: 20px; }
.codename-card { text-align: left; border: 1px solid var(--line); border-radius: 20px; background: var(--panel); padding: clamp(24px,6vw,38px); box-shadow: var(--shadow); animation: screen-in .3s ease both; }
.codename-card h1 { margin: 8px 0 12px; font-size: clamp(27px,5vw,36px); line-height: 1.15; letter-spacing: -.03em; }
.codename-form label { display: block; margin: 20px 0 6px; color: var(--ink); font-weight: 800; }
.codename-form input { width: 100%; min-height: 48px; border: 1px solid #626671; border-radius: 10px; padding: 10px 12px; background: #101115; color: var(--ink); }
.input-meta { display: flex; justify-content: space-between; gap: 10px; margin-top: 5px; color: var(--muted); font-size: 12px; }
.form-error { min-height: 1.5em; margin: 7px 0 0; color: var(--danger); font-weight: 700; font-size: 13px; }
main.screen-enter :is(.hero, .card, .field-note, .zonecard, .gamecard, .list > .box) { animation: element-in .48s cubic-bezier(.2,.7,.2,1) backwards; }
main.screen-enter :is(.grid, .zones, .list) > :nth-child(2) { animation-delay: .05s; }
main.screen-enter :is(.grid, .zones, .list) > :nth-child(3) { animation-delay: .1s; }
main.screen-enter :is(.grid, .zones, .list) > :nth-child(n+4) { animation-delay: .15s; }
main.screen-enter :is(.message, .answers, .flags) { animation: element-in .4s ease .08s backwards; }
.overlay { animation: overlay-in .2s ease backwards; }
.modal, .progress-modal { animation: modal-in .35s cubic-bezier(.2,.7,.2,1) backwards; }
.radar-cross { animation: radar-turn 18s linear infinite; }
.radar-lock { animation: lock-float 5s ease-in-out infinite; }
.status-dot { animation: status-glow 3s ease-in-out infinite; }
.nav-icon { transition: transform .18s ease, color .18s ease; }
.navbtn:hover .nav-icon, .navbtn:focus-visible .nav-icon { transform: translateX(3px); }
.answer:hover:not(:disabled), .flag:hover:not(:disabled) { transform: translateX(3px); }
.timer.low { animation: timer-glow 2s ease-in-out infinite; }
@keyframes element-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
@keyframes overlay-in { from { opacity: 0; } to { opacity: 1; } }
@keyframes modal-in { from { opacity: 0; transform: translateY(12px) scale(.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
@keyframes radar-turn { to { transform: rotate(360deg); } }
@keyframes lock-float { 50% { transform: translateY(-5px); } }
@keyframes status-glow { 50% { box-shadow: 0 0 15px rgba(184,188,198,.75); } }
@keyframes timer-glow { 50% { box-shadow: 0 0 0 4px rgba(255,200,87,.2); } }
@keyframes splash-in { from { opacity: 0; transform: scale(.9); } to { opacity: 1; transform: scale(1); } }
@keyframes sweep { from { transform: translateX(-75%); } to { transform: translateX(75%); } }
@keyframes fade-out { to { opacity: 0; transform: scale(.97); } }
@keyframes screen-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
@keyframes correct-pulse { 50% { box-shadow: 0 0 0 5px rgba(74,222,128,.18); } }
@keyframes soft-shake { 25%,75% { transform: translateX(-4px); } 50% { transform: translateX(4px); } }
@keyframes fall { to { transform: translateY(110vh) rotate(800deg); opacity: .8; } }
@keyframes toast-in { from { transform: translate(-50%,10px); opacity: 0; } to { transform: translate(-50%,0); opacity: 1; } }
@media (max-width: 1050px) {
  .toprow { flex-wrap: wrap; gap: 12px 18px; }
  .stats { margin-left: 0; justify-content: flex-start; }
}
@media (max-width: 850px) {
  .top { position: static; }
  .brand { order: 0; }
  .header-actions { order: 1; margin-left: auto; }
  .stats { order: 2; width: 100%; }
  .layout { display: block; margin-top: 18px; }
  .side { position: static; display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 6px; margin-bottom: 20px; }
  .navbtn { justify-content: center; padding: 8px; font-size: 12px; }
  .navbtn.active:before { left: 10px; right: 10px; top: auto; bottom: -1px; width: auto; height: 3px; }
  .nav-label, .side-note { display: none; }
}
@media (max-width: 700px) {
  .rank-road { grid-template-columns: repeat(2,minmax(0,1fr)); }
  .journey-summary { grid-template-columns: auto minmax(0,1fr); }
  .journey-percent { grid-column: 2; font-size: 18px; }
  .grid { grid-template-columns: 1fr; }
  .card { min-height: 0; }
  .hero { grid-template-columns: minmax(0,1fr) minmax(130px,.55fr); }
  .radar-lock { width: 68px; height: 68px; border-radius: 19px; }
  .radar-lock .lock-svg { width: 50px; height: 50px; }
}
@media (max-width: 480px) {
  .top { padding: 14px 18px; }
  .brand { gap: 8px; font-size: 12px; letter-spacing: .1em; }
  .brand small { font-size: 8px; letter-spacing: .11em; }
  .logo { width: 42px; height: 42px; flex-basis: 42px; }
  .header-actions { gap: 5px; }
  .toggle-long { display: none; }
  .toggle-short { display: inline; }
  .header-actions .toggle { padding: 8px; }
  .stats { display: grid; grid-template-columns: repeat(6,minmax(0,1fr)); gap: 3px 6px; }
  .agent-block, .rankchip { grid-column: span 3; }
  .header-stat { grid-column: span 2; }
  .agent-block { padding-left: 0; }
  .rankchip, .header-stat { padding: 0 7px; }
  .header-stat:nth-child(3) { border-left: 0; padding-left: 0; }
  .header-stat .stat-icon { display: none; }
  .side { grid-template-columns: repeat(2,minmax(0,1fr)); }
  .navbtn { justify-content: flex-start; gap: 8px; padding: 8px 10px; font-size: 12px; }
  .hero { display: block; min-height: 0; }
  .hero-art { display: none; }
  .hero h1 { font-size: clamp(38px,10vw,50px); }
  .zones { grid-template-columns: 1fr; }
  .shopitem { grid-template-columns: auto minmax(0,1fr); }
  .shopitem button { grid-column: 2; justify-self: start; }
  .message.text, .message.chat { max-width: 100%; }
  .skip { top: 12px; right: 12px; }
}
@media (prefers-reduced-motion: reduce) {
  *, *:before, *:after { animation-duration: .01ms !important; animation-delay: 0s !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; scroll-behavior: auto !important; }
}
.mp-players{display:grid;gap:8px;margin:14px 0}.mp-player{display:grid;grid-template-columns:1fr auto;align-items:center;gap:4px 12px;padding:12px;border:1px solid var(--line);border-radius:11px;background:#f8fbf9}.mp-player small{color:var(--muted)}.mp-player strong{color:var(--ink)}.mp-player .mp-score{grid-row:1/3;grid-column:2;font-weight:900;color:var(--cyan);font-size:20px}.mp-join{display:flex;gap:9px;flex-wrap:wrap;margin:14px 0}.mp-join input{flex:1;min-width:140px;padding:10px 12px;border:1px solid #bfd1c8;border-radius:9px;color:#183431;background:white}.mp-code{font-size:24px;letter-spacing:.18em;font-weight:900;color:#176b61}.mp-race-timer{font-size:22px;font-weight:900;color:#956318}.mp-question{padding:14px;background:#f5f8f6;border:1px solid var(--line);border-radius:12px;margin:12px 0;white-space:pre-wrap;color:var(--ink)}
:root{--cyan:var(--silver)}.mp-lobby-hero{display:block;min-height:auto}.mp-player{background:var(--panel);border-color:var(--line)}.mp-player small{color:var(--muted)}.mp-player strong{color:var(--ink)}.mp-player .mp-score{color:var(--silver)}.mp-join input{color:var(--ink);background:var(--panel-raised);border-color:var(--line)}.mp-code{color:var(--silver)}.mp-race-timer{color:var(--warning)}.mp-question{background:var(--panel-raised);border-color:var(--line);color:var(--ink)}</style></head><body>
<svg class="svg-defs" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="lock-silver" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="#E6E8EE"/><stop offset="1" stop-color="#8A8F9C"/>
    </linearGradient>
    <symbol id="padlock-mark" viewBox="0 0 96 96">
      <path d="M27 44V32a21 21 0 0 1 42 0v12" fill="none" stroke="url(#lock-silver)" stroke-width="9"/>
      <rect x="15" y="42" width="66" height="45" rx="12" fill="#16171B" stroke="url(#lock-silver)" stroke-width="3.5"/>
      <circle cx="48" cy="61" r="7" fill="#4BE4EF"/><path d="M45 65h6l2 13H43z" fill="#4BE4EF"/>
    </symbol>
  </defs>
</svg>
<div id="launch" class="launch">
  <div class="launch-stage" id="splashStage"><div class="splash-brand"><div class="splash-logo" aria-hidden="true"><svg class="lock-svg" viewBox="0 0 96 96"><use href="#padlock-mark"></use></svg></div><h1>CYBER <span>SAFE</span></h1><p>CYBER SLEUTH ACADEMY</p></div></div>
  <div class="launch-stage boot-panel" id="bootStage" hidden><div class="boot-title">CYBER SAFE · BOOT SEQUENCE</div><div id="bootLines" class="boot-lines" aria-hidden="true"></div><div id="bootProgress" class="xpbar boot-progress" role="progressbar" aria-label="Boot progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><span id="bootFill"></span></div></div>
  <button class="btn alt skip" id="skipLaunch" type="button">Skip</button>
</div>
<div id="app" hidden>
<header class="top">
  <div class="toprow">
    <div class="brand"><div class="logo" aria-hidden="true"><svg class="lock-svg" viewBox="0 0 96 96"><use href="#padlock-mark"></use></svg></div><div class="brand-name">CYBER <span>SAFE</span><small>CYBER SLEUTH ACADEMY</small></div></div>
    <div class="stats">
      <div class="agent-block"><span class="stat-label">Agent</span><span class="agent-name" id="agentName"></span></div>
      <div class="rankchip"><span class="rankbadge" id="rankIcon" role="img"></span><div><span class="stat-label">Rank</span><strong id="rankName">Bronze</strong></div></div>
      <div class="header-stat"><div><span class="stat-label">Level</span><strong id="level">1</strong></div></div>
      <div class="header-stat"><span class="stat-icon" aria-hidden="true">◆</span><div><span class="stat-label">Credits</span><strong id="coins">0</strong></div></div>
      <div class="header-stat"><span class="stat-icon" aria-hidden="true">↗</span><div><span class="stat-label">Streak</span><strong id="streak">0</strong></div></div>
    </div>
    <div class="header-actions">
      <button class="toggle" id="progressButton" aria-haspopup="dialog" aria-label="Your Progress" onclick="showCareerProgress()"><span class="toggle-long">Your Progress</span><span class="toggle-short" aria-hidden="true">Progress</span></button>
      <button class="toggle" id="mute" aria-label="Toggle sound"><span class="toggle-long" id="soundLabel">Sound on</span><span class="toggle-short" id="soundShort" aria-hidden="true">♪ On</span></button>
    </div>
  </div>
  <div class="xpwrap"><span id="xpLabel">0 XP</span><div class="xpbar" role="progressbar" aria-label="Level XP" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><span id="xpFill"></span></div><span id="xpNext">100 XP</span></div>
</header>
<div class="layout"><nav class="side" aria-label="Game menu">
  <div class="nav-label">YOUR CONSOLE</div>
  <button class="navbtn active" data-view="home"><span class="nav-icon" aria-hidden="true">⌂</span> Base</button>
  <button class="navbtn" data-view="multiplayer"><span class="nav-icon" aria-hidden="true">⚡</span> Race</button>
  <button class="navbtn" data-view="pc"><span class="nav-icon" aria-hidden="true">▣</span> PC Mode</button>
  <button class="navbtn" data-view="zones"><span class="nav-icon" aria-hidden="true">▦</span> Zones</button>
  <button class="navbtn" data-view="guide"><span class="nav-icon" aria-hidden="true">▤</span> Field Guide</button>
  <button class="navbtn" data-view="achievements"><span class="nav-icon" aria-hidden="true">★</span> Achievements</button>
  <button class="navbtn" data-view="shop"><span class="nav-icon" aria-hidden="true">✦</span> Cosmetic Lab</button>
  <button class="navbtn" data-view="settings"><span class="nav-icon" aria-hidden="true">⚙</span> Settings</button>
  <div class="side-note"><strong>TRAIN WITH CONFIDENCE</strong>Every scenario is fictional. Every practice helps sharpen your instincts.</div>
</nav><main id="main" tabindex="-1"></main></div><div id="modalRoot"></div></div><div id="live" aria-live="polite" aria-atomic="true" class="sr-only"></div>
<script>
const SCENARIOS=[
{id:'delivery',type:'Delivery fee',kind:'text',content:'ParcelPal: We missed you. Pay $1.35 redelivery fee now to release your package: parcel-pal.example.test/track',isScam:true,flags:['Unexpected fee','Look-alike domain','Urgency around a parcel'],why:'A tiny fee feels harmless, and a familiar delivery story catches you while you are busy.',do:'Do not tap. Check delivery status in the carrier’s official app or a website you type yourself.'},
{id:'bank',type:'Bank alert',kind:'message',content:'From: Northstar Bank <alerts@northstar-secure.example.test>\nURGENT: Account frozen. Verify your password at northstar-verify.example.test within 10 minutes or lose access.',isScam:true,flags:['Threat of account loss','Look-alike sender/domain','Password request'],why:'Fear and a short deadline make people act before checking who sent the message.',do:'Do not use the link or share a password. Call the bank using the number on your card or open its official app.'},
{id:'voice',type:'AI voice-clone call',kind:'call',content:'A caller who sounds like your nephew says: “I’m in trouble and need you to send help right now. Please don’t tell anyone yet.”',isScam:true,flags:['Urgent emotional request','Secrecy','Voice alone is treated as proof'],why:'A familiar voice and fear can bypass careful thinking. Voice cloning can imitate people.',do:'Hang up and call them or another family member on a number you already know. Agree on a family safe word.'},
{id:'support',type:'Tech support pop-up',kind:'screen',content:'SYSTEM WARNING: 12 viruses found! Call 1-800-555-0142 immediately. Do not close this window or your files will be deleted.',isScam:true,flags:['Scary pop-up claim','Pressure to call','Unrequested support number'],why:'Alarming warnings make people seek help from the very number the pop-up supplies.',do:'Do not call or install anything. Close the tab or browser; use your device’s trusted support channel.'},
{id:'job',type:'Job offer',kind:'message',content:'Congratulations! You are hired as a remote product tester. Deposit this check, buy equipment from our vendor, and send the leftover funds back. No interview needed!',isScam:true,flags:['Pay money to get a job','Send back part of a check','Unusually easy hiring'],why:'A hopeful opportunity and a seemingly available balance can hide a fake check that later bounces.',do:'Never send money back or pay to unlock a job. Verify the employer through independently found contact details.'},
{id:'romance',type:'Romance-investment pitch',kind:'chat',content:'“I feel so close to you ❤️ I can show you a private investment app where I made 40% this week. Start small and I’ll guide you. Keep it between us.”',isScam:true,flags:['Romance mixed with investing','Secret/private app','Guaranteed-sounding returns'],why:'Trust and affection can make a financial pitch feel like personal advice.',do:'Do not send money or identity documents. Talk it through with someone you trust and verify any firm independently.'},
{id:'ceo',type:'CEO invoice fraud',kind:'email',content:'From: Chief Executive\nSubject: Confidential — pay this revised vendor invoice today. I’m in meetings; skip the usual callback and keep this between us.',isScam:true,flags:['Bypasses normal process','Secrecy','Unexpected payment change'],why:'Authority, urgency, and confidentiality can pressure staff to skip routine safeguards.',do:'Verify payment changes with a known contact using the normal approval process. Never rely on the email thread alone.'},
{id:'code',type:'Unrequested verification code',kind:'text',content:'Your Starling Games sign-in code is 481903. We will never ask you to share this code. Didn’t request it? Secure your account in the official app.',isScam:true,flags:['Unexpected one-time code','Someone may be attempting sign-in','Code must stay private'],why:'A real code can arrive because someone else triggered a login. A follow-up may try to trick you into sharing it.',do:'Never share the code. Open the official app directly, change your password if needed, and enable multifactor authentication.'},
{id:'library',type:'Legitimate library notice',kind:'email',content:'From: reminders@maple-library.example.test\nYour library book is due Friday. See the title and due date in your account by opening the library app you already use. No action is needed today.',isScam:false,flags:[],why:'It is specific, low pressure, and points you toward an app you already use rather than demanding credentials.',do:'If unsure, check the due date in your known library app or ask the library using its published contact details.'},
{id:'clinic',type:'Legitimate appointment reminder',kind:'text',content:'Pine Street Clinic: Reminder — your appointment is Tuesday at 2:30 p.m. Reply C to confirm or call our usual office number to reschedule. We will not ask for payment by text.',isScam:false,flags:[],why:'A routine reminder can be legitimate. The useful habit is to verify through an established channel if anything feels off.',do:'Check your calendar or the clinic portal you normally use. Do not assume every unexpected message is fraudulent.'},
{id:'coworker',type:'Legitimate coworker request',kind:'chat',content:'“Hey, can you review the Q3 slide deck when you have a moment? It’s in the shared team folder. No rush — I’ll be online this afternoon.”',isScam:false,flags:[],why:'A familiar, ordinary request with no unusual pressure. Still, check the file and sender if anything about it seems unexpected.',do:'Use the team’s normal shared folder and ask the coworker through your usual channel if uncertain.'},
{id:'codehelp',type:'Legitimate security notice',kind:'email',content:'From: security@maple-mail.example.test\nWe noticed a sign-in from a new device. If this was you, no action is needed. Review recent activity from the security section inside the mail app.',isScam:false,flags:[],why:'It does not ask you to reply, disclose a code, or use a supplied link. It directs you to check inside the app.',do:'Open the app directly and review activity. If you see something unfamiliar, change your password there.'}
];
const ZONES=[{name:'Inbox Alley',icon:'✉',desc:'Messages that want a little too much.',boss:'The Fee Phantom',ids:['delivery','library','code']},{name:'Trustfall Boulevard',icon:'♡',desc:'Familiar voices, unfamiliar requests.',boss:'The Mimic',ids:['voice','romance','coworker']},{name:'Pop-up Panic Plaza',icon:'▣',desc:'Alarms, alerts, and account bait.',boss:'Captain Clickbait',ids:['support','bank','codehelp']},{name:'Opportunity Outpost',icon:'✦',desc:'Offers that sound too good to be true.',boss:'The Check Shuffler',ids:['job','romance','library']},{name:'Executive Grid',icon:'⌘',desc:'Payment requests under pressure.',boss:'The Invoice Impostor',ids:['ceo','bank','coworker']}];
const RANKS=[['Bronze',1,7,'#B8BCC6'],['Silver',8,14,'#E6E8EE'],['Gold',15,21,'#B8BCC6'],['Diamond',22,28,'#E6E8EE'],['Platinum',29,35,'#B8BCC6'],['Onyx',36,42,'#E6E8EE'],['Champion',43,50,'#E6E8EE']];
const REWARDS=[{id:'visor',name:'Neon Visor',icon:'🥽',cost:70,desc:'See the signal in style.'},{id:'drone',name:'Pocket Drone',icon:'🛸',cost:110,desc:'Your tiny airborne hype agent.'},{id:'fox',name:'Pixel Fox',icon:'🦊',cost:150,desc:'A clever companion for clever agents.'},{id:'theme_sunset',name:'Afterglow Theme',icon:'🌇',cost:90,desc:'A warm amber sheen for your console.'},{id:'theme_ice',name:'Icewire Theme',icon:'🧊',cost:90,desc:'A bright silver finish for your console.'}];
const DEFAULT={username:'',xp:0,coins:0,answered:0,correct:0,combo:0,bestCombo:0,streak:0,lastDay:'',unlocked:1,stars:[0,0,0,0,0],seen:[],achievements:[],owned:[],equipped:'',theme:'default',sound:true,rounds:0,sessionStart:Date.now(),longNudge:false,missed:[],pcUser:'',pcNotes:'',pcWallpaper:'mint',pcCalcValue:'0',pcCalcAcc:null,pcCalcOp:null,pcCalcFresh:false,pcVideoIndex:0,pcVideoPlaying:false,pcVideoPage:'home',pcVideoSearch:'',pcVideoSubscribed:false,pcChatContact:'Mika',pcChatHistory:[],pcBrowserPage:'home',pcSearchQuery:'',pcDrillAnswers:{},pcAdDismissed:false,pcAdSafe:null};
function freshState(){return {...DEFAULT,stars:[...DEFAULT.stars],seen:[],achievements:[],owned:[],missed:[],pcChatHistory:[],pcDrillAnswers:{},sessionStart:Date.now()}}
function load(){
  try{return {...freshState(),...JSON.parse(localStorage.getItem('signalsafe-save')||'{}')}}
  catch(error){console.warn('Could not read saved progress:',error);setTimeout(()=>toast('Saved progress could not be read in this browser.'),0);return freshState()}
}
let S=load(),round=null,roundTimer=null,nowQ=null,answered=false,view='home',huntPicked=[];
let questionRequest=null,modeDeck=[],lastMode='';
let pcClockTimer=null,pcStartOpen=false,pcLoadingTimer=null,pcAppLoadTimer=null,pcAppLoading=false,pcWindowLayout='partial',pcDragState=null;
let mpRoom='',mpPlayer='',mpData=null,mpPoll=null,mpRaceTimer=null,mpRenderedIndex=-1,mpServerOffset=0,mpScenarioCache={},mpPendingIndex=-1;
const $=s=>document.querySelector(s),main=$('#main');
function choose(items){return items[Math.floor(Math.random()*items.length)]}
function randomInt(min,max){return min+Math.floor(Math.random()*(max-min+1))}
function shuffle(items){let result=[...items];for(let i=result.length-1;i>0;i--){let j=Math.floor(Math.random()*(i+1));[result[i],result[j]]=[result[j],result[i]]}return result}
function nextMode(){
  if(!modeDeck.length){
    modeDeck=shuffle(['real','hunt','url','response']);
    if(modeDeck[modeDeck.length-1]===lastMode)[modeDeck[0],modeDeck[modeDeck.length-1]]=[modeDeck[modeDeck.length-1],modeDeck[0]];
  }
  return lastMode=modeDeck.pop();
}
function scenarioVariation(source){
  const fee=`$${(randomInt(100,999)/100).toFixed(2)}`;
  const amount=`$${randomInt(50,5000)}`;
  const deadline=`${randomInt(5,120)} minutes`;
  const day=choose(['Monday','Tuesday','Wednesday','Thursday','Friday']);
  const date=`${choose(['January','February','March','April','May','June','July','August','September','October','November','December'])} ${randomInt(1,28)}`;
  const time=`${randomInt(8,11)}:${choose(['00','15','30','45'])} a.m.`;
  const code=String(randomInt(100000,999999));
  const person=choose(['Ari','Bea','Cleo','Dara','Emery','Finn','Gio','Harper','Indigo','Jules','Kai','Lane','Milo','Nico','Ollie','Perry']);
  const topic=choose(['onboarding','workshop','planning','research','design','training','outreach','budget','volunteer','project','meeting','event']);
  const deck=`${topic} ${choose(['slides','notes','documents','materials','plans','summaries'])}`;
  const book=`The ${choose(['Amber','Bright','Clever','Distant','Emerald','Friendly','Golden','Hidden','Ivory','Jade','Kind','Little','Misty','Quiet','Silver','Secret'])} ${choose(['Atlas','Beacon','Bridge','Compass','Dream','Forest','Garden','Harbor','Island','Journey','Key','Lantern','Map','River','Signal','Voyage'])}`;
  const relative=choose(['nephew','cousin','grandchild','sibling']);
  const reason=choose(['unusual sign-in','security review','access check','new device','account review','safety alert']);
  const account=String(randomInt(0,9999)).padStart(4,'0');
  const phone=`1-800-555-${randomInt(100,199).toString().padStart(4,'0')}`;
  const viruses=randomInt(3,30);
  const role=choose(['product tester','data reviewer','remote assistant','catalog reviewer','equipment coordinator','online researcher']);
  const equipment=choose(['a laptop','a headset','office supplies','a tablet','a monitor','a work kit']);
  const returnRate=`${randomInt(15,80)}%`;
  const investment=choose(['Moonvault','Starvault','Silver Grove','Bright Peak','Quiet Harbor','Misty Ridge']);
  const investmentPeriod=choose(['this week','this month','over the weekend','by next week','within a month','in just days']);
  const invoice=choose(['office supplies','software','training materials','event services','equipment','design work','storage','shipping']);
  const appointment=choose(['checkup','consultation','follow-up','routine visit','office visit','scheduled visit']);
  const device=choose(['tablet','laptop','desktop','phone','browser','shared computer','home computer','mobile device']);
  const templates={
    delivery:[
      `ParcelPal: Your ${day} delivery is on hold. Pay a ${fee} redelivery fee now at parcel-pal.example.test/track to release your package.`,
      `ParcelPal notice: We missed your ${day} delivery. To avoid a return, pay ${fee} immediately at parcel-pal.example.test/track.`,
      `A parcel update says a ${fee} fee is due right away for a ${day} delivery. Visit parcel-pal.example.test/track to schedule another delivery.`
    ],
    bank:[
      `From: Northstar Bank <alerts@northstar-secure.example.test>\nAccount ending ${account} is frozen after a ${reason}. Verify your password at northstar-verify.example.test within ${deadline} or lose access.`,
      `Northstar Bank alert: After a ${reason}, access to account ending ${account} will be disabled in ${deadline}. Enter your password now at northstar-verify.example.test.`,
      `From: alerts@northstar-secure.example.test\nFollowing a ${reason}, account ending ${account} will close unless you submit your password at northstar-verify.example.test within ${deadline}.`
    ],
    voice:[
      `A caller who sounds like your ${relative} ${person} leaves a voicemail: “I'm in trouble. Send ${amount} right now, and please don't tell anyone.”`,
      `A voice like your ${relative} ${person}'s says: “I need ${amount} urgently. Keep this secret and don't call anyone else.”`,
      `Someone sounding like your ${relative} ${person} begs for ${amount} immediately and asks you to keep the request between you.`
    ],
    support:[
      `SYSTEM WARNING: ${viruses} viruses found on your ${device}! Call ${phone} immediately. Do not close this window or your files will be deleted.`,
      `SECURITY ALERT: ${viruses} infections found on your ${device}. Call ${phone} now and leave this window open or your files may be erased.`,
      `A pop-up claims ${viruses} viruses on your ${device} threaten your files. It demands an immediate call to ${phone} and warns you not to close it.`
    ],
    job:[
      `You are hired as a remote ${role} without an interview! Deposit our ${amount} check, buy ${equipment} from our vendor, and send the leftover money back.`,
      `Job offer for a ${role}: No interview needed. Deposit a ${amount} check, buy ${equipment} from our chosen vendor, and return the remaining funds.`,
      `A message promises easy remote work as a ${role}. First deposit its ${amount} check, buy ${equipment} from its vendor, and send back the unused amount.`
    ],
    romance:[
      `“I feel so close to you. My private ${investment} app guarantees ${returnRate} ${investmentPeriod}. Start with a transfer, and keep it between us.”`,
      `Someone you've grown close to recommends the secret ${investment} investment app with guaranteed ${returnRate} profits ${investmentPeriod} and asks you to send money without telling anyone.`,
      `“I trust you, so I'll share my private ${investment} app. A ${returnRate} return is guaranteed ${investmentPeriod} if you transfer money today. Please keep this secret.”`
    ],
    ceo:[
      `From: Chief Executive\nConfidential — pay this revised ${amount} invoice for ${invoice} today. I'm in meetings; skip the usual callback and tell no one.`,
      `A message claims to be from the chief executive: “Pay the changed ${amount} vendor invoice for ${invoice} immediately. Skip approval and keep it confidential.”`,
      `An invoice request appears to come from the chief executive. It demands ${amount} for ${invoice} to revised payment details today, without the normal callback or discussion.`
    ],
    code:[
      `Your Starling Games sign-in code is ${code}. We will never ask you to share it. Didn't request this? Secure your account in the official app.`,
      `Starling Games verification: Your code is ${code}. Don't share this code. If you did not sign in, open the official app to secure your account.`,
      `An unexpected Starling Games code arrives: ${code}. The message says not to share it and to use the official app if you did not request it.`
    ],
    library:[
      `From: reminders@maple-library.example.test\nYour book "${book}" is due ${date}. Check the title in the library app you already use. No action is needed today.`,
      `Maple Library reminder: "${book}" is due ${date}. You can review it in your usual library app; there is no urgent action.`,
      `A library email reminds you that "${book}" is due ${date}. It suggests opening the library app you know, with no request for credentials.`
    ],
    clinic:[
      `Pine Street Clinic reminder: Your ${appointment} is ${date} at ${time}. Reply C to confirm or call our usual office number. We won't ask for payment by text.`,
      `Appointment reminder: Pine Street Clinic has your ${appointment} scheduled for ${date} at ${time}. Use the usual office number to reschedule; no text payment is requested.`,
      `A routine clinic message reminds you of a ${appointment} on ${date} at ${time}. It asks for no payment and offers the usual office number for changes.`
    ],
    coworker:[
      `Your coworker ${person} writes: “Could you review the ${deck} for ${day} in our shared folder when you have a moment? No rush.”`,
      `${person} writes in your team chat: “The ${deck} for ${day} are in our usual folder. Please take a look whenever you have time.”`,
      `Your coworker ${person} asks: “When you're free, could you check the ${deck} for ${day}? They're in the normal shared team folder. Thanks!”`
    ],
    codehelp:[
      `From: security@maple-mail.example.test\nA new ${device} signed in on ${date} at ${time}. If this was you, no action is needed. Review activity in your mail app.`,
      `Maple Mail security notice: A sign-in from a new ${device} was recorded on ${date} at ${time}. Check activity in your usual app; no reply or code is requested.`,
      `An email reports a new ${device} sign-in on ${date} at ${time} and suggests checking the security section inside your mail app. It asks for no password or verification code.`
    ]
  };
  if(!templates[source.id])throw new Error(`No scenario variations for ${source.id}`);
  return {...source,content:choose(templates[source.id])};
}
async function claimScenario(source,signal){
  for(let attempt=0;attempt<64;attempt++){
    const scenario=scenarioVariation(source);
    const response=await fetch('/claim-question',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:scenario.content}),signal});
    if(!response.ok)throw new Error(`The local question history is unavailable (HTTP ${response.status}).`);
    const result=await response.json();
    if(result.used===true)continue;
    if(!Number.isSafeInteger(result.reference)||result.reference<1)throw new Error('Invalid question reference');
    return {...scenario,reference:result.reference};
  }
  throw new Error('Could not find an unused example for this topic. Try another zone or check back later.');
}
function persist(){
  try{localStorage.setItem('signalsafe-save',JSON.stringify(S));return true}
  catch(error){console.warn('Could not save progress:',error);toast('This browser could not save progress.');return false}
}
function level(){return Math.min(50,Math.floor(S.xp/100)+1)}function rankIndex(){for(let i=RANKS.length-1;i>=0;i--)if(level()>=RANKS[i][1])return i;return 0}
function rankNext(){let r=rankIndex();return r===6?null:RANKS[r+1]}
function rankArt(i){const a=RANKS[i][3];const art=[
`<svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="15" fill="#111216" stroke="${a}" stroke-width="3"/><circle cx="20" cy="20" r="10" fill="none" stroke="${a}" stroke-width="2"/><path d="M10 22q10-15 20 0M13 25q7-9 14 0" fill="none" stroke="${a}" stroke-width="2.4" stroke-linecap="round"/><circle cx="20" cy="15" r="2" fill="${a}"/></svg>`,
`<svg viewBox="0 0 40 40" aria-hidden="true"><path d="M20 3 34 11 34 28 20 37 6 28 6 11Z" fill="#111216" stroke="${a}" stroke-width="3" stroke-linejoin="round"/><path d="m9 13 11-6 11 6-11 6Zm0 0 4 13 7 9m11-22-4 13-7 9M9 26l11-7 11 7" fill="none" stroke="${a}" stroke-width="2" stroke-linejoin="round"/></svg>`,
`<svg viewBox="0 0 40 40" aria-hidden="true"><path d="m20 3 4.5 10 11-1.5-7 8 7 8L24 26l-4 11-4-11-11.5 1.5 7-8-7-8L16 13Z" fill="#111216" stroke="${a}" stroke-width="2.5" stroke-linejoin="round"/><path d="m20 11 2.5 6 6 .5-4.5 4 1.5 6-5.5-3-5.5 3 1.5-6-4.5-4 6-.5Z" fill="#2A2C33" stroke="${a}" stroke-width="1.5"/></svg>`,
`<svg viewBox="0 0 40 40" aria-hidden="true"><path d="M20 3 35 13 30 32 20 37 10 32 5 13Z" fill="#111216" stroke="${a}" stroke-width="3" stroke-linejoin="round"/><path d="m5 13 15 5 15-5M10 32l10-14 10 14M20 18v19" fill="none" stroke="${a}" stroke-width="2" stroke-linejoin="round"/><path d="m20 3 7 10-7 5-7-5Z" fill="#2A2C33" stroke="${a}" stroke-width="1.5"/></svg>`,
`<svg viewBox="0 0 40 40" aria-hidden="true"><path d="m20 3 5 8 9-2-3 9 6 6-9 3-3 9-6-6-8 4-1-10-8-5 8-5 1-9Z" fill="#111216" stroke="${a}" stroke-width="2.5" stroke-linejoin="round"/><path d="m20 11 2.5 5.5 6 .5-4.5 4 1.5 6-5.5-3-5.5 3 1.5-6-4.5-4 6-.5Z" fill="none" stroke="${a}" stroke-width="2" stroke-linejoin="round"/></svg>`,
`<svg viewBox="0 0 40 40" aria-hidden="true"><path d="M20 3 34 11 34 27 20 37 6 27 6 11Z" fill="#111216" stroke="${a}" stroke-width="3" stroke-linejoin="round"/><path d="m20 7 8 6-8 6-8-6Zm-8 10 8 6 8-6m-16 7 8 6 8-6" fill="none" stroke="${a}" stroke-width="2.2" stroke-linejoin="round"/></svg>`,
`<svg viewBox="0 0 40 40" aria-hidden="true"><path d="m20 2 5 7 9-1-1 9 6 6-7 6-1 9-9-3-8 4-4-8-8-4 5-8-2-8 9-1Z" fill="#111216" stroke="${a}" stroke-width="2.5" stroke-linejoin="round"/><path d="m20 9 3.5 7 7.5 1-5.5 5.5 1.5 8-7-3.5-7 3.5 1.5-8-5.5-5.5 7.5-1Z" fill="#2A2C33" stroke="${a}" stroke-width="2" stroke-linejoin="round"/><path d="m20 15 2 4 4 .5-3 3 .8 4.5-3.8-2-3.8 2 .8-4.5-3-3 4-.5Z" fill="${a}"/></svg>`];return art[i]}
function sync(){
  const ri=rankIndex(),r=RANKS[ri],inLevel=S.xp%100,tier=Math.min(3,Math.floor((level()-r[1])*3/(r[2]-r[1]+1))+1);
  const tierLabel=['','I','II','III'][tier],progress=level()===50?100:inLevel;
  $('#agentName').innerHTML=escapeHtml(S.username);
  $('#rankName').textContent=`${r[0]} ${tierLabel}`;
  $('#rankIcon').innerHTML=rankArt(ri);
  $('#rankIcon').setAttribute('aria-label',`${r[0]} ${tierLabel} badge`);
  $('#level').textContent=level();$('#coins').textContent=S.coins;$('#streak').textContent=S.streak;
  $('#xpLabel').textContent=`${inLevel} / 100 XP`;
  $('#xpNext').textContent=level()===50?'MAX LEVEL':`${100-inLevel} to level up`;
  $('#xpFill').style.width=`${progress}%`;$('#xpFill').parentElement.setAttribute('aria-valuenow',progress);
  document.body.dataset.theme=S.theme;
  $('#soundLabel').textContent=S.sound?'Sound on':'Sound off';
  $('#soundShort').textContent=S.sound?'♪ On':'♪ Off';$('#mute').setAttribute('aria-pressed',String(S.sound));
}
function careerTier(index=rankIndex()){let r=RANKS[index];return Math.min(3,Math.floor((level()-r[1])*3/(r[2]-r[1]+1))+1)}
function showCareerProgress(){let ri=rankIndex(),tier=careerTier(),pct=Math.min(100,S.xp/4900*100),current=`${RANKS[ri][0]} ${['','I','II','III'][tier]}`;let cards=RANKS.map((r,i)=>{let active=i===ri,rankTier=active?tier:(i<ri?3:0),state=i<ri?'done':i>ri?'future':'active';return `<section class="rank-stop ${state}"><div class="rank-stop-head"><span class="rankbadge" style="--rank:${r[3]}">${rankArt(i)}</span><div><strong>${r[0]}</strong><small>Levels ${r[1]}–${r[2]}</small></div></div><div class="rank-tiers">${['I','II','III'].map((t,j)=>{let tierState=j+1<rankTier||i<ri?'done':j+1===rankTier&&active?'active':'';return `<div class="rank-tier ${tierState}">${t}${tierState==='active'?' · YOU':''}</div>`}).join('')}</div></section>`}).join('');$('#modalRoot').innerHTML=`<div class="overlay" role="presentation" onclick="if(event.target===this)closeCareerProgress()"><section class="progress-modal" role="dialog" aria-modal="true" aria-labelledby="progressTitle"><div class="progress-modal-head"><div><div class="eyebrow">YOUR AGENT JOURNEY</div><h2 id="progressTitle">Your Progress</h2><div class="muted">Every tier, from first field badge to the top rank.</div></div><button class="close" aria-label="Close progress" onclick="closeCareerProgress()">×</button></div><div class="journey-summary"><span class="rankbadge" style="--rank:${RANKS[ri][3]}">${rankArt(ri)}</span><div><strong>${current}</strong><div class="muted">Level ${level()} of 50 · ${S.xp.toLocaleString()} / 4,900 XP</div><div class="journey-track" role="progressbar" aria-label="Overall progress from Bronze I to Champion III" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.floor(pct)}"><span style="width:${pct}%"></span></div></div><div class="journey-percent">${Math.floor(pct)}%</div></div><div class="journey-ends"><span>START · BRONZE I</span><span>DESTINATION · CHAMPION III</span></div><div class="rank-road" style="margin-top:10px">${cards}</div><p class="journey-hint">Your current tier is highlighted. Earn XP in rounds to light up each badge along the route.</p></section></div>`;let close=$('.progress-modal .close');if(close)close.focus()}
function closeCareerProgress(){$('#modalRoot').innerHTML='';$('#progressButton').focus()}

function saveView(v){
  view=v;
  document.querySelectorAll('.navbtn').forEach(b=>{const active=b.dataset.view===v;b.classList.toggle('active',active);if(active)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current')});
}
function toast(t){let x=document.createElement('div');x.className='toast';x.textContent=t;document.body.append(x);setTimeout(()=>x.remove(),2400)}
function sparkle(big=false){if(reducedMotion)return;let n=big?110:45;for(let i=0;i<n;i++){let e=document.createElement('i');e.className='confetti';e.style.left=Math.random()*100+'%';e.style.background=['#B8BCC6','#E6E8EE','#FFC857','#4ADE80','#8A8F9C'][i%5];e.style.animationDelay=Math.random()*.7+'s';document.body.append(e);setTimeout(()=>e.remove(),3600)}}
function unlockAudio(){
  if(!S.sound)return;
  const Audio=window.AudioContext||window.webkitAudioContext;
  if(!Audio)return;
  try{if(!audioContext)audioContext=new Audio();if(audioContext.state==='suspended')audioContext.resume().catch(error=>console.warn('Audio could not start:',error))}
  catch(error){console.warn('Audio is unavailable:',error)}
}
document.addEventListener('pointerdown',unlockAudio,{once:true});
document.addEventListener('keydown',unlockAudio,{once:true});
function sound(freq=620,duration=.12){
  if(!S.sound)return;
  const Audio=window.AudioContext||window.webkitAudioContext;
  if(!Audio)return;
  try{
    if(!audioContext)audioContext=new Audio();
    if(audioContext.state!=='running')return;
    const oscillator=audioContext.createOscillator(),gain=audioContext.createGain();
    oscillator.connect(gain);gain.connect(audioContext.destination);oscillator.frequency.value=freq;
    gain.gain.value=.045;oscillator.start();gain.gain.exponentialRampToValueAtTime(.001,audioContext.currentTime+duration);oscillator.stop(audioContext.currentTime+duration);
    oscillator.addEventListener('ended',()=>{oscillator.disconnect();gain.disconnect()},{once:true});
  }catch(error){console.warn('Audio could not play:',error)}
}
function addXP(amount){let oldLevel=level(),oldRank=rankIndex();S.xp+=amount;S.coins+=Math.max(1,Math.floor(amount/8));sync();if(level()>oldLevel){celebrate(`LEVEL ${level()}!`,`You are getting sharper. Keep trusting your checks.`)}if(rankIndex()>oldRank){let r=RANKS[rankIndex()];celebrate(`${r[0].toUpperCase()} RANK!`,`New badge unlocked. Your instincts are leveling up.`,true)}}
function celebrate(title,desc,big=false){
  sparkle(big);sound(big?950:760,.35);
  if(!$('#modalRoot [role="dialog"]'))modalReturnFocus=document.activeElement;
  $('#modalRoot').innerHTML=`<div class="overlay" role="presentation" onclick="if(event.target===this)closeCelebration()"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="celebrationTitle"><div style="font-size:48px" aria-hidden="true">${big?'🏆':'🎉'}</div><div class="eyebrow">${big?'RANK PROMOTION':'NICE WORK, AGENT'}</div><h2 id="celebrationTitle">${title}</h2><p class="muted">${desc}</p><button class="btn" onclick="closeCelebration()">Keep going</button></section></div>`;
  $('.modal button').focus();
}
function progressRank(){let r=rankIndex(),cur=RANKS[r],next=rankNext();if(!next)return `Top rank reached — Champion status secured.`;let at=level()-cur[1],span=next[1]-cur[1];return `${cur[0]} badge · ${at} / ${span} levels to ${next[0]}`}
function zoneCard(z,i){
  const open=i<S.unlocked,stars=S.stars[i]||0;
  return `<article class="zonecard ${open?'':'locked'}">
    <div class="zone-top"><div class="zone-identity"><span class="zone-icon" aria-hidden="true">${z.icon}</span><span class="zone-index">ZONE ${String(i+1).padStart(2,'0')}</span></div><span class="zone-status">${open?'UNLOCKED':'LOCKED'}</span></div>
    <h3>${z.name}</h3><p>${z.desc}</p>
    <div class="zone-details"><span class="stars" role="img" aria-label="${stars} of 3 stars">${'★'.repeat(stars)}<span class="off">${'☆'.repeat(3-stars)}</span></span><span class="pill">BOSS · ${z.boss}</span></div>
    <div class="actions"><button class="btn small ${open?'':'alt'}" ${open?`onclick="startRound(${i})" aria-label="Deploy to ${escapeAttr(z.name)}"`:'disabled'}>${open?'Deploy <span aria-hidden="true">→</span>':'Keep training'}</button></div>
  </article>`;
}
function home(){
  saveView('home');
  const tier=['','I','II','III'][careerTier()],daily=S.dailyDay===today()?Math.min(S.daily||0,3):0;
  main.innerHTML=`<section class="hero">
    <div class="hero-copy">
      <div class="eyebrow hero-kicker"><span class="status-dot" aria-hidden="true"></span> FIELD TRAINING · YOUR BASE</div>
      <p class="greeting">Welcome back, ${escapeHtml(S.username)}</p>
      <h1>Think before you <em>tap.</em></h1>
      <p class="hero-description">Scams try to rush you, worry you, or win your trust. Practice spotting the signals in a safe, fictional space. Every attempt makes your instincts sharper.</p>
      <div class="actions"><button class="btn" onclick="startRound(${Math.min(S.unlocked-1,4)})">Start a quick round <span aria-hidden="true">→</span></button><button class="btn alt" onclick="render('zones')">Explore zones</button>${S.missed.length?`<button class="btn alt" onclick="revenge()">Revenge Round (${S.missed.length})</button>`:''}</div>
      <div class="hero-note"><span><b aria-hidden="true">◷</b> 60–90 sec rounds</span><span><b aria-hidden="true">◇</b> 100% fictional</span><span><b aria-hidden="true">◈</b> Progress stays local</span></div>
    </div>
    <div class="hero-art" aria-hidden="true"><div class="radar"><div class="radar-cross"></div><div class="radar-lock"><svg class="lock-svg" viewBox="0 0 96 96"><use href="#padlock-mark"></use></svg></div></div><div class="hero-art-label">PAUSE &nbsp; / &nbsp; VERIFY &nbsp; / &nbsp; DECIDE</div></div>
  </section>
  <div class="grid">
    <div class="card"><div class="metric-head"><span class="eyebrow">CURRENT RANK</span><span class="metric-icon" aria-hidden="true">◇</span></div><h3>${RANKS[rankIndex()][0]} ${tier}</h3><p>${progressRank()}</p></div>
    <div class="card"><div class="metric-head"><span class="eyebrow">DAILY CHALLENGE</span><span class="metric-icon" aria-hidden="true">◷</span></div><h3>${daily} / 3 scenarios</h3><p>${daily===3?'Daily challenge complete.':'Three sharp calls, one day at a time.'}</p></div>
    <div class="card"><div class="metric-head"><span class="eyebrow">AGENT RECORD</span><span class="metric-icon" aria-hidden="true">↗</span></div><h3>${S.correct} clean reads</h3><p>Best combo ×${Math.max(1,S.bestCombo)} · ${S.answered} total scenarios</p></div>
  </div>
  <div class="field-note"><div class="field-note-icon" aria-hidden="true">✧</div><div><div class="eyebrow">A HABIT WORTH SHARING</div><strong>When in doubt, pause and verify.</strong><p>Check unexpected requests through a channel you already trust.</p></div></div>
  <div class="sectionhead"><div><div class="eyebrow">YOUR NEXT MISSION</div><h2>Choose your training zone</h2></div><span class="pill">${S.unlocked} / ${ZONES.length} OPEN</span></div>
  <div class="zones">${ZONES.map(zoneCard).join('')}</div>
  <p class="footer">No real links, money, or messages here. Just fictional training and sharper instincts.</p>`;
}
function zones(){saveView('zones');main.innerHTML=`<div class="eyebrow">PROGRESS BY TERRITORY</div><h1 class="screen-title">Training zones</h1><p class="muted">Clear a zone with 3 answers. Earn stars from accuracy, beat its boss scenario, and unlock the next district.</p><div class="zones">${ZONES.map(zoneCard).join('')}</div>`}
function pickScenario(zoneIndex){let z=ZONES[zoneIndex],arr=z.ids.map(id=>SCENARIOS.find(x=>x.id===id));let boss=arr[arr.length-1];return [...shuffle(arr.slice(0,-1)),boss]}
function startRound(zoneIndex){zoneIndex=Math.max(0,Math.min(zoneIndex,S.unlocked-1));let qs=pickScenario(zoneIndex);round={zoneIndex,qs,index:0,score:0,seconds:78,revenged:false,from:'zone'};playNext()}
function revenge(){if(!S.missed.length){toast('No missed calls in the queue. Your radar is clean!');return}round={zoneIndex:Math.min(S.unlocked-1,4),qs:S.missed.slice(0,5).map(id=>SCENARIOS.find(x=>x.id===id)),index:0,score:0,seconds:75,revenged:true,from:'revenge'};playNext()}
function cancelQuestionRequest(){if(questionRequest){questionRequest.abort();questionRequest=null}}
async function playNext(){
  clearInterval(roundTimer);roundTimer=null;cancelQuestionRequest();
  if(round.index>=round.qs.length){finishRound();return}
  const activeRound=round,index=round.index,request=new AbortController();
  questionRequest=request;nowQ=null;
  main.innerHTML=`<div class="gamecard"><div class="eyebrow">PREPARING YOUR MISSION</div><h1 class="screen-title">Finding a fresh signal</h1><p class="muted" role="status">Checking for a new fictional example…</p><div class="actions"><button class="btn alt" onclick="quitRound()">Back to base</button></div></div>`;
  animateScreen();main.focus();
  try{
    const scenario=await claimScenario(activeRound.qs[index],request.signal);
    if(questionRequest!==request||round!==activeRound||round.index!==index)return;
    questionRequest=null;nowQ=scenario;answered=false;huntPicked=[];round.mode=nextMode();
    renderQuestion();animateScreen();main.focus();
    roundTimer=setInterval(()=>{round.seconds--;let t=$('.timer');if(t){t.textContent=`⏱ ${round.seconds}s`;if(round.seconds<=15)t.classList.add('low')}if(round.seconds<=0){clearInterval(roundTimer);if(!answered){answer(false,'timeout')}}},1000);
  }catch(error){
    if(request.signal.aborted||round!==activeRound||questionRequest!==request)return;
    questionRequest=null;console.error('Could not prepare a question:',error);
    const message=error instanceof Error?error.message:'An unexpected error occurred.';
    main.innerHTML=`<div class="gamecard"><div class="eyebrow">MISSION PAUSED</div><h1 class="screen-title">A fresh signal is not ready</h1><p class="muted" role="alert">${escapeHtml(message)} You can retry or return to base.</p><div class="actions"><button class="btn" onclick="playNext()">Try again</button><button class="btn alt" onclick="quitRound()">Back to base</button></div></div>`;
    animateScreen();main.focus();
  }
}
function renderQuestion(){
  const q=nowQ,mode=round.mode;
  const modeTitle={real:'REAL OR SCAM?',hunt:'RED FLAG HUNT',url:'URL INSPECTOR',response:'CHOOSE YOUR RESPONSE'}[mode];
  const prompts={
    real:['Does this message look like a scam, or could it be legitimate?','How would you classify this signal: suspicious or potentially legitimate?','Is this a scam signal, or could the message be legitimate?'],
    hunt:['Tap the suspicious parts. Then lock in your read.','Which warning signs can you spot? Select them and lock in your scan.','Look for red flags, then confirm your assessment.'],
    url:['Which option would you trust least?','Which choice is the least safe to follow?','Which of these options raises the biggest concern?'],
    response:['What is the safest next move?','How would you respond most safely?','Which next step best protects you?']
  };
  const prompt=choose(prompts[mode]);
  let body='';
  if(mode==='real')body=`<div class="answers"><button class="answer" onclick="answer(true,'scam',this)"><span class="choice-icon scam" aria-hidden="true">!</span>Scam signal</button><button class="answer" onclick="answer(false,'legit',this)"><span class="choice-icon safe" aria-hidden="true">✓</span>Could be legitimate</button></div>`;
  if(mode==='hunt'){
    const chunks=shuffle([...q.flags,...(q.flags.length?['Sender looks slightly off','Message asks you to pause and verify']:['No urgent demand','Uses a known channel'])]).slice(0,5);
    body=`<div class="flags">${chunks.map(f=>`<button class="flag" aria-pressed="false" data-flag="${escapeAttr(f)}" onclick="this.classList.toggle('selected');toggleFlag(this)">${escapeHtml(f)}</button>`).join('')}</div><button class="btn" id="lockScan" onclick="submitHunt(this)">Lock in my scan</button>`;
  }
  if(mode==='url'){
    const opts=q.isScam?['https://'+(q.id==='bank'?'northstar-secure.example.test':'parcel-pal.example.test')+'/verify','Open the official app you already use','Type the known organization address yourself']:['https://maple-library.example.test/account','Tap an urgent shortened link','Reply with your account password'];
    body=`<div class="answers">${opts.map((o,i)=>`<button class="answer" onclick="answer(${q.isScam?i===0:i!==0},'url${i}',this)">${escapeHtml(o)}</button>`).join('')}</div>`;
  }
  if(mode==='response'){
    const opts=q.isScam?['Pause and verify through a known, independent channel','Reply quickly so the issue does not get worse','Share a code or payment to see what happens']:['Check in the established app or channel if uncertain','Report it as a scam without checking','Share extra personal details just in case'];
    body=`<div class="answers">${opts.map((o,i)=>`<button class="answer" onclick="answer(${i===0},'response${i}',this)">${escapeHtml(o)}</button>`).join('')}</div>`;
  }
  main.innerHTML=`<div class="gamehead"><span>${round.revenged?'↺ REVENGE ROUND':ZONES[round.zoneIndex].name.toUpperCase()} · ${modeTitle}</span><span class="timer ${round.seconds<=15?'low':''}">⏱ ${round.seconds}s</span></div>
    <div class="meter" role="progressbar" aria-label="Scenario progress" aria-valuemin="0" aria-valuemax="${round.qs.length}" aria-valuenow="${round.index}"><span style="width:${round.index/round.qs.length*100}%"></span></div>
    <div class="gamecard"><div class="eyebrow">${escapeHtml(q.type.toUpperCase())} · SCENARIO ${round.index+1} / ${round.qs.length}</div>
    <div class="message ${q.kind==='message'?'email':q.kind}"><div class="sender">${q.kind==='text'?'TEXT MESSAGE':q.kind==='message'?'EMAIL':q.kind.toUpperCase()} · FICTIONAL TRAINING EXAMPLE</div><div class="prompt">${escapeHtml(q.content)}</div></div>
    <h1 class="question-prompt">${prompt} <span class="muted">Case ${escapeHtml(q.reference)}</span></h1>${body}<div id="fb" aria-live="polite"></div>
    <div class="row" style="margin-top:18px"><span class="combo">${S.combo>1?'COMBO ×'+Math.min(S.combo,5):'Build a streak for an XP multiplier'}</span><button class="btn alt small" onclick="quitRound()">Back to base</button></div></div>`;
}
function toggleFlag(el){let f=el.dataset.flag;el.setAttribute('aria-pressed',String(el.classList.contains('selected')));if(huntPicked.includes(f))huntPicked=huntPicked.filter(x=>x!==f);else huntPicked.push(f)}
function submitHunt(button){let correct=nowQ.flags.length?huntPicked.some(f=>nowQ.flags.includes(f)):huntPicked.length===0;answer(correct,'hunt',button)}
function answer(ok,choice,button=null){
  if(answered)return;
  answered=true;clearInterval(roundTimer);roundTimer=null;
  const q=nowQ,exact=choice==='timeout'?false:(choice==='scam'||choice==='legit'?ok===q.isScam:ok);
  if(button)button.classList.add(exact?'correct':'wrong');
  let gain=exact?10+Math.min(round.seconds,20):0;
  if(exact){
    S.combo++;S.bestCombo=Math.max(S.bestCombo,S.combo);
    const mult=S.combo>=5?5:S.combo>=3?3:S.combo>=2?2:1;
    gain*=mult;round.score++;S.correct++;S.coins+=2;S.seen=[...new Set([...S.seen,q.id])];
    if(S.missed.includes(q.id))S.missed=S.missed.filter(id=>id!==q.id);
    sound(760);
  }else{
    S.combo=0;if(q.isScam&&!S.missed.includes(q.id))S.missed.push(q.id);sound(210);
  }
  S.answered++;S.rounds++;S.dailyDay ||= today();
  if(S.dailyDay!==today()){S.dailyDay=today();S.daily=0}
  S.daily=(S.daily||0)+1;
  if(S.daily>=3&&!S.achievements.includes('daily'))unlock('daily');
  if(exact)addXP(gain);else persist();
  updateAchievements();sync();
  const fb=$('#fb');
  if(fb){
    const right=q.isScam?'Scam signal':'Could be legitimate';
    fb.innerHTML=`<div class="feedback ${exact?'':'bad'}"><b>${exact?'Nice read!':choice==='timeout'?'Time’s up — no stress.':'Not quite — that’s what practice is for.'} ${gain?`+${gain} XP`:''}</b><p><strong>Read:</strong> <span class="verdict ${q.isScam?'scam':'safe'}">${right}</span>. ${escapeHtml(q.why)}</p><p><strong>Try this:</strong> ${escapeHtml(q.do)}</p></div><button class="btn" style="margin-top:12px" onclick="advance()">${round.index===round.qs.length-1?'See round result':'Next scenario'} →</button>`;
    main.querySelectorAll('.answer,.flag,#lockScan').forEach(b=>b.disabled=true);
  }
  persist();
}
function advance(){round.index++;playNext()}
function finishRound(){clearInterval(roundTimer);roundTimer=null;let i=round.zoneIndex,stars=round.score>=round.qs.length?3:round.score>=Math.ceil(round.qs.length*.67)?2:round.score>=1?1:0;let old=S.stars[i]||0;S.stars[i]=Math.max(old,stars);if(round.score>=Math.ceil(round.qs.length*.67)&&S.unlocked===i+1&&S.unlocked<ZONES.length){S.unlocked++;addXP(20);toast(`Zone unlocked: ${ZONES[i+1].name}!`)}else addXP(round.score*3);if(round.revenged){unlock('revenge')}S.streak++;S.lastDay=today();S.rounds++;persist();updateAchievements();let boss=round.qs[round.qs.length-1];main.innerHTML=`<div class="gamecard" style="text-align:center"><div style="font-size:45px">${stars===3?'🏆':'🛰️'}</div><div class="eyebrow">${round.revenged?'REVENGE ROUND COMPLETE':'ZONE REPORT'}</div><h1 class="screen-title">${round.score} / ${round.qs.length} sharp calls</h1><p class="muted">${stars} stars earned · ${ZONES[i].name} ${stars>=2?'cleared':'still open'}${round.score===round.qs.length?' · Boss handled!':''}</p><div class="stars" style="font-size:28px">${'★'.repeat(stars)}<span class="off">${'☆'.repeat(3-stars)}</span></div><p class="muted">${round.score===round.qs.length?'Clean sweep. Your radar is humming.':`Every answer is intel. Review misses in the Field Guide or try a Revenge Round.`}</p><div class="actions" style="justify-content:center"><button class="btn" onclick="startRound(${Math.min(S.unlocked-1,4)})">One more round</button><button class="btn alt" onclick="revenge()">↺ Revenge Round (${S.missed.length})</button><button class="btn alt" onclick="render('home')">Return to base</button></div></div>`;persist();round=null;nowQ=null;animateScreen();if(!$('#modalRoot [role="dialog"]'))main.focus()}
function quitRound(){render('home')}
function today(){let d=new Date();return `${d.getFullYear()}-${d.getMonth()+1}-${d.getDate()}`}
function unlock(id){if(!S.achievements.includes(id)){S.achievements.push(id);let a=ACH.find(x=>x.id===id);if(a)toast(`Achievement unlocked: ${a.name}`)}}
const ACH=[{id:'first',name:'First Contact',icon:'📡',desc:'Answer your first scenario.'},{id:'combo5',name:'Hot Streak',icon:'🔥',desc:'Get five right in a row.'},{id:'daily',name:'Daily Signal',icon:'☀️',desc:'Answer three scenarios today.'},{id:'revenge',name:'Bounce Back',icon:'↩️',desc:'Complete a Revenge Round.'},{id:'allzones',name:'Zone Hopper',icon:'🗺️',desc:'Unlock all five zones.'},{id:'guide8',name:'Pattern Finder',icon:'📚',desc:'Meet eight scam types.'},{id:'boss',name:'Boss Buffer',icon:'👾',desc:'Earn three stars in a zone.'}];
function updateAchievements(){if(S.answered)unlock('first');if(S.bestCombo>=5)unlock('combo5');if(S.seen.length>=8)unlock('guide8');if(S.unlocked>=5)unlock('allzones');if(S.stars.some(x=>x===3))unlock('boss')}
function fieldGuide(){saveView('guide');let seen=SCENARIOS.filter(x=>S.seen.includes(x.id));main.innerHTML=`<div class="eyebrow">INTEL ARCHIVE</div><h1 class="screen-title">Field Guide</h1><p class="muted">Your guide fills in as you meet scam patterns. Learn the move, then choose a verification path.</p><div class="box">${seen.length} / ${SCENARIOS.length} signals encountered · ${SCENARIOS.filter(x=>S.seen.includes(x.id)&&x.isScam).length} scam patterns studied</div><div class="list">${SCENARIOS.map(q=>`<article class="box"><div class="row"><span class="badge">${S.seen.includes(q.id)?(q.isScam?'🚩':'✅'):'🔒'}</span><strong>${S.seen.includes(q.id)?q.type:'Unidentified signal'}</strong><span class="pill">${S.seen.includes(q.id)?(q.isScam?'SCAM':'LEGIT SIGNAL'):'Meet this scenario to reveal'}</span></div>${S.seen.includes(q.id)?`<p class="muted">${escapeHtml(q.why)}</p><p><b>Safer move:</b> ${escapeHtml(q.do)}</p><button class="btn alt small" onclick="startCustom('${q.id}')">Practice this</button>`:''}</article>`).join('')}</div>`}
function startCustom(id){let q=SCENARIOS.find(x=>x.id===id);round={zoneIndex:0,qs:[q],index:0,score:0,seconds:45,revenged:true};playNext()}
function achievements(){saveView('achievements');main.innerHTML=`<div class="eyebrow">GOOD HABITS, RECOGNIZED</div><h1 class="screen-title">Achievements</h1><p class="muted">Badges are earned through practice. No pressure, no streak shaming.</p><div class="list">${ACH.map(a=>`<div class="box listrow"><span class="badge">${S.achievements.includes(a.id)?a.icon:'🔒'}</span><div style="flex:1"><strong>${a.name}</strong><div class="muted">${a.desc}</div></div><span class="pill">${S.achievements.includes(a.id)?'UNLOCKED':'IN TRAINING'}</span></div>`).join('')}</div><div class="box"><strong>Current best combo: ×${S.bestCombo}</strong><p class="muted">Correct answers build your streak multiplier: ×2, ×3, then ×5.</p></div>`}
function shop(){saveView('shop');main.innerHTML=`<div class="eyebrow">COSMETIC LAB</div><h1 class="screen-title">Make the console yours</h1><p class="muted">All credits are earned by answering training scenarios. No purchases, no real money.</p><div class="box"><strong>⚡ ${S.coins} earned credits</strong></div><div class="list">${REWARDS.map(x=>{let owned=S.owned.includes(x.id);let equipped=S.equipped===x.id;return `<article class="box shopitem"><span class="badge">${x.icon}</span><div><strong>${x.name}</strong><div class="muted">${x.desc}</div></div><button class="btn small ${owned?'alt':''}" onclick="buy('${x.id}')">${equipped?'Equipped':owned?'Equip':`${x.cost} credits`}</button></article>`}).join('')}</div>`}
function buy(id){let x=REWARDS.find(z=>z.id===id);if(S.owned.includes(id)){S.equipped=id;if(id.startsWith('theme_'))S.theme=id.slice(6);persist();sync();render('shop');return}if(S.coins<x.cost){toast('A few more training wins will get you there.');return}S.coins-=x.cost;S.owned.push(id);S.equipped=id;if(id.startsWith('theme_'))S.theme=id.slice(6);persist();sync();render('shop');toast(`${x.name} unlocked!`)}
function settings(){
  saveView('settings');
  main.innerHTML=`<div class="eyebrow">AGENT CONSOLE</div><h1 class="screen-title">Settings & safety</h1>
    <div class="box"><h3>Change codename</h3><p class="muted">Don't use your real name, email, or personal info. Pick a codename.</p>${codenameForm('changeName',true)}</div>
    <div class="box"><h3>Sound</h3><p class="muted">Short, locally generated arcade tones. No audio files or network requests.</p><button class="btn alt" onclick="toggleSound()">${S.sound?'Mute sound':'Enable sound'}</button></div>
    <div class="box"><h3>Progress & privacy</h3><p class="muted">Progress stays in this browser. The local server stores anonymous fingerprints of used examples, not codenames or answers, to prevent repeats. Race rooms send display name, rank, score, and progress to this game server. No account is required; solo progress stays in this browser. All names and domains are fictional.</p><button class="btn danger" onclick="resetProgress()">Reset all progress</button></div>
    <div class="box"><h3>Take a breather</h3><p class="muted">Your attention is the real superpower. A pause is always a good move.</p><button class="btn alt" onclick="toast('Stretch, sip some water, and come back whenever you like.')">Break reminder</button></div>`;
  bindCodenameForm('changeName',true);
}
function toggleSound(){S.sound=!S.sound;persist();sync();if(S.sound)unlockAudio();if(view==='settings')settings()}
function resetProgress(){
  if(!confirm('Reset all saved game progress and your codename in this browser?'))return;
  clearInterval(roundTimer);roundTimer=null;cancelQuestionRequest();round=null;nowQ=null;
  const oldState=S;S=freshState();
  if(!persist()){S=oldState;sync();return}
  sync();showCodenameScreen();toast('Fresh start. Choose a codename when you are ready.');
}
function animateScreen(){main.classList.remove('screen-enter');void main.offsetWidth;main.classList.add('screen-enter')}
function multiplayer(){view='multiplayer';clearInterval(mpPoll);if(!mpRoom){mpLobbyHome();return}mpPoll=setInterval(mpRefresh,1400);mpRefresh()}
function mpLobbyHome(error=''){main.innerHTML=`<section class="hero mp-lobby-hero"><div class="eyebrow">SIGNAL//SAFE · PUBLIC MATCH RACE</div><h1>Race your <em>radar.</em></h1><p>Create a room and share its code with anyone online. Compare ranks, then race through fresh scam signals against a shared 90-second clock.</p><div class="actions"><span class="pill">Public room · no account required</span><span class="pill">Top correct-call score wins</span></div></section><section class="gamecard"><h2>Join the race</h2><label class="muted" for="mpName">Agent name</label><div class="mp-join"><input id="mpName" maxlength="24" placeholder="Your display name" value="${escapeAttr(S.username||S.pcUser||'')}"><button class="btn" onclick="mpConnect('create')">Create a room</button></div><label class="muted" for="mpCode">Room code</label><div class="mp-join"><input id="mpCode" maxlength="6" placeholder="e.g. A7K4QZ" style="text-transform:uppercase"><button class="btn alt" onclick="mpConnect('join')">Join room</button></div>${error?`<p role="alert" style="color:#a2466d">${escapeHtml(error)}</p>`:''}<p class="muted">The host must keep this game running. Anyone with the code can join before the race starts.</p></section>`}
async function mpRequest(path,data){let response=await fetch(path,data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{});let result=await response.json();if(!response.ok||result.error)throw new Error(result.error||'Race server unavailable.');return result}
async function mpConnect(action){let name=($('#mpName')?.value||'').trim();let code=($('#mpCode')?.value||'').trim().toUpperCase();if(!name){mpLobbyHome('Enter an agent name first.');return}try{let result=await mpRequest('/api/race/join',{action,name,code,xp:S.xp,rank:$('#rankName').textContent,seen:S.seen||[]});mpRoom=result.code;mpPlayer=result.player;mpData=result.room;mpServerOffset=(mpData.serverNow||Date.now()/1000)-Date.now()/1000;mpRenderedIndex=-1;mpRefreshStart();mpDisplay()}catch(e){mpLobbyHome(e.message)}}
function mpRefreshStart(){clearInterval(mpPoll);mpPoll=setInterval(mpRefresh,1200)}
async function mpRefresh(){if(!mpRoom||!mpPlayer)return;try{let result=await mpRequest(`/api/race/room?code=${encodeURIComponent(mpRoom)}&player=${encodeURIComponent(mpPlayer)}`);mpData=result.room;mpServerOffset=(mpData.serverNow||Date.now()/1000)-Date.now()/1000;mpDisplay()}catch(e){if(view==='multiplayer')mpLobbyHome(e.message);clearInterval(mpPoll)}}
function mpPlayerCards(){let list=mpData?.players||[];return list.slice().sort((a,b)=>b.score-a.score||b.index-a.index).map((p,i)=>`<div class="mp-player"><strong>${i===0?'🏁 ':''}${escapeHtml(p.name)} ${p.id===mpPlayer?'(you)':''}</strong><small>${escapeHtml(p.rank)} · Level ${p.level} · ${p.online?'Online':'Away'} · ${p.finished?'Finished':`${p.index}/${mpData.race?.questions?.length||0} answered`}</small><span class="mp-score">${p.score} pts</span></div>`).join('')}
function mpDisplay(){if(view!=='multiplayer'||!mpData)return;let race=mpData.race,me=(mpData.players||[]).find(p=>p.id===mpPlayer);if(!me)return;if(!race){main.innerHTML=`<section class="gamecard"><div class="eyebrow">ROOM · ${escapeHtml(mpRoom)}</div><div class="mp-code">${escapeHtml(mpRoom)}</div><p class="muted">Share this room code with your friends. Rank and level are visible to everyone in the room.</p><div class="mp-players">${mpPlayerCards()}</div><button class="btn" onclick="mpStart()">Start 90-second race</button> <button class="btn alt" onclick="mpExit()">Leave room</button><p class="muted" style="margin-top:12px">Races need at least 2 agents. Each player gets a freshly generated example, even when a scam pattern is familiar.</p></section>`;return}if(!race.started){main.innerHTML=`<section class="gamecard"><div class="eyebrow">ROOM · ${escapeHtml(mpRoom)}</div><h1 class="screen-title">Race ready</h1><p class="muted">Waiting for race to begin…</p><div class="mp-players">${mpPlayerCards()}</div></section>`;return}if(me.finished||me.index>=race.questions.length||Date.now()/1000+mpServerOffset>=race.endsAt){if(!$('.mp-finished'))mpFinished(me,race);let finalBoard=$('.mp-finished .mp-players');if(finalBoard)finalBoard.innerHTML=mpPlayerCards();return}if(mpRenderedIndex!==me.index||!$('.mp-race-view'))mpRenderRace(me,race);else{let timer=$('.mp-timer');if(timer)timer.textContent=mpTimeLeft(race);let board=$('.mp-scoreboard');if(board)board.innerHTML=mpPlayerCards();if(Date.now()/1000+mpServerOffset>=race.endsAt&&!me.finished)mpSubmitTimeout(me)}}
function mpTimeLeft(race){return `${Math.max(0,Math.ceil(race.endsAt-(Date.now()/1000+mpServerOffset)))}s`}
async function mpStart(){try{let result=await mpRequest('/api/race/start',{code:mpRoom,player:mpPlayer});mpData=result.room;mpServerOffset=(mpData.serverNow||Date.now()/1000)-Date.now()/1000;mpScenarioCache={};mpPendingIndex=-1;mpRenderedIndex=-1;mpDisplay()}catch(e){toast(e.message)}}
async function mpRenderRace(me,race){clearInterval(mpRaceTimer);const index=me.index;mpRenderedIndex=index;if(me.finished||index>=race.questions.length||Date.now()/1000+mpServerOffset>=race.endsAt){mpFinished(me,race);return}let scenario=mpScenarioCache[index];if(!scenario){if(mpPendingIndex===index)return;mpPendingIndex=index;main.innerHTML=`<section class="gamecard mp-race-view"><div class="eyebrow">LIVE RACE · ROOM ${escapeHtml(mpRoom)}</div><h2 class="screen-title">Preparing a fresh signal…</h2><p class="muted">Checking the shared question history.</p><div class="mp-scoreboard mp-players">${mpPlayerCards()}</div></section>`;try{scenario=await claimScenario(SCENARIOS.find(x=>x.id===race.questions[index]));if(view!=='multiplayer'||!mpData||mpData.race?.questions?.[index]!==race.questions[index])return;let current=(mpData.players||[]).find(p=>p.id===mpPlayer);if(!current||current.index!==index)return;mpScenarioCache[index]=scenario;mpPendingIndex=-1;S.seen=[...new Set([...(S.seen||[]),scenario.id])];persist()}catch(error){mpPendingIndex=-1;if(view==='multiplayer')main.innerHTML=`<section class="gamecard mp-race-view"><div class="eyebrow">RACE QUESTION PAUSED</div><p role="alert" class="muted">${escapeHtml(error.message||'Could not prepare a fresh example.')}</p><button class="btn" onclick="mpRenderedIndex=-1;mpDisplay()">Try again</button></section>`;return}}scenario=mpScenarioCache[index]||scenario;let current=(mpData.players||[]).find(p=>p.id===mpPlayer);if(!current||current.index!==index||view!=='multiplayer')return;let q=scenario;S.seen=[...new Set([...(S.seen||[]),q.id])];persist();main.innerHTML=`<section class="gamecard mp-race-view"><div class="eyebrow">LIVE RACE · ROOM ${escapeHtml(mpRoom)}</div><div class="gamehead"><span>Question ${index+1} of ${race.questions.length} · Case #${q.reference}</span><span class="mp-race-timer mp-timer">${mpTimeLeft(race)}</span></div><div class="meter"><span style="width:${index/race.questions.length*100}%"></span></div><h2 class="screen-title">Scam signal or legitimate?</h2><div class="mp-question">${escapeHtml(q.content)}</div><div class="answers"><button class="answer" onclick="mpAnswer('${q.id}',true)">🚩 Scam signal</button><button class="answer" onclick="mpAnswer('${q.id}',false)">✅ Could be legitimate</button></div><div class="mp-scoreboard mp-players">${mpPlayerCards()}</div><button class="btn alt small" onclick="mpExit()">Leave race</button></section>`;mpRaceTimer=setInterval(()=>{let el=$('.mp-timer');if(el)el.textContent=mpTimeLeft(race);if(Date.now()/1000+mpServerOffset>=race.endsAt){clearInterval(mpRaceTimer);mpSubmitTimeout(current)}},250)}
async function mpAnswer(id,scam){let me=(mpData.players||[]).find(p=>p.id===mpPlayer),race=mpData.race,q=SCENARIOS.find(x=>x.id===id);if(!me||!race||me.finished||me.index!==mpRenderedIndex)return;let correct=scam===q.isScam;if(correct){me.score++;S.combo++;S.correct++;S.answered++;addXP(10);toast('+10 XP · Correct call')}else{S.combo=0;S.answered++;persist()}me.index++;if(me.index>=race.questions.length)me.finished=true;mpRenderedIndex=-1;try{await mpRequest('/api/race/progress',{code:mpRoom,player:mpPlayer,index:me.index,score:me.score,finished:me.finished});await mpRefresh()}catch(e){toast(e.message)}}
async function mpSubmitTimeout(me){if(me.finished)return;me.finished=true;try{await mpRequest('/api/race/progress',{code:mpRoom,player:mpPlayer,index:me.index,score:me.score,finished:true});await mpRefresh()}catch(e){}}
function mpFinished(me,race){clearInterval(mpRaceTimer);main.innerHTML=`<section class="gamecard mp-finished"><div class="eyebrow">RACE COMPLETE · ROOM ${escapeHtml(mpRoom)}</div><h1 class="screen-title">${me.finished?'Finish line!':'Time!'} You scored ${me.score}.</h1><p class="muted">The full room leaderboard shows correct calls. Ranks reflect each player’s local training save.</p><div class="mp-players">${mpPlayerCards()}</div><button class="btn alt" onclick="mpExit()">Leave room</button></section>`}
function mpExit(){clearInterval(mpPoll);clearInterval(mpRaceTimer);mpRoom='';mpPlayer='';mpData=null;mpRenderedIndex=-1;mpScenarioCache={};mpPendingIndex=-1;mpLobbyHome()}
function pcMode(){saveView('pc');clearInterval(pcClockTimer);pcLockScreen()}
function pcLockScreen(){clearTimeout(pcLoadingTimer);clearTimeout(pcAppLoadTimer);pcAppLoading=false;main.innerHTML=`<section class="pc-shell pc-lock-shell"><div class="pc-lockscreen" role="button" tabindex="0" aria-label="Click anywhere to wake Signal OS" onclick="pcWake()" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();pcWake()}"><div class="pc-lock-brand">◉ SIGNAL OS <span>SECURE LOCAL DESKTOP</span></div><button class="pc-fullscreen" onclick="pcFullscreen(event)" aria-label="Toggle fullscreen" title="Toggle fullscreen">⛶</button><div class="pc-lock-time"><div id="pcLockClock">${pcTime()}</div><span id="pcLockDate">${pcDate()}</span></div><div class="pc-lock-prompt"><div class="pc-lock-hint"><span class="pc-enter-icon">↥</span><span>Click anywhere or press Enter to continue</span></div><div class="pc-lock-user">${S.pcUser?`Signed in as <strong>${escapeHtml(S.pcUser)}</strong>`:'Local demo session · no account required'}</div></div></div></section>`;pcClockTimer=setInterval(()=>{let t=$('#pcLockClock'),d=$('#pcLockDate');if(t)t.textContent=pcTime();if(d)d.textContent=pcDate()},1000);$('.pc-lockscreen').focus()}
function pcWake(){clearInterval(pcClockTimer);pcLogin()}
function pcBoot(){clearInterval(pcClockTimer);clearTimeout(pcLoadingTimer);main.innerHTML=`<section class="pc-shell pc-boot"><div class="pc-boot-center"><div class="pc-boot-logo">◉</div><strong>SIGNAL OS</strong><span>Starting your local desktop…</span><div class="pc-boot-track"><i></i></div><small>Preparing your workspace</small></div></section>`;pcLoadingTimer=setTimeout(()=>{if(view==='pc'&&S.pcUser)pcDesktop()},1500)}
function pcFullscreen(e){if(e)e.stopPropagation();let el=$('#main');if(!el)return;if(document.fullscreenElement){document.exitFullscreen?.()}else{el.requestFullscreen?.().catch(()=>toast('Fullscreen is unavailable in this browser.'))}}

function pcLogin(){clearInterval(pcClockTimer);main.innerHTML=`<section class="pc-shell"><div class="pc-topbar"><strong>◉ SIGNAL OS</strong><span>LOCAL DEMO ENVIRONMENT</span><button class="pc-win-btn" aria-label="Toggle fullscreen" title="Toggle fullscreen" onclick="pcFullscreen(event)">⛶</button></div><div class="pc-login"><div class="pc-login-card"><div class="pc-avatar">⌁</div><div class="eyebrow">LOCAL USER LOGIN</div><h2>Sign in to your desktop</h2><div class="pc-login-clock" id="pcLoginClock">${pcTime()}</div><div class="pc-login-date" id="pcLoginDate">${pcDate()}</div><p>This is a local training computer. Enter your local user name to start your demo session.</p><form onsubmit="pcSignIn(event)"><label class="pc-user-label" for="pcUserInput">User name</label><input id="pcUserInput" class="pc-user-input" maxlength="28" autocomplete="username" value="${escapeHtml(S.pcUser||'')}" placeholder="Enter a user name" aria-label="User name" required><button class="btn" style="width:100%" type="submit">Sign in →</button></form><p class="pc-app-note">No password, email, or real account needed. Your display name stays in this browser only.</p><button class="btn alt small" onclick="render('home')">← Back to game</button></div></div></section>`;$('#pcUserInput').focus();pcClockTimer=setInterval(()=>{let t=$('#pcLoginClock'),d=$('#pcLoginDate');if(t)t.textContent=pcTime();if(d)d.textContent=pcDate()},1000)}
function pcSignIn(e){e.preventDefault();let name=$('#pcUserInput').value.trim().slice(0,28);if(!name){toast('Enter a user name to sign in.');return}S.pcUser=name;S.pcApp='';persist();pcBoot()}
function pcSignOut(){S.pcUser='';S.pcApp='';persist();clearInterval(pcClockTimer);pcLockScreen()}
function pcDate(){return new Date().toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric',year:'numeric'})}
function pcTime(){return new Date().toLocaleTimeString(undefined,{hour:'numeric',minute:'2-digit'})}
function pcIcon(id){let p={files:'<path d="M3 8V5a2 2 0 0 1 2-2h7l3 3h7a2 2 0 0 1 2 2v2M3 10h19l-2 10H5Z"/>',mail:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/>',browser:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/>',notes:'<path d="M6 3h9l4 4v14H6zM15 3v5h5M9 12h7M9 16h7"/>',calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 10h18m-13 4h2m4 0h2m-8 3h2"/>',calculator:'<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h8M8 12h1m3 0h1m3 0h1m-8 4h1m3 0h1m3 0h1"/>',video:'<rect x="3" y="5" width="13" height="14" rx="2"/><path d="m16 10 5-3v10l-5-3zM9 9l4 3-4 3z"/>',messages:'<path d="M21 11.5a8.5 8.5 0 0 1-12.6 7.4L3 21l1.8-5.1A8.5 8.5 0 1 1 21 11.5Z"/><path d="M8 11h8m-8 4h5"/>',safety:'<path d="M12 3 20 6v5c0 5-3.4 8.3-8 10-4.6-1.7-8-5-8-10V6z"/><path d="m8.5 12 2.2 2.2 4.8-5"/>',settings:'<circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.6a8 8 0 0 1-1.6.9l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.6-.9l-1.7.6-1.4-2.4 1.4-1.1a7 7 0 0 1 0-1.9L6.1 12l1.4-2.4 1.7.6a8 8 0 0 1 1.6-.9l.3-1.8h2.8l.3 1.8a8 8 0 0 1 1.6.9l1.7-.6 1.4 2.4-1.4 1.1a7 7 0 0 1-.1 1.9Z"/>',start:'<path d="M4 4h7v7H4zm9 0h7v7h-7zM4 13h7v7H4zm9 0h7v7h-7z"/>'};return `<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${p[id]||p.files}</svg>`}
function pcAppButton(id,icon,label,task=false){return `<button class="${task?'':'pc-icon'}" ${task?'':'aria-label="Open '+label+'"'} onclick="pcOpen('${id}')"><span>${pcIcon(id)}</span>${task?'':label}</button>`}
function pcDesktop(){clearInterval(pcClockTimer);let apps=[['files','📁','Files'],['browser','🌐','Browser'],['safety','🛡️','Safety Lab'],['notes','📝','Notes'],['calendar','🗓️','Calendar'],['calculator','🧮','Calculator'],['messages','💬','Ping'],['mail','✉️','Mail'],['settings','⚙️','Settings']];let app=S.pcApp?pcAppBody(S.pcApp):'';main.innerHTML=`<section class="pc-shell ${S.pcWallpaper==='lake'?'wall-lake':S.pcWallpaper==='dusk'?'wall-dusk':''}"><div class="pc-topbar"><strong>◉ SIGNAL OS <span style="font-weight:400;opacity:.75"> / Desktop</span></strong><div class="pc-top-right"><span class="pc-mode-chip">● LOCAL SESSION</span><span>${escapeHtml(S.pcUser)}</span><button class="pc-win-btn" aria-label="Toggle fullscreen" title="Toggle fullscreen" onclick="pcFullscreen(event)">⛶</button><button class="pc-win-btn" aria-label="Sign out" title="Sign out" onclick="pcSignOut()">↪</button></div></div><div class="pc-desktop"><div class="pc-icons">${apps.map(a=>pcAppButton(...a)).join('')}</div>${app}${S.pcStartOpen?`<div class="pc-start-menu"><h3>Signal OS</h3><div class="pc-start-grid">${apps.map(a=>`<button onclick="pcOpen('${a[0]}')"><span>${pcIcon(a[0])}</span>${a[2]}</button>`).join('')}</div><button class="btn alt small" style="margin-top:10px" onclick="pcSignOut()">Sign out</button></div>`:''}</div><div class="pc-taskbar"><button class="pc-start" aria-label="Open Start menu" onclick="pcStartOpen=!pcStartOpen;pcDesktop()"><span>${pcIcon('start')}</span></button>${apps.slice(0,7).map(a=>pcAppButton(a[0],a[1],a[2],true)).join('')}<div class="pc-task-clock"><span id="pcClock">${pcTime()}</span><br><span id="pcDate">${pcDate()}</span></div></div></section>`;if(S.pcApp==='calculator')pcCalcRefresh();pcClockTimer=setInterval(()=>{let t=$('#pcClock'),d=$('#pcDate');if(t)t.textContent=pcTime();if(d)d.textContent=pcDate()},1000)}
function pcOpen(app){clearTimeout(pcAppLoadTimer);S.pcApp=app;pcWindowLayout='partial';pcStartOpen=false;pcAppLoading=true;pcDesktop();pcAppLoadTimer=setTimeout(()=>{if(view==='pc'&&S.pcApp===app){pcAppLoading=false;pcDesktop()}},420)}
function pcClose(){clearTimeout(pcAppLoadTimer);pcAppLoading=false;S.pcApp='';pcDesktop()}
function pcBrowserBody(){let page=S.pcBrowserPage||'home',address=page==='viewtube'?'youtube.com':page==='results'?'signal.local/search':'signal.local/start';let content='';if(page==='viewtube')content=pcViewTubePage();else if(page==='results')content=`<div class="pc-search-results"><div class="eyebrow">SEARCH RESULTS</div><h3>No results for “${escapeHtml(S.pcSearchQuery||'')}”.</h3><p class="muted">Try searching <strong>youtube.com</strong>.</p><button class="btn alt small" onclick="pcNavigate('home')">Back to search</button></div>`;else content=`<div class="pc-browser-home"><div class="eyebrow">SIGNAL BROWSER · LOCAL START</div><h3>Search the web</h3><p class="muted">This browser is an offline demo. Search for the supported sample site to visit it.</p><form class="pc-web-search" onsubmit="pcBrowserSearch(event)"><input id="pcWebSearch" value="" placeholder="Search or enter a website" autocomplete="off" aria-label="Search websites"><button class="btn small" type="submit">Search</button></form><div class="pc-search-tip"><span>⌕</span><div><strong>Looking for a video site?</strong><div class="muted">Search for <b>youtube.com</b> to open the local ViewTube demo.</div></div></div><div class="pc-browser-tile" style="cursor:default"><span>🛡️</span><div><strong>Signal Safety Guide</strong><div class="muted">A local reminder: pause and verify before sharing information.</div></div></div></div>`;return `<div class="pc-browser-chrome"><button title="Back" aria-label="Back" onclick="pcBrowserBack()">‹</button><button title="Home" aria-label="Home" onclick="pcNavigate('home')">⌂</button><input value="${address}" readonly aria-label="Local address"><span class="pill">OFFLINE</span></div>${content}`}
function pcBrowserSearch(e){e.preventDefault();let input=$('#pcWebSearch'),query=input.value.trim();if(!query)return;S.pcSearchQuery=query;if(query.toLowerCase()==='youtube.com'){S.pcBrowserPage='viewtube';S.pcVideoPage='home';S.pcVideoSearch='';S.pcVideoPlaying=false;S.pcAdDismissed=false;S.pcAdSafe=null}else S.pcBrowserPage='results';pcDesktop()}

const PC_VIDEOS=[
{title:'The $1 Delivery Fee Trick',channel:'Signal Studio',duration:'4:18',views:'18K views',color:'#71a98d',lesson:'A tiny redelivery fee can be bait. Open the carrier app you already use and check there instead of tapping a surprise text link.'},
{title:'A Familiar Voice, A New Number',channel:'Agent Nova',duration:'6:02',views:'42K views',color:'#7a9cad',lesson:'Voice cloning can sound convincing. Hang up, call the person back on a number you already know, and verify with someone else.'},
{title:'The Fake Bank Alert Playbook',channel:'Bytewise Basics',duration:'5:36',views:'31K views',color:'#c18768',lesson:'Threats and look-alike sender addresses push you to act fast. Open your bank app directly or call the number on your card.'},
{title:'Job Offer Wants You to Pay?',channel:'Signal Studio',duration:'3:51',views:'24K views',color:'#b39a57',lesson:'A real employer should not ask you to deposit a check, buy equipment from a chosen vendor, and send money back. Verify the employer independently.'},
{title:'Romance Scams: Spot the Investment Pivot',channel:'Agent Nova',duration:'7:14',views:'56K views',color:'#ad7089',lesson:'When affection turns into a secret investment pitch, pause. Do not send money or identity documents; talk it through with someone you trust.'},
{title:'One-Time Code? Keep It to Yourself',channel:'Secure Steps',duration:'2:48',views:'67K views',color:'#568f9c',lesson:'An unexpected sign-in code can mean someone else started a login. Never share it. Check account activity in the official app.'},
{title:'Did the Boss Really Send That Invoice?',channel:'Bytewise Basics',duration:'5:09',views:'15K views',color:'#847ba8',lesson:'Payment changes and secrecy are reasons to pause. Confirm through your usual approval process and a known contact.'},
{title:'Real Reminder or Fake Tech Support?',channel:'Secure Steps',duration:'4:42',views:'29K views',color:'#748e69',lesson:'Scary pop-ups that demand a phone call are a classic pressure trick. Close the tab and use your device maker’s normal support route.'},
{title:'Legit Message, Scam Message: What Changes?',channel:'Signal Studio',duration:'8:20',views:'83K views',color:'#638cae',lesson:'Urgency, secrecy, surprise payment, and requests for codes are warning signs. Legitimate messages can exist too: verify calmly through a familiar channel.'},
{title:'A QR Code Is Still a Link',channel:'Secure Steps',duration:'3:27',views:'12K views',color:'#a67c52',lesson:'Treat an unexpected QR code like any other link. Check where it leads before entering information and use the organization’s official app when possible.'},
{title:'Three Calm Steps Before You Tap',channel:'Agent Nova',duration:'2:59',views:'104K views',color:'#548c79',lesson:'Pause. Verify the sender using a contact method you already trust. Then decide what to do without pressure.'}
].map((v,i)=>({...v,id:i}));
function pcVideoHeader(){return `<div class="viewtube-head"><button class="viewtube-logo-button" aria-label="ViewTube home" onclick="S.pcVideoPage='home';S.pcAdDismissed=false;S.pcAdSafe=null;pcDesktop()"><span class="viewtube-play">▶</span> ViewTube</button><input class="viewtube-search" value="${escapeAttr(S.pcVideoSearch||'')}" placeholder="Search videos" aria-label="Search ViewTube videos" oninput="pcFilterVideos(this.value)"><span class="viewtube-avatar">${escapeHtml((S.pcUser||'A')[0].toUpperCase())}</span></div>`}
function pcVideoCard(v){return `<button class="vt-card" data-video-title="${escapeAttr((v.title+' '+v.channel).toLowerCase())}" onclick="pcChooseVideo(${v.id})"><div class="vt-thumb" style="--thumb:${v.color}"><span class="vt-play">▶</span><span class="vt-duration">${v.duration}</span><span class="vt-thumb-caption">SIGNAL//SAFE · FIELD NOTES</span></div><div class="vt-card-meta"><span class="vt-channel-avatar">${v.channel[0]}</span><div><strong>${v.title}</strong><small>${v.channel} · ${v.views} · Local demo</small></div></div></button>`}
function pcViewTubePage(){let page=S.pcVideoPage||'home',video=PC_VIDEOS[S.pcVideoIndex||0],other=PC_VIDEOS.filter(v=>v.id!==video.id);if(page==='watch')return `<div class="viewtube-page">${pcVideoHeader()}<div class="vt-watch-grid"><main><div class="vt-player ${S.pcVideoPlaying?'is-playing':''}" style="--thumb:${video.color}"><div class="vt-scene"><span>◉</span><strong>${S.pcVideoPlaying?'NOW PLAYING · LOCAL PREVIEW':'VIDEO PREVIEW'}</strong></div><button aria-label="${S.pcVideoPlaying?'Pause':'Play'} ${video.title}" onclick="pcToggleVideo()">${S.pcVideoPlaying?'Ⅱ':'▶'}</button><div class="vt-player-title">${video.title}</div></div><div class="vt-timeline"><span style="width:${S.pcVideoPlaying?'36%':'0%'}"></span></div><div class="vt-watch-title"><h3>${video.title}</h3><span class="pill">${video.duration}</span></div><div class="vt-channel-row"><span class="vt-channel-avatar large">${video.channel[0]}</span><div><strong>${video.channel}</strong><small>Local learning channel · 12.4K subscribers</small></div><button class="vt-subscribe ${S.pcVideoSubscribed?'subscribed':''}" onclick="pcToggleSubscribe()">${S.pcVideoSubscribed?'Subscribed':'Subscribe'}</button><button class="vt-like" onclick="pcLikeVideo()">♡ ${S.pcVideoLikes||0}</button></div><div class="vt-description"><strong>${video.views} · Local demo · No network stream</strong><p>${video.lesson}</p><p>Field note: take your time. Verification through a known channel is a strong next step.</p></div></main><aside class="vt-recommendations"><strong>Up next</strong>${other.slice(0,7).map(pcVideoCard).join('')}</aside></div></div>`;let q=(S.pcVideoSearch||'').trim().toLowerCase(),matches=PC_VIDEOS.filter(v=>(v.title+' '+v.channel+' '+v.lesson).toLowerCase().includes(q));return `<div class="viewtube-page">${pcVideoHeader()}<div class="viewtube-nav"><span>All</span><span>Text scams</span><span>Calls</span><span>Jobs & money</span><span>Account safety</span><span>Local demo library</span></div><div class="vt-section-title"><h3>${q?'Search results':'Recommended'}</h3><small>${matches.length} local videos</small></div><div class="vt-grid">${matches.map(pcVideoCard).join('')}</div>${S.pcAdDismissed?`<div class="vt-ad-feedback ${S.pcAdSafe?'safe':'unsafe'}"><strong>${S.pcAdSafe?'Correct button — pop-up closed and reported.':'Wrong button. You were supposed to close and report the ad.'}</strong><p>A surprise prize that asks for a fee is a red flag. Verify promotions through the site's normal channels. No link or payment was activated.</p><button class="vt-ad-replay" onclick="pcReplayAd()">Try the ad check again</button></div>`:`<div class="vt-ad-overlay"><section class="vt-ad-popup" role="dialog" aria-labelledby="vtAdTitle"><div class="vt-ad-top"><span>✦ Sponsored message · training example</span><span>Pop-up ad</span></div><h3 id="vtAdTitle">Creator gear giveaway!</h3><p>You’ve been selected to claim a studio kit. Pay a small shipping fee at <b>creator-bonus.example.test</b>.</p><div class="vt-ad-note">This fictional ad is a scam-prevention drill. Close and report it for 10 XP. No link or payment is active.</div><div class="vt-ad-actions"><button onclick="pcAnswerAd(true)">Close and report</button><button class="claim" onclick="pcAnswerAd(false)">Claim the offer</button></div></section></div>`}<div class="vt-no-results ${matches.length?'hidden':''}">No videos found for “${escapeHtml(S.pcVideoSearch||'')}”. Try another search.</div></div>`}
function pcFilterVideos(query){S.pcVideoSearch=query;let q=query.trim().toLowerCase(),matches=PC_VIDEOS.filter(v=>(v.title+' '+v.channel+' '+v.lesson).toLowerCase().includes(q));document.querySelectorAll('.vt-card[data-video-title]').forEach(card=>card.hidden=!card.dataset.videoTitle.includes(q));let empty=$('.vt-no-results');if(empty){empty.classList.toggle('hidden',matches.length>0);empty.textContent=`No videos found for “${query}”. Try another search.`}let count=$('.vt-section-title small');if(count)count.textContent=`${matches.length} local videos`}
function pcToggleSubscribe(){S.pcVideoSubscribed=!S.pcVideoSubscribed;persist();pcDesktop()}

function pcNavigate(page){S.pcBrowserPage=page;if(page==='home')S.pcSearchQuery='';if(page==='viewtube'){S.pcVideoPage='home';S.pcAdDismissed=false;S.pcAdSafe=null}S.pcVideoPlaying=false;pcDesktop()}
function pcBrowserBack(){if(S.pcBrowserPage==='viewtube'&&S.pcVideoPage==='watch'){S.pcVideoPage='home';S.pcVideoPlaying=false;S.pcAdDismissed=false;S.pcAdSafe=null;pcDesktop()}else pcNavigate('home')}
function pcFilterVideos(query){let q=query.toLowerCase();document.querySelectorAll('[data-video-title]').forEach(x=>x.hidden=!x.dataset.videoTitle.includes(q))}
function pcLikeVideo(){S.pcVideoLikes=(S.pcVideoLikes||0)+1;persist();let n=$('#pcLikeCount');if(n)n.textContent=S.pcVideoLikes}

const PC_DRILLS=[
{id:'delivery',label:'Delivery text',channel:'Text message · ParcelPal',content:'Your parcel is held. Pay a $1.25 redelivery fee at parcel-pal.example.test to release it.',flags:'Unexpected fee · unfamiliar link · pressure about a delivery',safe:'Ignore/report the text, then check delivery in the carrier app you already use.',unsafe:'Pay through the message link.',why:'A small fee feels harmless. Surprise payment links and urgency are useful warning signs.'},
{id:'bank',label:'Bank alert',channel:'Email · Northstar Account Desk',content:'URGENT: Your account will close today. Sign in at northstar-secure.example.test to restore access.',flags:'Threat of account loss · look-alike domain · urgent sign-in request',safe:'Open your bank app directly or call the number on your card.',unsafe:'Use the message link and enter your sign-in details.',why:'Fear can rush people into a fake sign-in page. Verify independently through a known channel.'},
{id:'voice',label:'Family emergency call',channel:'Incoming call · caller sounds familiar',content:'“I’m in trouble. Send help right now, and please don’t tell anyone yet.”',flags:'Emotional urgency · secrecy · voice alone treated as proof',safe:'Hang up and call the person back on a number you already know; check with another family member.',unsafe:'Send money or personal information because the voice sounds familiar.',why:'A voice can be imitated. A separate call to a known number can break the pressure.'},
{id:'support',label:'Tech-support pop-up',channel:'Browser warning · unrequested',content:'DEVICE ALERT: Call 1-555-0142 now. Do not close this page or your files will be erased.',flags:'Scary warning · unrequested number · pressure not to close page',safe:'Close the tab or browser and use your device maker’s normal support channel.',unsafe:'Call the number shown in the pop-up.',why:'A browser page cannot reliably diagnose your device. Scammers use alarming messages to make you call them.'},
{id:'job',label:'Job offer',channel:'Recruiting message · BrightPath Testing',content:'You’re hired without an interview. Deposit our check, buy equipment from our vendor, and send back the extra.',flags:'No real hiring process · asks you to send money · check refund request',safe:'Do not deposit/send money. Verify the employer through contact details you find independently.',unsafe:'Deposit the check and send the leftover funds.',why:'A fake check may appear to clear before it is rejected, leaving you responsible for money sent back.'},
{id:'contest',label:'Contest-vote message',channel:'Ping · New profile',content:'“Can you vote for my entry? Sign in with your mail account at vote-friends.example.test — it only takes a second.”',flags:'Unexpected sign-in page · asks for account credentials · unfamiliar sender',safe:'Do not open the sign-in page. Contact your friend through the account or number you already know.',unsafe:'Enter your email password to cast the vote.',why:'A fake contest can be a pretext to steal account credentials. Verify the request using a separate known channel.'},
+{id:'friend',label:'Friend needs a quick favor',channel:'Text · New number claiming to be a friend',content:'“Hey, new phone. I’m stuck—can you buy a gift card and send me the code? Please keep it quiet.”',flags:'New number · asks for gift-card codes · secrecy and urgency',safe:'Do not buy or send anything. Call your friend on the number you already have.',unsafe:'Buy the card and text its code to the new number.',why:'Impersonators use urgency and secrecy to make unusual requests feel normal. Verify with the person directly.'},
+{id:'code',label:'One-time code request',channel:'Ping · Unknown number',content:'“A sign-in code came to your phone by mistake. Send it to me so I can finish logging in.”',flags:'Unexpected code · asks you to share it · unfamiliar contact',safe:'Never share the code. Open the service’s official app and review account activity.',unsafe:'Reply with the code to help the sender.',why:'Someone may be using the code to enter your account. Real support should not ask you to share it.'},
{id:'invoice',label:'Invoice change',channel:'Work chat · Executive Office',content:'“Pay this revised invoice today. I’m busy, so skip the callback and keep this confidential.”',flags:'Bypasses normal process · secrecy · payment change',safe:'Verify the change with a known contact using your usual approval process.',unsafe:'Pay quickly based on the message alone.',why:'Authority and time pressure can make people skip safeguards. Routine verification protects everyone.'}
];
function pcSafetyLab(){let a=S.pcDrillAnswers||{},done=Object.keys(a).length,blocked=Object.values(a).filter(Boolean).length;return `<div class="eyebrow">SIGNAL OS · DEFENSE TRAINING</div><h3>🛡️ Scam Safety Lab</h3><p class="muted">Inspect each fictional alert and choose how to stop it. Each correct response earns 10 XP. Nothing here opens a link, calls a number, or sends a message.</p><div class="pc-lab-summary"><strong>${blocked} prevented</strong><span>${done} / ${PC_DRILLS.length} scenarios reviewed</span></div><div class="pc-drill-list">${PC_DRILLS.map(d=>{let answer=a[d.id];return `<article class="pc-drill ${answer===true?'drill-safe':answer===false?'drill-missed':''}"><div class="pc-drill-head"><span class="pill">${d.label}</span><span class="pc-drill-source">${d.channel}</span></div><div class="pc-drill-message">${d.content}</div><div class="pc-drill-flags"><strong>Look for:</strong> ${d.flags}</div>${answer===undefined?`<div class="pc-drill-actions"><button class="safe-choice" onclick="pcAnswerDrill('${d.id}',true)">${d.safe}</button><button class="risky-choice" onclick="pcAnswerDrill('${d.id}',false)">${d.unsafe}</button></div>`:`<div class="pc-drill-feedback"><strong>${answer?'Correct button — threat prevented. Nice work.':'Wrong button. You were supposed to: '+d.safe}</strong><p>${d.why}</p>${answer?'':`<button class="btn alt small" onclick="pcRetryDrill('${d.id}')">Try again</button>`}<p><b>Safer move:</b> ${d.safe}</p></div>`}</article>`}).join('')}</div><button class="btn alt small" onclick="pcResetDrills()">Reset drills</button>`}
function awardPcXp(){S.correct++;S.answered++;addXP(10);persist();toast('+10 XP · Nice defense')}
function pcAnswerDrill(id,prevented){S.pcDrillAnswers=S.pcDrillAnswers||{};if(S.pcDrillAnswers[id]!==undefined)return;S.pcDrillAnswers[id]=prevented;if(prevented)awardPcXp();persist();pcDesktop()}
function pcRetryDrill(id){delete S.pcDrillAnswers[id];persist();pcDesktop()}
function pcResetDrills(){S.pcDrillAnswers={};persist();pcDesktop()}
function pcAnswerAd(safe){if(S.pcAdDismissed)return;S.pcAdDismissed=true;S.pcAdSafe=safe;if(safe)awardPcXp();persist();pcDesktop()}
function pcReplayAd(){S.pcAdDismissed=false;S.pcAdSafe=null;persist();pcDesktop()}

function pcAppBody(app){let title={files:'File Explorer',mail:'Signal Mail',browser:'Signal Browser',notes:'Notepad',calendar:'Calendar',calculator:'Calculator',settings:'Desktop Settings',messages:'Ping · Messages',safety:'Safety Lab'}[app]||'App';if(pcAppLoading)return `<section class="pc-window layout-${pcWindowLayout}" role="dialog" aria-label="Loading ${title}"><div class="pc-window-title" onpointerdown="pcDragStart(event)"><span>${title}</span><button class="pc-win-btn close" aria-label="Close window" onclick="pcClose()">×</button></div><div class="pc-loading-state"><div><div class="pc-spinner"></div>Opening ${title}…</div></div></section>`;let body='';if(app==='files')body=`<h3>📁 This PC</h3><p>Your local demo workspace. These are sample folders, not files on your actual computer.</p><div class="pc-file-item">📁 <strong>Training</strong><span class="muted"> · scam spotting practice</span></div><div class="pc-file-item">📁 <strong>Notes</strong><span class="muted"> · saved in this browser</span></div><div class="pc-file-item">📄 <strong>Readme.txt</strong><div class="muted">Welcome to Signal OS. Explore the apps from the desktop or taskbar.</div></div>`;if(app==='mail')body=`<h3>✉️ Inbox <span class="pill">4 DEMO MESSAGES</span></h3><p class="muted">Fictional local messages. Nothing here is sent or received online.</p><div class="pc-inbox-item"><strong>Team Training</strong><span class="muted"> · Today</span><p>New practice zone opens this afternoon. No rush, rookie.</p></div><div class="pc-inbox-item"><strong>Maple Library</strong><span class="muted"> · Yesterday</span><p>Your book is due Friday. Check the library app you already use.</p></div><div class="pc-inbox-item"><strong>ParcelPal Alert</strong><span class="pill">SUSPICIOUS</span><p>Message says a $1.25 redelivery fee is needed at parcel-pal.example.test.</p><button class="btn alt small" onclick="pcOpen('safety')">Review in Safety Lab</button></div><div class="pc-inbox-item"><strong>Security Desk</strong><span class="muted"> · Monday</span><p>Reminder: never share one-time sign-in codes with anyone.</p></div>`;if(app==='browser')body=pcBrowserBody();if(app==='notes')body=`<h3>📝 Notepad</h3><p>Your notes save automatically in this browser.</p><textarea class="pc-note-area" aria-label="Local notes" placeholder="Type a reminder or jot down your next training goal…" oninput="pcSaveNotes(this.value)">${escapeHtml(S.pcNotes||'')}</textarea><div class="muted" style="text-align:right;margin-top:5px">Saved locally</div>`;if(app==='calendar')body=`<h3>🗓️ Calendar</h3><div class="pc-event"><strong>${pcDate()}</strong><p>Today · Your schedule is yours. No countdowns, no pressure.</p></div><div class="pc-event"><strong>2:30 PM · Agent practice</strong><p>Optional training round. Take a break whenever you need one.</p></div><div class="pc-event"><strong>All day · Keep your codes private</strong><p>A helpful security reminder from your local demo calendar.</p></div>`;if(app==='calculator')body=`<div class="pc-calc"><h3>🧮 Calculator</h3><div class="pc-calc-display" id="pcCalcDisplay">${escapeHtml(S.pcCalcValue||'0')}</div><div class="pc-calc-grid">${['7','8','9','÷','4','5','6','×','1','2','3','−','C','0','.','+','='].map(k=>`<button class="${'+−×÷='.includes(k)?'op':''}" onclick="calcPress('${k}')">${k}</button>`).join('')}</div></div>`;if(app==='safety')body=pcSafetyLab();if(app==='settings')body=`<h3>⚙️ Desktop Settings</h3><p>Choose a wallpaper for this demo desktop.</p><div class="row"><button class="btn alt small" onclick="pcWallpaper('mint')">🌿 Mint</button><button class="btn alt small" onclick="pcWallpaper('lake')">🌊 Lake</button><button class="btn alt small" onclick="pcWallpaper('dusk')">🌆 Dusk</button></div><div class="pc-event" style="margin-top:16px"><strong>Signed in as ${escapeHtml(S.pcUser)}</strong><p>Display name and notes remain in this browser’s local storage.</p><button class="btn pink small" onclick="pcSignOut()">Sign out of demo</button></div>`;if(app==='messages'){let contacts=['Mika','Jordan','Sam'];let contact=S.pcChatContact||'Mika',history=(S.pcChatHistory||[]).filter(x=>x.contact===contact);let greetings={Mika:'Hey! Want to compare notes after the training round?',Jordan:'I found a great tip: pause, then verify using a number you already trust.',Sam:'Hi! I saved you a spot in the practice room.'};body=`<h3>💬 Ping <span class="pill">LOCAL MESSAGES</span></h3><p class="muted">A private demo chat. Messages stay on this device and are never sent.</p><div class="pc-message-alerts"><div class="pc-inbox-item"><strong>Unknown number · code request</strong><p>“A sign-in code came to you by mistake. Send it back?”</p></div><div class="pc-inbox-item"><strong>New profile · contest link</strong><p>“Vote for me—sign in at vote-friends.example.test.”</p></div><div class="pc-inbox-item"><strong>Friend on a new number</strong><p>“Buy a gift card and send me the code. Keep it quiet.”</p></div><button class="btn alt small" onclick="pcOpen('safety')">Practice safe responses in Safety Lab</button></div><div class="chat-layout"><div class="chat-contacts">${contacts.map(n=>`<button class="chat-contact ${contact===n?'active':''}" onclick="pcSelectChat('${n}')"><span>${n[0]}</span>${n}</button>`).join('')}</div><div class="chat-room"><strong>${contact}</strong><div class="chat-log"><div class="chat-bubble">${greetings[contact]}</div>${history.map(x=>`<div class="chat-bubble mine">${escapeHtml(x.text)}</div>`).join('')}</div><form class="chat-compose" onsubmit="pcSendMessage(event)"><input id="pcChatInput" maxlength="240" autocomplete="off" placeholder="Write a local message…" aria-label="Message to ${contact}"><button type="submit">Send</button></form></div></div>`}return `<section class="pc-window layout-${pcWindowLayout}" role="dialog" aria-label="${title}"><div class="pc-window-title" onpointerdown="pcDragStart(event)"><span>${title}</span><div class="pc-window-controls"><button class="pc-win-btn" aria-label="Minimize window" title="Minimize" onclick="pcClose()">−</button><div class="pc-size-control"><button class="pc-win-btn pc-size-trigger" aria-label="Choose window size" title="Window size options" aria-haspopup="menu" aria-expanded="false" onclick="pcToggleSizeMenu(event)">◱</button><div class="pc-size-menu" role="menu"><strong>Window size</strong><button role="menuitem" data-window-size="partial"><span>▢</span>Windowed</button><button role="menuitem" data-window-size="left"><span>◧</span>Left half</button><button role="menuitem" data-window-size="right"><span>◨</span>Right half</button><button role="menuitem" data-window-size="max"><span>▣</span>Fill desktop</button></div></div><button class="pc-win-btn close" aria-label="Close window" onclick="pcClose()">×</button></div></div><div class="pc-window-body">${body}</div></section>`}
function pcToggleSizeMenu(e){e.stopPropagation();let c=e.currentTarget.closest('.pc-size-control');c.classList.toggle('open');e.currentTarget.setAttribute('aria-expanded',String(c.classList.contains('open')))}
function pcSetWindowLayout(mode){let w=$('.pc-window');if(!w)return;pcWindowLayout=mode;w.classList.remove('layout-partial','layout-left','layout-right','layout-max');w.classList.add('layout-'+mode);Object.assign(w.style,{left:'',right:'',top:'',bottom:'',width:'',height:'',minWidth:'',maxWidth:'',maxHeight:'',transform:'',resize:'',transition:'left .2s ease,top .2s ease,width .2s ease,height .2s ease,right .2s ease,bottom .2s ease'});if(mode==='partial'){Object.assign(w.style,{left:'50%',top:'50%',right:'auto',bottom:'auto',width:'min(620px, calc(100% - 22px))',height:'auto',minWidth:'min(320px, calc(100% - 14px))',maxWidth:'calc(100% - 14px)',maxHeight:'calc(100% - 28px)',transform:'translate(-50%, -54%)',resize:'both'})}else if(mode==='left'){Object.assign(w.style,{left:'8px',right:'auto',top:'8px',bottom:'8px',width:'calc(50% - 12px)',height:'auto',minWidth:'0',maxWidth:'none',maxHeight:'none',transform:'none',resize:'none'})}else if(mode==='right'){Object.assign(w.style,{left:'auto',right:'8px',top:'8px',bottom:'8px',width:'calc(50% - 12px)',height:'auto',minWidth:'0',maxWidth:'none',maxHeight:'none',transform:'none',resize:'none'})}else if(mode==='max'){Object.assign(w.style,{left:'8px',right:'8px',top:'8px',bottom:'8px',width:'auto',height:'auto',minWidth:'0',maxWidth:'none',maxHeight:'none',transform:'none',resize:'none'})}let c=$('.pc-size-control');if(c)c.classList.remove('open');let t=$('.pc-size-trigger');if(t)t.setAttribute('aria-expanded','false');toast(({partial:'Windowed size',left:'Moved to left half',right:'Moved to right half',max:'Filled desktop'}[mode]||'Window size updated'))}
function pcDragStart(e){if(e.target.closest('button'))return;let w=e.currentTarget.closest('.pc-window');if(!w||['left','right','max'].some(m=>w.classList.contains('layout-'+m)))return;let area=w.parentElement,wr=w.getBoundingClientRect(),ar=area.getBoundingClientRect();w.style.transform='none';w.style.left=`${wr.left-ar.left}px`;w.style.top=`${wr.top-ar.top}px`;w.style.right='auto';pcDragState={win:w,area,dx:e.clientX-wr.left,dy:e.clientY-wr.top};w.setPointerCapture?.(e.pointerId);e.preventDefault()}
function pcDragMove(e){if(!pcDragState)return;let {win,area,dx,dy}=pcDragState,ar=area.getBoundingClientRect(),maxX=Math.max(0,ar.width-win.offsetWidth),maxY=Math.max(0,ar.height-win.offsetHeight);win.style.left=`${Math.min(maxX,Math.max(0,e.clientX-ar.left-dx))}px`;win.style.top=`${Math.min(maxY,Math.max(0,e.clientY-ar.top-dy))}px`}
function pcDragEnd(){if(pcDragState){pcDragState=null}}
window.addEventListener('pointermove',pcDragMove);window.addEventListener('pointerup',pcDragEnd);window.addEventListener('pointercancel',pcDragEnd);
function pcToggleVideo(){S.pcVideoPlaying=!S.pcVideoPlaying;pcDesktop()}
function pcChooseVideo(i){S.pcVideoIndex=i;S.pcVideoPlaying=false;S.pcVideoPage='watch';pcDesktop()}
function pcSelectChat(name){S.pcChatContact=name;pcDesktop()}
function pcSendMessage(e){e.preventDefault();let input=$('#pcChatInput'),text=input.value.trim();if(!text)return;S.pcChatHistory.push({contact:S.pcChatContact||'Mika',text});persist();pcDesktop()}

function pcSaveNotes(value){S.pcNotes=value;persist()}
function pcWallpaper(value){S.pcWallpaper=value;persist();pcDesktop()}
function pcCalcRefresh(){let d=$('#pcCalcDisplay');if(d)d.textContent=S.pcCalcValue||'0'}
function calcPress(k){let v=S.pcCalcValue||'0';if(k==='C'){S.pcCalcValue='0';S.pcCalcAcc=null;S.pcCalcOp=null;S.pcCalcFresh=false}else if(['+','−','×','÷'].includes(k)){if(S.pcCalcAcc!==null&&S.pcCalcOp&&!S.pcCalcFresh)calcApply();S.pcCalcAcc=Number(S.pcCalcValue)||0;S.pcCalcOp=k;S.pcCalcFresh=true}else if(k==='='){if(S.pcCalcOp)calcApply();S.pcCalcOp=null;S.pcCalcAcc=null;S.pcCalcFresh=true}else if(k==='.'){if(S.pcCalcFresh){S.pcCalcValue='0.';S.pcCalcFresh=false}else if(!v.includes('.'))S.pcCalcValue=v+'.'}else{S.pcCalcValue=S.pcCalcFresh||v==='0'?k:v+k;S.pcCalcFresh=false}pcCalcRefresh();persist()}
function calcApply(){let a=Number(S.pcCalcAcc),b=Number(S.pcCalcValue),out=0;if(S.pcCalcOp==='+')out=a+b;if(S.pcCalcOp==='−')out=a-b;if(S.pcCalcOp==='×')out=a*b;if(S.pcCalcOp==='÷')out=b===0?'Nope':a/b;S.pcCalcValue=typeof out==='number'?String(Number(out.toFixed(8))):out}

function render(v){
  clearInterval(roundTimer);roundTimer=null;cancelQuestionRequest();round=null;nowQ=null;
  clearInterval(pcClockTimer);clearTimeout(pcAppLoadTimer);clearTimeout(pcLoadingTimer);pcAppLoading=false;
  if(v==='home')home();else if(v==='zones')zones();else if(v==='guide')fieldGuide();else if(v==='achievements')achievements();else if(v==='shop')shop();else if(v==='settings')settings();else if(v==='pc')pcMode();else if(v==='multiplayer'){saveView('multiplayer');multiplayer()}
  animateScreen();main.focus();window.scrollTo({top:0,behavior:reducedMotion?'auto':'smooth'});
}
function escapeHtml(x){return String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}function escapeAttr(x){return escapeHtml(x)}
const BOOT_LINES=[
  'Initializing training environment...',
  'Loading scenario library... OK',
  'Calibrating scam radar... OK',
  'Sandbox verified: no real links, no real money... OK',
  'Agent console ready.'
];
const motionPreference=window.matchMedia('(prefers-reduced-motion: reduce)');
let reducedMotion=motionPreference.matches;
motionPreference.addEventListener('change',event=>{reducedMotion=event.matches});
let launchStage='splash',launchTimers=[],audioContext=null,modalReturnFocus=null;
function announce(message){$('#live').textContent=message}
function later(fn,ms){launchTimers.push(setTimeout(fn,ms))}
function cancelLaunchTimers(){launchTimers.forEach(clearTimeout);launchTimers=[]}
function validateCodename(value){
  const name=value.trim();
  if(!name)return 'Choose a codename to start your training.';
  if(name.length<3||name.length>16)return 'Use between 3 and 16 characters.';
  if(!/^[A-Za-z0-9 _-]+$/.test(name))return 'Use letters, numbers, spaces, underscores, or hyphens only.';
  if(['fuck','shit','bitch','asshole','porn'].some(word=>name.toLowerCase().includes(word)))return 'Please choose a friendly codename.';
  return '';
}
function codenameForm(prefix,changing=false){
  return `<form class="codename-form" id="${prefix}Form" novalidate>
    <label for="${prefix}Input">Codename</label>
    <input id="${prefix}Input" name="codename" type="text" maxlength="16" autocomplete="off" spellcheck="false" aria-describedby="${prefix}Hint ${prefix}Counter ${prefix}Error" ${changing?'':'autofocus'} value="${escapeAttr(changing?S.username:'')}">
    <div class="input-meta"><span id="${prefix}Hint">3–16 characters</span><span id="${prefix}Counter">0 / 16</span></div>
    <p class="form-error" id="${prefix}Error" aria-live="polite"></p>
    <div class="actions"><button type="button" class="btn alt" id="${prefix}Suggest">Suggest a codename</button><button type="submit" class="btn">${changing?'Save codename':'Start training'}</button></div>
  </form>`;
}
function bindCodenameForm(prefix,changing=false){
  const input=$(`#${prefix}Input`),counter=$(`#${prefix}Counter`),error=$(`#${prefix}Error`);
  function update(){counter.textContent=`${input.value.length} / 16`;error.textContent='';input.removeAttribute('aria-invalid')}
  input.addEventListener('input',update);
  $(`#${prefix}Suggest`).addEventListener('click',()=>{
    const adjectives=['Neon','Quiet','Clever','Bright','Pixel','Swift','Cosmic','Lucky'];
    const animals=['Fox','Signal','Otter','Owl','Panda','Comet','Sparrow','Scout'];
    input.value=adjectives[Math.floor(Math.random()*adjectives.length)]+animals[Math.floor(Math.random()*animals.length)]+Math.floor(Math.random()*100);
    update();input.focus();
  });
  $(`#${prefix}Form`).addEventListener('submit',event=>{
    event.preventDefault();
    const message=validateCodename(input.value);
    if(message){error.textContent=message;input.setAttribute('aria-invalid','true');input.focus();return}
    const oldName=S.username;
    S.username=input.value.trim();
    if(!persist()){S.username=oldName;error.textContent='Your codename could not be saved in this browser. Please enable local storage and try again.';input.focus();return}
    sync();
    if(changing){render('settings');toast('Codename updated.')}
    else {$('#launch').hidden=true;$('#launch').innerHTML='';$('#app').hidden=false;launchStage='game';render('home');announce(`Welcome, ${S.username}. Your training is ready.`)}
  });
  update();
}
function showCodenameScreen(){
  cancelLaunchTimers();launchStage='codename';
  $('#app').hidden=true;
  const launch=$('#launch');launch.hidden=false;launch.classList.remove('leaving');
  launch.innerHTML=`<div class="launch-stage codename-card"><div class="eyebrow">YOUR AGENT IDENTITY</div><h1>Welcome, new agent. Choose your codename.</h1><p class="muted">Don't use your real name, email, or personal info. Pick a codename.</p>${codenameForm('newName')}</div>`;
  bindCodenameForm('newName');$('#newNameInput').focus();announce('Choose a codename to start training.');
}
function finishLaunch(){
  if(launchStage!=='splash'&&launchStage!=='boot')return;
  cancelLaunchTimers();
  if(typeof S.username!=='string'||validateCodename(S.username)){showCodenameScreen();return}
  S.username=S.username.trim();launchStage='game';$('#launch').hidden=true;$('#launch').innerHTML='';$('#app').hidden=false;sync();render('home');announce(`Welcome back, ${S.username}. Your training is ready.`);
}
function startBoot(returning){
  if(launchStage!=='splash')return;
  launchStage='boot';const launch=$('#launch');launch.classList.remove('leaving');
  $('#splashStage').hidden=true;$('#bootStage').hidden=false;announce('Starting the training environment.');
  const lines=$('#bootLines'),bar=$('#bootFill'),progress=$('#bootProgress');
  let lineIndex=0;
  function nextLine(){
    if(launchStage!=='boot')return;
    if(lineIndex===BOOT_LINES.length){later(finishLaunch,reducedMotion?20:120);return}
    const text=BOOT_LINES[lineIndex],line=document.createElement('div');line.className='boot-line';lines.append(line);
    let character=0;
    function type(){
      if(launchStage!=='boot')return;
      character=reducedMotion?text.length:character+1;
      line.textContent=text.slice(0,character);
      if(character%8===1)sound(510+lineIndex*35,.025);
      if(character<text.length)later(type,returning?7:15);
      else {lineIndex++;const percent=Math.round(lineIndex/BOOT_LINES.length*100);bar.style.width=percent+'%';progress.setAttribute('aria-valuenow',percent);later(nextLine,reducedMotion?5:returning?20:120)}
    }
    type();
  }
  nextLine();
}
function startLaunch(){
  const returning=typeof S.username==='string'&&!validateCodename(S.username);
  announce('Cyber Safe logo. Starting your training console.');
  $('#skipLaunch').addEventListener('click',finishLaunch);
  $('#skipLaunch').focus();
  const duration=reducedMotion?80:returning?600:2450;
  if(!reducedMotion&&!returning)later(()=>$('#launch').classList.add('leaving'),duration-350);
  later(()=>startBoot(returning),duration);
}
function closeCelebration(){
  $('#modalRoot').innerHTML='';
  if(modalReturnFocus&&modalReturnFocus.isConnected&&!modalReturnFocus.disabled)modalReturnFocus.focus();else main.focus();
  modalReturnFocus=null;
}
document.addEventListener('keydown',event=>{
  if((launchStage==='splash'||launchStage==='boot')&&[' ','Enter','Escape'].includes(event.key)){event.preventDefault();finishLaunch();return}
  const dialog=$('#modalRoot [role="dialog"]');
  if(!dialog)return;
  if(event.key==='Escape'){event.preventDefault();if(dialog.classList.contains('progress-modal'))closeCareerProgress();else closeCelebration();return}
  if(event.key==='Tab'){
    const controls=[...dialog.querySelectorAll('button:not(:disabled),[href],input:not(:disabled),[tabindex]:not([tabindex="-1"])')];
    if(!controls.length){event.preventDefault();return}
    const first=controls[0],last=controls[controls.length-1];
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}
    else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}
  }
});

document.querySelectorAll('.navbtn').forEach(b=>b.addEventListener('click',()=>render(b.dataset.view)));
document.addEventListener('click',e=>{let option=e.target.closest('[data-window-size]');if(option){e.preventDefault();e.stopPropagation();pcSetWindowLayout(option.dataset.windowSize)}});
$('#mute').onclick=toggleSound;
sync();startLaunch();
setInterval(()=>{if(Date.now()-S.sessionStart>25*60*1000&&!S.longNudge){S.longNudge=true;toast('You’ve been training for a while. Take a break whenever you need one.');persist()}},60000);
</script></body></html>"""


class WebsiteHandler(BaseHTTPRequestHandler):
    """Serve the game page and ephemeral LAN race room API."""

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/race/room":
            query = parse_qs(parsed.query)
            code = query.get("code", [""])[0].upper()
            player_id = query.get("player", [""])[0]
            with ROOM_LOCK:
                room = ROOMS.get(code)
                if not room or player_id not in room["players"]:
                    self._json({"error": "Room or player not found."}, 404)
                    return
                room["players"][player_id]["last_seen"] = time.time()
                self._json({"room": self._public_room(room)})
            return
        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 20_000)
            data = json.loads(self.rfile.read(length) or b"{}")
            path = urlparse(self.path).path
            if path == "/claim-question":
                content = data.get("content") if isinstance(data, dict) else None
                if (
                    not isinstance(content, str)
                    or not content.strip()
                    or len(content) > 4000
                ):
                    self._json({"error": "Invalid question content."}, 400)
                    return
                digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
                try:
                    with closing(
                        sqlite3.connect(QUESTION_HISTORY, timeout=10)
                    ) as database:
                        with database:
                            database.execute(
                                "CREATE TABLE IF NOT EXISTS question_history (id INTEGER PRIMARY KEY AUTOINCREMENT, digest TEXT NOT NULL UNIQUE)"
                            )
                            result = database.execute(
                                "INSERT OR IGNORE INTO question_history (digest) VALUES (?)",
                                (digest,),
                            )
                            reference = result.lastrowid if result.rowcount else None
                except sqlite3.Error as error:
                    self.log_error("Could not check question history: %s", error)
                    self._json({"error": "The question history is unavailable."}, 503)
                    return
                self._json(
                    {"reference": reference}
                    if reference is not None
                    else {"used": True},
                    201 if reference is not None else 200,
                )
                return
            if path == "/api/race/join":
                with ROOM_LOCK:
                    action = data.get("action")
                    code = str(data.get("code", "")).strip().upper()
                    if action == "create":
                        now = time.time()
                        for old_code, old_room in list(ROOMS.items()):
                            if (
                                now - old_room.get("last_active", old_room["created"])
                                > 6 * 60 * 60
                            ):
                                ROOMS.pop(old_code, None)
                        if len(ROOMS) >= 100:
                            self._json(
                                {
                                    "error": "The room service is busy. Try again shortly."
                                },
                                503,
                            )
                            return
                        code = "".join(
                            random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=6)
                        )
                        ROOMS[code] = {
                            "players": {},
                            "race": None,
                            "created": now,
                            "last_active": now,
                        }
                    elif action != "join" or code not in ROOMS:
                        self._json({"error": "That room code was not found."}, 404)
                        return
                    room = ROOMS[code]
                    if room["race"]:
                        self._json({"error": "That race has already started."}, 409)
                        return
                    if len(room["players"]) >= 12:
                        self._json({"error": "This room already has 12 agents."}, 409)
                        return
                    name = (
                        " ".join(str(data.get("name", "Agent")).split())[:24] or "Agent"
                    )
                    player_id = secrets.token_urlsafe(12)
                    xp = max(0, min(int(data.get("xp", 0)), 4900))
                    rank = str(data.get("rank", "Bronze I"))[:32]
                    level = min(50, xp // 100 + 1)
                    seen = [x for x in data.get("seen", []) if isinstance(x, str)][
                        :1000
                    ]
                    room["players"][player_id] = {
                        "id": player_id,
                        "name": name,
                        "rank": rank,
                        "level": level,
                        "xp": xp,
                        "score": 0,
                        "index": 0,
                        "finished": False,
                        "seen": set(seen),
                        "last_seen": time.time(),
                    }
                    self._json(
                        {
                            "code": code,
                            "player": player_id,
                            "room": self._public_room(room),
                        }
                    )
                return
            if path == "/api/race/start":
                with ROOM_LOCK:
                    room = ROOMS.get(str(data.get("code", "")).upper())
                    if not room or data.get("player") not in room["players"]:
                        self._json({"error": "Room or player not found."}, 404)
                        return
                    if len(room["players"]) < 2:
                        self._json(
                            {
                                "error": "Invite at least one other agent before starting."
                            },
                            409,
                        )
                        return
                    if not room["race"]:
                        questions = random.sample(
                            SCENARIO_IDS, min(8, len(SCENARIO_IDS))
                        )
                        room["race"] = {
                            "started": time.time(),
                            "endsAt": time.time() + 90,
                            "questions": questions,
                        }
                    self._json({"room": self._public_room(room)})
                return
            if path == "/api/race/progress":
                with ROOM_LOCK:
                    room = ROOMS.get(str(data.get("code", "")).upper())
                    player = room["players"].get(data.get("player")) if room else None
                    if not room or not player or not room["race"]:
                        self._json({"error": "Race session not found."}, 404)
                        return
                    player["index"] = max(
                        player["index"],
                        min(int(data.get("index", 0)), len(room["race"]["questions"])),
                    )
                    player["score"] = max(
                        player["score"], min(int(data.get("score", 0)), player["index"])
                    )
                    player["finished"] = (
                        bool(data.get("finished"))
                        or player["index"] >= len(room["race"]["questions"])
                        or time.time() >= room["race"]["endsAt"]
                    )
                    player["last_seen"] = time.time()
                    self._json({"room": self._public_room(room)})
                return
            self._json({"error": "Unknown race endpoint."}, 404)
        except (ValueError, TypeError, json.JSONDecodeError):
            self._json({"error": "Invalid race request."}, 400)

    def _public_room(self, room: dict) -> dict:
        players = []
        now = time.time()
        room["last_active"] = now
        for player in room["players"].values():
            players.append(
                {
                    key: player[key]
                    for key in (
                        "id",
                        "name",
                        "rank",
                        "level",
                        "score",
                        "index",
                        "finished",
                    )
                }
                | {"online": now - player["last_seen"] < 5}
            )
        return {"players": players, "race": room["race"], "serverNow": now}

    def _json(self, value: dict, status: int = 200) -> None:
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), WebsiteHandler)
    print(
        f"Signal//Safe running locally at http://127.0.0.1:{PORT} (press Ctrl+C to stop)"
    )
    addresses = sorted(
        {
            item[4][0]
            for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
            if not item[4][0].startswith("127.")
        }
    )
    for address in addresses:
        print(f"LAN multiplayer address: http://{address}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down game.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
