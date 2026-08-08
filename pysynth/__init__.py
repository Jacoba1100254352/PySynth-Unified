"""Public PySynth compatibility facade."""

from tomita import SynthConfig, __version__, available_sounds, make_wav, parse_song
from tomita.progress import ProgressConfig

__all__ = [
    "ProgressConfig",
    "SynthConfig",
    "__version__",
    "available_sounds",
    "make_wav",
    "parse_song",
]
