"""dinostomp: build evals fast; everything gets stomped before it gets believed."""

from dinostomp.spec import (
    SCHEMA_NAMES,
    Issue,
    load_schema,
    load_spec,
    spec_sha256,
    validate_obj,
)

__version__ = "0.57.1"

__all__ = [
    "SCHEMA_NAMES",
    "Issue",
    "load_schema",
    "load_spec",
    "spec_sha256",
    "validate_obj",
    "__version__",
]
