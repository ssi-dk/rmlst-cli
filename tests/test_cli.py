import pytest
from click.testing import CliRunner
from unittest.mock import patch
from rmlst_cli.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_version(runner):
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "rmlst 0.0.0" in result.output


def test_cli_no_args(runner):
    result = runner.invoke(main, [])
    assert result.exit_code == 2
    assert "One of --fasta or --dir must be provided" in result.output


def test_cli_single_file_success(runner, tmp_path):
    f = tmp_path / "test.fasta"
    f.write_text(">seq1\nATGC")

    mock_resp = {"taxon_prediction": [{"taxon": "Species X"}]}

    with patch("rmlst_cli.api.identify", return_value=mock_resp):
        result = runner.invoke(main, ["-f", str(f)])
        assert result.exit_code == 0
        assert '"taxon": "Species X"' in result.output


def test_cli_single_file_species_only(runner, tmp_path):
    f = tmp_path / "test.fasta"
    f.write_text(">seq1\nATGC")

    mock_resp = {"taxon_prediction": [{"taxon": "Species X"}]}

    with patch("rmlst_cli.api.identify", return_value=mock_resp):
        result = runner.invoke(main, ["-f", str(f), "--species-only"])
        assert result.exit_code == 0
        assert result.output.strip() == "Species X"


def test_cli_dir_success(runner, tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    (d / "a.fasta").write_text(">seq1\nATGC")

    mock_resp = {"taxon_prediction": [{"taxon": "Species X"}]}

    with patch("rmlst_cli.api.identify", return_value=mock_resp):
        result = runner.invoke(main, ["-d", str(d)])
        assert result.exit_code == 0
        # Unwrapped mode default: just the API JSON
        assert '"taxon": "Species X"' in result.output


def test_cli_dir_wrapped_mode(runner, tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    (d / "a.fasta").write_text(">seq1\nATGC")

    mock_resp = {"taxon_prediction": [{"taxon": "Species X"}]}

    with patch("rmlst_cli.api.identify", return_value=mock_resp):
        # Force wrapped mode via --graceful
        result = runner.invoke(main, ["-d", str(d), "--graceful"])
        assert result.exit_code == 0
        assert '"file": "a.fasta"' in result.output
        assert '"result":' in result.output
