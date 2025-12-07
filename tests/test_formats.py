from rmlst_cli.formats import extract_species, extract_species_and_support


class TestFormats:
    def test_extract_species_normal(self):
        """Test extract_species with normal taxon_prediction data."""
        data = {
            "taxon_prediction": [
                {"taxon": "Species A", "support": 95},
                {"taxon": "Species B", "support": 80},
            ]
        }
        result = extract_species(data)
        assert result == "Species A,Species B"

    def test_extract_species_single(self):
        """Test extract_species with single species."""
        data = {
            "taxon_prediction": [{"taxon": "Vibrio parahaemolyticus", "support": 100}]
        }
        result = extract_species(data)
        assert result == "Vibrio parahaemolyticus"

    def test_extract_species_fields_fallback(self):
        """Test extract_species with fields fallback."""
        data = {"fields": {"species": "Campylobacter jejuni"}}
        result = extract_species(data)
        assert result == "Campylobacter jejuni"

    def test_extract_species_empty(self):
        """Test extract_species with empty data."""
        data = {}
        result = extract_species(data)
        assert result == ""

    def test_extract_species_and_support_normal(self):
        """Test extract_species_and_support with normal data."""
        data = {
            "taxon_prediction": [
                {"taxon": "Species A", "support": 95},
                {"taxon": "Species B", "support": 80},
            ]
        }
        species, support = extract_species_and_support(data)
        assert species == "Species A,Species B"
        assert support == "95,80"

    def test_extract_species_and_support_empty(self):
        """Test extract_species_and_support with empty data."""
        data = {}
        species, support = extract_species_and_support(data)
        assert species == ""
        assert support == ""
