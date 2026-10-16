from .urla import Urla


def to_csv(urla: Urla) -> bytes:
    return b""


def validate(xml: bytes) -> None:
    pass


def from_xml(xml: bytes) -> Urla:
    return Urla()
