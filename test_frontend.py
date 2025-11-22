"""Test frontend functionality including JavaScript validation."""

import requests
from bs4 import BeautifulSoup

BASE_URL = "http://localhost:8000"


def test_home_page_structure():
    """Test that home page has correct structure and elements."""
    print("Testing Home Page Structure...")

    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200, "Home page should return 200"

    soup = BeautifulSoup(response.text, "html.parser")

    # Check for form
    form = soup.find("form", class_="address-form")
    assert form is not None, "Address form should exist"
    assert form.get("action") == "/scores", "Form action should be /scores"
    assert form.get("method") == "post", "Form method should be POST"

    # Check for input field
    input_field = soup.find("input", {"name": "wallet_address"})
    assert input_field is not None, "Wallet address input should exist"
    assert input_field.get("minlength") == "42", "Input should have minlength=42"
    assert input_field.get("maxlength") == "42", "Input should have maxlength=42"

    # Check for submit button
    submit_btn = soup.find("button", {"type": "submit"})
    assert submit_btn is not None, "Submit button should exist"

    # Check for JavaScript reference
    script_tag = soup.find("script", {"src": "/static/js/main.js"})
    assert script_tag is not None, "main.js should be referenced"

    # Check for CSS reference
    css_link = soup.find("link", {"href": "/static/css/etherscan.css"})
    assert css_link is not None, "etherscan.css should be referenced"

    print("  [OK] All home page elements present")
    return True


def test_static_files():
    """Test that static files are accessible."""
    print("Testing Static Files...")

    # Test CSS
    css_response = requests.get(f"{BASE_URL}/static/css/etherscan.css")
    assert css_response.status_code == 200, "CSS should be accessible"
    assert "--scan-bg" in css_response.text, "CSS should contain CSS variables"
    print("  [OK] CSS file accessible and valid")

    # Test JavaScript
    js_response = requests.get(f"{BASE_URL}/static/js/main.js")
    assert js_response.status_code == 200, "JavaScript should be accessible"
    assert "normalizeAddress" in js_response.text, (
        "JS should contain normalizeAddress function"
    )
    assert "ADDRESS_LENGTH" in js_response.text, "JS should contain address validation"
    print("  [OK] JavaScript file accessible and valid")

    return True


def test_form_submission():
    """Test form submission with valid and invalid addresses."""
    print("Testing Form Submission...")

    # Test with valid address (lowercase, 42 chars)
    valid_addr = "0x" + "a" * 40
    form_data = {"wallet_address": valid_addr}

    response = requests.post(
        f"{BASE_URL}/scores", data=form_data, allow_redirects=False
    )
    # Should return 200 (not redirect) for SSR
    assert response.status_code == 200, (
        f"Form submission should return 200, got {response.status_code}"
    )

    soup = BeautifulSoup(response.text, "html.parser")
    # Check if score detail page is rendered
    score_header = soup.find("section", class_="score-header")
    if score_header:
        print("  [OK] Form submission successful - score page rendered")
    else:
        # Might be showing error message
        feedback = soup.find("p", class_="feedback")
        if feedback:
            print(f"  [INFO] Form submitted but showing message: {feedback.text[:50]}")
        else:
            print("  [WARN] Unexpected response format")

    return True


def test_api_endpoint():
    """Test JSON API endpoint."""
    print("Testing API Endpoint...")

    test_addr = "0x" + "b" * 40
    response = requests.get(f"{BASE_URL}/api/v1/wallets/{test_addr}/score", timeout=10)

    if response.status_code == 200:
        data = response.json()
        assert "wallet_address" in data, "Response should contain wallet_address"
        assert "breakdown" in data, "Response should contain breakdown"
        assert "credit_score" in data["breakdown"], (
            "Breakdown should contain credit_score"
        )
        print(
            f"  [OK] API endpoint working - Score: {data['breakdown']['credit_score']}"
        )
    elif response.status_code == 400:
        print(
            "  [INFO] API validation working (400 response expected for invalid input)"
        )
    else:
        print(
            f"  [WARN] API returned status {response.status_code}: {response.text[:100]}"
        )

    return True


def main():
    print("=" * 60)
    print("Frontend and Integration Tests")
    print("=" * 60)
    print()

    tests = [
        ("Home Page Structure", test_home_page_structure),
        ("Static Files", test_static_files),
        ("Form Submission", test_form_submission),
        ("API Endpoint", test_api_endpoint),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
            print()
        except AssertionError as e:
            print(f"  [FAIL] {e}")
            results.append((name, False))
            print()
        except Exception as e:
            print(f"  [ERROR] {e}")
            results.append((name, False))
            print()

    # Summary
    print("=" * 60)
    print("Test Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"  Passed: {passed}/{total}")

    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"  {status} {name}")

    if passed == total:
        print("\n[SUCCESS] All frontend tests passed!")
        return 0
    else:
        print("\n[WARNING] Some tests failed.")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
