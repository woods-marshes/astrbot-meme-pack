#!/usr/bin/env python3
"""
AstrBot Meme Pack Manager Script
Helps inspect, validate, and update manifest.json and semantic_metadata.json.
Compatible with AstrBot Meme Pack Protocol (schema v1, semantic metadata v2.0).
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "manifest.json"
SEMANTIC_PATH = ROOT / "semantic_metadata.json"
MEMES_DIR = ROOT / "memes"


def calculate_hashes(file_path: Path, category: str, relative_path: str):
    data = file_path.read_bytes()
    content_sha256 = hashlib.sha256(data).hexdigest().lower()
    entry_payload = f"{content_sha256}\0{category}\0{relative_path}".encode("utf-8")
    entry_id = hashlib.sha256(entry_payload).hexdigest().lower()
    return content_sha256, entry_id


def load_manifest():
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Missing {MANIFEST_PATH}")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_semantic():
    if not SEMANTIC_PATH.exists():
        return None
    return json.loads(SEMANTIC_PATH.read_text(encoding="utf-8"))


def cmd_check(args):
    print("Checking AstrBot meme pack conformance...")
    errors = []
    warnings = []

    # Schema validation with jsonschema if available
    try:
        import jsonschema
        manifest_schema_file = ROOT / "schemas" / "meme-pack-manifest.schema.json"
        semantic_schema_file = ROOT / "schemas" / "meme-pack-semantic.schema.json"
        if manifest_schema_file.exists():
            m_schema = json.loads(manifest_schema_file.read_text(encoding="utf-8"))
            m_inst = load_manifest()
            try:
                jsonschema.validate(instance=m_inst, schema=m_schema)
                print("[OK] manifest.json matches meme-pack-manifest.schema.json")
            except jsonschema.ValidationError as ve:
                errors.append(f"manifest.json schema validation error: {ve.message}")
        if semantic_schema_file.exists() and SEMANTIC_PATH.exists():
            s_schema = json.loads(semantic_schema_file.read_text(encoding="utf-8"))
            s_inst = load_semantic()
            try:
                jsonschema.validate(instance=s_inst, schema=s_schema)
                print("[OK] semantic_metadata.json matches meme-pack-semantic.schema.json")
            except jsonschema.ValidationError as ve:
                errors.append(f"semantic_metadata.json schema validation error: {ve.message}")
    except ImportError:
        pass

    # Check manifest.json
    try:
        manifest = load_manifest()
    except Exception as e:
        print(f"[FAIL] manifest.json error: {e}")
        return 1

    if manifest.get("schema_version") != 1:
        errors.append(f"manifest.schema_version must be 1, got {manifest.get('schema_version')}")

    pack_id = manifest.get("id")
    if not pack_id or not re.match(r"^[a-z0-9][a-z0-9._-]{1,63}$", pack_id):
        errors.append(f"manifest.id invalid: {pack_id}")

    categories = manifest.get("categories", {})
    if not categories:
        errors.append("manifest.categories is empty")

    for cat_name, cat_val in categories.items():
        if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$", cat_name):
            errors.append(f"Invalid category key: {cat_name}")
        if not isinstance(cat_val, dict) or not cat_val.get("description"):
            errors.append(f"Category '{cat_name}' missing non-empty description")

    for preview in manifest.get("previews", []):
        p_path = ROOT / preview
        if not p_path.exists():
            errors.append(f"Referenced preview does not exist: {preview}")

    # Check semantic metadata
    if SEMANTIC_PATH.exists():
        try:
            semantic = load_semantic()
        except Exception as e:
            errors.append(f"semantic_metadata.json json decode error: {e}")
            semantic = None

        if semantic:
            if semantic.get("schema_version") != "2.0":
                errors.append(f"semantic_metadata.schema_version must be '2.0', got {semantic.get('schema_version')}")
            if semantic.get("pack_id") != pack_id:
                errors.append(f"semantic_metadata.pack_id ({semantic.get('pack_id')}) does not match manifest.id ({pack_id})")

            images = semantic.get("images", {})
            for key, item in images.items():
                entry_id = item.get("entry_id")
                if key != entry_id:
                    errors.append(f"Image key '{key}' does not match entry_id '{entry_id}'")

                rel_path = item.get("relative_path", "")
                cat = item.get("category", "")
                full_path = ROOT / rel_path

                if not full_path.exists():
                    errors.append(f"Image file does not exist: {rel_path}")
                    continue

                if cat not in categories:
                    errors.append(f"Image category '{cat}' not defined in manifest.categories")

                expected_rel = f"memes/{cat}/{full_path.name}"
                if rel_path != expected_rel:
                    errors.append(f"Image relative_path '{rel_path}' does not match expected '{expected_rel}'")

                c_sha, e_id = calculate_hashes(full_path, cat, rel_path)
                if c_sha != item.get("content_sha256"):
                    errors.append(f"Content SHA256 mismatch for {rel_path}: expected {c_sha}, got {item.get('content_sha256')}")
                if e_id != entry_id:
                    errors.append(f"Entry ID mismatch for {rel_path}: calculated {e_id}, got {entry_id}")

                if item.get("caption_status") == "done" and not (item.get("caption") and item.get("caption").strip()):
                    errors.append(f"Image '{rel_path}' has caption_status 'done' but caption is empty")

    # Check memes directory
    if not MEMES_DIR.exists():
        errors.append("memes/ directory does not exist")
    else:
        for file_path in MEMES_DIR.rglob("*"):
            if file_path.is_file():
                rel = file_path.relative_to(ROOT).as_posix()
                parts = rel.split("/")
                if len(parts) != 3 or parts[0] != "memes":
                    warnings.append(f"Unexpected file path structure: {rel}")
                else:
                    cat = parts[1]
                    if cat not in categories:
                        warnings.append(f"File {rel} is in category '{cat}' which is not in manifest.json")

    print(f"\nManifest validation:")
    print(f"  Pack ID:    {pack_id}")
    print(f"  Name:       {manifest.get('name')}")
    print(f"  Version:    {manifest.get('version')}")
    print(f"  Categories: {len(categories)}")

    if SEMANTIC_PATH.exists() and semantic:
        print(f"\nSemantic metadata validation:")
        print(f"  Schema:     {semantic.get('schema_version')}")
        print(f"  Annotated:  {len(semantic.get('images', {}))} images")

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  [WARN] {w}")

    if errors:
        print("\nErrors:")
        for err in errors:
            print(f"  [FAIL] {err}")
        return 1
    else:
        print("\n[SUCCESS] Everything conforms to AstrBot Meme Pack Protocol!")
        return 0


def cmd_calc(args):
    img_path = Path(args.image)
    if not img_path.exists():
        print(f"Error: file not found {args.image}")
        return 1
    category = args.category
    rel_path = f"memes/{category}/{img_path.name}"
    c_sha, e_id = calculate_hashes(img_path, category, rel_path)
    print(f"Image:          {img_path.name}")
    print(f"Category:       {category}")
    print(f"Relative Path:  {rel_path}")
    print(f"content_sha256: {c_sha}")
    print(f"entry_id:       {e_id}")
    return 0


def cmd_sync(args):
    manifest = load_manifest()
    pack_id = manifest.get("id")
    categories = manifest.get("categories", {})

    semantic = load_semantic() or {
        "schema_version": "2.0",
        "pack_id": pack_id,
        "images": {}
    }
    semantic["pack_id"] = pack_id
    images = semantic.setdefault("images", {})

    modified = False
    for cat_dir in sorted(MEMES_DIR.iterdir()):
        if not cat_dir.is_dir():
            continue
        cat = cat_dir.name
        if cat not in categories:
            print(f"Skipping unregistered category dir: {cat}")
            continue

        for img_file in sorted(cat_dir.iterdir()):
            if not img_file.is_file() or img_file.name.startswith("."):
                continue

            rel_path = f"memes/{cat}/{img_file.name}"
            c_sha, e_id = calculate_hashes(img_file, cat, rel_path)

            if e_id not in images:
                # Find if there was an old entry with different hash or path
                print(f"[NEW] Found image not yet in semantic metadata: {rel_path}")
                if args.add_placeholders:
                    images[e_id] = {
                        "entry_id": e_id,
                        "content_sha256": c_sha,
                        "relative_path": rel_path,
                        "category": cat,
                        "caption": "",
                        "caption_status": "pending",
                        "tags": [],
                        "visible_text": ""
                    }
                    modified = True

    if modified:
        SEMANTIC_PATH.write_text(json.dumps(semantic, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Updated {SEMANTIC_PATH.name}")
    else:
        print("No changes written. (Use --add-placeholders to add pending entries for unannotated images)")
    return 0


def main():
    parser = argparse.ArgumentParser(description="AstrBot Meme Pack Management Utility")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("check", help="Validate manifest and semantic metadata")

    calc_p = subparsers.add_parser("calc", help="Calculate hashes for an image")
    calc_p.add_argument("image", help="Path to image file")
    calc_p.add_argument("category", help="Category name")

    sync_p = subparsers.add_parser("sync", help="Scan memes and sync semantic metadata")
    sync_p.add_argument("--add-placeholders", action="store_true", help="Add pending placeholder entries for images missing metadata")

    args = parser.parse_args()
    if args.command == "check" or not args.command:
        sys.exit(cmd_check(args))
    elif args.command == "calc":
        sys.exit(cmd_calc(args))
    elif args.command == "sync":
        sys.exit(cmd_sync(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
