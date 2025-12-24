# FocusPilot (v0.1)

ADHD 집중 코치: **타이머 + 오늘의 3개 목표 + 방해요소 기록 + 일일 리포트**  
"다음 행동 1줄 가이드"로 **지금 해야 할 일을** 자동으로 안내합니다.

## Features
- **Pomodoro 타이머(집중/휴식)**
  - 0초 도달 시 **집중 세션 자동 기록**
  - 소리/데스크톱 알림(옵션), 자동 휴식(옵션)
- **오늘의 3개 목표**
  - TODO/DONE 토글
- **방해요소 기록**
  - 한 줄 기록으로 흐름 복귀 지원
- **리포트**
  - 오늘의 세션/방해요소 기록 확인

## Requirements
- Python 3.10+ (권장: 3.11)
- Windows 11 / Linux / macOS (CPU only)

## Run
기본 포트: `8001`

### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python run.py
```

### Linux / macOS
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python run.py
```

- 접속: http://127.0.0.1:8001
- 리포트: http://127.0.0.1:8001/report

## Settings (UI)
타이머 카드 우측 ⚙️에서 설정 가능:
- 소리 ON/OFF
- 데스크톱 알림 ON/OFF (브라우저 권한 필요)
- 자동 휴식 ON/OFF

## Data
- SQLite DB: `focuspilot.db` (자동 생성)
- 로컬 전용 데이터이므로 기본적으로 gitignore 대상 권장

## Project Structure
```csharp
app/
  templates/       # HTML
  static/          # CSS/JS
run.py             # entrypoint
requirements.txt
```

## Troubleshooting
- 화면/JS/CSS가 반영 안 되면: **Ctrl + F5** (강력 새로고침)
- Windows에서 activate가 막히면: activate 없이 `.\.venv\Scripts\python` 경로로 실행하면 됨

## Roadmap (v0.2 ~ v0.4)
- v0.2: 날짜 선택(과거 리포트), 목표 완료율 그래프
- v0.3: 방해요소 태그 + TOP 태그통계
- v0.4: 세션 시작 시 목표 선택 → 목표별 투자시간 추적

 ## License
 MIT (see `LICENSE`)

 ## Changelog
 See `CHANGELOG.md`
