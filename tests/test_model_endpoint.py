# import pytest
# import requests

# pytestmark = pytest.mark.integration


# @pytest.fixture(scope="session")
# def model_api_response(model_endpoint, model_api_key):
#     """Make a single API call and cache the response for all tests."""
#     headers = {
#         "Content-Type": "application/json",
#         "api-key": model_api_key,
#     }
#     payload = {
#         "messages": [{"role": "system", "content": "You are an helpful assistant."}, {"role": "user", "content": "What are 3 things to visit in Seattle?"}],
#         "max_tokens": 1000,
#         "model": "gpt-5.2-chat"
#     }
#     resp = requests.post(model_endpoint, headers=headers,
#                          json=payload, timeout=10)

#     if resp.status_code != 200:
#         pytest.fail(
#             f"Model API request failed with status code {resp.status_code}: {resp.text} to endpoint {model_endpoint}")

#     return resp


# def test_model_endpoint_returns_success_status(model_api_response):
#     """Test that the model endpoint returns HTTP 200 status."""
#     assert model_api_response.status_code == 200


# def test_model_endpoint_returns_valid_json(model_api_response):
#     """Test that the model endpoint returns valid JSON data."""
#     data = model_api_response.json()
#     assert data is not None


# def test_model_endpoint_response_has_usage_tokens(model_api_response):
#     """Test that the response contains valid usage token count."""
#     data = model_api_response.json()
#     assert isinstance(data["usage"]["total_tokens"],
#                       int), "total_tokens is not an integer"


# def test_model_endpoint_response_has_message_content(model_api_response):
#     """Test that the response contains valid message content."""
#     data = model_api_response.json()
#     assert isinstance(data["choices"][0]["message"]
#                       ["content"], str), "Message content is not a string"
