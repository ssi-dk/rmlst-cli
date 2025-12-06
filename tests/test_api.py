import pytest
from unittest.mock import patch
from rmlst_cli import api, http
from rmlst_cli.fasta import InvalidFastaError


def test_identify_success(tmp_path):
    fasta_file = tmp_path / "test.fasta"
    fasta_file.write_text(">seq1\nATGC")

    mock_response = {"taxon_prediction": [{"taxon": "Neisseria meningitidis"}]}

    with patch(
        "rmlst_cli.http.call_rmlst_api", return_value=mock_response
    ) as mock_call:
        result = api.identify(str(fasta_file))
        assert result == mock_response
        mock_call.assert_called_once()


def test_identify_invalid_fasta(tmp_path):
    fasta_file = tmp_path / "test.fasta"
    fasta_file.write_text("NOT FASTA")

    with pytest.raises(InvalidFastaError):
        api.identify(str(fasta_file))


def test_identify_graceful_failure(tmp_path):
    fasta_file = tmp_path / "test.fasta"
    fasta_file.write_text(">seq1\nATGC")

    with patch(
        "rmlst_cli.http.call_rmlst_api",
        side_effect=http.RmlstNetworkError("Network error"),
    ):
        # graceful=False -> raises
        with pytest.raises(http.RmlstNetworkError):
            api.identify(str(fasta_file), graceful=False)

        # graceful=True -> returns {}
        result = api.identify(str(fasta_file), graceful=True)
        assert result == {}


def test_identify_dir(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    (d / "a.fasta").write_text(">seq1\nATGC")
    (d / "b.fa").write_text(">seq2\nCGTA")

    mock_response = {"taxon_prediction": [{"taxon": "Species A"}]}

    with patch("rmlst_cli.http.call_rmlst_api", return_value=mock_response):
        results = list(api.identify_dir(str(d)))
        assert len(results) == 2
        assert results[0][0] == "a.fasta"
        assert results[1][0] == "b.fa"


def test_identify_dir_graceful(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    (d / "a.fasta").write_text(">seq1\nATGC")
    (d / "b.fa").write_text(">seq2\nCGTA")

    # Fail on first, succeed on second
    with patch(
        "rmlst_cli.http.call_rmlst_api",
        side_effect=[http.RmlstNetworkError("Fail"), {"ok": True}],
    ):
        # graceful=False -> raises
        with pytest.raises(http.RmlstNetworkError):
            list(api.identify_dir(str(d), graceful=False))

    with patch(
        "rmlst_cli.http.call_rmlst_api",
        side_effect=[http.RmlstNetworkError("Fail"), {"ok": True}],
    ):
        # graceful=True -> yields empty dict for failure
        results = list(api.identify_dir(str(d), graceful=True))
        assert len(results) == 2
        assert results[0] == ("a.fasta", {})
        assert results[1] == ("b.fa", {"ok": True})
