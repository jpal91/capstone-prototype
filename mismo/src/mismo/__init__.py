"""MISMO v3.4 for the supported URLA subset: the data model and the mapper.

``core`` imports everything it needs from here, not from submodules.
"""

from importlib.util import find_spec

if find_spec("mismo.generated") is None:
    raise ImportError(
        "The MISMO bindings have not been generated. The schema is "
        "license-restricted, so it is not in the repository: download the "
        "MISMO v3.4 Reference Model (Build 324) into mismo/schema/, then run "
        "`just gen-schema` (see mismo/README.md)."
    )

from .convert import to_xml
from .convert.from_xml import MissingError, UnsupportedError, from_xml
from .urla import Urla, UrlaDraft

__all__ = [
    "MissingError",
    "UnsupportedError",
    "Urla",
    "UrlaDraft",
    "from_xml",
    "to_xml",
]
