"""
바이낸스 선물시장 탑트레이더 실시간 스캐너 + 디스코드 알림
- 다중 API 엔드포인트 지원
- GitHub Actions 다중 지역 대응
- 향상된 장애 복구
"""

import requests
import pandas as pd
import time
import os
import json
from typing import List, Dict, Optional
from datetime import datetime, timezone

class DiscordNotifier:
    """디스코드 알림 클래스"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.session = requests.Session()
    
    def send_scan_results(self, results: Dict, scan_info: str, total_symbols: int):
        """스캔 결과를 디스코드로 전송 (롱/숏 분리)"""
        try:
            if results['top_long'].empty and results['top_short'].empty:
                return False
            
            success_count = 0
            
            # 롱 계정 메시지
            if not results['top_long'].empty:
                long_embed = {
                    "title": "🚀 탑트레이더 롱 계정 TOP 5",
                    "description": f"**{scan_info}**\n총 {total_symbols}개 심볼 분석",
                    "color": 0x00ff00,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "footer": {"text": "바이낸스 선물 모니터"}
                }
                
                long_text = ""
                for i, (_, row) in enumerate(results['top_long'].iterrows(), 1):
                    symbol = row['symbol'].replace('USDT', '')
                    long_pct = row['longAccount']
                    short_pct = row['shortAccount']
                    volume = row['volume_24h']
                    change = row['change_24h']
                    
                    trend = "📈" if change > 0 else "📉"
                    
                    long_text += f"**{i}. {symbol}**\n"
                    long_text += f"롱 {long_pct:.1f}% | 숏 {short_pct:.1f}%\n"
                    long_text += f"거래량: ${volume:,.0f}\n"
                    long_text += f"{trend} {change:+.1f}%\n\n"
                
                long_embed["description"] += f"\n\n{long_text.strip()}"
                
                payload = {"embeds": [long_embed]}
                response = self.session.post(self.webhook_url, json=payload, timeout=10)
                if response.status_code == 204:
                    success_count += 1
            
            # 숏 계정 메시지
            if not results['top_short'].empty:
                short_embed = {
                    "title": "📉 탑트레이더 숏 계정 TOP 5",
                    "description": f"**{scan_info}**\n총 {total_symbols}개 심볼 분석",
                    "color": 0xff4444,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "footer": {"text": "바이낸스 선물 모니터"}
                }
                
                short_text = ""
                for i, (_, row) in enumerate(results['top_short'].iterrows(), 1):
                    symbol = row['symbol'].replace('USDT', '')
                    long_pct = row['longAccount']
                    short_pct = row['shortAccount']
                    volume = row['volume_24h']
                    change = row['change_24h']
                    
                    trend = "📈" if change > 0 else "📉"
                    
                    short_text += f"**{i}. {symbol}**\n"
                    short_text += f"롱 {long_pct:.1f}% | 숏 {short_pct:.1f}%\n"
                    short_text += f"거래량: ${volume:,.0f}\n"
                    short_text += f"{trend} {change:+.1f}%\n\n"
                
                short_embed["description"] += f"\n\n{short_text.strip()}"
                
                payload = {"embeds": [short_embed]}
                response = self.session.post(self.webhook_url, json=payload, timeout=10)
                if response.status_code == 204:
                    success_count += 1
            
            return success_count > 0
                
        except Exception as e:
            print(f"❌ 디스코드 알림 오류: {e}")
            return False
    
    def send_error_notification(self, error_message: str):
        """오류 알림 전송"""
        try:
            embed = {
                "title": "⚠️ 스캔 오류 발생",
                "description": error_message,
                "color": 0xff0000,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {"text": "바이낸스 선물 탑트레이더 모니터"}
            }
            
            payload = {"embeds": [embed]}
            response = self.session.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 204
        except Exception:
            return False
    
    def send_success_notification(self, message: str):
        """성공 알림 전송"""
        try:
            embed = {
                "title": "✅ 스캔 성공",
                "description": message,
                "color": 0x00ff00,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {"text": "바이낸스 선물 탑트레이더 모니터"}
            }
            
            payload = {"embeds": [embed]}
            response = self.session.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 204
        except Exception:
            return False

class BinanceTopTraderScanner:
    """바이낸스 탑트레이더 스캐너 - 다중 엔드포인트 지원"""
    
    def __init__(self, discord_webhook: str = None):
        # 환경변수에서 API 베이스 URL 가져오기
        self.base_url = os.getenv('BINANCE_API_BASE', 'https://fapi.binance.com')
        self.runner_os = os.getenv('RUNNER_OS', 'unknown')
        
        print(f"🌐 API 엔드포인트: {self.base_url}")
        print(f"🖥️ 실행 환경: {self.runner_os}")
        
        # 세션 설정
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': f'BinanceScanner/1.0 ({self.runner_os})',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        # 디스코드 알림 설정
        self.discord = None
        if discord_webhook:
            self.discord = DiscordNotifier(discord_webhook)
            print("✅ 디스코드 알림이 활성화되었습니다.")
    
    def test_connection(self) -> bool:
        """API 연결 테스트"""
        try:
            print(f"🔍 연결 테스트: {self.base_url}")
            url = f"{self.base_url}/fapi/v1/ping"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                print("✅ API 연결 성공")
                return True
            else:
                print(f"❌ API 연결 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ API 연결 오류: {e}")
            return False
    
    def make_request(self, endpoint: str, params: Dict = None, max_retries: int = 3) -> Optional[Dict]:
        """공통 HTTP 요청 함수"""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(max_retries):
            try:
                print(f"🌐 요청: {endpoint} (시도 {attempt+1}/{max_retries})")
                
                response = self.session.get(url, params=params, timeout=20)
                print(f"📡 응답: {response.status_code}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    print("⏰ 요청 제한 - 10초 대기")
                    time.sleep(10)
                elif response.status_code == 403:
                    print("🚫 접근 거부")
                    break  # 403은 재시도해도 소용없음
                else:
                    print(f"❌ HTTP 오류: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ 요청 오류 (시도 {attempt+1}): {e}")
                
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                print(f"⏰ {wait_time}초 후 재시도...")
                time.sleep(wait_time)
        
        return None
    
    def get_active_futures_symbols(self) -> List[str]:
        """활성 선물 심볼 조회"""
        print("📋 바이낸스 선물시장 활성 심볼 조회 중...")
        
        data = self.make_request("/fapi/v1/exchangeInfo")
        
        if not data:
            return []
        
        active_symbols = [
            s["symbol"] for s in data["symbols"]
            if (s["status"] == "TRADING"
                and s["symbol"].endswith("USDT")
                and s["contractType"] == "PERPETUAL")
        ]
        
        print(f"✅ 활성 영구선물 심볼 {len(active_symbols)}개 조회 완료")
        return active_symbols
    
    def get_top_volume_symbols(self, limit: int = 200) -> List[Dict]:
        """거래량 상위 심볼 조회"""
        active_symbols = self.get_active_futures_symbols()
        if not active_symbols:
            return []
        
        print(f"📊 거래량 상위 {limit}개 심볼 조회 중...")
        
        data = self.make_request("/fapi/v1/ticker/24hr")
        
        if not data:
            return []
        
        active_set = set(active_symbols)
        valid_pairs = [
            item for item in data
            if (item['symbol'] in active_set and float(item['quoteVolume']) > 5_000_000)
        ]
        
        sorted_pairs = sorted(valid_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)[:limit]
        
        print(f"✅ 유효한 선물 심볼 {len(sorted_pairs)}개 조회 완료")
        return sorted_pairs
    
    def get_trader_data(self, symbol: str) -> Optional[Dict]:
        """탑트레이더 데이터 조회"""
        # 계정 비율 조회
        params = {'symbol': symbol, 'period': '5m', 'limit': 1}
        data = self.make_request("/futures/data/topLongShortAccountRatio", params, max_retries=2)
        
        if data and len(data) > 0:
            ratio_data = data[0]
            account_ratio = float(ratio_data['longShortRatio'])
            
            total = account_ratio + 1.0
            long_percent = (account_ratio / total) * 100
            short_percent = (1.0 / total) * 100
            
            return {
                'symbol': symbol,
                'longAccount': long_percent,
                'shortAccount': short_percent,
                'positionRatio': account_ratio,
                'timestamp': ratio_data['timestamp']
            }
        
        return None
    
    def scan_top_traders(self, symbols_data: List[Dict], show_progress: bool = True) -> pd.DataFrame:
        """탑트레이더 스캔 실행"""
        if show_progress:
            print("\n🔍 탑트레이더 스캔 시작...")
        
        results = []
        total_symbols = len(symbols_data)
        
        for i, symbol_info in enumerate(symbols_data, 1):
            symbol = symbol_info['symbol']
            
            if show_progress and (i % 50 == 0 or i == total_symbols):
                print(f"스캔 진행: {i}/{total_symbols} ({i/total_symbols*100:.1f}%)")
            
            time.sleep(0.3)  # API 제한
            
            trader_data = self.get_trader_data(symbol)
            
            if trader_data:
                result = {
                    'symbol': symbol,
                    'volume_24h': float(symbol_info['quoteVolume']),
                    'price': float(symbol_info['lastPrice']),
                    'change_24h': float(symbol_info['priceChangePercent']),
                    'longAccount': trader_data['longAccount'],
                    'shortAccount': trader_data['shortAccount'],
                    'positionRatio': trader_data['positionRatio']
                }
                results.append(result)
        
        df = pd.DataFrame(results)
        if show_progress:
            print(f"✅ 스캔 완료: {len(df)}개 심볼 분석")
        
        return df
    
    def get_top_rankings(self, df: pd.DataFrame, top_n: int = 5) -> Dict:
        """계정 분포 기준 상위/하위 추출"""
        if df.empty:
            return {'top_long': pd.DataFrame(), 'top_short': pd.DataFrame()}
        
        df_sorted = df.sort_values('longAccount', ascending=False)
        
        top_long = df_sorted.head(top_n)
        top_short = df_sorted.tail(top_n).sort_values('longAccount', ascending=True)
        
        return {'top_long': top_long, 'top_short': top_short}
    
    def display_scan_results(self, results: Dict, scan_info: str = "", total_symbols: int = 0):
        """스캔 결과 출력"""
        if results['top_long'].empty:
            print("\n❌ 스캔 결과가 없습니다.")
            return
        
        print(f"\n{'='*80}")
        print(f"🚀 탑트레이더 롱계정 상위 5개 {scan_info}")
        print(f"{'='*80}")
        
        for i, (_, row) in enumerate(results['top_long'].iterrows(), 1):
            print(f"{i}. {row['symbol']}")
            print(f"   👥 롱 {row['longAccount']:.1f}% | 숏 {row['shortAccount']:.1f}%")
            print(f"   💰 거래량: ${row['volume_24h']:,.0f}")
            print(f"   💵 가격: ${row['price']:.4f} ({row['change_24h']:+.1f}%)")
            print("-" * 50)
        
        print(f"\n📉 탑트레이더 숏계정 상위 5개")
        print("=" * 80)
        
        for i, (_, row) in enumerate(results['top_short'].iterrows(), 1):
            print(f"{i}. {row['symbol']}")
            print(f"   👥 롱 {row['longAccount']:.1f}% | 숏 {row['shortAccount']:.1f}%")
            print(f"   💰 거래량: ${row['volume_24h']:,.0f}")
            print(f"   💵 가격: ${row['price']:.4f} ({row['change_24h']:+.1f}%)")
            print("-" * 50)
        
        # 디스코드 알림 전송
        if self.discord:
            discord_sent = self.discord.send_scan_results(results, scan_info, total_symbols)
            if discord_sent:
                print("\n📱 디스코드 알림 전송 완료!")
            else:
                print("\n❌ 디스코드 알림 전송 실패")
    
    def single_scan_mode(self):
        """1회 스캔 모드"""
        print("🎯 GitHub Actions 다중 엔드포인트 스캔")
        print("=" * 60)
        
        # 연결 테스트
        if not self.test_connection():
            error_msg = f"API 연결 실패: {self.base_url} ({self.runner_os})"
            print(f"❌ {error_msg}")
            if self.discord:
                self.discord.send_error_notification(error_msg)
            return
        
        # 심볼 조회
        top_symbols = self.get_top_volume_symbols(200)
        if not top_symbols:
            error_msg = f"심볼 조회 실패: {self.base_url} ({self.runner_os})"
            print(f"❌ {error_msg}")
            if self.discord:
                self.discord.send_error_notification(error_msg)
            return
        
        # 스캔 실행
        df_results = self.scan_top_traders(top_symbols, show_progress=True)
        if df_results.empty:
            error_msg = f"스캔 실패: {self.base_url} ({self.runner_os})"
            print(f"❌ {error_msg}")
            if self.discord:
                self.discord.send_error_notification(error_msg)
            return
        
        # 결과 출력
        rankings = self.get_top_rankings(df_results, 5)
        scan_time = datetime.now().strftime("(%Y-%m-%d %H:%M:%S)")
        scan_info = f"{scan_time} - {self.base_url} ({self.runner_os})"
        
        self.display_scan_results(rankings, scan_info, len(df_results))
        
        success_msg = f"스캔 성공: {len(df_results)}개 심볼 분석 - {self.base_url} ({self.runner_os})"
        print(f"\n✅ {success_msg}")
        
        if self.discord:
            self.discord.send_success_notification(success_msg)

def main():
    """메인 함수 - GitHub Actions용 다중 엔드포인트 스캔"""
    DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')
    
    if not DISCORD_WEBHOOK:
        print("❌ DISCORD_WEBHOOK 환경변수가 설정되지 않았습니다.")
        return
    
    scanner = BinanceTopTraderScanner(discord_webhook=DISCORD_WEBHOOK)
    
    try:
        scanner.single_scan_mode()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        if scanner.discord:
            scanner.discord.send_error_notification(f"심각한 오류: {str(e)}")

if __name__ == "__main__":
    main()
