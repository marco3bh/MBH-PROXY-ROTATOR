
import time
from pathlib import Path
from collections import deque
from urllib.parse import urlparse

import requests

PROXY_FILE = Path(__file__).with_name("proxies.txt")
IP_CHECK_URL = "https://api.ipify.org?format=json"
TIMEOUT = 10


def load_proxies():
    if not PROXY_FILE.exists():
        PROXY_FILE.write_text(
            "# One proxy per line\n"
            "# http://user:pass@host:port\n"
            "# socks5h://user:pass@host:port\n",
            encoding="utf-8"
        )
        print("[!] proxies.txt created. Add your proxies.")
        return []

    proxies = []

    for line in PROXY_FILE.read_text(encoding="utf-8").splitlines():
        proxy = line.strip()

        if not proxy or proxy.startswith("#"):
            continue

        if "://" not in proxy:
            proxy = "http://" + proxy

        parsed = urlparse(proxy)

        if parsed.scheme not in ("http", "https", "socks5", "socks5h"):
            print(f"[-] Unsupported proxy: {proxy}")
            continue

        if not parsed.hostname:
            print(f"[-] Invalid proxy: {proxy}")
            continue

        proxies.append(proxy)

    return list(dict.fromkeys(proxies))


class ProxyRotator:
    def __init__(self, proxies):
        self.proxies = deque(proxies)
        self.session = requests.Session()
        self.session.trust_env = False
        self.total_requests = 0
        self.successful = 0
        self.failed = 0

    def next_proxy(self):
        if not self.proxies:
            raise RuntimeError("No proxies available")

        proxy = self.proxies[0]
        self.proxies.rotate(-1)
        return proxy

    def request(self, url):
        if not self.proxies:
            raise RuntimeError("Proxy list is empty")

        for _ in range(len(self.proxies)):
            proxy = self.next_proxy()
            self.total_requests += 1

            try:
                response = self.session.get(
                    url,
                    proxies={
                        "http": proxy,
                        "https": proxy
                    },
                    timeout=TIMEOUT,
                    headers={
                        "User-Agent": "MBH-Proxy-Rotator/1.0"
                    }
                )

                response.raise_for_status()
                self.successful += 1

                print(f"[+] Working proxy: {proxy}")
                return response

            except requests.RequestException as error:
                self.failed += 1
                print(f"[-] Proxy failed: {proxy}")
                print(f"    {error}")

        raise RuntimeError("All proxies failed")

    def check_ip(self):
        response = self.request(IP_CHECK_URL)
        data = response.json()

        ip = data.get("ip", "Unknown")
        print(f"[+] Public IP: {ip}")

        return ip

    def auto_rotate(self, count, interval):
        for index in range(count):
            print(f"\n[*] Rotation {index + 1}/{count}")

            try:
                self.check_ip()
            except (RuntimeError, ValueError) as error:
                print(f"[-] {error}")

            if index < count - 1:
                time.sleep(interval)

    def stats(self):
        print("\n========== STATISTICS ==========")
        print(f"Total attempts : {self.total_requests}")
        print(f"Successful     : {self.successful}")
        print(f"Failed         : {self.failed}")
        print(f"Loaded proxies : {len(self.proxies)}")
        print("================================")


def banner():
    print(r"""
 __  __ ____  _   _
|  \/  | __ )| | | |
| |\/| |  _ \| |_| |
| |  | | |_) |  _  |
|_|  |_|____/|_| |_|

  ____  ____   _____  ____   __
 |  _ \|  _ \ / _ \ \/ /\ \ / /
 | |_) | |_) | | | \  /  \ V /
 |  __/|  _ <| |_| /  \   | |
 |_|   |_| \_\\___/_/\_\  |_|

       PROXY ROTATOR v1.0
    """)


def main():
    banner()

    proxies = load_proxies()

    if not proxies:
        print("[!] Add proxies to proxies.txt and restart.")
        return

    rotator = ProxyRotator(proxies)

    print(f"[+] Loaded {len(proxies)} proxies")

    while True:
        print("""
[1] CHECK CURRENT PROXY IP
[2] AUTO ROTATE PROXIES
[3] CUSTOM HTTP GET REQUEST
[4] STATISTICS
[0] EXIT
""")

        choice = input("MBH > ").strip()

        try:
            if choice == "1":
                rotator.check_ip()

            elif choice == "2":
                count = int(input("Number of rotations: "))
                interval = float(input("Interval in seconds (min 3): "))

                if not 1 <= count <= 100:
                    print("[-] Choose 1 to 100 rotations.")
                    continue

                interval = max(3.0, interval)
                rotator.auto_rotate(count, interval)

            elif choice == "3":
                url = input("Target URL: ").strip()

                parsed = urlparse(url)

                if parsed.scheme not in ("http", "https") or not parsed.hostname:
                    print("[-] Enter a valid HTTP/HTTPS URL.")
                    continue

                response = rotator.request(url)

                print(f"[+] Status: {response.status_code}")
                print(f"[+] Response preview:\n{response.text[:500]}")

            elif choice == "4":
                rotator.stats()

            elif choice == "0":
                print("[+] Goodbye.")
                break

            else:
                print("[-] Invalid option.")

        except (RuntimeError, ValueError, requests.RequestException) as error:
            print(f"[-] Error: {error}")


if __name__ == "__main__":
    main()