# morning-briefing-bot — 24/7 아침 브리핑 텔레그램 봇

[![CI](https://github.com/dashcloud-kr/morning-briefing-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/dashcloud-kr/morning-briefing-bot/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

**날씨 + 미세먼지 + 환율 + 주요 뉴스**를 매일 아침 한 메시지로 보내주는 텔레그램 봇입니다.
[대시클라우드(DashCloud)](https://dashcloud.kr)에서 **평생 무료로 24시간** 가동할 수 있습니다.

> **English** — A Telegram bot that sends a daily morning briefing: weather (KMA), air quality (AirKorea), exchange rates (Korea Exim Bank) and top news headlines. Built to run 24/7 on [DashCloud](https://dashcloud.kr) for free.

## 기능

| 기능 | 설명 |
| --- | --- |
| 날씨 | 기상청 단기예보 — 하늘·최고/최저·강수확률 (19개 도시) |
| 미세먼지 | 에어코리아 시도 평균 PM10·PM2.5 + 등급 (좋음~매우나쁨) |
| 환율 | 수출입은행 매매기준율 — USD·JPY(100)·EUR·CNY (휴장일 자동 폴백) |
| 주요 뉴스 | 구글 뉴스 헤드라인 5건 |
| 섹션 선택 | `/sections weather,news` — 원하는 항목만 |
| 시간·지역 | `/settime 07:30`, `/region 부산` |
| 주말 모드 | 기본 주말 제외, `/weekend on`으로 수신 |
| 섹션 격리 | 한 API가 실패해도 나머지 섹션은 정상 발송 |

## 명령어

```
/briefing on            매일 아침 브리핑 받기
/settime 07:30          발송 시각 (KST)
/region 서울             지역 (19개 도시)
/sections weather,dust,fx,news   섹션 선택
/weekend on             주말에도 받기

/preview                지금 바로 미리보기
/settings               내 설정 요약
/status /id             봇 상태 / 내 chat id
```

## 준비물 — API 키 2개 (무료)

1. **공공데이터포털** ([data.go.kr](https://www.data.go.kr)) — 회원가입 후 활용신청 (자동승인)
   - `단기예보 조회서비스` (기상청)
   - `에어코리아 대기오염정보` (한국환경공단)
   - → 마이페이지 → 개발계정의 **일반 인증키** → `DATA_GO_KR_KEY`
2. **한국수출입은행** ([koreaexim.go.kr](https://www.koreaexim.go.kr)) — 환율 API 키 신청 → `KOREAEXIM_API_KEY`

## 30초 로컬 실행

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env 에 TELEGRAM_BOT_TOKEN, DATA_GO_KR_KEY, KOREAEXIM_API_KEY 입력

python bot.py
```

## DashCloud로 24시간 무료 가동

1. [dashcloud.kr](https://dashcloud.kr) 가입 — 휴대폰 인증 1회, 결제 정보 불필요
2. 이 폴더를 대시보드에 **드래그 앤 드롭**
3. 환경변수에 3개 키 등록
4. 배포 — `dashcloud.json`이 런타임(Python 3.12)과 진입점을 자동 설정합니다

> 노트북을 덮어도 봇이 계속 돌아갑니다. Free 플랜은 평생 무료이며 갱신·슬립이 없습니다.

## 구조

```
morning-briefing-bot/
├── bot.py                        # 엔트리포인트 (마이그레이션·분 단위 발송 잡)
├── app/
│   ├── clients/                  # kma(날씨)·airkorea(미세먼지)·koreaexim(환율)·newsrss(뉴스)
│   ├── services/
│   │   ├── regions.py            # 19개 도시 → 기상청 격자·시도 매핑
│   │   ├── briefing.py           # 섹션 조립 (실패 격리) + 포맷
│   │   └── repository.py         # SQLite 설정
│   ├── handlers/briefing.py      # 명령어 + 발송 잡
│   └── utils/                    # 메시지 분할 등 공통
└── tests/                        # 78개 (API 모킹·폴백·시간 고정 잡 테스트)
```

## 테스트

```bash
pip install -r requirements-dev.txt
ruff check . && pytest -q
```

## 라이선스

[MIT](LICENSE) — 자유롭게 복사·수정·배포하세요.
