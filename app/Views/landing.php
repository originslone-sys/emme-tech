<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Crie agentes de IA para WhatsApp em minutos. Automatize atendimento, vendas e suporte com IA de ponta — sem código.">
<meta property="og:title" content="EMME Tech — Agentes de IA para WhatsApp">
<meta property="og:description" content="A plataforma SaaS para criar, configurar e escalar agentes de IA no WhatsApp. Com OpenRouter, RAG e automações.">
<meta property="og:type" content="website">
<title>EMME Tech — Agentes de IA para WhatsApp | Atendimento Inteligente 24/7</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
/* =============================================
   RESET & TOKENS
   ============================================= */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --c-bg:        #060a14;
  --c-bg2:       #0c1220;
  --c-surface:   #111827;
  --c-border:    rgba(255,255,255,.08);
  --c-border2:   rgba(255,255,255,.14);
  --c-text:      #f1f5f9;
  --c-muted:     #94a3b8;
  --c-accent:    #6366f1;
  --c-accent2:   #818cf8;
  --c-green:     #22c55e;
  --c-purple:    #a855f7;
  --c-cyan:      #06b6d4;
  --c-orange:    #f97316;
  --grad-hero:   linear-gradient(135deg,#6366f1 0%,#a855f7 50%,#06b6d4 100%);
  --grad-card:   linear-gradient(135deg,rgba(99,102,241,.12),rgba(168,85,247,.06));
  --r:           12px;
  --r-lg:        20px;
  --shadow-glow: 0 0 60px rgba(99,102,241,.35);
}
html { scroll-behavior: smooth; }
body {
  font-family: 'Inter', sans-serif;
  background: var(--c-bg);
  color: var(--c-text);
  line-height: 1.6;
  overflow-x: hidden;
}
a { color: inherit; text-decoration: none; }
img { max-width: 100%; }
.container { max-width: 1160px; margin: 0 auto; padding: 0 24px; }

/* =============================================
   NOISE OVERLAY
   ============================================= */
body::before {
  content: '';
  position: fixed; inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
  pointer-events: none;
  z-index: 0;
  opacity: .5;
}

/* =============================================
   NAV
   ============================================= */
.nav {
  position: fixed; top: 0; left: 0; right: 0;
  z-index: 999;
  padding: 0 24px;
  border-bottom: 1px solid transparent;
  transition: background .3s, border-color .3s, backdrop-filter .3s;
}
.nav.scrolled {
  background: rgba(6,10,20,.80);
  border-color: var(--c-border);
  backdrop-filter: blur(20px);
}
.nav-inner {
  max-width: 1160px; margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between;
  height: 70px;
}
.nav-logo {
  display: flex; align-items: center; gap: 4px;
  font-size: 22px; font-weight: 800;
  letter-spacing: -.5px;
}
.nav-logo-emme {
  background: var(--grad-hero);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-style: italic;
}
.nav-logo-icon {
  width: 36px; height: 36px; border-radius: 10px;
  background: var(--grad-hero);
  display: grid; place-items: center;
  font-size: 18px;
  box-shadow: 0 0 20px rgba(99,102,241,.5);
}
.nav-links {
  display: flex; align-items: center; gap: 32px;
  list-style: none;
}
.nav-links a {
  font-size: 14px; font-weight: 500; color: var(--c-muted);
  transition: color .2s;
}
.nav-links a:hover { color: var(--c-text); }
.nav-cta {
  display: flex; align-items: center; gap: 12px;
}
.btn-ghost {
  padding: 9px 20px; border-radius: 8px;
  font-size: 14px; font-weight: 600; color: var(--c-text);
  border: 1px solid var(--c-border2);
  transition: background .2s, border-color .2s;
  cursor: pointer;
}
.btn-ghost:hover { background: rgba(255,255,255,.06); }
.btn-primary {
  padding: 9px 22px; border-radius: 8px;
  font-size: 14px; font-weight: 600; color: #fff;
  background: var(--c-accent);
  border: 1px solid rgba(99,102,241,.5);
  box-shadow: 0 0 20px rgba(99,102,241,.35);
  transition: background .2s, box-shadow .2s, transform .15s;
  cursor: pointer;
  display: inline-flex; align-items: center; gap: 6px;
}
.btn-primary:hover {
  background: #4f46e5;
  box-shadow: 0 0 32px rgba(99,102,241,.55);
  transform: translateY(-1px);
}
.btn-primary:active { transform: translateY(0); }
.nav-toggle { display: none; flex-direction: column; gap: 5px; cursor: pointer; padding: 4px; }
.nav-toggle span { display: block; width: 22px; height: 2px; background: var(--c-text); border-radius: 2px; transition: .3s; }

/* =============================================
   HERO
   ============================================= */
