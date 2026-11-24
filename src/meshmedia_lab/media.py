"""Shared media metadata used by codecs and transport packets."""

from dataclasses import dataclass

PROTOCOL_VERSION = 1
MEDIA_TYPE_IMAGE = 0x01
CODEC_GRAYSCALE_PACKED = 0x01
CODEC_RGB332 = 0x02
MAX_IMAGE_WIDTH = 128
MAX_IMAGE_HEIGHT = 128


@dataclass(frozen=True, slots=True)
class ImageMetadata:
    """Parameters required by a receiver to decode an image payload."""

    width: int
    height: int
    levels: int
    version: int = PROTOCOL_VERSION
    media_type: int = MEDIA_TYPE_IMAGE
    codec: int = CODEC_GRAYSCALE_PACKED

    def __post_init__(self) -> None:
        if not 1 <= self.width <= MAX_IMAGE_WIDTH:
            raise ValueError(f"width must be between 1 and {MAX_IMAGE_WIDTH}")
        if not 1 <= self.height <= MAX_IMAGE_HEIGHT:
            raise ValueError(f"height must be between 1 and {MAX_IMAGE_HEIGHT}")
        if self.codec == CODEC_RGB332:
            if self.levels != 0:
                raise ValueError("RGB332 metadata must use levels=0")
        elif not 2 <= self.levels <= 256 or self.levels & (self.levels - 1):
            raise ValueError(
                "levels must be a power of two between 2 and 256, "
                "or 0 for RGB332"
            )
        if not 0 <= self.version <= 0xFF:
            raise ValueError("version must fit in 1 byte")
        if not 0 <= self.media_type <= 0xFF:
            raise ValueError("media_type must fit in 1 byte")
        if not 0 <= self.codec <= 0xFF:
            raise ValueError("codec must fit in 1 byte")
