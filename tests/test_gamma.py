"""Gamma API 연동 테스트 스크립트.

사용법:
  1. .env 파일에 GAMMA_API_KEY 설정
  2. python test_gamma.py --test auth       # 인증 확인 (테마 목록 조회)
  3. python test_gamma.py --test generate   # Generate API 테스트
  4. python test_gamma.py --test template --gamma-id <ID>  # Template API 테스트
"""

import argparse
import sys
from pathlib import Path

from proposal_pipeline.config import GAMMA_API_KEY, GAMMA_BASE_URL, POLL_INTERVAL_SEC, POLL_TIMEOUT_SEC
from proposal_pipeline.gamma.client import GammaHttpClient
from proposal_pipeline.gamma.models import GenerateRequest, TemplateRequest


def test_auth(client: GammaHttpClient):
    """인증 확인: 테마 + 폴더 목록 조회."""
    print("=== 인증 테스트 ===")
    print(f"Base URL: {GAMMA_BASE_URL}")
    print(f"API Key: {GAMMA_API_KEY[:15]}...")
    print()

    print("--- 테마 목록 (상위 5개) ---")
    themes = client.list_themes(limit=5)
    for t in themes:
        print(f"  [{t.type}] {t.name} (id: {t.id})")
    print(f"  총 {len(themes)}개 조회됨")
    print()

    print("--- 폴더 목록 (상위 5개) ---")
    folders = client.list_folders(limit=5)
    for f in folders:
        print(f"  {f.name} (id: {f.id})")
    print(f"  총 {len(folders)}개 조회됨")
    print()

    print("인증 성공!")


def test_generate(client: GammaHttpClient):
    """Generate API 테스트: 간단한 3카드 프레젠테이션 생성."""
    print("=== Generate API 테스트 ===")

    request = GenerateRequest(
        inputText="AI를 활용한 업무 자동화의 3가지 핵심 전략",
        textMode="generate",
        format="presentation",
        numCards=3,
        exportAs="pptx",
        imageOptions={"source": "noImages"},
    )

    print(f"요청: {request.model_dump(by_alias=True, exclude_none=True)}")
    print()

    print("생성 요청 중...")
    gen_id = client.generate(request)
    print(f"generationId: {gen_id}")
    print()

    print(f"완료 대기 중 (폴링 간격: {POLL_INTERVAL_SEC}초, 타임아웃: {POLL_TIMEOUT_SEC}초)...")
    status = client.wait_for_completion(
        gen_id,
        poll_interval=POLL_INTERVAL_SEC,
        timeout=POLL_TIMEOUT_SEC,
    )

    print(f"상태: {status.status}")
    if status.is_success:
        print(f"gammaUrl: {status.gamma_url}")
        if status.credits:
            print(f"크레딧: {status.credits.deducted} 사용, {status.credits.remaining} 남음")
        print("\nGenerate API 테스트 성공!")
    else:
        print(f"에러: {status.error}")
        print("\nGenerate API 테스트 실패!")


def test_template(client: GammaHttpClient, gamma_id: str):
    """Template API 테스트: 기존 템플릿으로 생성."""
    print("=== Template API 테스트 ===")

    request = TemplateRequest(
        gammaId=gamma_id,
        prompt="고객사: 테스트주식회사\n페인포인트: 반복 업무에 시간 소모\n솔루션: AI 자동화 도입\n기대효과: 업무 시간 50% 절감",
        exportAs="pptx",
    )

    print(f"gammaId: {gamma_id}")
    print(f"요청: {request.model_dump(by_alias=True, exclude_none=True)}")
    print()

    print("생성 요청 중...")
    gen_id = client.create_from_template(request)
    print(f"generationId: {gen_id}")
    print()

    print(f"완료 대기 중 (폴링 간격: {POLL_INTERVAL_SEC}초, 타임아웃: {POLL_TIMEOUT_SEC}초)...")
    status = client.wait_for_completion(
        gen_id,
        poll_interval=POLL_INTERVAL_SEC,
        timeout=POLL_TIMEOUT_SEC,
    )

    print(f"상태: {status.status}")
    if status.is_success:
        print(f"gammaUrl: {status.gamma_url}")
        if status.credits:
            print(f"크레딧: {status.credits.deducted} 사용, {status.credits.remaining} 남음")
        print("\nTemplate API 테스트 성공!")
    else:
        print(f"에러: {status.error}")
        print("\nTemplate API 테스트 실패!")


def main():
    parser = argparse.ArgumentParser(description="Gamma API 연동 테스트")
    parser.add_argument("--test", required=True, choices=["auth", "generate", "template"])
    parser.add_argument("--gamma-id", help="Template 테스트 시 사용할 gammaId")
    args = parser.parse_args()

    if not GAMMA_API_KEY:
        print("에러: GAMMA_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
        sys.exit(1)

    with GammaHttpClient(api_key=GAMMA_API_KEY, base_url=GAMMA_BASE_URL) as client:
        if args.test == "auth":
            test_auth(client)
        elif args.test == "generate":
            test_generate(client)
        elif args.test == "template":
            if not args.gamma_id:
                print("에러: --gamma-id 파라미터가 필요합니다.")
                sys.exit(1)
            test_template(client, args.gamma_id)


if __name__ == "__main__":
    main()
