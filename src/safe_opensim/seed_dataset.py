from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


REPRESENTATION_PATH_COLUMNS = {
    "g1": "move_g1_mujoco_path",
    "soma_uniform": "move_soma_uniform_path",
    "soma_proportional": "move_soma_proportional_path",
}


@dataclass(frozen=True)
class MotionRecord:
    row: dict[str, str]

    @property
    def filename(self) -> str:
        return self.row.get("filename") or self.row.get("move_name") or ""

    @property
    def move_name(self) -> str:
        return self.row.get("move_name") or self.filename

    @property
    def summary(self) -> str:
        category = self.row.get("category", "")
        package = self.row.get("package", "")
        description = (
            self.row.get("content_short_description")
            or self.row.get("content_natural_desc_1")
            or ""
        )
        parts = [self.filename]
        context = " / ".join(part for part in (package, category) if part)
        if context:
            parts.append(context)
        if description:
            parts.append(description)
        return " | ".join(parts)


class SeedDataset:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.metadata_path = self._find_metadata_csv()

    def rows(self) -> list[MotionRecord]:
        with self.metadata_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            return [MotionRecord(dict(row)) for row in reader]

    def search(self, query: str, *, limit: int = 20) -> list[MotionRecord]:
        needle = query.strip().lower()
        if not needle:
            return self.rows()[:limit]
        matches: list[MotionRecord] = []
        searchable_fields = (
            "filename",
            "move_name",
            "content_name",
            "content_short_description",
            "content_short_description_2",
            "content_natural_desc_1",
            "content_natural_desc_2",
            "content_natural_desc_3",
            "content_natural_desc_4",
            "content_technical_description",
            "category",
            "package",
        )
        for record in self.rows():
            haystack = " ".join(record.row.get(field, "") for field in searchable_fields)
            if needle in haystack.lower():
                matches.append(record)
                if len(matches) >= limit:
                    break
        return matches

    def find_one(self, motion: str) -> MotionRecord:
        needle = motion.strip().lower()
        exact: list[MotionRecord] = []
        partial: list[MotionRecord] = []
        for record in self.rows():
            names = {record.filename.lower(), record.move_name.lower()}
            if needle in names:
                exact.append(record)
            elif needle in " ".join(names):
                partial.append(record)
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            raise ValueError(f"{motion!r} matched {len(exact)} exact metadata rows")
        if len(partial) == 1:
            return partial[0]
        if not partial:
            raise ValueError(f"motion {motion!r} was not found in {self.metadata_path}")
        examples = ", ".join(record.filename for record in partial[:5])
        raise ValueError(f"{motion!r} matched {len(partial)} rows; first matches: {examples}")

    def motion_path(self, record: MotionRecord, representation: str) -> Path:
        normalized = representation.strip().lower()
        if normalized not in REPRESENTATION_PATH_COLUMNS:
            valid = ", ".join(sorted(REPRESENTATION_PATH_COLUMNS))
            raise ValueError(f"representation must be one of {valid}")
        column = REPRESENTATION_PATH_COLUMNS[normalized]
        relative = record.row.get(column, "")
        if not relative:
            relative = self._fallback_relative_path(record, normalized)
        path = self.root / relative
        if not path.exists():
            raise FileNotFoundError(f"{path} does not exist; has the dataset archive been extracted?")
        return path

    def _find_metadata_csv(self) -> Path:
        metadata_dir = self.root / "metadata"
        if not metadata_dir.exists():
            raise FileNotFoundError(f"{metadata_dir} does not exist")
        matches = sorted(metadata_dir.glob("seed_metadata_v*.csv"))
        if not matches:
            raise FileNotFoundError(
                f"no seed_metadata_v*.csv found in {metadata_dir}; download metadata CSV first"
            )
        return matches[-1]

    def _fallback_relative_path(self, record: MotionRecord, representation: str) -> str:
        filename = record.filename
        if not filename:
            raise ValueError("metadata row has no filename or move_name")
        take_date = record.row.get("take_date", "")
        if not take_date:
            raise ValueError(f"metadata row for {filename} has no path column or take_date")
        if representation == "g1":
            return f"g1/csv/{take_date}/{filename}.csv"
        if representation == "soma_uniform":
            return f"soma_uniform/bvh/{take_date}/{filename}.bvh"
        return f"soma_proportional/bvh/{take_date}/{filename}.bvh"
