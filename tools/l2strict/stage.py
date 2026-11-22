"""Stage and decrypt only the packages required by one L2 map."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from .crypto import decrypt
from .errors import StageError

CATEGORIES = {
    ".unr": "MAPS",
    ".usx": "StaticMeshes",
    ".utx": "Textures",
    ".ukx": "Animations",
}


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(slots=True)
class SourceIndex:
    root: str
    _by_name: dict[str, str]

    @classmethod
    def scan(cls, root: str) -> "SourceIndex":
        by_name: dict[str, str] = {}
        for category in ("MAPS", "StaticMeshes", "Textures", "Animations"):
            folder = os.path.join(root, category)
            if not os.path.isdir(folder):
                continue
            for entry in sorted(os.listdir(folder)):
                path = os.path.join(folder, entry)
                if not os.path.isfile(path):
                    continue
                ext = os.path.splitext(entry)[1].lower()
                if ext not in CATEGORIES:
                    continue
                key = entry.casefold()
                if key in by_name and by_name[key] != path:
                    raise StageError(f"ambiguous source package name: {entry}")
                by_name[key] = path
        return cls(root=root, _by_name=by_name)

    def find(self, name: str, category: str | None = None) -> str:
        request = name.strip()
        if not request:
            raise StageError("empty package name")
        candidates = [request, f"{request}.unr", f"{request}.usx", f"{request}.utx"]
        for candidate in candidates:
            path = self._by_name.get(candidate.casefold())
            if path is None:
                continue
            if category is not None:
                ext = os.path.splitext(path)[1].lower()
                if CATEGORIES[ext] != category:
                    continue
            return path
        raise StageError(
            f"source package not found for {name!r}"
            + (f" in {category}" if category else "")
        )


class Stager:
    def __init__(self, source_root: str, destination_root: str) -> None:
        self.source_root = os.path.abspath(source_root)
        self.destination_root = os.path.abspath(destination_root)
        self.index = SourceIndex.scan(self.source_root)
        self.entries: dict[str, dict] = {}
        self.manifest_path = os.path.join(self.destination_root, "manifest.json")
        if os.path.isfile(self.manifest_path):
            with open(self.manifest_path, "r", encoding="utf-8") as fp:
                previous = json.load(fp)
            for entry in previous.get("files", []):
                key = Path(entry["source"]).stem.casefold()
                self.entries[key] = entry

    def stage(self, name: str, *, category: str | None = None) -> str:
        try:
            source = self.index.find(name, category)
        except StageError:
            if category is None:
                raise
            # DEVLOG-136 (the 20_19 build): some L2 mesh packages carry
            # their MATERIALS inside the StaticMesh package itself
            # (Field_Deco_Artifact_s), so material staging requests the
            # mesh name with the Textures category. The category is a
            # PREFERENCE, not a filter: fall back to the package's actual
            # category — PackageSet reads every staged category, and the
            # texture-resolution pass still catches real absences.
            source = self.index.find(name)
        ext = os.path.splitext(source)[1].lower()
        actual_category = CATEGORIES[ext]
        relative = os.path.join(actual_category, os.path.basename(source))
        output = os.path.join(self.destination_root, relative)

        with open(source, "rb") as fp:
            raw = fp.read()
        plain, crypt_version, key = decrypt(raw, os.path.basename(source))
        os.makedirs(os.path.dirname(output), exist_ok=True)
        with open(output, "wb") as fp:
            fp.write(plain)

        request_key = Path(source).stem.casefold()
        entry = {
            "request": name,
            "category": actual_category,
            "source": source,
            "output": output,
            "source_size": len(raw),
            "output_size": len(plain),
            "source_sha256": _sha256(source),
            "output_sha256": _sha256(output),
            "crypt_version": crypt_version,
            "xor_key": key,
        }
        self.entries[request_key] = entry
        return output

    def stage_many(self, names, *, category: str | None = None) -> list[str]:
        outputs = []
        for name in names:
            outputs.append(self.stage(name, category=category))
        return outputs

    def save_manifest(self) -> str:
        os.makedirs(self.destination_root, exist_ok=True)
        manifest = {
            "schema": 1,
            "source_root": self.source_root,
            "destination_root": self.destination_root,
            "files": [self.entries[key] for key in sorted(self.entries)],
        }
        with open(self.manifest_path, "w", encoding="utf-8") as fp:
            json.dump(manifest, fp, indent=2)
            fp.write("\n")
        return self.manifest_path