.hero {
  min-height: 100vh;
  display: flex; align-items: center;
  padding: 120px 24px 80px;
  position: relative; overflow: hidden;
}
.hero-glow {
  position: absolute; top: -200px; left: 50%; transform: translateX(-50%);
  width: 900px; height: 900px; border-radius: 50%;
  background: radial-gradient(ellipse,rgba(99,102,241,.18) 0%,rgba(168,85,247,.08) 40%,transparent 70%);
  pointer-events: none;
}
.hero-grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(99,102,241,.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99,102,241,.04) 1px, transparent 1px);
  background-size: 60px 60px;
  mask-image: radial-gradient(ellipse 80% 60% at 50% 0%, black 0%, transparent 100%);
}
.hero-content { position: relative; z-index: 1; max-width: 860px; margin: 0 auto; text-align: center; }
.hero-badge {
  display: inline-flex; align-items: center; gap: 8px;
  background: rgba(99,102,241,.12);
  border: 1px solid rgba(99,102,241,.3);
  border-radius: 9999px;
  padding: 6px 16px;
  font-size: 13px; font-weight: 600;
  color: var(--c-accent2);
  margin-bottom: 28px;
  backdrop-filter: blur(10px);
}
.hero-badge-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--c-green); box-shadow: 0 0 8px var(--c-green); animation: pulse 2s infinite; }
.hero h1 {
  font-size: clamp(40px, 7vw, 76px);
  font-weight: 900;
  line-height: 1.05;
  letter-spacing: -2.5px;
  margin-bottom: 24px;
}
.hero h1 .grad {
  background: var(--grad-hero);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-sub {
  font-size: clamp(16px, 2.5vw, 20px);
  color: var(--c-muted);
  max-width: 600px; margin: 0 auto 40px;
  line-height: 1.7;
}
.hero-actions { display: flex; justify-content: center; gap: 14px; flex-wrap: wrap; margin-bottom: 56px; }
.btn-hero {
  padding: 15px 32px; border-radius: 10px;
  font-size: 16px; font-weight: 700; color: #fff;
  background: var(--grad-hero);
  border: none; box-shadow: 0 0 40px rgba(99,102,241,.45), 0 8px 32px rgba(0,0,0,.3);
  transition: transform .2s, box-shadow .2s;
  cursor: pointer; display: inline-flex; align-items: center; gap: 8px;
}
.btn-hero:hover { transform: translateY(-2px); box-shadow: 0 0 60px rgba(99,102,241,.6), 0 12px 40px rgba(0,0,0,.3); }
.btn-hero-outline {
  padding: 15px 32px; border-radius: 10px;
  font-size: 16px; font-weight: 600;
  color: var(--c-text);
  background: rgba(255,255,255,.04);
  border: 1px solid var(--c-border2);
  backdrop-filter: blur(10px);
  transition: background .2s, transform .2s;
  cursor: pointer; display: inline-flex; align-items: center; gap: 8px;
}
.btn-hero-outline:hover { background: rgba(255,255,255,.08); transform: translateY(-2px); }
.hero-stats {
  display: flex; justify-content: center; gap: 40px; flex-wrap: wrap;
}
.hero-stat { text-align: center; }
.hero-stat-val { font-size: 28px; font-weight: 800; background: var(--grad-hero); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.hero-stat-lbl { font-size: 12px; color: var(--c-muted); margin-top: 2px; font-weight: 500; }

/* hero visual */
.hero-visual {
  position: relative; max-width: 900px; margin: 60px auto 0;
  z-index: 1;
}
.hero-mockup {
  background: var(--c-surface);
  border: 1px solid var(--c-border2);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 40px 120px rgba(0,0,0,.6), 0 0 0 1px var(--c-border), var(--shadow-glow);
}
.mockup-bar {
  background: rgba(255,255,255,.04);
  border-bottom: 1px solid var(--c-border);
  padding: 14px 20px;
  display: flex; align-items: center; gap: 10px;
}
.mockup-dots { display: flex; gap: 6px; }
.mockup-dots span { width: 12px; height: 12px; border-radius: 50%; }
.mockup-dots .d1 { background: #ff5f57; }
.mockup-dots .d2 { background: #febc2e; }
.mockup-dots .d3 { background: #28c840; }
.mockup-url {
  flex: 1; background: rgba(255,255,255,.06); border-radius: 6px;
  padding: 6px 14px; font-size: 12px; color: var(--c-muted); text-align: center;
}
.mockup-body {
  display: grid; grid-template-columns: 200px 1fr 280px;
  min-height: 320px;
}
.mockup-sidebar {
  border-right: 1px solid var(--c-border);
  padding: 16px;
  background: rgba(0,0,0,.2);
}
.mockup-sidebar-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; border-radius: 7px;
  font-size: 12px; color: var(--c-muted);
  margin-bottom: 4px;
  transition: background .15s;
}
.mockup-sidebar-item.active { background: rgba(99,102,241,.2); color: var(--c-accent2); font-weight: 600; }
.mockup-main { padding: 20px; }
.mockup-agent-card {
  background: var(--grad-card);
  border: 1px solid var(--c-border2);
  border-radius: 12px; padding: 16px; margin-bottom: 12px;
  display: flex; align-items: center; gap: 12px;
}
.agent-avatar {
  width: 40px; height: 40px; border-radius: 10px;
  background: var(--grad-hero);
  display: grid; place-items: center; font-size: 18px; flex-shrink: 0;
}
.agent-info h4 { font-size: 13px; font-weight: 700; }
.agent-info p { font-size: 11px; color: var(--c-muted); }
.agent-badge { margin-left: auto; background: rgba(34,197,94,.15); color: #22c55e; border: 1px solid rgba(34,197,94,.3); border-radius: 9999px; padding: 3px 10px; font-size: 10px; font-weight: 700; }
.mockup-stat-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.mockup-stat { background: rgba(255,255,255,.04); border: 1px solid var(--c-border); border-radius: 8px; padding: 12px; }
.mockup-stat-n { font-size: 20px; font-weight: 800; color: var(--c-accent2); }
.mockup-stat-l { font-size: 10px; color: var(--c-muted); }
.mockup-chat { border-left: 1px solid var(--c-border); padding: 16px; background: rgba(0,0,0,.15); display: flex; flex-direction: column; gap: 10px; }
.chat-msg { max-width: 85%; }
.chat-msg.in .bubble { background: rgba(255,255,255,.07); border-radius: 12px 12px 12px 2px; }
.chat-msg.out { align-self: flex-end; }
.chat-msg.out .bubble { background: rgba(99,102,241,.25); border-radius: 12px 12px 2px 12px; }
.bubble { padding: 8px 12px; font-size: 11px; line-height: 1.5; }
.bubble-meta { font-size: 9px; color: var(--c-muted); margin-top: 3px; padding: 0 4px; }

/* =============================================
   SECTION BASE
   ============================================= */
section { position: relative; z-index: 1; }
.section-label {
  display: inline-flex; align-items: center; gap: 6px;
  background: rgba(99,102,241,.1);
  border: 1px solid rgba(99,102,241,.25);
  border-radius: 9999px;
  padding: 5px 14px;
  font-size: 12px; font-weight: 700;
  color: var(--c-accent2);
  letter-spacing: .06em; text-transform: uppercase;
  margin-bottom: 16px;
}
.section-title {
  font-size: clamp(28px, 4.5vw, 48px);
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -1.5px;
  margin-bottom: 16px;
}
.section-title .grad { background: var(--grad-hero); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.section-sub { font-size: 17px; color: var(--c-muted); max-width: 560px; line-height: 1.7; }
.text-center { text-align: center; }
.text-center .section-sub { margin: 0 auto; }

/* =============================================
   LOGOS / TRUSTED BY
   ============================================= */
.trusted { padding: 40px 0 60px; }
.trusted-label { text-align: center; font-size: 12px; color: var(--c-muted); font-weight: 600; letter-spacing: .1em; text-transform: uppercase; margin-bottom: 28px; }
.logos-track { display: flex; justify-content: center; align-items: center; gap: 48px; flex-wrap: wrap; opacity: .45; filter: grayscale(1); }
.logo-item { font-size: 20px; font-weight: 800; letter-spacing: -1px; color: var(--c-text); }

/* =============================================
   FEATURES
   ============================================= */
.features { padding: 100px 0; }
.features-header { text-align: center; margin-bottom: 72px; }
.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2px;
  background: var(--c-border);
  border: 1px solid var(--c-border);
  border-radius: var(--r-lg);
  overflow: hidden;
}
.feature-cell {
  background: var(--c-bg);
  padding: 36px 32px;
  transition: background .25s;
  position: relative; overflow: hidden;
}
.feature-cell::before {
  content: '';
  position: absolute; inset: 0;
  background: var(--grad-card);
  opacity: 0;
  transition: opacity .3s;
}
.feature-cell:hover { background: var(--c-bg2); }
.feature-cell:hover::before { opacity: 1; }
.feature-icon {
  width: 52px; height: 52px; border-radius: 14px;
  display: grid; place-items: center;
  font-size: 24px; margin-bottom: 20px;
  position: relative; z-index: 1;
}
.ic-purple { background: rgba(168,85,247,.15); box-shadow: 0 0 20px rgba(168,85,247,.2); }
.ic-blue   { background: rgba(99,102,241,.15); box-shadow: 0 0 20px rgba(99,102,241,.2); }
.ic-cyan   { background: rgba(6,182,212,.15);  box-shadow: 0 0 20px rgba(6,182,212,.2); }
.ic-green  { background: rgba(34,197,94,.15);  box-shadow: 0 0 20px rgba(34,197,94,.2); }
.ic-orange { background: rgba(249,115,22,.15); box-shadow: 0 0 20px rgba(249,115,22,.2); }
.ic-pink   { background: rgba(236,72,153,.15); box-shadow: 0 0 20px rgba(236,72,153,.2); }
.feature-cell h3 { font-size: 17px; font-weight: 700; margin-bottom: 10px; position: relative; z-index: 1; }
.feature-cell p  { font-size: 14px; color: var(--c-muted); line-height: 1.65; position: relative; z-index: 1; }

/* =============================================
   HOW IT WORKS
   ============================================= */
.how { padding: 100px 0; background: linear-gradient(180deg, transparent, var(--c-bg2) 20%, var(--c-bg2) 80%, transparent); }
.how-inner { display: grid; grid-template-columns: 1fr 1fr; gap: 80px; align-items: center; }
.how-steps { display: flex; flex-direction: column; gap: 0; }
.step {
  display: flex; gap: 20px;
  padding: 28px 0;
  border-bottom: 1px solid var(--c-border);
  cursor: pointer;
  transition: opacity .2s;
}
.step:last-child { border-bottom: none; }
.step-num {
  width: 40px; height: 40px; flex-shrink: 0;
  border-radius: 10px; display: grid; place-items: center;
  font-size: 14px; font-weight: 800;
  background: rgba(99,102,241,.1);
  border: 1px solid rgba(99,102,241,.2);
  color: var(--c-accent2);
  transition: background .3s, border-color .3s, box-shadow .3s;
}
.step.active .step-num {
  background: var(--c-accent);
  border-color: var(--c-accent);
  box-shadow: 0 0 20px rgba(99,102,241,.5);
  color: #fff;
}
.step-body h4 { font-size: 16px; font-weight: 700; margin-bottom: 6px; }
.step-body p  { font-size: 14px; color: var(--c-muted); line-height: 1.6; }
.how-visual {
  position: relative;
}
.how-screen {
  background: var(--c-surface);
  border: 1px solid var(--c-border2);
  border-radius: var(--r-lg);
  overflow: hidden;
  box-shadow: 0 30px 80px rgba(0,0,0,.5), var(--shadow-glow);
}
.how-screen-bar { background: rgba(255,255,255,.04); border-bottom: 1px solid var(--c-border); padding: 12px 16px; display: flex; align-items: center; gap: 8px; }
.how-screen-bar .dots { display: flex; gap: 5px; }
.how-screen-bar .dots span { width: 10px; height: 10px; border-radius: 50%; }
.how-screen-content { padding: 24px; }
/* Floating badge on how visual */
.how-float {
  position: absolute; bottom: -20px; right: -20px;
  background: var(--c-surface);
  border: 1px solid var(--c-border2);
  border-radius: 14px; padding: 14px 18px;
  box-shadow: 0 20px 60px rgba(0,0,0,.5);
  display: flex; align-items: center; gap: 12px;
  font-size: 13px; font-weight: 600;
}
.how-float-icon { width: 36px; height: 36px; border-radius: 9px; background: rgba(34,197,94,.15); display: grid; place-items: center; font-size: 18px; }

/* =============================================
   METRICS BANNER
   ============================================= */
.metrics { padding: 80px 0; }
.metrics-grid {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 2px; background: var(--c-border);
  border: 1px solid var(--c-border);
  border-radius: var(--r-lg); overflow: hidden;
}
.metric-card {
  background: var(--c-bg2);
  padding: 40px 32px; text-align: center;
}
.metric-val {
  font-size: 48px; font-weight: 900;
  letter-spacing: -2px;
  background: var(--grad-hero);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  line-height: 1;
}
.metric-lbl { font-size: 14px; color: var(--c-muted); margin-top: 8px; font-weight: 500; }

/* =============================================
   ANIMATIONS
   ============================================= */
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.6;transform:scale(1.2)} }
@keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-12px)} }
@keyframes fadeUp { from{opacity:0;transform:translateY(30px)} to{opacity:1;transform:translateY(0)} }
@keyframes spin { to{transform:rotate(360deg)} }
@keyframes shimmer { from{background-position:-400px 0} to{background-position:400px 0} }

