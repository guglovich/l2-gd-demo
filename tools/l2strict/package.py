"""Strict reader for Lineage 2 UE2 package tables and object references."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .errors import BoundsError, PackageError, ReferenceError
from .reader import Reader

PACKAGE_MAGIC = 0x9E2A83C1
RF_HAS_STACK = 0x02000000


@dataclass(slots=True)
class NameEntry:
    text: str
    flags: int


@dataclass(slots=True)
class ImportEntry:
    class_package: int
    class_name: int
    package_index: int
    object_name: int


@dataclass(slots=True)
class ExportEntry:
    class_index: int
    super_index: int
    package_index: int
    object_name: int
    object_flags: int
    serial_size: int
    serial_offset: int


@dataclass(slots=True)
class ResolvedRef:
    ref: int
    kind: str
    package: str | None
    outer_package: str | None
    object: str
    class_name: str
    outer_chain: list[str] = field(default_factory=list)
    export_index: int | None = None
    import_index: int | None = None


@dataclass(slots=True)
class Package:
    data: bytes
    path: str | None = None
    tag: int = 0
    version: int = 0
    licensee: int = 0
    flags: int = 0
    names: list[NameEntry] = field(default_factory=list)
    imports: list[ImportEntry] = field(default_factory=list)
    exports: list[ExportEntry] = field(default_factory=list)
    header_guid: bytes = b""
    _name_count: int = field(default=0, repr=False)
    _name_offset: int = field(default=0, repr=False)
    _import_count: int = field(default=0, repr=False)
    _import_offset: int = field(default=0, repr=False)
    _export_count: int = field(default=0, repr=False)
    _export_offset: int = field(default=0, repr=False)

    @classmethod
    def from_bytes(cls, data: bytes, path: str | None = None) -> "Package":
        self = cls(data=data, path=path)
        self._read_summary()
        self._read_names()
        self._read_imports()
        self._read_exports()
        self._validate_tables()
        return self

    @classmethod
    def from_file(cls, path: str) -> "Package":
        with open(path, "rb") as fp:
            data = fp.read()
        return cls.from_bytes(data, path)

    @property
    def stem(self) -> str:
        if self.path:
            return Path(self.path).stem
        return "package"

    @property
    def package_name(self) -> str:
        return self.stem

    @property
    def size(self) -> int:
        return len(self.data)

    @property
    def name_count(self) -> int:
        return len(self.names)

    @property
    def import_count(self) -> int:
        return len(self.imports)

    @property
    def export_count(self) -> int:
        return len(self.exports)

    def _read_summary(self) -> None:
        if len(self.data) < 52:
            raise PackageError(f"{self.path or '<bytes>'}: package too short")
        r = Reader(self.data, 0, context=f"{self.path or '<bytes>'} summary")
        self.tag = r.u32()
        if self.tag != PACKAGE_MAGIC:
            raise PackageError(
                f"{self.path or '<bytes>'}: bad package magic 0x{self.tag:08X}"
            )
        self.version = r.u16()
        self.licensee = r.u16()
        self.flags = r.u32()
        name_count = r.i32()
        name_offset = r.i32()
        export_count = r.i32()
        export_offset = r.i32()
        import_count = r.i32()
        import_offset = r.i32()
        self.header_guid = r.take(16)
        for label, count, offset in (
            ("names", name_count, name_offset),
            ("imports", import_count, import_offset),
            ("exports", export_count, export_offset),
        ):
            if count < 0 or count > 10_000_000:
                raise PackageError(
                    f"{self.path or '<bytes>'}: invalid {label} count {count}"
                )
            if offset < 0 or offset > len(self.data):
                raise PackageError(
                    f"{self.path or '<bytes>'}: invalid {label} offset 0x{offset:X}"
                )
        self._name_count = name_count
        self._name_offset = name_offset
        self._import_count = import_count
        self._import_offset = import_offset
        self._export_count = export_count
        self._export_offset = export_offset

    def _read_names(self) -> None:
        r = Reader(
            self.data,
            self._name_offset,
            context=f"{self.path or '<bytes>'} name table",
        )
        names: list[NameEntry] = []
        for i in range(self._name_count):
            length = r.u8()
            if length == 0xFF:
                signed = r.i32()
                n = abs(signed)
                if n > 4096:
                    raise PackageError(
                        f"{self.path or '<bytes>'}: name {i} length {n} is implausible"
                    )
                raw = r.take(n * 2)
                if raw.endswith(b"\x00\x00"):
                    raw = raw[:-2]
                text = raw.decode("utf-16-le", "replace")
            else:
                raw = r.take(length)
                if raw.endswith(b"\x00"):
                    raw = raw[:-1]
                text = raw.decode("latin-1", "replace")
            if len(text) > 4096:
                raise PackageError(
                    f"{self.path or '<bytes>'}: name {i} is implausibly long"
                )
            names.append(NameEntry(text=text, flags=r.u32()))
        self.names = names

    def _read_imports(self) -> None:
        r = Reader(
            self.data,
            self._import_offset,
            context=f"{self.path or '<bytes>'} import table",
        )
        imports: list[ImportEntry] = []
        for i in range(self._import_count):
            imports.append(
                ImportEntry(
                    class_package=r.compact(),
                    class_name=r.compact(),
                    package_index=r.i32(),
                    object_name=r.compact(),
                )
            )
        self.imports = imports

    def _read_exports(self) -> None:
        r = Reader(
            self.data,
            self._export_offset,
            context=f"{self.path or '<bytes>'} export table",
        )
        exports: list[ExportEntry] = []
        for i in range(self._export_count):
            class_index = r.compact()
            super_index = r.compact()
            package_index = r.i32()
            object_name = r.compact()
            object_flags = r.u32()
            serial_size = r.compact()
            serial_offset = r.compact() if serial_size > 0 else 0
            exports.append(
                ExportEntry(
                    class_index=class_index,
                    super_index=super_index,
                    package_index=package_index,
                    object_name=object_name,
                    object_flags=object_flags,
                    serial_size=serial_size,
                    serial_offset=serial_offset,
                )
            )
        self.exports = exports

    def _validate_tables(self) -> None:
        for i, imp in enumerate(self.imports):
            for label, idx in (
                ("class_package", imp.class_package),
                ("class_name", imp.class_name),
                ("object_name", imp.object_name),
            ):
                if idx < 0 or idx >= len(self.names):
                    raise PackageError(
                        f"{self.path or '<bytes>'}: import {i} {label} name "
                        f"index {idx} out of range"
                    )
            if imp.package_index > len(self.exports):
                raise PackageError(
                    f"{self.path or '<bytes>'}: import {i} package_index "
                    f"{imp.package_index} out of range"
                )
            if imp.package_index < -len(self.imports):
                raise PackageError(
                    f"{self.path or '<bytes>'}: import {i} package_index "
                    f"{imp.package_index} out of range"
                )
        for i, exp in enumerate(self.exports):
            if exp.object_name < 0 or exp.object_name >= len(self.names):
                raise PackageError(
                    f"{self.path or '<bytes>'}: export {i} object name index "
                    f"{exp.object_name} out of range"
                )
            if exp.class_index > len(self.exports) or exp.class_index < -len(
                self.imports
            ):
                raise PackageError(
                    f"{self.path or '<bytes>'}: export {i} class index "
                    f"{exp.class_index} out of range"
                )
            if exp.serial_size < 0:
                raise PackageError(
                    f"{self.path or '<bytes>'}: export {i} negative serial size"
                )
            if exp.serial_size:
                end = exp.serial_offset + exp.serial_size
                if exp.serial_offset < 0 or end > len(self.data):
                    raise BoundsError(
                        f"{self.path or '<bytes>'}: export {i} serial range "
                        f"0x{exp.serial_offset:X}+0x{exp.serial_size:X} "
                        f"exceeds package size 0x{len(self.data):X}"
                    )

    # ---- names and references ------------------------------------------------

    def name(self, index: int) -> str:
        if index < 0 or index >= len(self.names):
            raise ReferenceError(
                f"{self.path or '<bytes>'}: name index {index} out of range "
                f"({len(self.names)} names)"
            )
        return self.names[index].text

    def name_or_none(self, index: int) -> str | None:
        if 0 <= index < len(self.names):
            return self.names[index].text
        return None

    def object_name_of_ref(self, ref: int) -> str | None:
        if ref == 0:
            return None
        if ref > 0:
            idx = ref - 1
            if idx >= len(self.exports):
                raise ReferenceError(
                    f"{self.path or '<bytes>'}: export ref {ref} out of range"
                )
            return self.name(self.exports[idx].object_name)
        idx = -ref - 1
        if idx >= len(self.imports):
            raise ReferenceError(
                f"{self.path or '<bytes>'}: import ref {ref} out of range"
            )
        return self.name(self.imports[idx].object_name)

    def class_name_of_ref(self, ref: int) -> str:
        """Return the class object's name for a class index ``ref``."""
        obj = self.object_name_of_ref(ref)
        if obj is None:
            raise ReferenceError(
                f"{self.path or '<bytes>'}: null class reference"
            )
        return obj

    def class_name_of_export(self, export_index: int) -> str:
        exp = self.exports[export_index]
        return self.class_name_of_ref(exp.class_index)

    def class_name_of_import(self, import_index: int) -> str:
        return self.name(self.imports[import_index].class_name)

    def outer_chain(self, package_index: int) -> list[tuple[str, str]]:
        """Return ``(object_name, class_name)`` for each outer object."""
        chain: list[tuple[str, str]] = []
        cur = package_index
        seen: set[int] = set()
        while cur != 0:
            key = cur
            if key in seen:
                raise ReferenceError(
                    f"{self.path or '<bytes>'}: cyclic outer chain at {cur}"
                )
            seen.add(key)
            if cur < 0:
                idx = -cur - 1
                if idx >= len(self.imports):
                    raise ReferenceError(
                        f"{self.path or '<bytes>'}: outer import {cur} out of range"
                    )
                imp = self.imports[idx]
                chain.append(
                    (
                        self.name(imp.object_name),
                        self.class_name_of_import(idx),
                    )
                )
                cur = imp.package_index
            else:
                idx = cur - 1
                if idx >= len(self.exports):
                    raise ReferenceError(
                        f"{self.path or '<bytes>'}: outer export {cur} out of range"
                    )
                exp = self.exports[idx]
                chain.append(
                    (
                        self.name(exp.object_name),
                        self.class_name_of_export(idx),
                    )
                )
                cur = exp.package_index
        return chain

    def resolve_ref(self, ref: int) -> ResolvedRef | None:
        if ref == 0:
            return None
        if ref > 0:
            idx = ref - 1
            if idx >= len(self.exports):
                raise ReferenceError(
                    f"{self.path or '<bytes>'}: export ref {ref} out of range"
                )
            exp = self.exports[idx]
            return ResolvedRef(
                ref=ref,
                kind="export",
                package=self.package_name,
                outer_package=None,
                object=self.name(exp.object_name),
                class_name=self.class_name_of_export(idx),
                export_index=idx,
            )

        idx = -ref - 1
        if idx >= len(self.imports):
            raise ReferenceError(
                f"{self.path or '<bytes>'}: import ref {ref} out of range"
            )
        imp = self.imports[idx]
        chain = self.outer_chain(imp.package_index)
        package_chain = [name for name, cls in chain if cls == "Package"]
        outer_package = package_chain[-1] if package_chain else (
            chain[-1][0] if chain else None
        )
        return ResolvedRef(
            ref=ref,
            kind="import",
            package=outer_package,
            outer_package=outer_package,
            object=self.name(imp.object_name),
            class_name=self.class_name_of_import(idx),
            outer_chain=[name for name, _ in chain],
            import_index=idx,
        )

    def export_data(self, export_index: int) -> bytes:
        exp = self.exports[export_index]
        if exp.serial_size == 0:
            return b""
        end = exp.serial_offset + exp.serial_size
        if end > len(self.data):
            raise BoundsError(
                f"{self.path or '<bytes>'}: export {export_index} data out of range"
            )
        return self.data[exp.serial_offset:end]

    def export_by_name(
        self, name: str, class_name: str | None = None,
        on_ambiguous: str = "raise",
    ) -> int | None:
        found = []
        for i, exp in enumerate(self.exports):
            if self.name(exp.object_name) != name:
                continue
            if class_name is not None and self.class_name_of_export(i) != class_name:
                continue
            found.append(i)
        if not found:
            return None
        if len(found) > 1:
            classes = [self.class_name_of_export(i) for i in found]
            if on_ambiguous == "first":
                # DEVLOG-108: the L2 duplicate-name quirk (two Texture
                # exports sharing one name; the payloads differed by 28
                # bytes in the small-mip tails only). UE2 name binding
                # resolves the FIRST export — follow it, loudly.
                print(f"WARN {self.path or '<bytes>'}: object {name!r} is "
                      f"ambiguous {classes} — using the first export "
                      f"{found[0]} (UE2 name binding)")
                return found[0]
            raise PackageError(
                f"{self.path or '<bytes>'}: object {name!r} is ambiguous "
                f"({classes})"
            )
        return found[0]

    def summary(self) -> dict:
        return {
            "path": os.path.abspath(self.path) if self.path else None,
            "package": self.package_name,
            "version": self.version,
            "licensee": self.licensee,
            "flags": self.flags,
            "names": len(self.names),
            "imports": len(self.imports),
            "exports": len(self.exports),
            "size": len(self.data),
        }


