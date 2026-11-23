"""Experimental media protocol laboratory for constrained mesh networks."""

__version__ = "0.1.0"

from .application.pipeline import ImagePipeline, TransmissionResult
from .media import ImageMetadata

__all__ = ["ImageMetadata", "ImagePipeline", "TransmissionResult", "__version__"]
