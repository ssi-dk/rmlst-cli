import pytest
from click.testing import CliRunner
from unittest.mock import patch
from rmlst_cli.cli import main
from rmlst_cli import __version__


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_version(runner):
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert f"rmlst {__version__}" in result.output


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

    mock_resp = {"taxon_prediction": [{"taxon": "Species X", "support": 95}]}

    with patch("rmlst_cli.api.identify", return_value=mock_resp):
        result = runner.invoke(main, ["-f", str(f), "--species-only"])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert lines[0] == "species\tsupport"
        assert lines[1] == "Species X\t95"


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


def test_cli_dir_species_only(runner, tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    (d / "a.fasta").write_text(">seq1\nATGC")
    (d / "b.fasta").write_text(">seq2\nATGC")

    mock_resp = {"taxon_prediction": [{"taxon": "Species X", "support": 95}]}

    with patch("rmlst_cli.api.identify", return_value=mock_resp):
        result = runner.invoke(main, ["-d", str(d), "--species-only"])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        # Header
        assert lines[0] == "file\tspecies\tsupport"
        # Rows (sorted by filename)
        assert "a.fasta\tSpecies X\t95" in lines
        assert "b.fasta\tSpecies X\t95" in lines


def test_cli_force_overwrite(runner, tmp_path):
    f = tmp_path / "test.fasta"
    f.write_text(">seq1\nATGC")
    out = tmp_path / "output.txt"
    out.write_text("existing content")

    mock_resp = {"taxon_prediction": [{"taxon": "Species X", "support": 95}]}

    with patch("rmlst_cli.api.identify", return_value=mock_resp):
        result = runner.invoke(
            main, ["-f", str(f), "--species-only", "--output", str(out), "--force"]
        )
        assert result.exit_code == 0
        # Should have overwritten
        content = out.read_text()
        lines = content.strip().split("\n")
        assert lines[0] == "species\tsupport"
        assert lines[1] == "Species X\t95"
