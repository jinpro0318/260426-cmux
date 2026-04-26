import os
import json
import glob
import sys
from flask import Flask, render_template_string, request, jsonify, Response

path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path not in sys.path:
    sys.path.insert(0, path)

from sentinel_cli.src.web_auditor import SentinelWebAuditor
from sentinel_cli.src.reporter import SentinelReporter
from sentinel_cli.src.fuzzer import SentinelFuzzer

app = Flask(__name__)
REPORT_DIR = "/tmp" if os.getenv("VERCEL") else os.getcwd()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sentinel-CLI Enterprise</title>
  <script src="https://cdn.tailwindcss.com/3.4.1/tailwind.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
  <style>
    * { font-family: 'Inter', sans-serif; }
    body { background: #000; }

    .bg-grid {
      background-image:
        linear-gradient(rgba(59,130,246,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(59,130,246,0.04) 1px, transparent 1px);
      background-size: 44px 44px;
    }

    .title-gradient {
      background: linear-gradient(135deg, #93C5FD 0%, #60A5FA 30%, #06B6D4 60%, #3B82F6 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      filter: drop-shadow(0 0 28px rgba(6,182,212,0.55)) drop-shadow(0 0 8px rgba(59,130,246,0.4));
    }

    .sub-gradient {
      background: linear-gradient(90deg, #60A5FA, #06B6D4);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    .scan-input {
      background: rgba(15,20,40,0.85);
      border: 1.5px solid rgba(59,130,246,0.35);
      border-radius: 14px 0 0 14px;
      color: #e2e8f0;
      font-size: 1rem;
      padding: 1rem 1.4rem;
      width: 100%;
      outline: none;
      transition: border-color 0.2s;
      backdrop-filter: blur(12px);
    }
    .scan-input:focus { border-color: #06B6D4; }
    .scan-input::placeholder { color: rgba(148,163,184,0.5); }

    .scan-btn {
      background: linear-gradient(135deg, #2563EB, #0891B2);
      border-radius: 0 14px 14px 0;
      color: #fff;
      font-weight: 900;
      font-size: 0.9rem;
      letter-spacing: 0.08em;
      padding: 1rem 2rem;
      cursor: pointer;
      transition: filter 0.2s, transform 0.15s;
      white-space: nowrap;
      box-shadow: 0 0 24px rgba(6,182,212,0.3);
    }
    .scan-btn:hover { filter: brightness(1.15); transform: translateY(-1px); }
    .scan-btn:active { transform: scale(0.98); }

    .card {
      background: rgba(10,14,26,0.9);
      border: 1px solid rgba(59,130,246,0.12);
      border-radius: 20px;
      backdrop-filter: blur(10px);
      transition: border-color 0.25s, box-shadow 0.25s;
    }
    .card:hover { border-color: rgba(6,182,212,0.3); box-shadow: 0 0 32px rgba(6,182,212,0.07); }

    .badge-critical { background: rgba(239,68,68,0.12); color: #FCA5A5; border: 1px solid rgba(239,68,68,0.3); }
    .badge-high     { background: rgba(249,115,22,0.12); color: #FDBA74; border: 1px solid rgba(249,115,22,0.3); }
    .badge-medium   { background: rgba(234,179,8,0.12);  color: #FDE047; border: 1px solid rgba(234,179,8,0.3); }
    .badge-low      { background: rgba(34,197,94,0.12);  color: #86EFAC; border: 1px solid rgba(34,197,94,0.3); }

    #loading-overlay { background: rgba(0,0,0,0.93); backdrop-filter: blur(6px); }

    .ring {
      width: 72px; height: 72px;
      border: 3px solid transparent;
      border-top-color: #06B6D4;
      border-right-color: rgba(6,182,212,0.3);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .pulse-dot {
      width: 10px; height: 10px;
      background: #06B6D4;
      border-radius: 50%;
      animation: pulse 1.6s ease-in-out infinite;
    }
    @keyframes pulse {
      0%,100% { opacity:1; transform: scale(1); box-shadow: 0 0 0 0 rgba(6,182,212,0.5); }
      50% { opacity:0.8; transform: scale(1.1); box-shadow: 0 0 0 8px rgba(6,182,212,0); }
    }

    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(59,130,246,0.3); border-radius: 3px; }

    .code-block {
      background: rgba(0,0,0,0.6);
      border: 1px solid rgba(59,130,246,0.1);
      border-radius: 12px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.72rem;
      color: #6EE7B7;
    }

    .navbar {
      background: rgba(0,0,0,0.75);
      border-bottom: 1px solid rgba(59,130,246,0.1);
      backdrop-filter: blur(20px);
    }

    .orb {
      position: absolute;
      border-radius: 50%;
      filter: blur(120px);
      pointer-events: none;
    }

    @keyframes fadeUp {
      from { opacity:0; transform: translateY(24px); }
      to   { opacity:1; transform: translateY(0); }
    }
    .fade-up { animation: fadeUp 0.7s ease forwards; }
    .delay-1 { animation-delay: 0.1s; opacity:0; }
    .delay-2 { animation-delay: 0.22s; opacity:0; }
    .delay-3 { animation-delay: 0.36s; opacity:0; }
    .delay-4 { animation-delay: 0.5s; opacity:0; }

    @keyframes slideIn {
      from { opacity:0; transform: translateY(16px); }
      to   { opacity:1; transform: translateY(0); }
    }
    .slide-in { animation: slideIn 0.4s ease forwards; }

    .risk-high   { color: #FCA5A5; border-color: rgba(239,68,68,0.4);  background: rgba(239,68,68,0.08); }
    .risk-medium { color: #FDE047; border-color: rgba(234,179,8,0.4);  background: rgba(234,179,8,0.08); }
    .risk-low    { color: #86EFAC; border-color: rgba(34,197,94,0.4);  background: rgba(34,197,94,0.08); }
  </style>
</head>
<body class="bg-black text-slate-200 min-h-screen">

  <!-- Loading Overlay -->
  <div id="loading-overlay" class="hidden fixed inset-0 z-50 flex flex-col items-center justify-center">
    <div class="ring mb-6"></div>
    <p class="text-cyan-400 font-bold text-lg tracking-wide" style="font-family:'JetBrains Mono',monospace">
      AI 보안 분석 중...
    </p>
    <p class="text-slate-500 text-sm mt-2">취약점을 탐지하고 있습니다</p>
  </div>

  <!-- Navbar -->
  <nav class="navbar fixed top-0 left-0 right-0 z-40 px-6 py-4">
    <div class="max-w-7xl mx-auto flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg flex items-center justify-center" style="background:linear-gradient(135deg,#2563EB,#0891B2)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
        </div>
        <span class="font-black text-sm tracking-widest" style="font-family:'JetBrains Mono',monospace">
          <span class="sub-gradient">SENTINEL</span><span class="text-slate-300">-CLI</span>
        </span>
        <span class="text-[10px] border border-blue-500/25 bg-blue-500/8 text-blue-400 rounded-full px-2 py-0.5 font-mono">v2.0</span>
      </div>
      <div class="flex items-center gap-2">
        <button onclick="setLang('ko')" id="btn-ko" class="px-3 py-1.5 text-xs font-mono rounded-lg bg-blue-500/15 text-blue-300 border border-blue-500/20">KO</button>
        <button onclick="setLang('en')" id="btn-en" class="px-3 py-1.5 text-xs font-mono rounded-lg text-slate-500 hover:text-slate-300 transition-colors">EN</button>
      </div>
    </div>
  </nav>

  <!-- HERO SECTION -->
  <section class="relative min-h-screen flex flex-col items-center justify-center bg-grid pt-20 pb-16 overflow-hidden">
    <div class="orb w-[600px] h-[600px] bg-blue-600/8 top-0 left-1/2 -translate-x-1/2 -translate-y-1/3"></div>
    <div class="orb w-[400px] h-[400px] bg-cyan-500/6 top-1/2 right-0 translate-x-1/3 -translate-y-1/2"></div>

    <div class="relative z-10 text-center px-6 max-w-4xl mx-auto">
      <div class="fade-up delay-1 inline-flex items-center gap-2 rounded-full px-4 py-1.5 mb-8 border border-blue-500/20 bg-blue-500/6 text-blue-300 text-xs font-mono">
        <div class="pulse-dot"></div>
        LLM Red Team Platform &nbsp;·&nbsp; Enterprise Edition
      </div>

      <h1 class="fade-up delay-2 text-6xl font-black leading-none tracking-tight mb-6 md:text-7xl lg:text-8xl">
        <span class="title-gradient">SENTINEL</span>
      </h1>
      <h2 class="fade-up delay-2 text-3xl font-black leading-tight tracking-tight mb-4 md:text-4xl">
        <span class="title-gradient" data-i18n="hero_title">차세대 AI 보안 통합 진단</span>
      </h2>
      <p class="fade-up delay-3 text-slate-400 text-lg mb-12 max-w-xl mx-auto leading-relaxed" data-i18n="hero_desc">
        웹사이트 URL을 입력하면 AI가 취약점을 자동 탐지하고<br>보완 코드까지 즉시 생성합니다.
      </p>

      <div class="fade-up delay-4 max-w-2xl mx-auto">
        <div class="flex shadow-2xl shadow-blue-900/30">
          <input type="text" id="url-input" class="scan-input" placeholder="https://example.com">
          <button onclick="startAudit()" class="scan-btn" data-i18n="scan_btn">SCAN</button>
        </div>
        <p class="text-slate-600 text-xs mt-3 font-mono">예: https://yoursite.com &nbsp;·&nbsp; 평균 소요 시간 20–40초</p>
      </div>

      <div class="fade-up delay-4 mt-14 flex flex-wrap items-center justify-center gap-8 border-t border-white/5 pt-10">
        <div class="text-center">
          <p class="text-2xl font-black sub-gradient">7+</p>
          <p class="text-xs text-slate-500 mt-0.5">Attack Vectors</p>
        </div>
        <div class="w-px h-8 bg-white/5"></div>
        <div class="text-center">
          <p class="text-2xl font-black sub-gradient">OWASP</p>
          <p class="text-xs text-slate-500 mt-0.5">LLM Top 10</p>
        </div>
        <div class="w-px h-8 bg-white/5"></div>
        <div class="text-center">
          <p class="text-2xl font-black sub-gradient">AI</p>
          <p class="text-xs text-slate-500 mt-0.5">Auto Remediation</p>
        </div>
        <div class="w-px h-8 bg-white/5"></div>
        <div class="text-center">
          <p class="text-2xl font-black sub-gradient">PDF</p>
          <p class="text-xs text-slate-500 mt-0.5">Report Export</p>
        </div>
      </div>
    </div>
  </section>

  <!-- DASHBOARD SECTION -->
  <div class="max-w-7xl mx-auto px-6 py-16 space-y-8">

    <!-- Top cards: Stats + Sandbox -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="card lg:col-span-2 p-7">
        <h3 class="sub-gradient font-bold text-sm uppercase tracking-widest mb-6 font-mono" data-i18n="stats_title">보안 취약점 통계</h3>
        <div class="h-56">
          <canvas id="statsChart"></canvas>
        </div>
      </div>

      <div class="card p-7 flex flex-col">
        <h3 class="sub-gradient font-bold text-sm uppercase tracking-widest mb-1 font-mono" data-i18n="sandbox_title">페이로드 샌드박스</h3>
        <p class="text-slate-500 text-xs mb-4" data-i18n="sandbox_desc">커스텀 공격 프롬프트를 AI 모델에 직접 테스트해 보세요.</p>
        <textarea id="sandbox-prompt" rows="4"
          class="w-full bg-black/60 border border-blue-500/15 rounded-xl p-3 text-sm text-slate-200 placeholder-slate-600 mb-3 focus:outline-none focus:border-blue-500/40 resize-none font-mono"
          placeholder="Enter attack prompt..."></textarea>
        <button onclick="runSandbox()"
          class="w-full py-2.5 rounded-xl font-bold text-sm text-white transition-all hover:brightness-110"
          style="background:linear-gradient(135deg,#7C3AED,#6366F1)">
          TEST ATTACK
        </button>
        <div id="sandbox-result" class="mt-3 p-3 bg-black/50 rounded-lg text-[10px] font-mono text-purple-300 max-h-20 overflow-auto border border-purple-500/10"></div>
      </div>
    </div>

    <!-- Audit Results (dynamic) -->
    <div id="results-section" class="grid grid-cols-1 gap-6">

      <!-- Empty state (shown by default) -->
      <div id="empty-state" class="card flex flex-col items-center justify-center py-20 text-center">
        <div class="w-14 h-14 rounded-2xl flex items-center justify-center mb-4" style="background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.15)">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#60A5FA" stroke-width="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
        </div>
        <p class="text-slate-400 font-medium">아직 스캔 결과가 없습니다</p>
        <p class="text-slate-600 text-sm mt-1">위 검색창에 URL을 입력하여 보안 진단을 시작하세요</p>
      </div>

      <!-- Results (rendered dynamically) -->
      <div id="audit-results" class="hidden space-y-4">

        <!-- Summary row -->
        <div id="result-summary" class="card p-6 flex flex-wrap items-center gap-6"></div>

        <!-- Vulnerability list -->
        <div id="vuln-list" class="card overflow-hidden">
          <div class="px-7 py-5 border-b border-blue-500/10 flex items-center justify-between">
            <h3 class="sub-gradient font-bold text-sm uppercase tracking-widest font-mono">AI 진단 결과 &amp; 패치 가이드</h3>
            <span id="issue-count" class="text-xs text-slate-600 font-mono"></span>
          </div>
          <div id="vuln-items"></div>
        </div>

        <!-- General recommendations -->
        <div id="reco-card" class="card p-7 hidden">
          <h3 class="sub-gradient font-bold text-sm uppercase tracking-widest mb-4 font-mono">종합 보안 권고사항</h3>
          <p id="reco-text" class="text-slate-300 text-sm leading-relaxed"></p>
        </div>
      </div>
    </div>
  </div>

  <!-- Footer -->
  <footer class="border-t border-blue-500/8 py-8 mt-8">
    <p class="text-center text-slate-600 text-xs font-mono">
      SENTINEL-CLI ENTERPRISE &nbsp;·&nbsp; For authorized security research only &nbsp;·&nbsp; © 2026
    </p>
  </footer>

  <script>
    /* ── i18n ── */
    const i18n = {
      ko: {
        hero_title: "차세대 AI 보안 통합 진단",
        hero_desc: "웹사이트 URL을 입력하면 AI가 취약점을 자동 탐지하고 보완 코드까지 즉시 생성합니다.",
        scan_btn: "SCAN",
        sandbox_title: "페이로드 샌드박스",
        sandbox_desc: "커스텀 공격 프롬프트를 AI 모델에 직접 테스트해 보세요.",
        stats_title: "보안 취약점 통계",
        improvement: "보완 자동화 코드",
        archive: "보안 리포트 목록"
      },
      en: {
        hero_title: "Next-Gen AI Security Audit",
        hero_desc: "Enter a URL and our AI instantly detects vulnerabilities and generates remediation code.",
        scan_btn: "SCAN",
        sandbox_title: "Payload Sandbox",
        sandbox_desc: "Test custom attack prompts against AI models.",
        stats_title: "Vulnerability Statistics",
        improvement: "Auto-Remediation Code",
        archive: "Report Archive"
      }
    };
    function setLang(lang) {
      document.querySelectorAll('[data-i18n]').forEach(el => {
        el.innerText = i18n[lang][el.getAttribute('data-i18n')] || el.innerText;
      });
      document.getElementById('btn-ko').className = lang === 'ko'
        ? 'px-3 py-1.5 text-xs font-mono rounded-lg bg-blue-500/15 text-blue-300 border border-blue-500/20'
        : 'px-3 py-1.5 text-xs font-mono rounded-lg text-slate-500 hover:text-slate-300 transition-colors';
      document.getElementById('btn-en').className = lang === 'en'
        ? 'px-3 py-1.5 text-xs font-mono rounded-lg bg-blue-500/15 text-blue-300 border border-blue-500/20'
        : 'px-3 py-1.5 text-xs font-mono rounded-lg text-slate-500 hover:text-slate-300 transition-colors';
    }

    /* ── Chart ── */
    const chartData = { critical: 0, high: 0, medium: 0, low: 0 };
    const ctx = document.getElementById('statsChart').getContext('2d');
    Chart.defaults.color = '#64748b';
    const statsChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Critical', 'High', 'Medium', 'Low'],
        datasets: [{
          data: [0, 0, 0, 0],
          backgroundColor: ['rgba(239,68,68,0.7)','rgba(249,115,22,0.7)','rgba(234,179,8,0.7)','rgba(34,197,94,0.7)'],
          borderColor: ['#EF4444','#F97316','#EAB308','#22C55E'],
          borderWidth: 1,
          borderRadius: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, grid: { color: 'rgba(59,130,246,0.07)' }, ticks: { color: '#475569' } },
          x: { grid: { display: false }, ticks: { color: '#475569' } }
        }
      }
    });

    function updateChart(vulns) {
      const counts = { critical: 0, high: 0, medium: 0, low: 0 };
      vulns.forEach(v => {
        const s = (v.severity || '').toLowerCase();
        if (counts[s] !== undefined) counts[s]++;
      });
      statsChart.data.datasets[0].data = [counts.critical, counts.high, counts.medium, counts.low];
      statsChart.update();
    }

    /* ── Render results ── */
    function escapeHtml(s) {
      return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    function renderResults(analysis) {
      const vulns = analysis.vulnerabilities || [];
      const risk = (analysis.overall_risk || '').toLowerCase();
      const reco = analysis.general_recommendations || '';

      // Summary
      const riskClass = risk.includes('high') || risk.includes('critical') ? 'risk-high' : risk.includes('medium') ? 'risk-medium' : 'risk-low';
      document.getElementById('result-summary').innerHTML = `
        <div>
          <p class="text-xs text-slate-500 font-mono mb-1">OVERALL RISK</p>
          <span class="text-lg font-black px-4 py-1.5 rounded-xl border font-mono ${riskClass}">${escapeHtml(analysis.overall_risk || 'Unknown')}</span>
        </div>
        <div class="w-px h-10 bg-white/5 hidden md:block"></div>
        <div>
          <p class="text-xs text-slate-500 font-mono mb-1">ISSUES FOUND</p>
          <p class="text-2xl font-black text-white">${vulns.length}</p>
        </div>
        <div class="w-px h-10 bg-white/5 hidden md:block"></div>
        <div>
          <p class="text-xs text-slate-500 font-mono mb-1">TARGET</p>
          <p class="text-sm text-cyan-400 font-mono truncate max-w-xs">${escapeHtml(document.getElementById('url-input').value)}</p>
        </div>
      `;

      // Issue count
      document.getElementById('issue-count').textContent = vulns.length + ' issues found';

      // Vulnerabilities
      const container = document.getElementById('vuln-items');
      container.innerHTML = '';
      if (vulns.length === 0) {
        container.innerHTML = '<div class="px-7 py-10 text-center text-slate-500">취약점이 발견되지 않았습니다.</div>';
      } else {
        vulns.forEach((v, i) => {
          const sev = (v.severity || 'low').toLowerCase();
          const div = document.createElement('div');
          div.className = 'px-7 py-6 border-b border-white/5 last:border-0 hover:bg-blue-500/3 transition-colors slide-in';
          div.style.animationDelay = (i * 0.07) + 's';
          div.style.opacity = '0';
          div.innerHTML = `
            <div class="flex items-start justify-between gap-4 mb-3">
              <h4 class="text-white font-semibold leading-snug">${escapeHtml(v.issue || '')}</h4>
              <span class="shrink-0 text-[10px] font-black px-2.5 py-1 rounded-lg badge-${sev}">${escapeHtml(v.severity || '')}</span>
            </div>
            <p class="text-slate-400 text-sm mb-4 leading-relaxed">${escapeHtml(v.description || '')}</p>
            <div class="code-block p-4">
              <div class="flex items-center justify-between mb-2">
                <span class="text-[10px] text-emerald-400 font-bold uppercase tracking-wider">보완 자동화 코드</span>
                <button onclick="navigator.clipboard.writeText(${JSON.stringify(v.improvement || '')})"
                  class="text-[10px] border border-white/10 rounded px-2 py-0.5 text-slate-500 hover:text-slate-200 transition-colors">COPY</button>
              </div>
              <pre class="text-[11px] whitespace-pre-wrap leading-relaxed">${escapeHtml(v.improvement || '')}</pre>
            </div>
          `;
          container.appendChild(div);
        });
      }

      // General recommendations
      if (reco) {
        document.getElementById('reco-text').textContent = reco;
        document.getElementById('reco-card').classList.remove('hidden');
      }

      // Update chart
      updateChart(vulns);

      // Show results, hide empty state
      document.getElementById('empty-state').classList.add('hidden');
      document.getElementById('audit-results').classList.remove('hidden');

      // Scroll to results
      document.getElementById('results-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    /* ── Audit ── */
    async function startAudit() {
      const url = document.getElementById('url-input').value.trim();
      if (!url) { alert('URL을 입력해주세요.'); return; }
      document.getElementById('loading-overlay').classList.remove('hidden');
      try {
        const res = await fetch('/api/audit', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({url})
        });
        const data = await res.json();
        document.getElementById('loading-overlay').classList.add('hidden');
        if (data.success && data.analysis) {
          renderResults(data.analysis);
        } else {
          alert('진단 실패: ' + (data.error || '알 수 없는 오류'));
        }
      } catch(e) {
        document.getElementById('loading-overlay').classList.add('hidden');
        alert('오류: ' + e.message);
      }
    }
    document.getElementById('url-input').addEventListener('keydown', e => { if (e.key === 'Enter') startAudit(); });

    /* ── Sandbox ── */
    async function runSandbox() {
      const prompt = document.getElementById('sandbox-prompt').value.trim();
      if (!prompt) { alert('프롬프트를 입력해주세요.'); return; }
      const el = document.getElementById('sandbox-result');
      el.innerText = 'Analyzing...';
      try {
        const res = await fetch('/api/sandbox', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({prompt})
        });
        const data = await res.json();
        el.innerText = JSON.stringify(data.result || data.error, null, 2);
      } catch(e) { el.innerText = 'Error: ' + e.message; }
    }
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/audit', methods=['POST'])
def audit():
    try:
        data = request.json
        url = data.get('url')
        if not url:
            return jsonify({"success": False, "error": "URL이 필요합니다."})
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return jsonify({"success": False, "error": "API 키가 설정되지 않았습니다. Vercel 환경변수에 GEMINI_API_KEY를 추가해주세요."})
        model_name = os.getenv("TARGET_MODEL", "gemini/gemini-2.0-flash")
        auditor = SentinelWebAuditor(model_name=model_name)
        site_data = auditor.fetch_site_data(url)
        if "error" in site_data:
            return jsonify({"success": False, "error": f"사이트 접근 실패: {site_data['error']}"})
        raw = auditor.analyze_with_ai(site_data)
        analysis = json.JSONDecoder(strict=False).decode(raw)
        if "error" in analysis:
            return jsonify({"success": False, "error": analysis["error"]})
        # Save report (best-effort; not required for display)
        try:
            reporter = SentinelReporter(model_name, f"WEB_AUDIT: {url}")
            reporter.save_json(analysis)
        except Exception:
            pass
        return jsonify({"success": True, "analysis": analysis})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/sandbox', methods=['POST'])
def sandbox():
    try:
        data = request.json
        prompt = data.get('prompt')
        model_name = os.getenv("TARGET_MODEL", "gemini/gemini-2.0-flash")
        fuzzer = SentinelFuzzer(model_name=model_name)
        res = fuzzer.run_scan(prompt)
        return jsonify({"result": res})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/view/<filename>')
def view(filename):
    try:
        full_path = os.path.join(REPORT_DIR, filename)
        if not os.path.exists(full_path):
            return jsonify({"error": "Report file not found"}), 404
        with open(full_path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/favicon.ico')
def favicon():
    return Response(status=204)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