.animate-float { animation: float 5s ease-in-out infinite; }
.fade-up { opacity: 0; animation: fadeUp .7s ease forwards; }
.fade-up.delay-1 { animation-delay: .1s; }
.fade-up.delay-2 { animation-delay: .2s; }
.fade-up.delay-3 { animation-delay: .3s; }

/* =============================================
   PRICING
   ============================================= */
.pricing { padding: 100px 0; }
.pricing-header { text-align: center; margin-bottom: 60px; }
.pricing-toggle {
  display: inline-flex; background: rgba(255,255,255,.06); border: 1px solid var(--c-border); border-radius: 9999px; padding: 4px; margin: 24px auto 0; gap: 4px;
}
.ptoggle-btn {
  padding: 8px 20px; border-radius: 9999px; font-size: 13px; font-weight: 600; cursor: pointer; border: none; background: transparent; color: var(--c-muted); transition: .2s;
}
.ptoggle-btn.active { background: var(--c-accent); color: #fff; box-shadow: 0 0 16px rgba(99,102,241,.4); }
.pricing-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 20px; }
.plan-card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--r-lg); padding: 36px; position: relative;
  transition: border-color .3s, transform .3s, box-shadow .3s;
  display: flex; flex-direction: column;
}
.plan-card:hover { border-color: var(--c-border2); transform: translateY(-4px); box-shadow: 0 20px 60px rgba(0,0,0,.4); }
.plan-card.featured {
  border-color: rgba(99,102,241,.5);
  background: linear-gradient(145deg, var(--c-surface), rgba(99,102,241,.07));
  box-shadow: 0 0 0 1px rgba(99,102,241,.2), 0 20px 60px rgba(99,102,241,.12);
}
.plan-card.featured:hover { box-shadow: 0 0 0 1px rgba(99,102,241,.4), 0 28px 80px rgba(99,102,241,.2); }
.plan-popular {
  position: absolute; top: -13px; left: 50%; transform: translateX(-50%);
  background: var(--grad-hero); color: #fff;
  border-radius: 9999px; padding: 4px 16px; font-size: 11px; font-weight: 800;
  letter-spacing: .06em; text-transform: uppercase; white-space: nowrap;
  box-shadow: 0 4px 16px rgba(99,102,241,.4);
}
.plan-name { font-size: 13px; font-weight: 700; color: var(--c-muted); text-transform: uppercase; letter-spacing: .08em; margin-bottom: 12px; }
.plan-price-wrap { margin-bottom: 8px; }
.plan-price { font-size: 52px; font-weight: 900; letter-spacing: -2px; line-height: 1; }
.plan-price sup { font-size: 22px; vertical-align: top; margin-top: 10px; font-weight: 700; color: var(--c-muted); }
.plan-period { font-size: 14px; color: var(--c-muted); margin-bottom: 24px; }
.plan-divider { border: none; border-top: 1px solid var(--c-border); margin: 24px 0; }
.plan-features-list { list-style: none; display: flex; flex-direction: column; gap: 12px; flex: 1; }
.plan-features-list li { display: flex; align-items: flex-start; gap: 10px; font-size: 14px; }
.plan-features-list li .check { color: var(--c-green); font-size: 16px; flex-shrink: 0; margin-top: 1px; }
.plan-features-list li .cross { color: var(--c-muted); font-size: 16px; flex-shrink: 0; opacity: .5; }
.plan-cta {
  margin-top: 28px; width: 100%; padding: 14px; border-radius: 10px;
  font-size: 15px; font-weight: 700; cursor: pointer; border: none;
  transition: .2s;
}
.plan-cta-secondary { background: rgba(255,255,255,.06); color: var(--c-text); border: 1px solid var(--c-border2); }
.plan-cta-secondary:hover { background: rgba(255,255,255,.1); }
.plan-cta-primary { background: var(--grad-hero); color: #fff; box-shadow: 0 0 30px rgba(99,102,241,.35); }
.plan-cta-primary:hover { box-shadow: 0 0 50px rgba(99,102,241,.55); transform: translateY(-1px); }
.pricing-note { text-align: center; margin-top: 28px; font-size: 13px; color: var(--c-muted); }
.pricing-note a { color: var(--c-accent2); }

/* =============================================
   TESTIMONIALS
   ============================================= */
.testimonials { padding: 100px 0; }
.testi-header { text-align: center; margin-bottom: 60px; }
.testi-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 20px; }
.testi-card {
  background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--r-lg); padding: 28px;
  transition: border-color .2s, transform .2s;
}
.testi-card:hover { border-color: var(--c-border2); transform: translateY(-3px); }
.testi-stars { color: #fbbf24; font-size: 14px; margin-bottom: 16px; letter-spacing: 2px; }
.testi-quote { font-size: 15px; line-height: 1.7; color: var(--c-muted); margin-bottom: 20px; font-style: italic; }
.testi-quote strong { color: var(--c-text); font-style: normal; }
.testi-author { display: flex; align-items: center; gap: 12px; }
.testi-avatar {
  width: 42px; height: 42px; border-radius: 50%;
  display: grid; place-items: center; font-size: 18px;
  background: var(--grad-card); border: 1px solid var(--c-border2); flex-shrink: 0;
}
.testi-name { font-size: 14px; font-weight: 700; }
.testi-role { font-size: 12px; color: var(--c-muted); }

/* =============================================
   FAQ
   ============================================= */
.faq { padding: 100px 0; }
.faq-inner { max-width: 760px; margin: 0 auto; }
.faq-header { text-align: center; margin-bottom: 56px; }
.faq-item {
  border-bottom: 1px solid var(--c-border);
  overflow: hidden;
}
.faq-q {
  width: 100%; text-align: left; background: none; border: none; color: var(--c-text);
  font-size: 16px; font-weight: 600; padding: 22px 0; cursor: pointer;
  display: flex; justify-content: space-between; align-items: center; gap: 16px;
  transition: color .2s;
}
.faq-q:hover { color: var(--c-accent2); }
.faq-arrow { font-size: 20px; transition: transform .3s; flex-shrink: 0; }
.faq-item.open .faq-arrow { transform: rotate(45deg); }
.faq-a { font-size: 15px; color: var(--c-muted); line-height: 1.75; max-height: 0; overflow: hidden; transition: max-height .4s ease, padding .3s; }
.faq-item.open .faq-a { max-height: 300px; padding-bottom: 20px; }

/* =============================================
   CTA BANNER
   ============================================= */
.cta-banner { padding: 100px 0; }
.cta-box {
  background: linear-gradient(135deg, rgba(99,102,241,.15) 0%, rgba(168,85,247,.12) 50%, rgba(6,182,212,.08) 100%);
  border: 1px solid rgba(99,102,241,.3);
  border-radius: 28px; padding: 80px 40px; text-align: center; position: relative; overflow: hidden;
}
.cta-box::before {
  content: '';
  position: absolute; top: -60%; left: 50%; transform: translateX(-50%);
  width: 600px; height: 600px; border-radius: 50%;
  background: radial-gradient(ellipse, rgba(99,102,241,.15) 0%, transparent 70%);
  pointer-events: none;
}
.cta-box h2 { font-size: clamp(28px,5vw,52px); font-weight: 900; letter-spacing: -1.5px; margin-bottom: 16px; }
.cta-box p  { font-size: 18px; color: var(--c-muted); margin-bottom: 40px; max-width: 500px; margin-left: auto; margin-right: auto; }
.cta-actions { display: flex; justify-content: center; gap: 14px; flex-wrap: wrap; }
.cta-trust { margin-top: 24px; display: flex; justify-content: center; align-items: center; gap: 24px; flex-wrap: wrap; font-size: 13px; color: var(--c-muted); }
.cta-trust span { display: flex; align-items: center; gap: 6px; }

/* =============================================
   FOOTER
   ============================================= */
.footer {
  background: var(--c-surface);
  border-top: 1px solid var(--c-border);
  padding: 64px 24px 40px;
}
.footer-inner { max-width: 1160px; margin: 0 auto; }
.footer-grid { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 48px; margin-bottom: 56px; }
.footer-brand p { font-size: 14px; color: var(--c-muted); line-height: 1.7; margin: 16px 0 24px; max-width: 300px; }
.footer-social { display: flex; gap: 12px; }
.social-btn {
  width: 36px; height: 36px; border-radius: 8px;
  background: rgba(255,255,255,.06); border: 1px solid var(--c-border);
  display: grid; place-items: center; font-size: 16px;
  transition: background .2s, border-color .2s;
  cursor: pointer;
}
.social-btn:hover { background: rgba(99,102,241,.15); border-color: rgba(99,102,241,.4); }
.footer-col h4 { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: var(--c-muted); margin-bottom: 16px; }
.footer-col ul { list-style: none; display: flex; flex-direction: column; gap: 10px; }
.footer-col ul a { font-size: 14px; color: var(--c-muted); transition: color .2s; }
.footer-col ul a:hover { color: var(--c-text); }
.footer-bottom { border-top: 1px solid var(--c-border); padding-top: 28px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
.footer-bottom p { font-size: 13px; color: var(--c-muted); }
.footer-badges { display: flex; gap: 12px; flex-wrap: wrap; }
.footer-badge { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--c-muted); background: rgba(255,255,255,.04); border: 1px solid var(--c-border); border-radius: 6px; padding: 5px 10px; }

/* =============================================
   NOTIFICATION TOAST
   ============================================= */
.toast-wrap { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); z-index: 9999; display: flex; flex-direction: column; gap: 10px; align-items: center; pointer-events: none; }
.toast { background: var(--c-surface); border: 1px solid var(--c-border2); border-radius: 10px; padding: 12px 20px; font-size: 14px; font-weight: 600; box-shadow: 0 8px 32px rgba(0,0,0,.4); display: flex; align-items: center; gap: 10px; animation: fadeUp .4s ease; pointer-events: all; }

