"""Public PySynth compatibility facade."""

from tomita import SynthConfig, available_sounds, make_wav, parse_song
from tomita.progress import ProgressConfig

__all__ = [
    "ProgressConfig",
    "SynthConfig",
    "available_sounds",
    "make_wav",
    "parse_song",
]
