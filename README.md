# 바이낸스 탑트레이더 GitHub Actions 모니터링

GitHub Actions를 사용하여 30분마다 자동으로 바이낸스 선물시장의 탑트레이더 롱/숏 분포와 미결제약정(OI) 변화를 모니터링하고 디스코드로 알림을 보내는 시스템입니다.

## 기능

- **30분 간격 자동 모니터링** (GitHub Actions Cron)
- **탑트레이더 분석**: 롱/숏 계정 분포 상위 5개
- **미결제약정 분석**: OI 급증 상위 5개  
- **디스코드 웹훅 알림**: 실시간 결과 전송
- **환경변수 기반 설정**: 유연한 구성 관리

## 설정 방법

### 1. 리포지토리 설정

1. GitHub에서 새로운 리포지토리를 생성합니다
2. 다음 파일들을 업로드합니다:
   - `binance_top_trader_monitor_github.py` (메인 모니터링 스크립트)
   - `.github/workflows/monitor.yml` (워크플로우 파일)
   - `requirements.txt` (의존성 파일)

### 2. GitHub Secrets 설정

GitHub 리포지토리 Settings > Secrets and variables > Actions에서 다음을 설정합니다:

#### Repository Secrets:
- `DISCORD_WEBHOOK_URL`: 디스코드 웹훅 URL
  ```
  https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
  ```

#### Repository Variables (선택사항):
- `MIN_VOLUME_USD`: 최소 거래량 필터 (기본값: 5000000)
- `SYMBOLS_LIMIT`: 분석할 심볼 개수 (기본값: 200)

### 3. 디스코드 웹훅 생성

1. 디스코드에서 알림을 받을 채널로 이동
2. 채널 설정 > 연동 > 웹훅 > 새 웹훅 생성
3. 웹훅 URL을 복사하여 GitHub Secrets에 추가

### 4. 워크플로우 활성화

1. GitHub 리포지토리의 Actions 탭으로 이동
2. "Binance Top Trader Monitor" 워크플로우를 활성화
3. 수동 실행으로 테스트: "Run workflow" 버튼 클릭

## 파일 구조

```
your-repo/
├── binance_top_trader_monitor_github.py  # 메인 모니터링 스크립트
├── requirements.txt                       # Python 의존성
├── .github/
│   └── workflows/
│       └── monitor.yml                   # GitHub Actions 워크플로우
└── README.md                             # 이 파일
```

## 모니터링 결과 예시

디스코드에 다음과 같은 형태로 알림이 전송됩니다:

### 롱 계정 상위 5개
- BTC: 롱 68.5% | 숏 31.5% | 거래량: $2,450,000,000 | 변화 +2.3%
- ETH: 롱 65.2% | 숏 34.8% | 거래량: $1,230,000,000 | 변화 +1.8%

### 숏 계정 상위 5개  
- DOGE: 롱 35.4% | 숏 64.6% | 거래량: $890,000,000 | 변화 -3.2%
- ADA: 롱 38.1% | 숏 61.9% | 거래량: $450,000,000 | 변화 -1.9%

### 미결제약정 급증 상위 5개
- SOL: OI +12.5% | 가격 +4.1%
- AVAX: OI +8.7% | 가격 +2.8%

## 실행 주기

- **자동 실행**: 매 30분마다 (UTC 기준)
- **수동 실행**: GitHub Actions 페이지에서 언제든지 가능

## 문제 해결

### 1. 워크플로우가 실행되지 않는 경우
- Repository Settings > Actions > General에서 Actions 권한 확인
- Public 리포지토리는 무료, Private 리포지토리는 GitHub Actions 사용량 확인

### 2. 디스코드 알림이 오지 않는 경우
- `DISCORD_WEBHOOK_URL` Secret이 올바르게 설정되었는지 확인
- 웹훅 URL이 유효한지 확인 (직접 테스트 메시지 전송해보기)

### 3. API 오류가 발생하는 경우
- 바이낸스 API 상태 확인: https://www.binance.com/en/support/announcement
- 네트워크 연결 문제일 수 있음 (GitHub Actions 서버 위치)

### 4. 로그 확인
- Actions 탭 > 해당 워크플로우 실행 > 로그 확인
- 실패 시 error-logs 아티팩트 다운로드 가능

## 커스터마이징

### 모니터링 주기 변경
`.github/workflows/monitor.yml` 파일의 cron 설정을 수정합니다:
```yaml
schedule:
  - cron: '*/15 * * * *'  # 15분마다
  - cron: '0 * * * *'     # 매시 정각
  - cron: '0 */2 * * *'   # 2시간마다
```

### 필터 조건 변경
Repository Variables에서 다음 값들을 조정합니다:
- `MIN_VOLUME_USD`: 최소 거래량 필터
- `SYMBOLS_LIMIT`: 분석할 심볼 개수

### 알림 형식 변경
`binance_top_trader_monitor_github.py` 파일의 `DiscordNotifier` 클래스를 수정합니다.

## 주의사항

1. **GitHub Actions 사용량**: Public 리포지토리는 무료, Private는 월 사용량 제한 있음
2. **API 제한**: 바이낸스 API Rate Limit 준수 (코드에 적절한 지연 시간 포함됨)
3. **웹훅 보안**: 디스코드 웹훅 URL을 공개하지 마세요
4. **투자 참고용**: 이 도구는 정보 제공 목적이며, 투자 결정은 신중히 하세요

## 라이선스

MIT License - 자유롭게 사용하고 수정 가능합니다.
