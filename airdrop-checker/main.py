import requests
import json
import random
from colorama import Fore, Style, init
from fake_useragent import UserAgent

init()

class Colors:
    INFO = Fore.LIGHTCYAN_EX
    SUCCESS = Fore.LIGHTGREEN_EX
    WARNING = Fore.LIGHTYELLOW_EX
    ERROR = Fore.LIGHTRED_EX
    RESET = Style.RESET_ALL
    TOKEN = Fore.LIGHTMAGENTA_EX

class AirdropChecker:
    def __init__(self):
        self.base_url = "https://api.nodepay.ai/api"
        self.proxies = self.load_proxies()
        self.tokens = self.load_tokens()
        self.ua = UserAgent()
        self.success_count = 0
        self.failed_count = 0
        self.eligible_count = 0
        self.token_count = 0
        
    def load_proxies(self):
        try:
            with open('proxies.txt', 'r') as f:
                proxies = [line.strip() for line in f if line.strip()]
                if not proxies:
                    print(f"{Colors.WARNING}No proxies loaded - will continue without proxy{Colors.RESET}\n")
                return proxies
        except FileNotFoundError:
            print(f"{Colors.WARNING}proxies.txt not found - will continue without proxy{Colors.RESET}\n")
            return []

    def load_tokens(self):
        try:
            with open('tokens.txt', 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"{Colors.ERROR}[ERROR] tokens.txt not found{Colors.RESET}")
            return []

    def format_proxy(self, proxy_line):
        try:
            if "://" in proxy_line:
                protocol = proxy_line.split("://")[0].lower()
                if protocol in ['http', 'https', 'socks4', 'socks5']:
                    return proxy_line
                return None
            
            parts = proxy_line.strip().split(':')
            if len(parts) == 3:
                protocol, host, port = parts
                if protocol.lower() in ['http', 'https', 'socks4', 'socks5']:
                    return f"{protocol}://{host}:{port}"
            elif len(parts) == 5:
                protocol, host, port, user, password = parts
                if protocol.lower() in ['http', 'https', 'socks4', 'socks5']:
                    return f"{protocol}://{user}:{password}@{host}:{port}"
            return None
        except Exception:
            return None

    def get_random_proxy(self):
        if not self.proxies:
            return None
        proxy_line = random.choice(self.proxies)
        formatted_proxy = self.format_proxy(proxy_line)
        if formatted_proxy:
            protocol = formatted_proxy.split("://")[0].lower()
            if protocol in ['socks4', 'socks5']:
                return {
                    "http": formatted_proxy,
                    "https": formatted_proxy
                }
            else:
                return {
                    "http": formatted_proxy,
                    "https": formatted_proxy
                }
        return None

    def get_headers(self, token):
        return {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': f'Bearer {token}',
            'content-type': 'application/json',
            'origin': 'https://app.nodepay.ai',
            'referer': 'https://app.nodepay.ai/',
            'user-agent': self.ua.random
        }

    def mask_token(self, token):
        self.token_count += 1
        if len(token) <= 10:
            return token
        return f"Token{self.token_count}: {token[:5]}...{token[-5:]}"

    def get_season_tokens(self, eligibility_info, for_display=True):
        season_tokens = []
        season_keys = sorted([k for k in eligibility_info.keys() if k.startswith('season') and k.endswith('_tokens')])
        is_eligible = eligibility_info.get('is_eligible', False)
        
        for key in season_keys:
            season_num = key.split('season')[1].split('_')[0]
            value = eligibility_info[key]
            
            if not is_eligible or value is None:
                value = "0"
                
            if for_display:
                season_tokens.append(f"{Colors.INFO}Season {season_num}: {Colors.RESET}{Colors.TOKEN}{value}{Colors.RESET}")
            else:
                season_tokens.append(f"Season {season_num}: {value}")
            
        return " ".join(season_tokens)

    def save_eligible(self, data):
        with open('eligible.txt', 'a', encoding='utf-8') as f:
            seasons_data = self.get_season_tokens(data['eligibility_info'], for_display=False)
            line = f"{data['token']} | {data['email']} | {data['full_wallet']} | {seasons_data}\n"
            f.write(line)

    def make_request(self, method, url, headers, proxy=None, **kwargs):
        try:
            if proxy:
                response = requests.request(method, url, headers=headers, proxies=proxy, timeout=30, **kwargs)
            else:
                response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
            return response
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")

    def check_account(self, token, index, total):
        try:
            masked_token = self.mask_token(token)
            proxy = self.get_random_proxy()
            headers = self.get_headers(token)
            
            session_response = self.make_request(
                'POST',
                f"{self.base_url}/auth/session",
                headers=headers,
                proxy=proxy
            )
            session_data = session_response.json()

            if not session_data.get('success'):
                log_line = f"[{Colors.ERROR}Bearer Inactive:{Colors.RESET} {Colors.TOKEN}{masked_token}{Colors.RESET}]"
                print(log_line)
                self.failed_count += 1
                return

            user_info = session_data['data']
            email = user_info['email']

            airdrop_response = self.make_request(
                'GET',
                f"{self.base_url}/season/airdrop-status",
                headers=headers,
                proxy=proxy
            )
            airdrop_data = airdrop_response.json()

            if airdrop_data.get('success'):
                eligibility_info = airdrop_data['data']
                full_wallet = eligibility_info.get('wallet_address')
                season_info = self.get_season_tokens(eligibility_info, for_display=True)
                
                is_eligible = eligibility_info['is_eligible']
                status_color = Colors.SUCCESS if is_eligible else Colors.ERROR
                eligibility_status = "ELIGIBLE!" if is_eligible else "NOT ELIGIBLE!"
                
                log_line = (
                    f"[{Colors.SUCCESS}Bearer Active:{Colors.RESET} {Colors.TOKEN}{masked_token}{Colors.RESET}]\n"
                    f"{Colors.INFO}Account: {Colors.RESET}{Colors.WARNING}{email}{Colors.RESET} | "
                    f"{Colors.INFO}Wallet Address: {Colors.RESET}{Colors.WARNING}{full_wallet}{Colors.RESET} | "
                    f"{status_color}{eligibility_status}{Colors.RESET} | {season_info}"
                )
                
                print(log_line)
                
                if is_eligible:
                    self.eligible_count += 1
                    self.save_eligible({
                        'token': token,
                        'email': email,
                        'full_wallet': full_wallet,
                        'eligibility_info': eligibility_info
                    })
                
                self.success_count += 1
            else:
                log_line = (
                    f"[{Colors.SUCCESS}Bearer Active:{Colors.RESET} {Colors.TOKEN}{masked_token}{Colors.RESET} | Failed: {airdrop_data.get('msg', 'Error checking eligibility')}]"
                )
                print(log_line)
                self.failed_count += 1

        except Exception as e:
            log_line = (
                f"[{Colors.SUCCESS}Bearer Active:{Colors.RESET} {Colors.TOKEN}{masked_token}{Colors.RESET} | Error: {str(e)}]"
            )
            print(log_line)
            self.failed_count += 1

    def run(self):
        if not self.tokens:
            print(f"{Colors.ERROR}No tokens found in tokens.txt{Colors.RESET}")
            return

        for i, token in enumerate(self.tokens, 1):
            self.check_account(token, i, len(self.tokens))

        print(f"\n{Colors.INFO}===== SUMMARY =====")
        print(f"{Colors.SUCCESS}Success: {self.success_count}")
        print(f"{Colors.ERROR}Failed: {self.failed_count}")
        print(f"{Colors.SUCCESS}Eligible: {self.eligible_count}{Colors.RESET}")

if __name__ == "__main__":
    banner = """ __  __   ___   ____    ____ ____   ___  _  _
 ||\\ ||  // \\\\  || \\\\  ||    || \\\\ // \\\\ \\\\//
 ||\\\\|| ((   )) ||  )) ||==  ||_// ||=||  )/ 
 || \\||  \\\\_//  ||_//  ||___ ||    || || //  

    Eligibility Checker - Github: Mittyadav"""
    print(f"{Colors.INFO}{banner}{Colors.RESET}\n")
    checker = AirdropChecker()
    checker.run()