/* =============================================
   RESPONSIVE
   ============================================= */
@media (max-width: 1024px) {
  .features-grid { grid-template-columns: repeat(2,1fr); }
  .pricing-grid  { grid-template-columns: repeat(2,1fr); }
  .testi-grid    { grid-template-columns: repeat(2,1fr); }
  .metrics-grid  { grid-template-columns: repeat(2,1fr); }
  .footer-grid   { grid-template-columns: 1fr 1fr; }
  .how-inner     { grid-template-columns: 1fr; }
  .how-visual    { order: -1; }
  .mockup-body   { grid-template-columns: 1fr 1fr; }
  .mockup-sidebar { display: none; }
}
@media (max-width: 768px) {
  .nav-links, .nav-cta .btn-ghost { display: none; }
  .nav-toggle { display: flex; }
  .nav-links.open { display: flex; flex-direction: column; position: absolute; top: 70px; left: 0; right: 0; background: rgba(6,10,20,.95); backdrop-filter: blur(20px); padding: 24px; border-bottom: 1px solid var(--c-border); }
  .features-grid { grid-template-columns: 1fr; }
  .pricing-grid  { grid-template-columns: 1fr; }
  .testi-grid    { grid-template-columns: 1fr; }
  .metrics-grid  { grid-template-columns: repeat(2,1fr); }
  .footer-grid   { grid-template-columns: 1fr; }
  .hero-stats    { gap: 24px; }
  .how-float     { display: none; }
  .mockup-chat   { display: none; }
  .cta-box       { padding: 48px 24px; }
}
@media (max-width: 480px) {
  .metrics-grid { grid-template-columns: 1fr 1fr; }
  .hero-actions { flex-direction: column; align-items: center; }
  .btn-hero, .btn-hero-outline { width: 100%; justify-content: center; }
}
</style>
</head>
<body>

