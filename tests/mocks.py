"""Mock HKT SMS API for testing."""

import random
import time


class MockHKTResponse:
    """Mock HKT API response."""

    def __init__(self, status_code: int = 200, text: str = "SUCCESS"):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        """Raise HTTPError for bad status codes."""
        if self.status_code >= 400:
            from requests.exceptions import HTTPError
            raise HTTPError(response=self)


class MockHKTPost:
    """Mock requests.post function for HKT API."""

    def __init__(self, failure_rate: float = 0.1, min_delay: float = 0.5, max_delay: float = 5.0):
        self.failure_rate = failure_rate
        self.min_delay = min_delay
        self.max_delay = max_delay

    def __call__(self, *args, **kwargs):
        """Simulate HKT API call."""
        # Simulate network delay
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

        # Simulate random failures
        if random.random() < self.failure_rate:
            from requests.exceptions import RequestException
            raise RequestException("Simulated HKT API failure")

        # Return successful response
        return MockHKTResponse(status_code=200, text="SUCCESS")
