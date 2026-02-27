from dotenv import load_dotenv
import os

load_dotenv()

GAMMA_API_KEY: str = os.getenv("GAMMA_API_KEY", "")
GAMMA_BASE_URL: str = "https://public-api.gamma.app/v1.0"

# 폴링 설정
POLL_INTERVAL_SEC: float = 5.0
POLL_TIMEOUT_SEC: float = 300.0