<!-- ============================================================
     NAV
     ============================================================ -->
<nav class="nav" id="mainNav">
  <div class="nav-inner">
    <a href="/" class="nav-logo">
      <span class="nav-logo-emme">EMME</span>&nbsp;Tech
    </a>
    <ul class="nav-links" id="navLinks">
      <li><a href="#features">Funcionalidades</a></li>
      <li><a href="#como-funciona">Como funciona</a></li>
      <li><a href="#pricing">Planos</a></li>
      <li><a href="#faq">FAQ</a></li>
    </ul>
    <div class="nav-cta">
      <a href="/app/login" class="btn-ghost">Entrar</a>
      <a href="/app/register" class="btn-primary">
        Começar grátis
        <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
      </a>
    </div>
    <div class="nav-toggle" id="navToggle">
      <span></span><span></span><span></span>
    </div>
  </div>
</nav>

<!-- ============================================================
     HERO
     ============================================================ -->
<section class="hero">
  <div class="hero-glow"></div>
  <div class="hero-grid"></div>
  <div class="container">
    <div class="hero-content">
      <div class="hero-badge fade-up">
        <span class="hero-badge-dot"></span>
        Trial gratuito de 14 dias · Sem cartão de crédito
      </div>
      <h1 class="fade-up delay-1">
        Agentes de IA no<br>
        <span class="grad">WhatsApp que vendem,</span><br>
        atendem e encantam
      </h1>
      <p class="hero-sub fade-up delay-2">
        Configure agentes inteligentes em minutos. Memória de documentos, automações, múltiplos modelos de IA — tudo sem precisar escrever uma linha de código.
      </p>
      <div class="hero-actions fade-up delay-3">
        <a href="/app/register" class="btn-hero">
          🚀 Criar conta grátis
        </a>
        <a href="#como-funciona" class="btn-hero-outline">
          ▶ Ver como funciona
        </a>
      </div>
      <div class="hero-stats fade-up delay-3">
        <div class="hero-stat">
          <div class="hero-stat-val">98%</div>
          <div class="hero-stat-lbl">Taxa de resposta</div>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-val">&lt;2s</div>
          <div class="hero-stat-lbl">Tempo de resposta</div>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-val">24/7</div>
          <div class="hero-stat-lbl">Disponibilidade</div>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-val">+40%</div>
          <div class="hero-stat-lbl">Conversões em média</div>
        </div>
      </div>
    </div>

    <!-- Dashboard mockup -->
    <div class="hero-visual animate-float">
      <div class="hero-mockup">
        <div class="mockup-bar">
          <div class="mockup-dots">
            <span class="d1"></span><span class="d2"></span><span class="d3"></span>
          </div>
          <div class="mockup-url">app.wams.io/dashboard</div>
        </div>
        <div class="mockup-body">
          <div class="mockup-sidebar">
            <div class="mockup-sidebar-item active">🏠 Visão Geral</div>
            <div class="mockup-sidebar-item">🤖 Agentes</div>
            <div class="mockup-sidebar-item">📚 Documentos</div>
            <div class="mockup-sidebar-item">💬 Conversas</div>
            <div class="mockup-sidebar-item">⏰ Automações</div>
            <div class="mockup-sidebar-item">💳 Assinatura</div>
          </div>
          <div class="mockup-main">
            <div class="mockup-agent-card">
              <div class="agent-avatar">🤖</div>
              <div class="agent-info">
                <h4>TechBot Suporte</h4>
                <p>GPT-4o Mini · 1.2k msgs hoje</p>
              </div>
              <div class="agent-badge">● ATIVO</div>
            </div>
            <div class="mockup-stat-row">
              <div class="mockup-stat">
                <div class="mockup-stat-n">1.247</div>
                <div class="mockup-stat-l">Msgs hoje</div>
              </div>
              <div class="mockup-stat">
                <div class="mockup-stat-n">98%</div>
                <div class="mockup-stat-l">Satisfação</div>
              </div>
            </div>
          </div>
          <div class="mockup-chat">
            <div class="chat-msg in">
              <div class="bubble">Olá! Preciso de ajuda com meu pedido #4821</div>
              <div class="bubble-meta">João Silva · 14:32</div>
            </div>
            <div class="chat-msg out">
              <div class="bubble">Oi João! 😊 Localizei seu pedido #4821. Ele está em separação e sai amanhã!</div>
              <div class="bubble-meta">IA · 14:32 · ✓✓</div>
            </div>
            <div class="chat-msg in">
              <div class="bubble">Perfeito, obrigado!</div>
              <div class="bubble-meta">João Silva · 14:33</div>
            </div>
            <div class="chat-msg out">
              <div class="bubble">Disponha! Qualquer dúvida estou aqui 🚀</div>
              <div class="bubble-meta">IA · 14:33 · ✓✓</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ============================================================
     TRUSTED BY
     ============================================================ -->
<div class="trusted container">
  <p class="trusted-label">Usado por empresas que crescem com IA</p>
  <div class="logos-track">
    <span class="logo-item">Loja Digital</span>
    <span class="logo-item">TechFlow</span>
    <span class="logo-item">Clinica+</span>
    <span class="logo-item">FastVendas</span>
    <span class="logo-item">AtendeJá</span>
    <span class="logo-item">SuportePro</span>
  </div>
</div>

<!-- ============================================================
     FEATURES
     ============================================================ -->
<section class="features" id="features">
  <div class="container">
    <div class="features-header">
      <div class="section-label">✨ Funcionalidades</div>
      <h2 class="section-title">Tudo que você precisa para<br><span class="grad">escalar com IA no WhatsApp</span></h2>
      <p class="section-sub text-center" style="margin:0 auto">Do zero ao atendimento automatizado em menos de 30 minutos. Sem código. Sem complexidade.</p>
    </div>
    <div class="features-grid">
      <div class="feature-cell">
        <div class="feature-icon ic-purple">🤖</div>
        <h3>Multi-agentes por tenant</h3>
        <p>Crie quantos agentes o seu plano permitir, cada um com persona, modelo e configurações independentes. Ideal para equipes e múltiplos números.</p>
      </div>
      <div class="feature-cell">
        <div class="feature-icon ic-blue">🧠</div>
        <h3>Memória com seus documentos</h3>
        <p>Faça upload de TXTs, MDs e PDFs. O sistema faz chunking automático com busca FULLTEXT e injeta trechos relevantes no contexto da IA.</p>
      </div>
      <div class="feature-cell">
        <div class="feature-icon ic-cyan">⚡</div>
        <h3>Catálogo de modelos de IA</h3>
        <p>Escolha entre GPT-4o, Claude 3, Llama 3, Gemini e muito mais via OpenRouter. Troque de modelo a qualquer hora sem perder as configurações.</p>
      </div>
      <div class="feature-cell">
        <div class="feature-icon ic-green">⏰</div>
        <h3>Automações e crons</h3>
        <p>Agende envios automáticos com expressões cron. Envie templates fora da janela de 24h, lembretes, promoções e notificações recorrentes.</p>
      </div>
      <div class="feature-cell">
        <div class="feature-icon ic-orange">💳</div>
        <h3>Billing com Stripe</h3>
        <p>Checkout e portal de gerenciamento integrados. Planos configuráveis, pagamento recorrente, webhook automático — tudo pronto para produção.</p>
      </div>
      <div class="feature-cell">
        <div class="feature-icon ic-pink">🛡️</div>
        <h3>Segurança enterprise</h3>
        <p>Tokens criptografados com AES-256-GCM, sessões seguras, CSRF em todos os forms, validação de assinatura do WhatsApp e auditoria completa.</p>
      </div>
    </div>
  </div>