class PackageSet:
    """A case-insensitive set of decrypted packages and object lookup."""

    def __init__(self) -> None:
        self._by_alias: dict[str, Package] = {}
        self._packages: list[Package] = []

    def add(self, package: Package) -> None:
        self._packages.append(package)
        aliases = {package.stem.casefold()}
        if package.path:
            aliases.add(Path(package.path).stem.casefold())
            aliases.add(Path(package.path).name.casefold())
        for alias in aliases:
            old = self._by_alias.get(alias)
            if old is not None and old is not package:
                # Identical names in different directories are ambiguous.  Keep
                # the first one and let explicit path-based staging resolve it.
                continue
            self._by_alias[alias] = package

    def add_path(self, path: str) -> Package:
        package = Package.from_file(path)
        self.add(package)
        return package

    def add_directory(self, root: str, subdirs: tuple[str, ...] = ()) -> None:
        for subdir in subdirs:
            folder = os.path.join(root, subdir)
            if not os.path.isdir(folder):
                continue
            for name in sorted(os.listdir(folder)):
                if name.lower().endswith((".unr", ".usx", ".utx", ".ukx")):
                    self.add_path(os.path.join(folder, name))

    def packages(self) -> list[Package]:
        return list(self._packages)

    def get(self, name_or_path: str) -> Package | None:
        key = Path(name_or_path).stem.casefold()
        package = self._by_alias.get(key)
        if package is not None:
            return package
        if os.path.isfile(name_or_path):
            package = Package.from_file(name_or_path)
            self.add(package)
            return package
        return None

    def require(self, name: str) -> Package:
        package = self.get(name)
        if package is None:
            raise PackageError(f"package not staged/loaded: {name}")
        return package

    def find_object(
        self,
        owner: str | None,
        object_name: str,
        class_name: str | None = None,
    ) -> tuple[Package, int]:
        candidates: list[tuple[Package, int]] = []
        # Texture references use UE2 first-match name binding (the
        # duplicate-name quirk, DEVLOG-108); everything else stays strict.
        mode = "first" if class_name == "Texture" else "raise"
        if owner:
            package = self.get(owner)
            if package is not None:
                idx = package.export_by_name(object_name, class_name, mode)
                if idx is not None:
                    return package, idx
                # Some L2 imports name a group package that is only an alias
                # for the file package.  Fall through to the global search.
        for package in self._packages:
            idx = package.export_by_name(object_name, class_name, mode)
            if idx is not None:
                candidates.append((package, idx))
        if len(candidates) == 1:
            return candidates[0]
        if not candidates:
            raise PackageError(
                f"object not found: owner={owner!r} object={object_name!r} "
                f"class={class_name!r}"
            )
        names = [p.package_name for p, _ in candidates]
        raise PackageError(
            f"object is ambiguous: owner={owner!r} object={object_name!r} "
            f"class={class_name!r} candidates={names}"
        )

    def resolve(
        self, source_package: Package, ref: int
    ) -> tuple[ResolvedRef, Package | None, int | None]:
        resolved = source_package.resolve_ref(ref)
        if resolved is None:
            return resolved, None, None  # type: ignore[return-value]
        if resolved.kind == "export":
            return resolved, source_package, resolved.export_index
        package, idx = self.find_object(
            resolved.package, resolved.object, resolved.class_name
        )
        return resolved, package, idx

    def summary(self) -> list[dict]:
        return [p.summary() for p in self._packages]
