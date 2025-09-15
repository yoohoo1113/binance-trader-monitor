#!/usr/bin/env python3
"""
GitHub Actions용 바이낸스 탑트레이더 30분 모니터링 시스템
=========================================================
기능: 탑트레이더 롱/숏 계정 분포 + OI 변화 자동 분석
- 30분마다 자동 실행 (GitHub Actions Cron)
- 디스코드 웹훅으로 결과 전송
- 환경변수 기반 설정
- 로그 및 오류 처리 최적화
"""

import requests
import pandas as pd
import os
import json
import time
from typing import List, Dict, Optional
from datetime import datetime, timezone

class DiscordNotifier:
    """디스코드 알림 클래스"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.session = requests.Session()
    
    def send_scan_results(self, results: Dict, scan_info: str, total_symbols: int):
        """스캔 결과를 디스코드로 전송"""
        try:
            if (results['top_long'].empty and 
                results['top_short'].empty and 
                results['top_oi'].empty):
                return False
            
            success_count = 0
            
            # 롱 계정 메시지
            if not results['top_long'].empty:
                long_embed = self._create_long_embed(results['top_long'], scan_info, total_symbols)
                if self._send_embed(long_embed):
                    success_count += 1
                    time.sleep(1)  # Rate limit 방지
            
            # 숏 계정 메시지
            if not results['top_short'].empty:
                short_embed = self._create_short_embed(results['top_short'], scan_info, total_symbols)
                if self._send_embed(short_embed):
                    success_count += 1
                    time.sleep(1)
            
            # 미결제약정 메시지
            if not results['top_oi'].empty:
                oi_embed = self._create_oi_embed(results['top_oi'], scan_info, total_symbols)
                if self._send_embed(oi_embed):
                    success_count += 1
            
            return success_count > 0
                
        except Exception as e:
            print(f"❌ 디스코드 알림 오류: {e}")
            return False
    
    def _create_long_embed(self, df: pd.DataFrame, scan_info: str, total_symbols: int) -> Dict:
        """롱 계정 Embed 생성"""
        embed = {
            "title": "🚀 탑트레이더 롱 계정 TOP 5",
            "description": f"**{scan_info}**\n총 {total_symbols}개 심볼 분석",
            "color": 0x00ff00,  # 초록색
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": "바이낸스 선물 모니터 (GitHub Actions)"}
        }
        
        long_text = ""
        for i, (_, row) in enumerate(df.iterrows(), 1):
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
        
        embed["description"] += f"\n\n{long_text.strip()}"
        return embed
    
    def _create_short_embed(self, df: pd.DataFrame, scan_info: str, total_symbols: int) -> Dict:
        """숏 계정 Embed 생성"""
        embed = {
            "title": "📉 탑트레이더 숏 계정 TOP 5",
            "description": f"**{scan_info}**\n총 {total_symbols}개 심볼 분석",
            "color": 0xff4444,  # 빨간색
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": "바이낸스 선물 모니터 (GitHub Actions)"}
        }
        
        short_text = ""
        for i, (_, row) in enumerate(df.iterrows(), 1):
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
        
        embed["description"] += f"\n\n{short_text.strip()}"
        return embed
    
    def _create_oi_embed(self, df: pd.DataFrame, scan_info: str, total_symbols: int) -> Dict:
        """미결제약정 Embed 생성"""
        embed = {
            "title": "🔥 미결제약정 급증 TOP 5",
            "description": f"**{scan_info}**\n총 {total_symbols}개 심볼 분석",
            "color": 0x9933ff,  # 보라색
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": "바이낸스 선물 모니터 (GitHub Actions)"}
        }
        
        oi_text = ""
        for i, (_, row) in enumerate(df.iterrows(), 1):
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
        
        embed["description"] += f"\n\n{oi_text.strip()}"
        return embed
    
    def _send_embed(self, embed: Dict) -> bool:
        """Embed 전송"""
        try:
            payload = {"embeds": [embed]}
            response = self.session.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            return response.status_code == 204
        except Exception as e:
            print(f"❌ Embed 전송 실패: {e}")
            return False
    
    def send_error_notification(self, error_message: str):
        """오류 알림 전송"""
        try:
            embed = {
                "title": "⚠️ 모니터링 오류 발생",
                "description": f"```\n{error_message}\n```",
                "color": 0xff0000,  # 빨간색
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {"text": "바이낸스 탑트레이더 모니터 (GitHub Actions)"}
            }
            
            return self._send_embed(embed)
            
        except Exception:
            return False
    
    def send_start_notification(self):
        """시작 알림 전송"""
        try:
            embed = {
                "title": "🎯 탑트레이더 모니터링 시작",
                "description": "GitHub Actions에서 30분 간격 모니터링이 시작되었습니다.",
                "color": 0x0099ff,  # 파란색
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {"text": "바이낸스 탑트레이더 모니터 (GitHub Actions)"}
            }
            
            return self._send_embed(embed)
            
        except Exception:
            return False

class BinanceTopTraderMonitor:
    """GitHub Actions용 바이낸스 탑트레이더 모니터"""
    
    def __init__(self):
        self.base_url = "https://fapi.binance.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BinanceTopTraderMonitor/1.0 (GitHub Actions)',
            'Accept': 'application/json'
        })
        
        # 디스코드 웹훅 설정
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        self.discord = None
        
        if self.discord_webhook:
            self.discord = DiscordNotifier(self.discord_webhook)
            print("✅ 디스코드 알림이 활성화되었습니다.")
        else:
            print("⚠️ DISCORD_WEBHOOK_URL 환경변수가 설정되지 않았습니다.")
    
    def get_active_futures_symbols(self) -> List[str]:
        """활성 선물 심볼 조회"""
        try:
            print("📋 바이낸스 선물시장 활성 심볼 조회 중...")
            
            url = f"{self.base_url}/fapi/v1/exchangeInfo"
            response = self.session.get(url, timeout=15)
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
            error_msg = f"활성 심볼 조회 실패: {e}"
            print(f"❌ {error_msg}")
            if self.discord:
                self.discord.send_error_notification(error_msg)
            return []
    
    def get_top_volume_symbols(self, limit: int = 200) -> List[Dict]:
        """거래량 상위 심볼 조회"""
        try:
            active_symbols = self.get_active_futures_symbols()
            if not active_symbols:
                return []
            
            print(f"📊 거래량 상위 {limit}개 심볼 조회 중...")
            
            url = f"{self.base_url}/fapi/v1/ticker/24hr"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            active_set = set(active_symbols)
            valid_pairs = []
            
            # 최소 거래량 필터 (5백만 달러)
            min_volume = float(os.getenv('MIN_VOLUME_USD', '5000000'))
            
            for item in data:
                if (item['symbol'] in active_set and 
                    float(item['quoteVolume']) > min_volume):
                    valid_pairs.append(item)
            
            sorted_pairs = sorted(
                valid_pairs, 
                key=lambda x: float(x['quoteVolume']), 
                reverse=True
            )[:limit]
            
            print(f"✅ 유효한 선물 심볼 {len(sorted_pairs)}개 조회 완료")
            return sorted_pairs
            
        except Exception as e:
            error_msg = f"거래량 데이터 조회 실패: {e}"
            print(f"❌ {error_msg}")
            if self.discord:
                self.discord.send_error_notification(error_msg)
            return []
    
    def get_trader_data(self, symbol: str) -> Optional[Dict]:
        """탑트레이더 데이터 조회"""
        try:
            # 계정 비율 조회 (차트 데이터)
            url = f"{self.base_url}/futures/data/topLongShortAccountRatio"
            params = {'symbol': symbol, 'period': '5m', 'limit': 1}
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            if not data or len(data) == 0:
                return None
            
            ratio_data = data[0]
            account_ratio = float(ratio_data['longShortRatio'])
            
            # 롱/숏 퍼센트 계산
            total = account_ratio + 1.0
            long_percent = (account_ratio / total) * 100
            short_percent = (1.0 / total) * 100
            
            # 포지션 비율 조회
            pos_url = f"{self.base_url}/futures/data/topLongShortPositionRatio"
            pos_response = self.session.get(pos_url, params=params, timeout=10)
            
            position_ratio = account_ratio  # 기본값
            if pos_response.status_code == 200:
                pos_data = pos_response.json()
                if pos_data and len(pos_data) > 0:
                    position_ratio = float(pos_data[0]['longShortRatio'])
            
            return {
                'symbol': symbol,
                'longAccount': long_percent,
                'shortAccount': short_percent,
                'positionRatio': position_ratio,
                'timestamp': ratio_data['timestamp']
            }
            
        except Exception as e:
            print(f"⚠️ {symbol} 트레이더 데이터 조회 실패: {e}")
            return None
    
    def get_open_interest_data(self, symbol: str) -> Optional[Dict]:
        """미결제약정 데이터 조회"""
        try:
            # 현재 미결제약정
            url = f"{self.base_url}/fapi/v1/openInterest"
            params = {'symbol': symbol}
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                return None
            
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
            
            oi_change_24h = 0
            if hist_response.status_code == 200:
                hist_data = hist_response.json()
                if len(hist_data) >= 2:
                    yesterday_amount = float(hist_data[-2]['sumOpenInterest'])
                    if yesterday_amount > 0:
                        oi_change_24h = ((current_amount - yesterday_amount) / yesterday_amount) * 100
            
            return {
                'symbol': symbol,
                'openInterest': current_amount,
                'oi_change_24h': oi_change_24h,
                'timestamp': current_oi['time']
            }
            
        except Exception as e:
            print(f"⚠️ {symbol} OI 데이터 조회 실패: {e}")
            return None
    
    def scan_top_traders(self, symbols_data: List[Dict]) -> pd.DataFrame:
        """탑트레이더 스캔 실행"""
        print(f"\n🔍 {len(symbols_data)}개 심볼 탑트레이더 스캔 시작...")
        
        results = []
        total_symbols = len(symbols_data)
        
        for i, symbol_info in enumerate(symbols_data, 1):
            symbol = symbol_info['symbol']
            
            # 진행상황 출력 (50개마다)
            if i % 50 == 0 or i == total_symbols:
                print(f"스캔 진행: {i}/{total_symbols} ({i/total_symbols*100:.1f}%)")
            
            # API 제한을 위한 대기
            time.sleep(0.1)
            
            trader_data = self.get_trader_data(symbol)
            if not trader_data:
                continue
            
            oi_data = self.get_open_interest_data(symbol)
            
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
        
        # 롱 계정 비율 기준 정렬
        df_sorted = df.sort_values('longAccount', ascending=False)
        
        top_long = df_sorted.head(top_n)
        top_short = df_sorted.tail(top_n).sort_values('longAccount', ascending=True)
        
        # 미결제약정 변화율 기준 상위
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
    
    def run_monitoring_cycle(self):
        """모니터링 사이클 실행"""
        try:
            print("🎯 바이낸스 탑트레이더 30분 모니터링 시작")
            print("=" * 70)
            
            # 시작 알림
            if self.discord:
                self.discord.send_start_notification()
            
            # 1. 거래량 상위 심볼 조회
            symbols_limit = int(os.getenv('SYMBOLS_LIMIT', '200'))
            top_symbols = self.get_top_volume_symbols(symbols_limit)
            
            if not top_symbols:
                error_msg = "심볼 조회 실패"
                print(f"❌ {error_msg}")
                if self.discord:
                    self.discord.send_error_notification(error_msg)
                return False
            
            # 2. 탑트레이더 스캔 실행
            df_results = self.scan_top_traders(top_symbols)
            
            if df_results.empty:
                error_msg = "탑트레이더 스캔 실패 - 데이터 없음"
                print(f"❌ {error_msg}")
                if self.discord:
                    self.discord.send_error_notification(error_msg)
                return False
            
            # 3. 상위 랭킹 추출
            rankings = self.get_top_rankings(df_results, 5)
            
            # 4. 결과 출력
            scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S KST")
            scan_info = f"GitHub Actions 자동 스캔 ({scan_time})"
            
            self.display_results(rankings, scan_info, len(df_results))
            
            # 5. 디스코드 알림 전송
            if self.discord:
                discord_sent = self.discord.send_scan_results(rankings, scan_info, len(df_results))
                if discord_sent:
                    print("\n📱 디스코드 알림 전송 완료!")
                else:
                    print("\n❌ 디스코드 알림 전송 실패")
            
            print(f"\n✅ 모니터링 사이클 완료! (총 {len(df_results)}개 심볼 분석)")
            return True
            
        except Exception as e:
            error_msg = f"모니터링 사이클 오류: {str(e)}"
            print(f"❌ {error_msg}")
            if self.discord:
                self.discord.send_error_notification(error_msg)
            return False
    
    def display_results(self, results: Dict, scan_info: str, total_symbols: int):
        """결과 출력 (간단 버전)"""
        print(f"\n{'='*70}")
        print(f"🚀 탑트레이더 분석 결과 - {scan_info}")
        print(f"총 {total_symbols}개 심볼 분석")
        print(f"{'='*70}")
        
        # 롱 계정 상위 5개
        if not results['top_long'].empty:
            print("\n🟢 롱 계정 상위 5개:")
            for i, (_, row) in enumerate(results['top_long'].iterrows(), 1):
                symbol = row['symbol'].replace('USDT', '')
                print(f"{i}. {symbol}: 롱 {row['longAccount']:.1f}% | 숏 {row['shortAccount']:.1f}% | 변화 {row['change_24h']:+.1f}%")
        
        # 숏 계정 상위 5개
        if not results['top_short'].empty:
            print("\n🔴 숏 계정 상위 5개:")
            for i, (_, row) in enumerate(results['top_short'].iterrows(), 1):
                symbol = row['symbol'].replace('USDT', '')
                print(f"{i}. {symbol}: 롱 {row['longAccount']:.1f}% | 숏 {row['shortAccount']:.1f}% | 변화 {row['change_24h']:+.1f}%")
        
        # OI 급증 상위 5개
        if not results['top_oi'].empty:
            print("\n🟣 미결제약정 급증 상위 5개:")
            for i, (_, row) in enumerate(results['top_oi'].iterrows(), 1):
                symbol = row['symbol'].replace('USDT', '')
                print(f"{i}. {symbol}: OI {row['oi_change_24h']:+.1f}% | 가격 {row['change_24h']:+.1f}%")

def main():
    """메인 함수 - GitHub Actions 실행용"""
    try:
        print("🎯 바이낸스 탑트레이더 모니터링 시작")
        print(f"현재 시간: {datetime.now()}")
        
        # 환경변수 확인
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        min_volume = os.getenv('MIN_VOLUME_USD', '5000000')
        symbols_limit = os.getenv('SYMBOLS_LIMIT', '200')
        
        print(f"환경변수 확인:")
        print(f"- DISCORD_WEBHOOK_URL: {'설정됨' if webhook_url else '설정되지 않음'}")
        print(f"- MIN_VOLUME_USD: {min_volume}")
        print(f"- SYMBOLS_LIMIT: {symbols_limit}")
        
        if not webhook_url:
            print("❌ DISCORD_WEBHOOK_URL이 설정되지 않았습니다.")
            print("GitHub Secrets에서 DISCORD_WEBHOOK_URL을 설정해주세요.")
            exit(1)
        
        monitor = BinanceTopTraderMonitor()
        success = monitor.run_monitoring_cycle()
        
        if success:
            print("\n🎉 모니터링이 성공적으로 완료되었습니다!")
            exit(0)
        else:
            print("\n❌ 모니터링이 실패했습니다!")
            exit(1)
            
    except ImportError as e:
        print(f"\n💥 모듈 import 오류: {e}")
        print("requirements.txt의 패키지가 올바르게 설치되었는지 확인하세요.")
        exit(1)
    except Exception as e:
        print(f"\n💥 예상치 못한 오류: {e}")
        import traceback
        print("전체 오류 스택:")
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()
