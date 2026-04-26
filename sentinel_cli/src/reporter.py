import json
import os
import re
from datetime import datetime
from fpdf import FPDF

class SentinelReporter:
    def __init__(self, target_model, target_prompt):
        self.target_model = target_model
        self.target_prompt = target_prompt
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.save_dir = "/tmp" if os.getenv("VERCEL") else os.getcwd()

    def _clean_text(self, text):
        """FPDF의 한계로 인해 비라틴 문자(한글 등)를 제거합니다."""
        if not text: return ""
        # 라틴 문자, 숫자, 일반적인 기호만 남기고 제거
        return re.sub(r'[^\x00-\x7F]+', ' ', str(text))

    def save_json(self, results):
        report = {
            "metadata": {
                "target_model": self.target_model,
                "target_prompt": self.target_prompt,
                "timestamp": self.timestamp
            }
        }
        if isinstance(results, dict) and "vulnerabilities" in results:
            report.update(results)
        else:
            report["results"] = results
            
        filename = f"sentinel_report_{self.timestamp}.json"
        full_path = os.path.join(self.save_dir, filename)
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
        return filename

    def save_web_audit_pdf(self, analysis):
        """Web Audit전용 PDF 리포트 생성 (한글 필터링 적용)"""
        try:
            pdf = FPDF()
            pdf.add_page()
            
            # Header
            pdf.set_font("Helvetica", "B", 20)
            pdf.set_text_color(0, 102, 204)
            pdf.cell(0, 15, "WEB SECURITY AUDIT REPORT", ln=True, align="C")
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(0, 5, "(Note: Non-Latin characters removed for compatibility)", ln=True, align="C")
            pdf.ln(5)
            
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, f"Audit ID: SENTINEL-{self.timestamp}", ln=True, align="R")
            pdf.cell(0, 5, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="R")
            pdf.ln(10)
            
            # Metadata
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 10, " SCAN OVERVIEW", ln=True, fill=True)
            pdf.ln(2)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(40, 8, "Target URL:", 0)
            pdf.cell(0, 8, self._clean_text(self.target_prompt), ln=True)
            pdf.cell(40, 8, "Overall Risk:", 0)
            
            risk = str(analysis.get("overall_risk", "Unknown")).upper()
            if "HIGH" in risk or "CRITICAL" in risk: pdf.set_text_color(255, 0, 0)
            elif "MEDIUM" in risk: pdf.set_text_color(200, 150, 0)
            else: pdf.set_text_color(0, 150, 0)
            
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 8, risk, ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(10)
            
            # Vulnerabilities
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, " SECURITY VULNERABILITIES", ln=True, fill=True)
            pdf.ln(5)
            
            for vuln in analysis.get("vulnerabilities", []):
                if pdf.get_y() > 250: pdf.add_page()
                
                # Issue Title
                pdf.set_font("Helvetica", "B", 11)
                issue_title = self._clean_text(vuln.get("issue", "Security Issue"))
                pdf.cell(0, 8, f"> {issue_title[:70]}", ln=True)
                
                # Severity
                pdf.set_font("Helvetica", "I", 9)
                pdf.cell(30, 6, f"Severity: {vuln.get('severity', 'N/A')}", ln=True)
                
                # Description & Improvement
                pdf.set_font("Helvetica", "", 9)
                desc = self._clean_text(vuln.get("description", ""))
                pdf.multi_cell(0, 5, f"Description: {desc}")
                pdf.ln(2)
                
                pdf.set_fill_color(245, 255, 245)
                imp = self._clean_text(vuln.get("improvement", ""))
                pdf.multi_cell(0, 5, f"FIX: {imp}", border=1, fill=True)
                pdf.ln(5)

            filename = f"sentinel_report_{self.timestamp}.pdf"
            full_path = os.path.join(self.save_dir, filename)
            pdf.output(full_path)
            return filename
        except Exception as e:
            print(f"CRITICAL PDF ERROR: {e}")
            return None

    def save_pdf(self, results):
        # Legacy support
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, "SENTINEL-CLI SCAN REPORT", ln=True)
            filename = f"sentinel_report_{self.timestamp}.pdf"
            full_path = os.path.join(self.save_dir, filename)
            pdf.output(full_path)
            return filename
        except:
            return None

    def generate_summary(self, results):
        if isinstance(results, dict) and "vulnerabilities" in results:
            vulnerabilities = results["vulnerabilities"]
            total = len(vulnerabilities)
            vuln_count = len([v for v in vulnerabilities if v["severity"] in ["High", "Critical", "Medium"]])
        else:
            vulnerabilities = [r for r in results if r["status"] == "VULNERABLE"]
            total = len(results)
            vuln_count = len(vulnerabilities)
        
        return {
            "total_tests": total,
            "vulnerabilities_found": vuln_count,
            "risk_score": (vuln_count / total) * 100 if total > 0 else 0
        }
