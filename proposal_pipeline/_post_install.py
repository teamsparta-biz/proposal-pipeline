"""Playwright 브라우저 설치 헬퍼.

proposal-install-browsers 명령어로 실행:
  proposal-install-browsers          # Chromium만 설치
"""

import subprocess
import sys


def main():
    cmd = [sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("Chromium 설치 완료.")


if __name__ == "__main__":
    main()
