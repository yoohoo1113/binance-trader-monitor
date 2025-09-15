"""
바이낸스 선물시장 탑트레이더 실시간 스캐너 + 디스코드 알림
- GitHub Actions 환경 최적화
- 대안 API 접근 방식
- 향상된 오류 처리
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
        """스캔 결과를 디스코드로 전송 (롱/숏/OI 분리)"""
        try:
            if (results['top_long'].empty and 
                results['top_short'].empty and 
                results['top_oi'].empty):
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
                    pos_ratio = row['positionRatio']
                    
                    trend = "📈" if change > 0 else "📉"
                    
                    long_text += f"**{i}. {symbol}**\n"
                    long_text += f"롱 {long_pct:.1f}% | 숏 {short_pct:.1f}%\n"
                    long_text += f"거래량: ${volume:,.0f}\n"
                    long_text += f"{trend} {change:+.1f}% | 포지션 비율: {pos_ratio:.2f}\n\n"
                
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
                    pos_ratio = row['positionRatio']
                    
                    trend = "📈" if change > 0 else "📉"
                    
                    short_text += f"**{i}. {symbol}**\n"
                    short_text += f"롱 {long_pct:.1f}% | 숏 {short_pct:.1f}%\n"
                    short_text += f"거래량: ${volume:,.0f}\n"
                    short_text += f"{trend} {change:+.1f}% | 포지션 비율: {pos_ratio:.2f}\n\n"
                
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

class BinanceTopTraderScanner:
    """바이낸스 탑트레이더 스캐너 - GitHub Actions 최적화"""
    
    def __init__(self, discord_webhook: str = None):
        self.base_url = "https://fapi.binance.com"
        
        # GitHub Actions 환경에 특화된 세션 설정
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'python-requests/2.31.0',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        # 디스코드 알림 설정
        self.discord = None
        if discord_webhook:
            self.discord = DiscordNotifier(discord_webhook)
            print("✅ 디스코드 알림이 활성화되었습니다.")
    
    def make_request(self, url: str, params: Dict = None, max_retries: int = 3) -> Optional[Dict]:
        """공통 HTTP 요청 함수 (향상된 오류 처리)"""
        for attempt in range(max_retries):
            try:
                print(f"🌐 요청: {url} (시도 {attempt+1}/{max_retries})")
                
                response = self.session.get(url, params=params, timeout=20)
                print(f"📡 응답: {response.status_code}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    print("⏰ 요청 제한 - 10초 대기")
                    time.sleep(10)
                elif response.status_code == 403:
                    print("🚫 접근 거부 - IP 차단 가능성")
                    time.sleep(5)
                else:
                    print(f"❌ HTTP 오류: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ 요청 오류 (시도 {attempt+1}): {e}")
                
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                print(f"⏰ {wait_time}초 후 재시도...")
                time.sleep(wait_time)
        
        return None
    
    def get_active_futures_symbols(self) -> List[str]:
        """활성 선물 심볼 조회"""
        print("📋 바이낸스 선물시장 활성 심볼 조회 중...")
        
        url = f"{self.base_url}/fapi/v1/exchangeInfo"
        data = self.make_request(url)
        
        if not data:
            print("❌ 활성 심볼 조회 실패")
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
        
        url = f"{self.base_url}/fapi/v1/ticker/24hr"
        data = self.make_request(url)
        
        if not data:
            print("❌ 거래량 데이터 조회 실패")
            if self.discord:
                self.discord.send_error_notification("거래량 데이터 조회 실패")
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
        """탑트레이더 데이터 조회 (계정 비율 중심)"""
        # 계정 비율 조회
        url = f"{self.base_url}/futures/data/topLongShortAccountRatio"
        params = {'symbol': symbol, 'period': '5m', 'limit': 1}
        data = self.make_request(url, params, max_retries=2)
        
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
        """탑트레이더 스캔 실행 (간소화)"""
        if show_progress:
            print("\n🔍 탑트레이더 스캔 시작...")
        
        results = []
        total_symbols = len(symbols_data)
        
        for i, symbol_info in enumerate(symbols_data, 1):
            symbol = symbol_info['symbol']
            
            if show_progress and (i % 50 == 0 or i == total_symbols):
                print(f"스캔 진행: {i}/{total_symbols} ({i/total_symbols*100:.1f}%)")
            
            time.sleep(0.3)  # API 제한 완화
            
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
            return {
                'top_long': pd.DataFrame(), 
                'top_short': pd.DataFrame(),
                'top_oi': pd.DataFrame()
            }
        
        df_sorted = df.sort_values('longAccount', ascending=False)
        
        top_long = df_sorted.head(top_n)
        top_short = df_sorted.tail(top_n).sort_values('longAccount', ascending=True)
        
        return {
            'top_long': top_long, 
            'top_short': top_short,
            'top_oi': pd.DataFrame()  # OI 데이터 제외 (단순화)
        }
    
    def display_scan_results(self, results: Dict, scan_info: str = "", total_symbols: int = 0):
        """스캔 결과 출력"""
        if results['top_long'].empty:
            print("\n❌ 스캔 결과가 없습니다.")
            return
        
        print(f"\n{'='*80}")
        print(f"🚀 탑트레이더 롱계정 상위 5개 {scan_info}")
        print(f"{'='*80}")
        
        for i, (_, row) in enumerate(results['top_long'].iterrows(), 1):
            long_pct = row['longAccount']
            short_pct = row['shortAccount']
            pos_ratio = row['positionRatio']
            
            print(f"{i}. {row['symbol']}")
            print(f"   👥 계정: 롱 {long_pct:.2f}% | 숏 {short_pct:.2f}%")
            print(f"   📈 포지션 비율: {pos_ratio:.4f}")
            print(f"   💰 거래량: ${row['volume_24h']:,.0f}")
            print(f"   💵 가격: ${row['price']:.4f} ({row['change_24h']:+.2f}%)")
            print("-" * 50)
        
        print(f"\n{'='*80}")
        print(f"📉 탑트레이더 숏계정 상위 5개 {scan_info}")
        print(f"{'='*80}")
        
        for i, (_, row) in enumerate(results['top_short'].iterrows(), 1):
            long_pct = row['longAccount']
            short_pct = row['shortAccount']
            pos_ratio = row['positionRatio']
            
            print(f"{i}. {row['symbol']}")
            print(f"   👥 계정: 롱 {long_pct:.2f}% | 숏 {short_pct:.2f}%")
            print(f"   📉 포지션 비율: {pos_ratio:.4f}")
            print(f"   💰 거래량: ${row['volume_24h']:,.0f}")
            print(f"   💵 가격: ${row['price']:.4f} ({row['change_24h']:+.2f}%)")
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
        print("🎯 GitHub Actions 스캔 모드")
        print("=" * 60)
        
        top_symbols = self.get_top_volume_symbols(200)
        if not top_symbols:
            print("❌ 심볼 조회 실패")
            if self.discord:
                self.discord.send_error_notification("심볼 조회 실패")
            return
        
        df_results = self.scan_top_traders(top_symbols, show_progress=True)
        if df_results.empty:
            print("❌ 스캔 실패")
            if self.discord:
                self.discord.send_error_notification("스캔 실패 - 데이터 없음")
            return
        
        rankings = self.get_top_rankings(df_results, 5)
        scan_time = datetime.now().strftime("(%Y-%m-%d %H:%M:%S)")
        
        self.display_scan_results(rankings, scan_time, len(df_results))
        print(f"\n✅ 스캔 완료! 총 {len(df_results)}개 심볼 분석")

def main():
    """메인 함수 - GitHub Actions용 1회 스캔"""
    DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')
    
    if not DISCORD_WEBHOOK:
        print("❌ DISCORD_WEBHOOK 환경변수가 설정되지 않았습니다.")
        return
    
    scanner = BinanceTopTraderScanner(discord_webhook=DISCORD_WEBHOOK)
    
    try:
        print("🎯 GitHub Actions - 바이낸스 탑트레이더 스캔")
        print("=" * 60)
        scanner.single_scan_mode()
        print("\n✅ GitHub Actions 스캔 완료!")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        if scanner.discord:
            scanner.discord.send_error_notification(f"GitHub Actions 스캔 오류: {str(e)}")

if __name__ == "__main__":
    main()
