#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


def load_taxonomy(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def alias_matches(source, alias):
    needle = alias.strip().lower()
    if not needle:
        return False
    if re.fullmatch(r"[a-z0-9 .+/&'-]+", needle):
        pattern = re.escape(needle).replace(r"\ ", r"[\s_-]+")
        return re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", source) is not None
    return needle in source


def normalize(text, taxonomy):
    source = re.sub(r"\s+", " ", text.strip().lower())
    result = {}
    for dimension, groups in taxonomy["dimensions"].items():
        hits = []
        for canonical, aliases in groups.items():
            if any(alias_matches(source, alias) for alias in aliases):
                hits.append(canonical)
        result[dimension] = sorted(set(hits))
    parts = []
    for dimension in ["bag_shape", "material", "function", "scene", "style", "audience"]:
        parts.append("+".join(result[dimension]) or "unknown")
    result["product_signature"] = " × ".join(parts)
    result["source_text"] = text
    return result


def main():
    parser = argparse.ArgumentParser(description="Normalize handbag titles into product signatures")
    parser.add_argument("texts", nargs="*", help="titles or product descriptions")
    parser.add_argument("--input", help="UTF-8 text file, one title per line")
    parser.add_argument("--taxonomy", default=str(Path(__file__).resolve().parents[1] / "references" / "handbag-taxonomy.json"))
    args = parser.parse_args()
    texts = list(args.texts)
    if args.input:
        texts.extend(x.strip() for x in Path(args.input).read_text(encoding="utf-8-sig").splitlines() if x.strip())
    taxonomy = load_taxonomy(args.taxonomy)
    print(json.dumps([normalize(x, taxonomy) for x in texts], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
