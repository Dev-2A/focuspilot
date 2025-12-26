# Changelog
이 프로젝트의 주요 변경사항을 기록합니다.

형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 참고했고,
버전은 (가능하면) Semantic Versioning을 따릅니다.

## [Unreleased]
### Added
- (예) 

### Changed
- (예) 

### Fixed
- (예) 

---

## [0.1.0] - 2025-12-24
### Added
- Pomodoro 타이머(집중/휴식) UI
- 0초 도달 시 집중 세션 자동 기록
- 소리/데스크톱 알림/자동 휴식 옵션(⚙ 설정)
- 오늘의 3개 목표(저장/완료 토글)
- 방해요소 한 줄 기록
- 일일 리포트 페이지

### Changed
- 미니멀 UI 정리 및 버튼 위계(Start 중심) 개선
- “다음 행동 1줄 가이드” + 클릭 시 해당 카드 이동/자동 포커스

### Fixed
- 버튼/라벨 줄바꿈으로 인한 세로쓰기 현상 수정

## [0.2.0] - 2025-12-26
### Added
- 리포트 날짜 선택(일간 보기)
- 선택 날짜 기준 최근 7일 주간 보기
- 목표 완료율 Progress Bar

### Fixed
- 세션 저장 시 DB 스키마 호환 처리(sessions.date NOT NULL 케이스)
- Break 스킵 시 타이머 interval 꼬임 수정