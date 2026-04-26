import os
import sys

# 프로젝트 루트 디렉토리를 Python 경로에 추가
path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path not in sys.path:
    sys.path.insert(0, path)

from sentinel_cli.src.dashboard import app

# Vercel은 'app' 객체를 자동으로 찾습니다.
# dashboard.py 내부의 Flask 인스턴스 이름이 'app'이어야 합니다.
app = app
