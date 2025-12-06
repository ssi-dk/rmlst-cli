import pytest
import os
from rmlst_cli import api
from rmlst_cli.fasta import TooManyContigsError

# Path to fixtures
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
LARGE_FASTA = os.path.join(FIXTURES_DIR, "real_large.fasta")
VALID_FASTA = os.path.join(FIXTURES_DIR, "real_valid_small.fasta")


def test_large_fasta_limit():
    """
    Test that processing a large FASTA file (>5000 contigs) raises TooManyContigsError
    when trim_to_5000 is False.
    """
    if not os.path.exists(LARGE_FASTA):
        pytest.skip("real_large.fasta fixture not found")

    with pytest.raises(TooManyContigsError):
        # We don't need to mock the API call because it should fail BEFORE calling the API
        api.identify(LARGE_FASTA, trim_to_5000=False)


def test_large_fasta_trim():
    """
    Test that processing a large FASTA file with trim_to_5000=True works
    (at least the FASTA processing part).
    We mock the API call to avoid sending a huge payload.
    """
    if not os.path.exists(LARGE_FASTA):
        pytest.skip("real_large.fasta fixture not found")

    from unittest.mock import patch

    # Mock the API call to return success
    with patch(
        "rmlst_cli.http.call_rmlst_api", return_value={"mock": "result"}
    ) as mock_api:
        result = api.identify(LARGE_FASTA, trim_to_5000=True)
        assert result == {"mock": "result"}

        # Verify that the API was called
        mock_api.assert_called_once()

        # We could inspect the call args to verify the payload size/content if we wanted,
        # but just checking it didn't raise is good for now.


@pytest.mark.integration
def test_real_api_call():
    """
    Integration test hitting the real PubMLST API.
    """
    if not os.path.exists(VALID_FASTA):
        pytest.skip("real_valid_small.fasta fixture not found")

    # This calls the REAL API
    try:
        result = api.identify(VALID_FASTA)

        # Basic validation of the response structure
        assert isinstance(result, dict)
        # We expect some taxon prediction or at least a valid JSON response
        # The exact content depends on the file, but it shouldn't be empty or error

        # If the file is a valid rMLST sample, it should have taxon_prediction
        # If it's just random DNA, it might return no match but still success (empty prediction)
        # But we shouldn't get an exception.

    except Exception as e:
        pytest.fail(f"Real API call failed: {e}")