</section>

<!-- ============================================================
     HOW IT WORKS
     ============================================================ -->
<section class="how" id="como-funciona">
  <div class="container">
    <div class="how-inner">
      <div class="how-steps">
        <div class="section-label">🗺️ Como funciona</div>
        <h2 class="section-title" style="margin-bottom:32px">De zero a agente ativo<br><span class="grad">em 4 passos simples</span></h2>
        <div class="step active" data-step="0">
          <div class="step-num">1</div>
          <div class="step-body">
            <h4>Crie sua conta e configure o agente</h4>
            <p>Registre-se gratuitamente, crie seu primeiro agente, defina o nome, modelo de IA e o prompt do sistema. Leva menos de 5 minutos.</p>
          </div>
        </div>
        <div class="step" data-step="1">
          <div class="step-num">2</div>
          <div class="step-body">
            <h4>Conecte seu WhatsApp Business</h4>
            <p>Cole o Phone Number ID e o Access Token da WhatsApp Cloud API. O webhook já está pronto — basta apontar a URL no Meta Developer Console.</p>
          </div>
        </div>
        <div class="step" data-step="2">
          <div class="step-num">3</div>
          <div class="step-body">
            <h4>Suba seus documentos e defina a persona</h4>
            <p>Faça upload dos seus catálogos, FAQs e manuais. A IA vai usar esses documentos como memória para responder com precisão.</p>
          </div>
        </div>
        <div class="step" data-step="3">
          <div class="step-num">4</div>
          <div class="step-body">
            <h4>Ative e monitore as conversas</h4>
            <p>Seu agente já está respondendo automaticamente 24/7. Acompanhe conversas em tempo real, veja métricas e ajuste quando quiser.</p>
          </div>
        </div>
      </div>
      <div class="how-visual">
        <div class="how-screen">
          <div class="how-screen-bar">
            <div class="dots">
              <span style="background:#ff5f57"></span>
              <span style="background:#febc2e"></span>
              <span style="background:#28c840"></span>
            </div>
            <span style="font-size:12px;color:var(--c-muted);margin-left:8px">Novo Agente</span>
          </div>
          <div class="how-screen-content">
            <div style="display:flex;flex-direction:column;gap:14px">
              <div style="background:rgba(255,255,255,.04);border:1px solid var(--c-border);border-radius:8px;padding:14px">
                <div style="font-size:11px;color:var(--c-muted);margin-bottom:6px;font-weight:600;text-transform:uppercase;letter-spacing:.06em">Nome do Agente</div>
                <div style="font-size:14px;font-weight:600;display:flex;align-items:center;gap:8px">🤖 SupportBot <span style="background:rgba(34,197,94,.15);color:#22c55e;border-radius:9999px;padding:2px 8px;font-size:10px;font-weight:700">ATIVO</span></div>
              </div>
              <div style="background:rgba(255,255,255,.04);border:1px solid var(--c-border);border-radius:8px;padding:14px">
                <div style="font-size:11px;color:var(--c-muted);margin-bottom:6px;font-weight:600;text-transform:uppercase;letter-spacing:.06em">Modelo de IA</div>
                <div style="font-size:13px;display:flex;align-items:center;justify-content:space-between">
                  <span>openai/gpt-4o-mini</span>
                  <span style="font-size:11px;color:var(--c-muted)">temp: 0.7</span>
                </div>
              </div>
              <div style="background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.2);border-radius:8px;padding:14px">
                <div style="font-size:11px;color:var(--c-accent2);margin-bottom:6px;font-weight:600;text-transform:uppercase;letter-spacing:.06em">📚 Base de Conhecimento</div>
                <div style="font-size:12px;color:var(--c-muted)">3 documentos · 128 chunks indexados · FULLTEXT ativo</div>
                <div style="margin-top:8px;background:rgba(34,197,94,.1);border-radius:4px;height:4px"><div style="background:#22c55e;height:4px;border-radius:4px;width:72%"></div></div>
              </div>
              <div style="background:rgba(255,255,255,.04);border:1px solid var(--c-border);border-radius:8px;padding:14px">
                <div style="font-size:11px;color:var(--c-muted);margin-bottom:8px;font-weight:600;text-transform:uppercase;letter-spacing:.06em">Webhook WhatsApp</div>
                <code style="font-size:11px;color:var(--c-accent2);background:rgba(99,102,241,.1);padding:6px 10px;border-radius:6px;display:block;word-break:break-all">https://app.wams.io/webhook/whatsapp</code>
              </div>
            </div>
          </div>
        </div>
        <div class="how-float">
          <div class="how-float-icon">✅</div>
          <div>
            <div style="font-size:13px;font-weight:700">Agente online!</div>
            <div style="font-size:11px;color:var(--c-muted)">Respondendo em tempo real</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ============================================================
     METRICS
     ============================================================ -->
<section class="metrics">
  <div class="container">
    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-val">10M+</div>
        <div class="metric-lbl">Mensagens processadas</div>
      </div>
      <div class="metric-card">
        <div class="metric-val">99.9%</div>
        <div class="metric-lbl">Uptime garantido</div>
      </div>
      <div class="metric-card">
        <div class="metric-val">&lt;1.5s</div>
        <div class="metric-lbl">Latência média</div>
      </div>
      <div class="metric-card">
        <div class="metric-val">6+</div>
        <div class="metric-lbl">Modelos de IA disponíveis</div>
      </div>
    </div>
  </div>
</section>

<!-- ============================================================
     PRICING
     ============================================================ -->
