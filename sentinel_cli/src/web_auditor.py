import requests
from bs4 import BeautifulSoup
from litellm import completion
import os
from dotenv import load_dotenv

load_dotenv()

class SentinelWebAuditor:
    def __init__(self, model_name="anthropic/claude-3-5-sonnet-20241022"):
        self.model_name = model_name

    def fetch_site_data(self, url):
        """웹사이트의 헤더와 HTML 구조를 수집합니다."""
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 보안 관련 핵심 데이터 추출
            data = {
                "url": url,
                "headers": dict(response.headers),
                "title": soup.title.string if soup.title else "No Title",
                "scripts": [script.get('src') for script in soup.find_all('script') if script.get('src')],
                "forms": len(soup.find_all('form')),
                "meta_tags": [str(meta) for meta in soup.find_all('meta')]
            }
            return data
        except Exception as e:
            return {"error": str(e)}

    def analyze_with_ai(self, site_data):
        """수집된 데이터를 AI가 분석하여 보안 리포트를 생성합니다."""
        prompt = f"""
        You are a Senior Security Engineer and Pentester. 
        Analyze the following web application data for security vulnerabilities and provide a detailed report.
        
        DATA:
        {site_data}
        
        REPORT FORMAT (STRICT JSON ONLY):
        {{
            "overall_risk": "High/Medium/Low",
            "vulnerabilities": [
                {{
                    "issue": "Specific security issue found",
                    "severity": "Critical/High/Medium/Low",
                    "description": "Why this is a problem",
                    "improvement": "Exact steps or code to fix this"
                }}
            ],
            "general_recommendations": "Broader advice for the developer"
        }}
        
        IMPORTANT: Return ONLY the raw JSON object. No markdown, no explanation.
        Answer in Korean.
        """
        
        try:
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.choices[0].message.content
            # Remove markdown code blocks if present
            content = content.replace("```json", "").replace("```", "").strip()
            return content
        except Exception as e:
            return f"{{\"error\": \"AI Analysis failed: {str(e)}\"}}"
