import json
from typing import Dict, Any, List, Tuple


def extract_species_data(api_json: Dict[str, Any]) -> List[Tuple[str, int]]:
    """
    Extracts species and support from the API JSON response.
    Returns a list of (species, support) tuples, ordered by descending support.
    """
    predictions = api_json.get("taxon_prediction", [])
    if not predictions:
        # Fallback to fields.species if taxon_prediction is empty/missing
        fields_species = api_json.get("fields", {}).get("species")
        if fields_species:
            return [(fields_species, 100)]  # Assume 100% support for fields.species
        return []

    # Collect (taxon, support) tuples
    # Support might be missing, default to 0
    species_list = []
    for pred in predictions:
        taxon = pred.get("taxon")
        if taxon:
            support = pred.get("support", 0)
            # Try to cast support to float/int just in case
            try:
                support = float(support)
            except (ValueError, TypeError):
                support = 0
            species_list.append((taxon, support))

    if not species_list:
        return []

    # Deduplicate while keeping max support for each taxon
    unique_species: dict[str, float] = {}
    for taxon, support in species_list:
        if taxon in unique_species:
            unique_species[taxon] = max(unique_species[taxon], support)
        else:
            unique_species[taxon] = support

    # Sort by support desc, then taxon asc
    sorted_species = sorted(unique_species.items(), key=lambda x: (-x[1], x[0]))

    # Convert support to int
    return [(s[0], int(s[1])) for s in sorted_species]


def extract_species(api_json: Dict[str, Any]) -> str:
    """
    Extracts species from the API JSON response.
    Returns a comma-separated string of unique species, ordered by descending support/probability.
    """
    data = extract_species_data(api_json)
    return ",".join([s[0] for s in data])


def extract_species_and_support(api_json: Dict[str, Any]) -> Tuple[str, str]:
    """
    Extracts species and support strings.
    Returns (species_str, support_str).
    """
    data = extract_species_data(api_json)
    if not data:
        return "", ""

    names = ",".join([s[0] for s in data])
    supports = ",".join([str(s[1]) for s in data])
    return names, supports


def format_json(data: Any) -> str:
    """
    Format data as pretty JSON with 2-space indent.
    """
    return json.dumps(data, indent=2)