<section class="pricing" id="pricing">
  <div class="container">
    <div class="pricing-header">
      <div class="section-label">💳 Planos</div>
      <h2 class="section-title">Preço justo para<br><span class="grad">qualquer tamanho de negócio</span></h2>
      <p class="section-sub" style="margin:0 auto;text-align:center">Comece grátis por 14 dias. Sem cartão de crédito. Cancele quando quiser.</p>
    </div>

    <?php if (!empty($plans)): ?>
    <div class="pricing-grid">
      <?php
      $planCount = count($plans);
      foreach ($plans as $i => $p):
        $isFeatured = $planCount >= 2 && $i === 1;
        $features = [
          "{$p['max_agents']} agente" . ($p['max_agents'] > 1 ? 's' : '') . ' de IA',
          $p['max_messages_per_month'] > 0 ? number_format($p['max_messages_per_month']) . ' mensagens/mês' : 'Mensagens ilimitadas',
          $p['feature_docs']  ? "Até {$p['max_docs']} documentos / RAG" : null,
          $p['feature_crons'] ? "Até {$p['max_crons']} automações/crons" : null,
          'WhatsApp Cloud API oficial',
          'Suporte por e-mail',
          $isFeatured ? 'Painel multi-agente' : null,
          $p['feature_api_access'] ? 'Acesso à API REST' : null,
        ];
        $features = array_values(array_filter($features));
      ?>
      <div class="plan-card <?= $isFeatured ? 'featured' : '' ?>">
        <?php if ($isFeatured): ?>
        <div class="plan-popular">⭐ Mais popular</div>
        <?php endif; ?>
        <div class="plan-name"><?= htmlspecialchars($p['name']) ?></div>
        <div class="plan-price-wrap">
          <div class="plan-price">
            <sup>R$</sup><?= number_format($p['price_monthly'], 0, ',', '.') ?>
          </div>
        </div>
        <div class="plan-period">por mês · cobrado mensalmente</div>
        <?php if ($p['price_yearly'] > 0): ?>
        <div style="font-size:12px;color:var(--c-green);margin-top:-8px;margin-bottom:12px">
          💡 R$ <?= number_format($p['price_yearly'], 0, ',', '.') ?>/ano — economize <?= round((1 - $p['price_yearly'] / ($p['price_monthly'] * 12)) * 100) ?>%
        </div>
        <?php endif; ?>
        <hr class="plan-divider">
        <ul class="plan-features-list">
          <?php foreach ($features as $f): ?>
          <li>
            <span class="check">✓</span>
            <?= htmlspecialchars($f) ?>
          </li>
          <?php endforeach; ?>
        </ul>
        <a href="/app/register" class="plan-cta <?= $isFeatured ? 'plan-cta-primary' : 'plan-cta-secondary' ?>">
          <?= $isFeatured ? '🚀 Começar agora' : 'Escolher plano' ?>
        </a>
      </div>
      <?php endforeach; ?>
    </div>

    <?php else: ?>
    <!-- Fallback pricing (quando DB indisponível) -->
    <div class="pricing-grid">
      <?php
      $fallback = [
        ['name'=>'Starter','price'=>'49','agents'=>1,'msgs'=>'500','docs'=>5,'crons'=>false,'featured'=>false],
        ['name'=>'Pro',    'price'=>'149','agents'=>3,'msgs'=>'5.000','docs'=>20,'crons'=>true,'featured'=>true],
        ['name'=>'Business','price'=>'299','agents'=>5,'msgs'=>'Ilimitadas','docs'=>100,'crons'=>true,'featured'=>false],
      ];
      foreach ($fallback as $p):
      ?>
      <div class="plan-card <?= $p['featured'] ? 'featured' : '' ?>">
        <?php if ($p['featured']): ?><div class="plan-popular">⭐ Mais popular</div><?php endif; ?>
        <div class="plan-name"><?= $p['name'] ?></div>
        <div class="plan-price-wrap"><div class="plan-price"><sup>R$</sup><?= $p['price'] ?></div></div>
        <div class="plan-period">por mês</div>
        <hr class="plan-divider">
        <ul class="plan-features-list">
          <li><span class="check">✓</span> <?= $p['agents'] ?> agente<?= $p['agents']>1?'s':'' ?> de IA</li>
          <li><span class="check">✓</span> <?= $p['msgs'] ?> mensagens/mês</li>
          <li><span class="check">✓</span> <?= $p['docs'] ?> documentos / RAG</li>
          <li><?= $p['crons'] ? '<span class="check">✓</span>' : '<span class="cross">✗</span>' ?> Automações e crons</li>
          <li><span class="check">✓</span> WhatsApp Cloud API</li>
          <li><span class="check">✓</span> Suporte prioritário</li>
        </ul>
        <a href="/app/register" class="plan-cta <?= $p['featured'] ? 'plan-cta-primary' : 'plan-cta-secondary' ?>">
          <?= $p['featured'] ? '🚀 Começar agora' : 'Escolher plano' ?>
        </a>
      </div>
      <?php endforeach; ?>
    </div>
    <?php endif; ?>

    <p class="pricing-note">
      🔒 Pagamento 100% seguro via Stripe · Cancele a qualquer momento ·
      <a href="/app/register">Trial grátis de 14 dias</a>
    </p>
  </div>
</section>

<!-- ============================================================
     TESTIMONIALS
     ============================================================ -->
<section class="testimonials" id="depoimentos">
  <div class="container">
    <div class="testi-header">
      <div class="section-label">💬 Depoimentos</div>
      <h2 class="section-title">Empresas que já <span class="grad">transformaram seu atendimento</span></h2>
    </div>
    <div class="testi-grid">
      <div class="testi-card">
        <div class="testi-stars">★★★★★</div>
        <p class="testi-quote">Configuramos o agente em uma tarde. Hoje ele responde <strong>mais de 400 perguntas por dia</strong> sobre nossos produtos sem intervenção humana. Incrível.</p>
        <div class="testi-author">
          <div class="testi-avatar">👨‍💼</div>
          <div>
            <div class="testi-name">Ricardo Almeida</div>
            <div class="testi-role">CEO · Loja Digital SP</div>
          </div>
        </div>
      </div>
      <div class="testi-card">
        <div class="testi-stars">★★★★★</div>
        <p class="testi-quote">Subimos o catálogo e o manual de procedimentos como documentos. O bot <strong>responde com precisão cirúrgica</strong> qualquer pergunta dos pacientes.</p>
        <div class="testi-author">
          <div class="testi-avatar">👩‍⚕️</div>
          <div>
            <div class="testi-name">Dra. Fernanda Costa</div>
            <div class="testi-role">Diretora · Clínica Saúde+</div>
          </div>
        </div>
      </div>
      <div class="testi-card">
        <div class="testi-stars">★★★★★</div>
        <p class="testi-quote">Usamos as automações para enviar lembretes de cobrança via template. A <strong>taxa de inadimplência caiu 38%</strong> no primeiro mês. ROI imediato.</p>
        <div class="testi-author">
          <div class="testi-avatar">👨‍💻</div>
          <div>
            <div class="testi-name">Marcos Pereira</div>
            <div class="testi-role">CTO · FastVendas</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ============================================================
     FAQ
     ============================================================ -->
<section class="faq" id="faq">
  <div class="container">
    <div class="faq-inner">
      <div class="faq-header">
        <div class="section-label">❓ FAQ</div>
        <h2 class="section-title">Perguntas <span class="grad">frequentes</span></h2>
      </div>
      <?php
      $faqs = [
        ['Preciso de conhecimento técnico para usar?', 'Não. A interface é totalmente visual. Você configura o agente, sobe os documentos e conecta o WhatsApp em poucos cliques, sem escrever código.'],
        ['Como funciona a integração com o WhatsApp?', 'Usamos a WhatsApp Cloud API oficial da Meta. Você cria um App no Meta Developer Console, obtém o Phone Number ID e o Access Token, e cola no painel. O webhook já está configurado — basta apontar a URL.'],
        ['Posso usar qualquer modelo de IA?', 'O administrador da plataforma mantém um catálogo de modelos via OpenRouter (GPT-4o, Claude, Llama, Gemini, etc.). Você escolhe o modelo disponível para cada agente.'],
        ['O que é a "Memória de Documentos" (RAG)?', 'Você pode subir documentos (txt, md, pdf). O sistema os divide em partes (chunks), indexa com FULLTEXT e, a cada mensagem recebida, busca os trechos mais relevantes e os injeta no contexto da IA — como dar uma "cola" para o bot responder com as suas informações.'],
        ['O que acontece fora da janela de 24h do WhatsApp?', 'A política da Meta exige o uso de Templates aprovados para contatos que não enviaram mensagem nas últimas 24h. O EMME Tech detecta isso automaticamente e as automações/crons usam templates para esse caso.'],
        ['Posso cancelar a qualquer momento?', 'Sim. O cancelamento é feito direto no portal do Stripe, sem burocracia. Você mantém acesso até o fim do período pago.'],
        ['Meus dados e tokens ficam seguros?', 'Todos os tokens (WhatsApp, OpenRouter) são armazenados criptografados com AES-256-GCM no banco. Sua chave mestra fica apenas no .env do seu servidor — nunca é enviada a terceiros.'],
      ];
      foreach ($faqs as $f): ?>
      <div class="faq-item">
        <button class="faq-q" onclick="toggleFaq(this)">
          <?= htmlspecialchars($f[0]) ?>
          <span class="faq-arrow">+</span>
        </button>
        <div class="faq-a"><?= htmlspecialchars($f[1]) ?></div>
      </div>
      <?php endforeach; ?>
    </div>
  </div>
