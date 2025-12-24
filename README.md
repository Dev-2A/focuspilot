# FocusPilot (v0.1)

ADHD 집중 코치: 타이머 + 오늘의 3개 목표 + 방해요소 기록 + 일일 리포트

## 실행
### Windows
```powershell
py -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\pythono run.py
```
### Linux
```bash
python -m venv .venv
. .\venv/bin/activate
pip install -r requirements.txt
python run.py
```
접속: http://127.0.0.1:8001  
리포트: http://127.0.0.1:8001/report

## 데이터
- SQLite 파일: focuspilot.db (자동 생성)

## 다음 확장 로드맵 (v0.2~v0.4)
- v0.2: 날짜 선택(어제/지난주 리포트 보기), 목표 "완료율" 그래프
- v0.3: 방해요소 태그(슬랙/유튜브/잡일) + TOP 태그 통계
- v0.4: "세션 시작 시 목표 선택" → 목표별 실제 투자시간 추적