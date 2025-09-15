"""
바이낸스 선물시장 탑트레이더 실시간 스캐너 + 디스코드 알림
- 계정 분포 기준 정렬 (차트 데이터와 일치)
- 1회 스캔 / 주기적 스캔 메뉴
- 실시간 모니터링 기능
- 디스코드 Embed 스타일 알림
- 미결제약정(OI) 독립 알림 추가
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
                    "color": 0x00ff00,  # 초록색
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "footer": {
                        "text": "바이낸스 선물 모니터"
                    }
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
                
                # 롱 메시지 전송
                payload = {"embeds": [long_embed]}
                response = self.session.post(
                    self.webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                if response.status_code == 204:
                    success_count += 1
            
            # 숏 계정 메시지
            if not results['top_short'].empty:
                short_embed = {
                    "title": "📉 탑트레이더 숏 계정 TOP 5",
                    "description": f"**{scan_info}**\n총 {total_symbols}개 심볼 분석",
                    "color": 0xff4444,  # 빨간색
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "footer": {
                        "text": "바이낸스 선물 모니터"
                    }
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
                
                # 숏 메시지 전송
                payload = {"embeds": [short_embed]}
                response = self.session.post(
                    self.webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                if response.status_code == 204:
                    success_count += 1
            
            # 미결제약정 메시지
            if not results['top_oi'].empty:
                oi_embed = {
                    "title": "🔥 미결제약정 급증 TOP 5",
                    "description": f"**{scan_info}**\n총 {total_symbols}개 심볼 분석",
                    "color": 0x9933ff,  # 보라색
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "footer": {
                        "text": "바이낸스 선물 모니터"
                    }
                }
                
                oi_text = ""
                for i, (_, row) in enumerate(results['top_oi'].iterrows(), 1):
                    symbol = row['symbol'].replace('USDT', '')
                    oi_amount = row['openInterest']
                    oi_change = row['oi_change_24h']
                    price = row['price']
                    change = row['change_24h']
                    
                    trend = "📈" if change > 0 else "📉"
                    oi_trend = "🔥" if oi_change > 0 else "❄️"
                    
                    oi_text += f"**{i}. {symbol}**\n"
                    oi_text += f"OI: ${oi_amount:,.0f} {oi_trend} {oi_change:+.1f}%\n"
                    oi_text += f"가격: ${price:.4f} {trend} {change:+.1f}%\n\n"
                
                oi_embed["description"] += f"\n\n{oi_text.strip()}"
                
                # OI 메시지 전송
                payload = {"embeds": [oi_embed]}
                response = self.session.post(
                    self.webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
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
                "color": 0xff0000,  # 빨간색
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {
                    "text": "바이낸스 선물 탑트레이더 모니터"
                }
            }
            
            payload = {"embeds": [embed]}
            
            response = self.session.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            return response.status_code == 204
            
        except Exception:
            return False
    
    def send_start_notification(self, mode: str):
        """시작 알림 전송"""
        try:
            embed = {
                "title": "🎯 탑트레이더 스캔 시작",
                "description": f"**{mode}** 모니터링이 시작되었습니다.",
                "color": 0x0099ff,  # 파란색
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {
                    "text": "바이낸스 선물 탑트레이더 모니터"
                }
            }
            
            payload = {"embeds": [embed]}
            
            response = self.session.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            return response.status_code == 204
            
        except Exception:
            return False

class BinanceTopTraderScanner:
    """바이낸스 탑트레이더 스캐너"""
    
    def __init__(self, discord_webhook: str = None):
        self.base_url = "https://fapi.binance.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.running = False
        
        # 디스코드 알림 설정
        self.discord = None
        if discord_webhook:
            self.discord = DiscordNotifier(discord_webhook)
            print("✅ 디스코드 알림이 활성화되었습니다.")
    
    def clear_screen(self):
        """화면 클리어"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def get_active_futures_symbols(self) -> List[str]:
        """활성 선물 심볼 조회"""
        try:
            print("📋 바이낸스 선물시장 활성 심볼 조회 중...")
            
            url = f"{self.base_url}/fapi/v1/exchangeInfo"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            active_symbols = []
            for symbol_info in data['symbols']:
                if (symbol_info['status'] == 'TRADING' and 
                    symbol_info['symbol'].endswith('USDT') and
                    symbol_info['contractType'] == 'PERPETUAL'):
                    active_symbols.append(symbol_info['symbol'])
            
            print(f"✅ 활성 영구선물 심볼 {len(active_symbols)}개 조회 완료")
            return active_symbols
            
        except Exception as e:
            print(f"❌ 활성 심볼 조회 실패: {e}")
            return []
    
    def get_top_volume_symbols(self, limit: int = 200) -> List[Dict]:
        """거래량 상위 심볼 조회"""
        try:
            active_symbols = self.get_active_futures_symbols()
            if not active_symbols:
                return []
            
            print(f"📊 거래량 상위 {limit}개 심볼 조회 중...")
            
            url = f"{self.base_url}/fapi/v1/ticker/24hr"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            active_set = set(active_symbols)
            valid_pairs = []
            
            for item in data:
                if (item['symbol'] in active_set and 
                    float(item['quoteVolume']) > 5_000_000):
                    valid_pairs.append(item)
            
            sorted_pairs = sorted(
                valid_pairs, 
                key=lambda x: float(x['quoteVolume']), 
                reverse=True
            )[:limit]
            
            print(f"✅ 유효한 선물 심볼 {len(sorted_pairs)}개 조회 완료")
            return sorted_pairs
            
        except Exception as e:
            print(f"❌ 거래량 데이터 조회 실패: {e}")
            if self.discord:
                self.discord.send_error_notification(f"거래량 데이터 조회 실패: {str(e)}")
            return []
    
    def get_trader_data(self, symbol: str) -> Optional[Dict]:
        """탑트레이더 데이터 조회"""
        account_data = None
        position_data = None
        
        # 계정 비율 조회 (차트 데이터)
        try:
            url = f"{self.base_url}/futures/data/topLongShortAccountRatio"
            params = {'symbol': symbol, 'period': '5m', 'limit': 1}
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    ratio_data = data[0]
                    account_ratio = float(ratio_data['longShortRatio'])
                    
                    total = account_ratio + 1.0
                    long_percent = (account_ratio / total) * 100
                    short_percent = (1.0 / total) * 100
                    
                    account_data = {
                        'longAccount': long_percent,
                        'shortAccount': short_percent,
                        'accountRatio': account_ratio,
                        'timestamp': ratio_data['timestamp']
                    }
        except Exception:
            pass
        
        # 포지션 비율 조회
        try:
            url = f"{self.base_url}/futures/data/topLongShortPositionRatio"
            params = {'symbol': symbol, 'period': '5m', 'limit': 1}
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    ratio_data = data[0]
                    position_ratio = float(ratio_data['longShortRatio'])
                    
                    position_data = {
                        'positionRatio': position_ratio,
                        'timestamp': ratio_data['timestamp']
                    }
        except Exception:
            pass
        
        # 데이터 병합
        if account_data and position_data:
            return {
                'symbol': symbol,
                'longAccount': account_data['longAccount'],
                'shortAccount': account_data['shortAccount'],
                'positionRatio': position_data['positionRatio'],
                'timestamp': account_data['timestamp']
            }
        elif account_data:
            return {
                'symbol': symbol,
                'longAccount': account_data['longAccount'],
                'shortAccount': account_data['shortAccount'],
                'positionRatio': account_data['accountRatio'],
                'timestamp': account_data['timestamp']
            }
        elif position_data:
            # 기존 포지션 API 백업
            try:
                url = f"{self.base_url}/futures/data/topLongShortPositionRatio"
                params = {'symbol': symbol, 'period': '5m', 'limit': 1}
                response = self.session.get(url, params=params, timeout=10)
                data = response.json()
                
                if data and len(data) > 0:
                    ratio_data = data[0]
                    long_acc = float(ratio_data.get('longAccount', 0))
                    short_acc = float(ratio_data.get('shortAccount', 0))
                    
                    if long_acc <= 1.0:
                        long_percent = long_acc * 100
                        short_percent = short_acc * 100
                    else:
                        long_percent = long_acc
                        short_percent = short_acc
                    
                    return {
                        'symbol': symbol,
                        'longAccount': long_percent,
                        'shortAccount': short_percent,
                        'positionRatio': position_data['positionRatio'],
                        'timestamp': position_data['timestamp']
                    }
            except Exception:
                pass
        
        return None
    
    def get_open_interest_data(self, symbol: str) -> Optional[Dict]:
        """미결제약정 데이터 조회"""
        try:
            # 현재 미결제약정
            url = f"{self.base_url}/fapi/v1/openInterest"
            params = {'symbol': symbol}
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                current_oi = response.json()
                current_amount = float(current_oi['openInterest'])
                
                # 24시간 전 미결제약정 (히스토리)
                hist_url = f"{self.base_url}/futures/data/openInterestHist"
                hist_params = {
                    'symbol': symbol,
                    'period': '1d',
                    'limit': 2
                }
                hist_response = self.session.get(hist_url, params=hist_params, timeout=10)
                
                if hist_response.status_code == 200:
                    hist_data = hist_response.json()
                    if len(hist_data) >= 2:
                        yesterday_amount = float(hist_data[-2]['sumOpenInterest'])
                        change_24h = ((current_amount - yesterday_amount) / yesterday_amount) * 100 if yesterday_amount > 0 else 0
                        
                        return {
                            'symbol': symbol,
                            'openInterest': current_amount,
                            'oi_change_24h': change_24h,
                            'timestamp': current_oi['time']
                        }
                
                # 히스토리 실패 시 현재 데이터만 반환
                return {
                    'symbol': symbol,
                    'openInterest': current_amount,
                    'oi_change_24h': 0,
                    'timestamp': current_oi['time']
                }
        except Exception:
            pass
        
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
            
            time.sleep(0.2)  # API 제한
            
            trader_data = self.get_trader_data(symbol)
            oi_data = self.get_open_interest_data(symbol)
            
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
                
                # OI 데이터 추가
                if oi_data:
                    result['openInterest'] = oi_data['openInterest']
                    result['oi_change_24h'] = oi_data['oi_change_24h']
                else:
                    result['openInterest'] = 0
                    result['oi_change_24h'] = 0
                
                results.append(result)
        
        df = pd.DataFrame(results)
        if show_progress:
            print(f"✅ 스캔 완료: {len(df)}개 심볼 분석")
        
        return df
    
    def get_top_rankings(self, df: pd.DataFrame, top_n: int = 5) -> Dict:
        """계정 분포 기준 상위/하위 추출 + OI 상위"""
        if df.empty:
            return {
                'top_long': pd.DataFrame(), 
                'top_short': pd.DataFrame(),
                'top_oi': pd.DataFrame()
            }
        
        df_sorted = df.sort_values('longAccount', ascending=False)
        
        top_long = df_sorted.head(top_n)
        top_short = df_sorted.tail(top_n).sort_values('longAccount', ascending=True)
        
        # 미결제약정 변화율 기준 상위 (OI 데이터가 있는 것만)
        df_with_oi = df[df['openInterest'] > 0].copy()
        if not df_with_oi.empty:
            top_oi = df_with_oi.sort_values('oi_change_24h', ascending=False).head(top_n)
        else:
            top_oi = pd.DataFrame()
        
        return {
            'top_long': top_long, 
            'top_short': top_short,
            'top_oi': top_oi
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
            print(f"   📈 포지션 비율: {pos_ratio:.4f} (롱이 {pos_ratio:.2f}배 큼)")
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
            short_dominance = 1 / pos_ratio if pos_ratio > 0 else float('inf')
            
            print(f"{i}. {row['symbol']}")
            print(f"   👥 계정: 롱 {long_pct:.2f}% | 숏 {short_pct:.2f}%")
            print(f"   📉 포지션 비율: {pos_ratio:.4f} (숏이 {short_dominance:.2f}배 큼)")
            print(f"   💰 거래량: ${row['volume_24h']:,.0f}")
            print(f"   💵 가격: ${row['price']:.4f} ({row['change_24h']:+.2f}%)")
            print("-" * 50)
        
        # 미결제약정 결과 출력
        if not results['top_oi'].empty:
            print(f"\n{'='*80}")
            print(f"🔥 미결제약정 급증 상위 5개 {scan_info}")
            print(f"{'='*80}")
            
            for i, (_, row) in enumerate(results['top_oi'].iterrows(), 1):
                oi_amount = row['openInterest']
                oi_change = row['oi_change_24h']
                
                print(f"{i}. {row['symbol']}")
                print(f"   🔥 미결제약정: ${oi_amount:,.0f} ({oi_change:+.2f}%)")
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
    
    def periodic_scan_mode(self, interval_minutes: int):
        """주기적 스캔 모드"""
        self.running = True
        scan_count = 0
        
        mode_name = f"{interval_minutes}분 주기 스캔"
        
        print(f"🔄 {mode_name} 시작")
        print("📝 Ctrl+C로 중지 가능")
        print("=" * 60)
        
        # 시작 알림
        if self.discord:
            self.discord.send_start_notification(mode_name)
        
        while self.running:
            try:
                scan_count += 1
                scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                print(f"🔄 주기 스캔 #{scan_count} - 매 {interval_minutes}분 ({scan_time})")
                print("=" * 60)
                print("📝 Ctrl+C로 중지 가능\n")
                
                # 스캔 실행
                top_symbols = self.get_top_volume_symbols(200)
                if not top_symbols:
                    error_msg = "심볼 조회 실패, 재시도 대기 중..."
                    print(f"❌ {error_msg}")
                    if self.discord:
                        self.discord.send_error_notification(error_msg)
                    self._wait_with_interrupt(interval_minutes * 60)
                    continue
                
                df_results = self.scan_top_traders(top_symbols, show_progress=False)
                if df_results.empty:
                    error_msg = "스캔 실패, 재시도 대기 중..."
                    print(f"❌ {error_msg}")
                    if self.discord:
                        self.discord.send_error_notification(error_msg)
                    self._wait_with_interrupt(interval_minutes * 60)
                    continue
                
                rankings = self.get_top_rankings(df_results, 5)
                scan_info = f"#{scan_count} ({scan_time})"
                self.display_scan_results(rankings, scan_info, len(df_results))
                
                print(f"\n✅ 스캔 #{scan_count} 완료! ({len(df_results)}개 심볼)")
                print(f"⏰ {interval_minutes}분 후 다음 스캔...")
                
                # 대기 (중단 가능)
                self._wait_with_interrupt(interval_minutes * 60)
                
            except KeyboardInterrupt:
                self.running = False
                print("\n\n🛑 스캔이 중지되었습니다.")
                break
            except Exception as e:
                error_msg = f"스캔 오류: {str(e)}"
                print(f"\n❌ {error_msg}")
                if self.discord:
                    self.discord.send_error_notification(error_msg)
                print(f"⏰ {interval_minutes}분 후 재시도...")
                self._wait_with_interrupt(interval_minutes * 60)
    
    def _wait_with_interrupt(self, seconds: int):
        """중단 가능한 대기"""
        for _ in range(seconds):
            if not self.running:
                break
            time.sleep(1)

def main():
    """메인 함수 - GitHub Actions용 1회 스캔"""
    # 환경변수에서 디스코드 웹훅 URL 가져오기
    DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')
    
    if not DISCORD_WEBHOOK:
        print("❌ DISCORD_WEBHOOK 환경변수가 설정되지 않았습니다.")
        return
    
    scanner = BinanceTopTraderScanner(discord_webhook=DISCORD_WEBHOOK)
    
    try:
        print("🎯 GitHub Actions - 탑트레이더 1회 스캔 시작")
        print("=" * 60)
        scanner.single_scan_mode()
        print("\n✅ GitHub Actions 스캔 완료!")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        if scanner.discord:
            scanner.discord.send_error_notification(f"GitHub Actions 스캔 오류: {str(e)}")

if __name__ == "__main__":
    main()
