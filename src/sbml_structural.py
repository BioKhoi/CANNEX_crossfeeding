from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


ENCODED_COMPARTMENT = re.compile(r"^(?:M_)?(?P<base>.+)__91__(?P<comp>[A-Za-z0-9]+)__93__$")
BRACKET_COMPARTMENT = re.compile(r"^(?:M_)?(?P<base>.+)\[(?P<comp>[A-Za-z0-9]+)\]$")


@dataclass(frozen=True)
class SpeciesRecord:
    species_id: str
    base_id: str
    compartment: str
    name: str


@dataclass(frozen=True)
class ReactionRecord:
    reaction_id: str
    reaction_name: str
    lower_bound: float
    upper_bound: float
    reactants: tuple[tuple[str, float], ...]
    products: tuple[tuple[str, float], ...]
    equation: str
    boundary: bool


@dataclass
class ModelRecord:
    path: Path
    model_id: str
    model_name: str
    species: dict[str, SpeciesRecord]
    reactions: list[ReactionRecord]


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def local_attribute(element: ET.Element, name: str) -> str | None:
    for key, value in element.attrib.items():
        if local_name(key) == name:
            return value
    return None


def direct_child(element: ET.Element, name: str) -> ET.Element | None:
    for child in element:
        if local_name(child.tag) == name:
            return child
    return None


def species_references(reaction: ET.Element, list_name: str) -> tuple[tuple[str, float], ...]:
    container = direct_child(reaction, list_name)
    if container is None:
        return ()
    records: list[tuple[str, float]] = []
    for reference in container:
        if local_name(reference.tag) != "speciesReference":
            continue
        species_id = reference.attrib.get("species")
        if not species_id:
            continue
        try:
            stoichiometry = float(reference.attrib.get("stoichiometry", "1"))
        except ValueError:
            stoichiometry = 1.0
        records.append((species_id, stoichiometry))
    return tuple(records)


def decode_species(species_id: str, compartment: str) -> tuple[str, str]:
    encoded = ENCODED_COMPARTMENT.match(species_id)
    if encoded:
        return encoded.group("base"), encoded.group("comp")
    bracketed = BRACKET_COMPARTMENT.match(species_id)
    if bracketed:
        return bracketed.group("base"), bracketed.group("comp")
    value = species_id[2:] if species_id.startswith("M_") else species_id
    suffix = f"_{compartment}"
    if compartment and value.endswith(suffix):
        value = value[: -len(suffix)]
    return value, compartment


def bound_value(
    reaction: ET.Element,
    bound_name: str,
    parameters: dict[str, float],
    fallback: float,
) -> float:
    parameter_id = local_attribute(reaction, bound_name)
    if parameter_id is None:
        return fallback
    return parameters.get(parameter_id, fallback)


def format_coefficient(value: float) -> str:
    if abs(value - 1.0) < 1e-12:
        return ""
    if float(value).is_integer():
        return f"{int(value)} "
    return f"{value:g} "


def format_side(references: tuple[tuple[str, float], ...], species: dict[str, SpeciesRecord]) -> str:
    parts: list[str] = []
    for species_id, coefficient in references:
        record = species.get(species_id)
        label = (
            f"{record.base_id}[{record.compartment}]"
            if record is not None
            else species_id
        )
        parts.append(f"{format_coefficient(coefficient)}{label}")
    return " + ".join(parts) if parts else "∅"


