import base64
import time
import requests
from typing import Dict, Any
from . import __version__

DEFAULT_URI = (
    "https://rest.pubmlst.org/db/pubmlst_rmlst_seqdef_kiosk/schemes/1/sequence"
)
FALLBACK_URI = "https://rest.pubmlst.org/db/pubmlst_rmlst_seqdef/schemes/1/sequence"

USER_AGENT = f"rmlst-cli/{__version__} (+https://github.com/ssi-dk/rmlst_cli; maintainer: pmat@ssi.dk)"


class RmlstNetworkError(Exception):
    """Raised when network errors occur after retries."""

    pass


class RmlstHttpError(Exception):
    """Raised when HTTP error (non-200) occurs."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


def _make_request(
    session: requests.Session,
    uri: str,
    payload: Dict[str, Any],
    retries: int,
    retry_delay: int,
    debug: bool = False,
) -> Dict[str, Any]:
    """
    Helper to make request with retries.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            if debug:
                print(f"DEBUG: Attempt {attempt}, URI: {uri}, Timeout: (30, 300)")
                start_time = time.time()

            response = session.post(
                uri,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": USER_AGENT,
                },
                timeout=(30, 300),  # connect, read
            )

            if debug:
                print(
                    f"DEBUG: Response {response.status_code} in {time.time() - start_time:.2f}s"
                )

            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError:
                    raise RmlstHttpError(response.status_code, "Invalid JSON response")

            # Check for retryable codes
            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt <= retries:
                    time.sleep(retry_delay)
                    continue
                else:
                    # Exhausted retries on HTTP error
                    raise RmlstHttpError(
                        response.status_code, response.text[:1000]
                    )  # Truncate body

            # Non-retryable 4xx
            raise RmlstHttpError(response.status_code, response.text[:1000])

        except requests.RequestException as e:
            # Network errors (DNS, timeout, connection reset, TLS error)
            if attempt <= retries:
                time.sleep(retry_delay)
                continue
            else:
                raise RmlstNetworkError(f"Network error: {e}")


def call_rmlst_api(
    fasta_str: str,
    uri: str = DEFAULT_URI,
    retries: int = 3,
    retry_delay: int = 60,
    debug: bool = False,
) -> Dict[str, Any]:
    """
    Calls the rMLST API with the given FASTA string.
    Handles retries and fallback to non-kiosk endpoint if using default URI.
    """
    # Prepare payload
    b64_seq = base64.b64encode(fasta_str.encode("utf-8")).decode("ascii")
    payload = {"base64": True, "details": True, "sequence": b64_seq}

    session = requests.Session()

    try:
        return _make_request(session, uri, payload, retries, retry_delay, debug)
    except (RmlstNetworkError, RmlstHttpError):
        # Check if we should fallback
        if uri == DEFAULT_URI:
            try:
                return _make_request(
                    session, FALLBACK_URI, payload, retries, retry_delay, debug
                )
            except (RmlstNetworkError, RmlstHttpError):
                # If fallback also fails, raise the error from the fallback attempt
                raise
        else:
            raise
