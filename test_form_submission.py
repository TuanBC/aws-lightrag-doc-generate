"""Test form submission to verify the fix."""

import requests

BASE_URL = "http://localhost:8000"


def test_form_submission():
    """Test form submission with proper form data."""
    print("Testing form submission...")

    # Test with valid address
    test_address = "0x" + "a" * 40
    form_data = {"wallet_address": test_address}

    response = requests.post(
        f"{BASE_URL}/scores",
        data=form_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        allow_redirects=False,
    )

    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
    print(f"Response Length: {len(response.text)} bytes")

    if response.status_code == 200:
        if "score-header" in response.text or "score-value" in response.text:
            print("[SUCCESS] Form submission working! Score page rendered.")
        else:
            print("[INFO] Form submitted but unexpected response format")
            print(f"Preview: {response.text[:200]}...")
    else:
        print(f"[ERROR] Form submission failed with status {response.status_code}")
        print(f"Response: {response.text[:500]}")

    return response.status_code == 200


if __name__ == "__main__":
    test_form_submission()