</section>

<!-- ============================================================
     CTA BANNER
     ============================================================ -->
<section class="cta-banner">
  <div class="container">
    <div class="cta-box">
      <h2>Pronto para atender<br><span class="grad">com IA 24/7?</span></h2>
      <p>Junte-se a centenas de empresas que já automatizaram o atendimento no WhatsApp. Comece grátis hoje.</p>
      <div class="cta-actions">
        <a href="/app/register" class="btn-hero">
          🚀 Criar conta grátis — 14 dias sem cartão
        </a>
        <a href="/app/login" class="btn-hero-outline">
          Já tenho conta
        </a>
      </div>
      <div class="cta-trust">
        <span>🔒 SSL &amp; dados protegidos</span>
        <span>✅ Trial de 14 dias grátis</span>
        <span>🚫 Sem cartão de crédito</span>
        <span>⚡ Ativo em minutos</span>
      </div>
    </div>
  </div>
</section>

<!-- ============================================================
     FOOTER
     ============================================================ -->
<footer class="footer">
  <div class="footer-inner">
    <div class="footer-grid">
      <div class="footer-brand">
        <div class="nav-logo" style="font-size:20px;display:inline-flex">
          <span class="nav-logo-emme">EMME</span>&nbsp;Tech
        </div>
        <p>A plataforma completa para criar e gerenciar agentes de IA no WhatsApp. Simples para quem começa, poderoso para quem escala.</p>
        <div class="footer-social">
          <a class="social-btn" href="#" title="Twitter/X">𝕏</a>
          <a class="social-btn" href="#" title="LinkedIn">in</a>
          <a class="social-btn" href="#" title="Instagram">📸</a>
        </div>
      </div>
      <div class="footer-col">
        <h4>Produto</h4>
        <ul>
          <li><a href="#features">Funcionalidades</a></li>
          <li><a href="#pricing">Planos e Preços</a></li>
          <li><a href="#como-funciona">Como funciona</a></li>
          <li><a href="#depoimentos">Cases</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>Conta</h4>
        <ul>
          <li><a href="/app/register">Criar conta</a></li>
          <li><a href="/app/login">Entrar</a></li>
          <li><a href="/app/dashboard">Dashboard</a></li>
          <li><a href="/admin/login">Admin</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>Suporte</h4>
        <ul>
          <li><a href="#faq">FAQ</a></li>
          <li><a href="mailto:suporte@wams.io">E-mail suporte</a></li>
          <li><a href="#" onclick="event.preventDefault();showToast('📖 Documentação em breve!')">Documentação</a></li>
          <li><a href="#" onclick="event.preventDefault();showToast('📬 Status: 100% operacional ✅')">Status da API</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <p>© <?= date('Y') ?> EMME Tech. Todos os direitos reservados.</p>
      <div class="footer-badges">
        <span class="footer-badge">🔒 AES-256-GCM</span>
        <span class="footer-badge">⚡ PHP 8.1+</span>
        <span class="footer-badge">💳 Stripe</span>
        <span class="footer-badge">🤖 OpenRouter</span>
      </div>
    </div>
  </div>
</footer>

<!-- Toast container -->
<div class="toast-wrap" id="toastWrap"></div>

<!-- ============================================================
     JAVASCRIPT
     ============================================================ -->
<script>
(function() {
  /* ---- Nav scroll ---- */
  const nav = document.getElementById('mainNav');
  const onScroll = () => {
    nav.classList.toggle('scrolled', window.scrollY > 20);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ---- Mobile nav ---- */
  const toggle = document.getElementById('navToggle');
  const links  = document.getElementById('navLinks');
  toggle.addEventListener('click', () => links.classList.toggle('open'));

  /* ---- Smooth close on link click ---- */
  links.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => links.classList.remove('open'));
  });

  /* ---- How it works step highlight ---- */
  const steps = document.querySelectorAll('.step');
  steps.forEach(step => {
    step.addEventListener('click', () => {
      steps.forEach(s => s.classList.remove('active'));
      step.classList.add('active');
    });
  });

  /* Auto-rotate steps */
  let cur = 0;
  setInterval(() => {
    steps.forEach(s => s.classList.remove('active'));
    cur = (cur + 1) % steps.length;
    steps[cur].classList.add('active');
  }, 3500);

  /* ---- Intersection Observer for fade-up ---- */
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.style.animationPlayState = 'running';
        observer.unobserve(e.target);
      }
    });
  }, { threshold: 0.15 });

  document.querySelectorAll('.fade-up').forEach(el => {
    el.style.animationPlayState = 'paused';
    observer.observe(el);
  });

  /* ---- Feature cells entrance ---- */
  const cellObs = new IntersectionObserver((entries) => {
    entries.forEach((e, i) => {
      if (e.isIntersecting) {
        setTimeout(() => {
          e.target.style.opacity = '1';
          e.target.style.transform = 'translateY(0)';
        }, i * 80);
        cellObs.unobserve(e.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.feature-cell').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity .5s ease, transform .5s ease';
    cellObs.observe(el);
  });

  /* ---- Metric counter animation ---- */
  function animateVal(el) {
    const text   = el.textContent;
    const num    = parseFloat(text.replace(/[^0-9.]/g, ''));
    const suffix = text.replace(/[\d.]/g, '');
    const prefix = text.startsWith('<') ? '<' : text.startsWith('+') ? '+' : '';
    if (!num) return;
    const cleanSuffix = suffix.replace(prefix, '');
    let start = 0; const steps = 60;
    const inc = num / steps;
    const timer = setInterval(() => {
      start += inc;
      if (start >= num) { start = num; clearInterval(timer); }
      const display = Number.isInteger(num) ? Math.floor(start) : start.toFixed(1);
      el.textContent = prefix + (num >= 1000 ? Math.floor(start).toLocaleString('pt-BR') : display) + cleanSuffix;
    }, 25);
  }

  const metricObs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        animateVal(e.target);
        metricObs.unobserve(e.target);
      }
    });
  }, { threshold: 0.5 });

  document.querySelectorAll('.metric-val').forEach(el => metricObs.observe(el));

  /* ---- Stat counter in hero ---- */
  const heroStatObs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const vals = e.target.querySelectorAll('.hero-stat-val');
        vals.forEach(v => animateVal(v));
        heroStatObs.unobserve(e.target);
      }
    });
  }, { threshold: 0.5 });

  const heroStats = document.querySelector('.hero-stats');
  if (heroStats) heroStatObs.observe(heroStats);
})();

/* ---- FAQ ---- */
function toggleFaq(btn) {
  const item = btn.closest('.faq-item');
  const isOpen = item.classList.contains('open');
  document.querySelectorAll('.faq-item.open').forEach(i => i.classList.remove('open'));
  if (!isOpen) item.classList.add('open');
}

/* ---- Toast notifications ---- */
function showToast(msg) {
  const wrap  = document.getElementById('toastWrap');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = msg;
  wrap.appendChild(toast);
  setTimeout(() => {
    toast.style.transition = 'opacity .4s';
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 400);
  }, 3000);
}
</script>
</body>
</html>
