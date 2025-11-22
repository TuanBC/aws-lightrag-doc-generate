"""Quick test script to verify server endpoints."""

import requests
import sys
import time
import io

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_URL = "http://localhost:8000"


def test_endpoint(path, description):
    """Test an endpoint and report results."""
    try:
        url = f"{BASE_URL}{path}"
        response = requests.get(url, timeout=5)
        print(f"[OK] {description}")
        print(f"   URL: {url}")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            if "application/json" in response.headers.get("content-type", ""):
                print(f"   Response: {response.json()}")
            else:
                content_len = len(response.text)
                print(f"   Content Length: {content_len} bytes")
                if content_len < 500:
                    print(f"   Preview: {response.text[:200]}...")
        print()
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print(f"[FAIL] {description}")
        print("   Error: Cannot connect to server. Is it running?")
        print()
        return False
    except Exception as e:
        print(f"[FAIL] {description}")
        print(f"   Error: {e}")
        print()
        return False


def main():
    print("Testing Onchain Credit Scoring Server\n")
    print("=" * 60)
    print()

    # Wait a moment for server to be ready
    print("Waiting for server to be ready...")
    time.sleep(2)

    results = []

    # Test health endpoint
    results.append(
        ("Health Check", test_endpoint("/api/health", "Health Check Endpoint"))
    )

    # Test home page
    results.append(("Home Page", test_endpoint("/", "Home Page (SSR)")))

    # Test static files
    results.append(
        ("CSS", test_endpoint("/static/css/etherscan.css", "CSS Stylesheet"))
    )
    results.append(
        ("JavaScript", test_endpoint("/static/js/main.js", "JavaScript File"))
    )

    # Test API docs
    results.append(("API Docs", test_endpoint("/docs", "OpenAPI Documentation")))

    # Test with a sample wallet address (this will fail if API key not set, but we can see the error)
    print("Testing API endpoint with sample address...")
    try:
        test_addr = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
        url = f"{BASE_URL}/api/v1/wallets/{test_addr}/score"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("[OK] Score API Endpoint")
            print(f"   URL: {url}")
            print(f"   Status: {response.status_code}")
            data = response.json()
            print(f"   Score: {data.get('breakdown', {}).get('credit_score', 'N/A')}")
            print()
        else:
            print("[WARN] Score API Endpoint")
            print(f"   URL: {url}")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            print()
    except Exception as e:
        print("[WARN] Score API Endpoint")
        print(f"   Error: {e}")
        print("   (This is expected if ETHERSCAN_API_KEY is not set)")
        print()

    # Summary
    print("=" * 60)
    print("\nTest Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"   Passed: {passed}/{total}")

    if passed == total:
        print("\n[SUCCESS] All tests passed! Server is running correctly.")
        return 0
    else:
        print("\n[WARNING] Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