def load_model(path: str | Path) -> ModelRecord:
    model_path = Path(path).expanduser().resolve()
    root = ET.parse(model_path).getroot()
    model_element = next(
        (element for element in root.iter() if local_name(element.tag) == "model"),
        root,
    )
    parameters: dict[str, float] = {}
    species: dict[str, SpeciesRecord] = {}
    for element in root.iter():
        tag = local_name(element.tag)
        if tag == "parameter" and element.attrib.get("id"):
            try:
                parameters[element.attrib["id"]] = float(element.attrib.get("value", "0"))
            except ValueError:
                continue
        elif tag == "species" and element.attrib.get("id"):
            species_id = element.attrib["id"]
            compartment = element.attrib.get("compartment", "")
            base_id, decoded_compartment = decode_species(species_id, compartment)
            species[species_id] = SpeciesRecord(
                species_id=species_id,
                base_id=base_id,
                compartment=decoded_compartment,
                name=element.attrib.get("name", base_id),
            )
    reactions: list[ReactionRecord] = []
    for reaction in (element for element in root.iter() if local_name(element.tag) == "reaction"):
        reaction_id = reaction.attrib.get("id", "")
        reaction_name = reaction.attrib.get("name", reaction_id)
        reactants = species_references(reaction, "listOfReactants")
        products = species_references(reaction, "listOfProducts")
        reversible = reaction.attrib.get("reversible", "false").lower() == "true"
        lower_bound = bound_value(
            reaction,
            "lowerFluxBound",
            parameters,
            -1000.0 if reversible else 0.0,
        )
        upper_bound = bound_value(reaction, "upperFluxBound", parameters, 1000.0)
        involved = {species_id for species_id, _ in reactants + products}
        boundary = bool(
            len(involved) == 1
            and next(iter(involved)) in species
            and species[next(iter(involved))].compartment == "e"
        )
        arrow = "⇄" if lower_bound < 0 < upper_bound else "→"
        equation = f"{format_side(reactants, species)} {arrow} {format_side(products, species)}"
        reactions.append(
            ReactionRecord(
                reaction_id=reaction_id,
                reaction_name=reaction_name,
                lower_bound=lower_bound,
                upper_bound=upper_bound,
                reactants=reactants,
                products=products,
                equation=equation,
                boundary=boundary,
            )
        )
    return ModelRecord(
        path=model_path,
        model_id=model_element.attrib.get("id", model_path.stem),
        model_name=model_element.attrib.get("name", model_path.stem),
        species=species,
        reactions=reactions,
    )


