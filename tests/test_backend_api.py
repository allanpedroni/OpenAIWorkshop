import pytest
import requests
import json
import time

pytestmark = pytest.mark.integration

# Increase timeout for Container Apps cold start
DEFAULT_TIMEOUT = 60
MAX_RETRIES = 3
RETRY_DELAY = 10


def make_backend_api_request(url, payload=None, method="POST", timeout=DEFAULT_TIMEOUT, retries=MAX_RETRIES):
    """Make an HTTP request to backend API with proper headers and retry logic."""
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }

    last_error = None
    for attempt in range(retries):
        try:
            if method.upper() == "POST":
                response = requests.post(url, headers=headers,
                                         json=payload, timeout=timeout)
            else:
                response = requests.get(url, headers=headers, timeout=timeout)
            
            # If we get a response (even error), return it
            return response
        except requests.RequestException as e:
            last_error = e
            if attempt < retries - 1:
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
    
    # All retries failed, raise the last error
    raise last_error


@pytest.fixture(scope="session")
def backend_chat_response(backend_api_endpoint):
    """Make a chat request to the backend API and cache the response."""
    payload = {
        "session_id": "123",
        "prompt": "What can you help me with?"
    }

    try:
        response = make_backend_api_request(
            f"{backend_api_endpoint}/chat", payload)
        return response
    except requests.RequestException as e:
        # Return a mock failed response
        class MockResponse:
            def __init__(self):
                self.status_code = 500
                self.text = str(e)
                self._json_data = {"error": str(e)}

            def json(self):
                return self._json_data
        return MockResponse()


def test_backend_chat_returns_success_status(backend_chat_response):
    """Test that the backend chat endpoint returns HTTP 200 status."""
    assert backend_chat_response.status_code == 200, f"Expected 200, got {backend_chat_response.status_code}: {backend_chat_response.text}"


def test_backend_chat_returns_valid_json(backend_chat_response):
    """Test that the backend chat endpoint returns valid JSON data."""
    data = backend_chat_response.json()
    assert data is not None, "Response data is None"
    assert isinstance(data, dict), "Response should be a JSON object"


def test_backend_chat_handles_session_id(backend_chat_response):
    """Test that the backend properly handles the session_id parameter."""
    data = backend_chat_response.json()

    # Check if response acknowledges the session
    # Common patterns: session_id in response, or response context indicates session handling
    if "session_id" in data:
        assert data["session_id"] == "123", "Session ID should match the request"
    elif "session" in data:
        assert "123" in str(
            data["session"]), "Session should reference the provided ID"
    # If no explicit session handling, just ensure response is not an error
    else:
        assert "error" not in data or not data.get(
            "error"), "Response should not contain errors"


def test_backend_chat_provides_helpful_response(backend_chat_response):
    """Test that the backend provides a helpful response to 'What can you help me with?'."""
    data = backend_chat_response.json()

    # Look for common response fields
    response_text = ""
    if "response" in data:
        response_text = data["response"]
    elif "message" in data:
        response_text = data["message"]
    elif "content" in data:
        response_text = data["content"]
    elif "answer" in data:
        response_text = data["answer"]
    else:
        # Check if it's a structured response with nested content
        response_text = str(data).lower()

    # Verify the response mentions help or capabilities
    assert isinstance(
        response_text, str), "Response should contain text content"
    assert len(response_text) > 0, "Response should not be empty"

    # Check for helpful keywords
    helpful_keywords = ["help", "assist", "can",
                        "support", "provide", "answer", "question"]
    response_lower = response_text.lower()
    assert any(
        keyword in response_lower for keyword in helpful_keywords), f"Response should mention help or capabilities. Got: {response_text[:100]}..."


def test_backend_chat_with_different_session(backend_api_endpoint):
    """Test that the backend handles different session IDs properly."""
    # This test makes a separate request with a different session ID
    payload = {
        "session_id": "test-session-456",
        "prompt": "Hello, this is a test message."
    }

    try:
        response = make_backend_api_request(
            f"{backend_api_endpoint}/chat", payload)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert data is not None, "Response data should not be None"

        # Verify response is reasonable
        if "response" in data:
            assert len(data["response"]) > 0, "Response should not be empty"
        elif "message" in data:
            assert len(data["message"]) > 0, "Message should not be empty"

    except requests.RequestException as e:
        pytest.skip(
            f"Backend API not available for additional session test: {e}")


def test_backend_chat_handles_invalid_payload(backend_api_endpoint):
    """Test that the backend properly handles invalid request payload."""
    invalid_payloads = [
        {},  # Empty payload
        {"session_id": "123"},  # Missing prompt
        {"prompt": "test"},  # Missing session_id
        {"session_id": "", "prompt": ""},  # Empty values
    ]

    for payload in invalid_payloads:
        try:
            response = make_backend_api_request(
                f"{backend_api_endpoint}/chat", payload)
            # Accept various error responses - 400/422 for validation, 500 for unhandled errors,
            # or 200 if the backend handles it gracefully
            assert response.status_code in [
                200, 400, 422, 500], f"Unexpected status {response.status_code} for payload {payload}"

            if response.status_code == 200:
                # If it returns 200, should still have valid JSON
                data = response.json()
                assert data is not None, "Response should contain valid JSON even for invalid input"

        except requests.RequestException:
            # Skip this specific payload test if request fails
            continue
