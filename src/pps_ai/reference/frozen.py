"""Hash-pinned loader for the supplied frozen L41 baseline artifact."""

from __future__ import annotations

import hashlib
import importlib
import sys
from types import ModuleType
from pathlib import Path
import zipfile


class FrozenL41Reference:
    def __init__(self, zip_path: str | Path, expected_sha256: str) -> None:
        self.zip_path = Path(zip_path).resolve()
        digest = hashlib.sha256(self.zip_path.read_bytes()).hexdigest()
        if digest != expected_sha256:
            raise ValueError(f"reference ZIP hash differs: {digest}")
        with zipfile.ZipFile(self.zip_path) as archive:
            infos = archive.infolist()
            if len(infos) != 1 or infos[0].filename != "script.py":
                raise ValueError("reference ZIP must contain exactly script.py")
            info = infos[0]
            if info.is_dir() or info.filename.startswith("/") or ".." in Path(info.filename).parts:
                raise ValueError("unsafe reference ZIP member")
            source_bytes = archive.read(info)
        self.script_sha256 = hashlib.sha256(source_bytes).hexdigest()
        module_name = "_pps_frozen_l41_reference"
        existing = sys.modules.get(module_name)
        if existing is None:
            module = ModuleType(module_name)
            module.__file__ = f"{self.zip_path}!/script.py"
            module.__package__ = ""
            sys.modules[module_name] = module
            exec(compile(source_bytes, module.__file__, "exec"), module.__dict__)
            existing = module
        self.entrypoint = existing
        if getattr(existing, "VERSION", None) != "l41-frozen-three-expert-submission-v1":
            raise ValueError("unexpected frozen reference version")
        self.baseline = importlib.import_module("baseline.script")
        self.fact_builder_module = importlib.import_module("dev.fact_builder")
        self.section_module = importlib.import_module("dev.section_extractor")
        self.catalog_module = importlib.import_module("dev.catalog_bge")
        self.pipeline = importlib.import_module("submission.l41_candidate.pipeline")

    def builder(self, data_dir: str | Path):
        return self.fact_builder_module.FactBuilder(str(data_dir))