def exchange_records(model: ModelRecord, base_id: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for reaction in model.reactions:
        if not reaction.boundary:
            continue
        reactant_ids = {species_id for species_id, _ in reaction.reactants}
        product_ids = {species_id for species_id, _ in reaction.products}
        involved = reactant_ids | product_ids
        species_id = next(iter(involved))
        species_record = model.species[species_id]
        if species_record.base_id != base_id:
            continue
        if species_id in reactant_ids:
            export_allowed = reaction.upper_bound > 0
            import_allowed = reaction.lower_bound < 0
        else:
            export_allowed = reaction.lower_bound < 0
            import_allowed = reaction.upper_bound > 0
        records.append(
            {
                "reaction_id": reaction.reaction_id,
                "reaction_name": reaction.reaction_name,
                "equation": reaction.equation,
                "species_id": species_id,
                "lower_bound": reaction.lower_bound,
                "upper_bound": reaction.upper_bound,
                "export_allowed": export_allowed,
                "import_allowed": import_allowed,
            }
        )
    return records


def exchange_inventory(model: ModelRecord) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for reaction in model.reactions:
        if not reaction.boundary:
            continue
        reactant_ids = {species_id for species_id, _ in reaction.reactants}
        product_ids = {species_id for species_id, _ in reaction.products}
        involved = reactant_ids | product_ids
        species_id = next(iter(involved))
        species_record = model.species[species_id]
        if species_id in reactant_ids:
            export_allowed = reaction.upper_bound > 0
            import_allowed = reaction.lower_bound < 0
        else:
            export_allowed = reaction.lower_bound < 0
            import_allowed = reaction.upper_bound > 0
        records.append(
            {
                "base_id": species_record.base_id,
                "reaction_id": reaction.reaction_id,
                "reaction_name": reaction.reaction_name,
                "equation": reaction.equation,
                "species_id": species_id,
                "lower_bound": reaction.lower_bound,
                "upper_bound": reaction.upper_bound,
                "export_allowed": export_allowed,
                "import_allowed": import_allowed,
            }
        )
    return records


def capability_label(export_allowed: bool, import_allowed: bool) -> str:
    if export_allowed and import_allowed:
        return "Import and export"
    if export_allowed:
        return "Export only"
    if import_allowed:
        return "Import only"
    return "Blocked"


def directional_views(reaction: ReactionRecord) -> list[tuple[str, set[str], set[str]]]:
    reactants = {species_id for species_id, _ in reaction.reactants}
    products = {species_id for species_id, _ in reaction.products}
    views: list[tuple[str, set[str], set[str]]] = []
    if reaction.upper_bound > 0:
        views.append(("forward", reactants, products))
    if reaction.lower_bound < 0:
        views.append(("reverse", products, reactants))
    return views


def directional_reaction_records(model: ModelRecord) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for index, reaction in enumerate(model.reactions):
        if reaction.boundary or not reaction.reactants or not reaction.products:
            continue
        base_reaction_id = reaction.reaction_id or f"reaction_{index + 1}"
        if reaction.upper_bound > 0:
            records.append(
                {
                    "normalized_id": f"{base_reaction_id}__forward",
                    "reaction_id": base_reaction_id,
                    "reaction_name": reaction.reaction_name,
                    "direction": "forward",
                    "reactants": reaction.reactants,
                    "products": reaction.products,
                    "equation": (
                        f"{format_side(reaction.reactants, model.species)} → "
                        f"{format_side(reaction.products, model.species)}"
                    ),
                }
            )
        if reaction.lower_bound < 0:
            records.append(
                {
                    "normalized_id": f"{base_reaction_id}__reverse",
                    "reaction_id": base_reaction_id,
                    "reaction_name": reaction.reaction_name,
                    "direction": "reverse",
                    "reactants": reaction.products,
                    "products": reaction.reactants,
                    "equation": (
                        f"{format_side(reaction.products, model.species)} → "
                        f"{format_side(reaction.reactants, model.species)}"
                    ),
                }
            )
    return records


def target_species_ids(model: ModelRecord, base_id: str, compartment: str) -> list[str]:
    return sorted(
        species_id
        for species_id, record in model.species.items()
        if record.base_id == base_id and record.compartment == compartment
    )


def transport_records(model: ModelRecord, base_id: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for reaction in model.reactions:
        if reaction.boundary:
            continue
        directions: set[str] = set()
        for direction, substrates, products in directional_views(reaction):
            substrate_compartments = {
                model.species[species_id].compartment
                for species_id in substrates
                if species_id in model.species and model.species[species_id].base_id == base_id
            }
            product_compartments = {
                model.species[species_id].compartment
                for species_id in products
                if species_id in model.species and model.species[species_id].base_id == base_id
            }
            if "c" in substrate_compartments and "e" in product_compartments:
                directions.add("c_to_e")
            if "e" in substrate_compartments and "c" in product_compartments:
                directions.add("e_to_c")
        if not directions:
            continue
        records.append(
            {
                "reaction_id": reaction.reaction_id,
                "reaction_name": reaction.reaction_name,
                "equation": reaction.equation,
                "lower_bound": reaction.lower_bound,
                "upper_bound": reaction.upper_bound,
                "c_to_e_allowed": "c_to_e" in directions,
                "e_to_c_allowed": "e_to_c" in directions,
            }
        )

    # Gram-negative reconstructions commonly split membrane transport into
    # cytosol <-> periplasm and periplasm <-> extracellular reactions.  Treat
    # a directionally valid chain as compartment transport while preserving
    # every reaction and compartment in the reported evidence.
    graph: dict[str, list[tuple[str, ReactionRecord, str]]] = {}
    for reaction in model.reactions:
        if reaction.boundary:
            continue
        for direction, substrates, products in directional_views(reaction):
            substrate_compartments = {
                model.species[species_id].compartment
                for species_id in substrates
                if species_id in model.species
                and model.species[species_id].base_id == base_id
            }
            product_compartments = {
                model.species[species_id].compartment
                for species_id in products
                if species_id in model.species
                and model.species[species_id].base_id == base_id
            }
            for source in substrate_compartments:
                for destination in product_compartments:
                    if source != destination:
                        graph.setdefault(source, []).append(
                            (destination, reaction, direction)
                        )

    def shortest_path(
        source: str,
        destination: str,
    ) -> list[tuple[str, str, ReactionRecord, str]]:
        queue = deque([(source, [])])
        visited = {source}
        while queue:
            compartment, path = queue.popleft()
            for next_compartment, reaction, direction in sorted(
                graph.get(compartment, []),
                key=lambda value: (
                    value[0],
                    value[1].reaction_id,
                    value[2],
                ),
            ):
                next_path = path + [
                    (compartment, next_compartment, reaction, direction)
                ]
                if next_compartment == destination:
                    return next_path
                if next_compartment not in visited:
                    visited.add(next_compartment)
                    queue.append((next_compartment, next_path))
        return []

    for source, destination, direction_key in (
        ("c", "e", "c_to_e"),
        ("e", "c", "e_to_c"),
    ):
        path = shortest_path(source, destination)
        if len(path) <= 1:
            continue
        reaction_labels = [
            f"{reaction.reaction_id} [{direction}]"
            for _, _, reaction, direction in path
        ]
        compartments = [source] + [step[1] for step in path]
        records.append(
            {
                "reaction_id": "; ".join(reaction_labels),
                "reaction_name": (
                    f"Multistep compartment transport ({len(path)} reactions)"
                ),
                "equation": " → ".join(
                    f"{base_id}[{compartment}]" for compartment in compartments
                ),
                "lower_bound": None,
                "upper_bound": None,
                "c_to_e_allowed": direction_key == "c_to_e",
                "e_to_c_allowed": direction_key == "e_to_c",
                "transport_path_reactions": "; ".join(reaction_labels),
                "transport_path_compartments": " → ".join(compartments),
            }
        )
    return records
