"""Validate the size and checksum of a downloaded FIT file."""

_CRC_TABLE = (
    0,
    0xCC01,
    0xD801,
    0x1400,
    0xF001,
    0x3C00,
    0x2800,
    0xE401,
    0xA001,
    0x6C00,
    0x7800,
    0xB401,
    0x5000,
    0x9C01,
    0x8801,
    0x4400,
)


def validate_fit(content: bytes) -> None:
    """Reject incomplete FIT files and files with an invalid file checksum."""
    if (
        len(content) < 14
        or content[0] < 12
        or content[1] < 0x10
        or content[8:12] != b".FIT"
    ):
        raise ValueError("Garmin archive contains invalid FIT data")
    size = int.from_bytes(content[4:8], "little")
    if not size or len(content) != content[0] + size + 2:
        raise ValueError("Garmin archive contains incomplete FIT data")
    crc = 0
    for byte in content[:-2]:
        crc = ((crc >> 4) & 0xFFF) ^ _CRC_TABLE[crc & 0xF] ^ _CRC_TABLE[byte & 0xF]
        crc = ((crc >> 4) & 0xFFF) ^ _CRC_TABLE[crc & 0xF] ^ _CRC_TABLE[byte >> 4]
    if crc != int.from_bytes(content[-2:], "little"):
        raise ValueError("Garmin archive contains a FIT checksum error")
