#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from itertools import product

from rdflib import Graph, URIRef, BNode
from rdflib.namespace import RDF, RDFS, OWL


def local_name(uri: URIRef) -> str:
    s = str(uri)
    if "#" in s:
        return s.rsplit("#", 1)[1]
    return s.rstrip("/").rsplit("/", 1)[-1]


def parse_args():
    p = argparse.ArgumentParser(
        description="Convert ontology TTL to EDC eval txt format (clean triples)."
    )
    p.add_argument("--input_ttl", required=True, help="Path to .ttl file")
    p.add_argument("--output_txt", required=True, help="Path to output .txt file")
    p.add_argument(
        "--class_mapping_jsonl",
        default="datasets/intern/gold/leanix_ontology_classes.jsonl",
        help="Optional JSONL with class uri->name mapping",
    )
    p.add_argument(
        "--include_subclass",
        action="store_true",
        help="Also include [ChildClass, subClassOf, ParentClass] triples",
    )
    p.add_argument(
        "--one_line",
        action="store_true",
        help="Write all triples into one line list (default: one line)",
    )
    return p.parse_args()


def load_class_name_map(jsonl_path: str):
    mapping = {}
    p = Path(jsonl_path)
    if not p.exists():
        return mapping

    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            uri = obj.get("uri")
            name = obj.get("name")
            if uri and name:
                mapping[uri] = name

    return mapping


def class_display_name(uri: URIRef, class_name_map: dict) -> str:
    return class_name_map.get(str(uri), local_name(uri))


def get_named_classes(g: Graph):
    classes = set()
    for s in g.subjects(RDF.type, OWL.Class):
        if isinstance(s, URIRef):
            classes.add(s)
    return classes


def get_object_properties(g: Graph):
    props = set()
    for p in g.subjects(RDF.type, OWL.ObjectProperty):
        if isinstance(p, URIRef):
            props.add(p)
    return props


def rdf_list_members(g: Graph, head):
    # Parse RDF collection: (a b c)
    current = head
    while current and current != RDF.nil:
        first = g.value(current, RDF.first)
        if first is None:
            break
        yield first
        current = g.value(current, RDF.rest)


def expand_class_expr_to_named_uris(g: Graph, node, class_uris: set):
    # Handles plain URI class and anonymous unionOf/intersectionOf class expressions.
    if isinstance(node, URIRef):
        return {node} if node in class_uris else set()

    if isinstance(node, BNode):
        out = set()
        for list_pred in (OWL.unionOf, OWL.intersectionOf):
            list_head = g.value(node, list_pred)
            if list_head is None:
                continue
            for member in rdf_list_members(g, list_head):
                if isinstance(member, URIRef) and member in class_uris:
                    out.add(member)
                elif isinstance(member, BNode):
                    out.update(expand_class_expr_to_named_uris(g, member, class_uris))
        return out

    return set()


def collect_domain_range_triples(g: Graph, class_name_map: dict):
    class_uris = get_named_classes(g)
    obj_props = get_object_properties(g)

    triples = []
    for prop in obj_props:
        domains = set()
        ranges = set()

        for d in g.objects(prop, RDFS.domain):
            domains.update(expand_class_expr_to_named_uris(g, d, class_uris))
        for r in g.objects(prop, RDFS.range):
            ranges.update(expand_class_expr_to_named_uris(g, r, class_uris))

        if not domains or not ranges:
            continue

        pred = local_name(prop)
        for d, r in product(sorted(domains, key=str), sorted(ranges, key=str)):
            triples.append([
                class_display_name(d, class_name_map),
                pred,
                class_display_name(r, class_name_map),
            ])

    return triples


def collect_subclass_triples(g: Graph, class_name_map: dict):
    class_uris = get_named_classes(g)
    triples = []
    for child, parent in g.subject_objects(RDFS.subClassOf):
        if isinstance(child, URIRef) and isinstance(parent, URIRef):
            if child in class_uris and parent in class_uris:
                triples.append([
                    class_display_name(child, class_name_map),
                    "subClassOf",
                    class_display_name(parent, class_name_map),
                ])
    return triples


def dedupe_and_sort(triples):
    uniq = {tuple(t) for t in triples}
    return [list(t) for t in sorted(uniq, key=lambda x: (x[0], x[1], x[2]))]


def main():
    args = parse_args()
    class_name_map = load_class_name_map(args.class_mapping_jsonl)

    g = Graph()
    g.parse(args.input_ttl, format="turtle")

    triples = collect_domain_range_triples(g, class_name_map)

    if args.include_subclass:
        triples.extend(collect_subclass_triples(g, class_name_map))

    triples = dedupe_and_sort(triples)

    out = Path(args.output_txt)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8") as f:
        f.write(str(triples) + "\n")

    print(f"Wrote {len(triples)} triples to {out}")


if __name__ == "__main__":
    main()