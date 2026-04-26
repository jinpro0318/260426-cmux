import os
import json
import glob
import sys
from datetime import datetime
from flask import Flask, render_template_string, send_from_directory, request, jsonify

# 경로 설정
path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path not in sys.path:
    sys.path.insert(0, path)

from sentinel_cli.src.web_auditor import SentinelWebAuditor
from sentinel_cli.src.reporter import SentinelReporter
from sentinel_cli.src.fuzzer import SentinelFuzzer

app = Flask(__name__)
# Vercel 환경에서는 /tmp 디렉토리만 쓰기 가능함
REPORT_DIR = "/tmp" if os.getenv("VERCEL") else os.getcwd()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sentinel-CLI Enterprise Security</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        let currentLang = 'ko';
        const i18n = {
            en: {
                title: "SENTINEL-CLI ENTERPRISE",
                hero_title: "Next-Gen AI Security Audit",
                scan_btn: "Start Audit",
                sandbox_title: "Payload Sandbox",
                sandbox_desc: "Test custom attack prompts against AI models.",
                stats_title: "Vulnerability Statistics",
                improvement: "Auto-Remediation Code"
            },
            ko: {
                title: "Sentinel-CLI 엔터프라이즈",
                hero_title: "차세대 AI 보안 통합 진단",
                scan_btn: "실시간 진단",
                sandbox_title: "페이로드 샌드박스",
                sandbox_desc: "커스텀 공격 프롬프트를 AI 모델에 직접 테스트해 보세요.",
                stats_title: "보안 취약점 통계",
                improvement: "보완 자동화 코드"
            }
        };

        function setLang(lang) {
            currentLang = lang;
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                el.innerText = i18n[lang][key];
            });
        }

        async function startAudit() {
            const url = document.getElementById('url-input').value;
            if(!url) return alert('URL을 입력해주세요.');
            document.getElementById('loading-overlay').classList.remove('hidden');
            const res = await fetch('/api/audit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url: url})
            });
            const data = await res.json();
            if(data.success) location.reload();
            else { alert('진단 실패: ' + data.error); document.getElementById('loading-overlay').classList.add('hidden'); }
        }

        async function runSandbox() {
            const prompt = document.getElementById('sandbox-prompt').value;
            if(!prompt) return alert('프롬프트를 입력해주세요.');
            document.getElementById('sandbox-result').innerText = "Analyzing...";
            const res = await fetch('/api/sandbox', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({prompt: prompt})
            });
            const data = await res.json();
            document.getElementById('sandbox-result').innerText = JSON.stringify(data.result, null, 2);
        }
    </script>
