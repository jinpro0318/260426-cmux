import sys
import os
import argparse
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from .fuzzer import SentinelFuzzer
from .web_auditor import SentinelWebAuditor
from .reporter import SentinelReporter

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
console = Console()

def display_banner():
    banner_text = "[bold cyan]SENTINEL-CLI[/bold cyan]\n[dim]AI Security & Web Vulnerability Scanner[/dim]"
    console.print(Panel(banner_text, expand=False, border_style="cyan"))

def run_web_audit(url, model_name):
    auditor = SentinelWebAuditor(model_name=model_name)
    console.print(f"[bold yellow][*][/bold yellow] Starting Web Audit for: [link={url}]{url}[/link]")
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="Collecting site data...", total=None)
        site_data = auditor.fetch_site_data(url)
        
        if "error" in site_data:
            console.print(f"[bold red][!] Error:[/bold red] {site_data['error']}")
            return

        progress.add_task(description="AI Analysis in progress...", total=None)
        analysis_json = auditor.analyze_with_ai(site_data)
        analysis = json.loads(analysis_json)

    # UI Display
    console.print(f"\n[bold]Overall Risk: [/bold][{'red' if analysis['overall_risk']=='High' else 'yellow'}]{analysis['overall_risk']}[/]")
    
    table = Table(title=f"Security Analysis: {url}")
    table.add_column("Issue", style="magenta", width=30)
    table.add_column("Severity", justify="center")
    table.add_column("Improvement Strategy", style="green")

    for vuln in analysis.get("vulnerabilities", []):
        sev_color = "red" if vuln["severity"] in ["Critical", "High"] else "yellow"
        table.add_row(
            vuln["issue"],
            f"[{sev_color}]{vuln['severity']}[/]",
            vuln["improvement"]
        )
    console.print(table)
    
    # Save Report
    reporter = SentinelReporter(model_name, f"WEB_AUDIT: {url}")
    json_file = reporter.save_json(analysis)
    console.print(f"\n[bold blue][+][/bold blue] Full audit report saved: [underline]{json_file}[/underline]")

def main():
    display_banner()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="Prompt for model scan OR URL for web audit")
    parser.add_argument("--url", action="store_true", help="Enable Web Audit mode")
    parser.add_argument("--lang", default="en", choices=["en", "ko"], help="Language for model scan")
    args = parser.parse_args()

    model_name = os.getenv("TARGET_MODEL", "anthropic/claude-sonnet-4-6")
    if "claude" in model_name and "/" not in model_name: model_name = f"anthropic/{model_name}"
    elif "gemini" in model_name and "/" not in model_name: model_name = f"gemini/{model_name}"

    if args.url:
        run_web_audit(args.target, model_name)
    else:
        # Existing Model Scan Logic
        fuzzer = SentinelFuzzer(model_name=model_name)
        reporter = SentinelReporter(model_name, args.target)
        
        console.print(f"[*] Target Model: {model_name} | Lang: {args.lang.upper()}")
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task(description=f"Running {args.lang.upper()} scan...", total=None)
            results = fuzzer.run_scan(args.target, lang=args.lang)

        table = Table(title="Security Scan Results")
        table.add_column("Attack Type", style="magenta")
        table.add_column("Status", justify="center")
        table.add_column("Partial Response", style="dim", overflow="ellipsis")
        for res in results:
            status_style = "bold green" if res["status"] == "SAFE" else "bold red"
            table.add_row(res["attack_name"], f"[{status_style}]{res['status']}[/]", res["response"])
        console.print(table)
        reporter.save_json(results)

if __name__ == "__main__":
    main()