</head>
<body class="bg-gray-900 text-white min-h-screen font-sans">
    <div id="loading-overlay" class="hidden fixed inset-0 bg-black/90 z-50 flex flex-col items-center justify-center">
        <div class="w-20 h-20 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mb-6 shadow-lg shadow-cyan-500/50"></div>
        <p class="text-cyan-400 font-bold text-xl animate-pulse">AI 보안 전문가가 정밀 분석 중입니다...</p>
    </div>

    <!-- Top Nav -->
    <nav class="bg-gray-800 p-6 border-b border-cyan-500/20 shadow-xl">
        <div class="container mx-auto flex justify-between items-center">
            <h1 data-i18n="title" class="text-2xl font-black text-cyan-400 tracking-tighter">SENTINEL-CLI ENTERPRISE</h1>
            <div class="flex bg-gray-900 rounded-lg p-1">
                <button onclick="setLang('ko')" class="px-3 py-1 text-xs">KO</button>
                <button onclick="setLang('en')" class="px-3 py-1 text-xs">EN</button>
            </div>
        </div>
    </nav>

    <main class="container mx-auto py-10 px-4">
        <!-- Stats Row -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-10">
            <div class="lg:col-span-2 bg-gray-800 p-8 rounded-3xl border border-gray-700 shadow-2xl">
                <h2 data-i18n="stats_title" class="text-xl font-bold mb-6 text-cyan-400 uppercase tracking-widest">보안 취약점 통계</h2>
                <div class="h-64">
                    <canvas id="statsChart"></canvas>
                </div>
            </div>
            <div class="bg-gray-800 p-8 rounded-3xl border border-gray-700 shadow-2xl">
                <h2 data-i18n="sandbox_title" class="text-xl font-bold mb-2 text-purple-400">페이로드 샌드박스</h2>
                <p data-i18n="sandbox_desc" class="text-xs text-gray-500 mb-4">커스텀 공격 프롬프트를 테스트해 보세요.</p>
                <textarea id="sandbox-prompt" class="w-full h-24 bg-gray-900 border border-gray-700 rounded-xl p-3 text-sm mb-3 focus:outline-none focus:border-purple-500" placeholder="Type attack prompt..."></textarea>
                <button onclick="runSandbox()" class="w-full bg-purple-600 hover:bg-purple-500 py-3 rounded-xl font-bold transition-all">TEST ATTACK</button>
                <div id="sandbox-result" class="mt-4 p-3 bg-black/50 rounded-lg text-[10px] font-mono text-purple-300 max-h-20 overflow-auto"></div>
            </div>
        </div>

        <!-- Hero URL Input -->
        <div class="bg-gradient-to-r from-cyan-900/20 to-blue-900/20 p-10 rounded-3xl border border-cyan-500/30 mb-10 text-center">
            <h2 data-i18n="hero_title" class="text-3xl font-bold mb-6">차세대 AI 보안 통합 진단</h2>
            <div class="max-w-2xl mx-auto flex gap-2">
                <input type="text" id="url-input" placeholder="https://..." class="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-5 py-4 focus:outline-none focus:border-cyan-500">
                <button onclick="startAudit()" class="bg-cyan-600 hover:bg-cyan-500 px-8 py-4 rounded-xl font-black">SCAN</button>
            </div>
        </div>

        <!-- Latest Results & Archive -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div class="lg:col-span-2 space-y-8">
                {% if latest_report and latest_report.vulnerabilities %}
                <div class="bg-gray-800 rounded-3xl border border-gray-700 overflow-hidden shadow-2xl">
                    <div class="px-8 py-6 bg-gray-700/20 border-b border-gray-700">
                        <h2 class="text-xl font-bold text-cyan-400">AI 보안 진단 결과 & 패치 가이드</h2>
                    </div>
                    {% for vuln in latest_report.vulnerabilities %}
                    <div class="p-8 border-b border-gray-700/50 last:border-0 hover:bg-gray-700/20 transition-all">
                        <div class="flex justify-between items-start mb-4">
                            <h3 class="text-lg font-bold">{{ vuln.issue }}</h3>
                            <span class="px-3 py-1 rounded-lg text-xs font-black border border-red-500/50 text-red-400 bg-red-900/20">{{ vuln.severity }}</span>
                        </div>
                        <p class="text-sm text-gray-400 mb-6 italic">{{ vuln.description }}</p>
                        <div class="bg-gray-900 rounded-2xl p-6 border border-gray-700">
                            <div class="flex justify-between items-center mb-4">
                                <span data-i18n="improvement" class="text-xs font-bold text-green-500 uppercase tracking-widest">보완 자동화 코드</span>
                                <button class="text-[10px] bg-gray-800 px-2 py-1 rounded border border-gray-600 hover:text-white" onclick="navigator.clipboard.writeText(`{{ vuln.improvement }}`)">COPY CODE</button>
                            </div>
                            <pre class="text-xs text-green-400 font-mono whitespace-pre-wrap">{{ vuln.improvement }}</pre>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
            </div>

            <div class="bg-gray-800 p-8 rounded-3xl border border-gray-700 shadow-2xl h-fit">
                <h2 data-i18n="archive" class="text-xl font-bold mb-6">보안 리포트 목록</h2>
                <div class="space-y-3">
                    {% for report in all_reports %}
                    <div class="flex items-center justify-between p-4 bg-gray-900/50 rounded-xl border border-gray-700">
                        <div class="truncate">
                            <p class="text-xs font-bold truncate">{{ report.name }}</p>
                        </div>
                        <a href="/view/{{ report.name }}" target="_blank" class="text-[10px] bg-cyan-900/30 text-cyan-400 px-3 py-1 rounded border border-cyan-500/30">VIEW</a>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </main>

    <script>
        const ctx = document.getElementById('statsChart').getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Critical', 'High', 'Medium', 'Low'],
                datasets: [{
                    label: 'Vulnerabilities Found',
                    data: [{{ stats.critical }}, {{ stats.high }}, {{ stats.medium }}, {{ stats.low }}],
                    backgroundColor: ['#ef4444', '#f97316', '#eab308', '#22c55e']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, grid: { color: '#374151' } } }
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    json_files = glob.glob(os.path.join(REPORT_DIR, "sentinel_report_*.json"))
    all_reports = []
    stats = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    
    for f in json_files:
        all_reports.append({
            "name": os.path.basename(f), 
            "date": os.path.getmtime(f)
        })
        try:
            with open(f, 'r') as jf:
                data = json.load(jf)
                for v in data.get("vulnerabilities", []):
                    s = v.get("severity", "").lower()
                    if s in stats: stats[s] += 1
        except: pass

    all_reports.sort(key=lambda x: x["date"], reverse=True)
    
    latest_report = None
    if json_files:
        latest_file = max(json_files, key=os.path.getmtime)
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                latest_report = json.load(f)
        except: pass
            
    return render_template_string(HTML_TEMPLATE, latest_report=latest_report, all_reports=all_reports, stats=stats)

@app.route('/api/audit', methods=['POST'])
def audit():
    try:
        data = request.json
        url = data.get('url')
        model_name = os.getenv("TARGET_MODEL", "anthropic/claude-sonnet-4-6")
        auditor = SentinelWebAuditor(model_name=model_name)
        site_data = auditor.fetch_site_data(url)
        analysis = json.loads(auditor.analyze_with_ai(site_data))
        reporter = SentinelReporter(model_name, f"WEB_AUDIT: {url}")
        reporter.save_json(analysis)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/sandbox', methods=['POST'])
def sandbox():
    try:
        data = request.json
        prompt = data.get('prompt')
        model_name = os.getenv("TARGET_MODEL", "anthropic/claude-sonnet-4-6")
        fuzzer = SentinelFuzzer(model_name=model_name)
        # 샌드박스용 간단한 스캔 로직
        res = fuzzer.run_scan(prompt)
        return jsonify({"result": res})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/view/<filename>')
def view(filename):
    """500 에러 해결: 안전한 파일 읽기 및 JSON 반환"""
    try:
        full_path = os.path.join(REPORT_DIR, filename)
        if not os.path.exists(full_path):
            return jsonify({"error": "Report file not found"}), 404
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
