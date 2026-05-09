"""Unified PySynth sound selection and rendering API."""

from __future__ import print_function

import importlib
import json
import os
import re
import shlex

from tomita.progress import ProgressConfig


SOUND_MODULES = {
    "a": "tomita.legacy.pysynth",
    "b": "tomita.legacy.pysynth_b",
    "c": "tomita.legacy.pysynth_c",
    "d": "tomita.legacy.pysynth_d",
    "e": "tomita.legacy.pysynth_e",
    "p": "tomita.legacy.pysynth_p",
    "s": "tomita.legacy.pysynth_s",
    "samp": "tomita.legacy.pysynth_samp",
    "beeper": "tomita.legacy.pysynth_beeper",
}

SOUND_DESCRIPTIONS = {
    "a": "flute/organ-like pure-Python PySynth A",
    "b": "piano-like NumPy synth with overlapping note tails",
    "c": "subtractive analog-style saw voice",
    "d": "subtractive analog-style square voice",
    "e": "bright FM e-piano voice",
    "p": "percussive subtractive/noise voice",
    "s": "plucked string voice for guitar, banjo, or harpsichord-like parts",
    "samp": "sample-backed Salamander piano renderer",
    "beeper": "simple ringtone/beeper waveform renderer",
}

SOUND_ALIASES = {
    "default": "a",
    "flute": "a",
    "organ": "a",
    "piano": "b",
    "analog-c": "c",
    "analog-d": "d",
    "analog-p": "p",
    "epiano": "e",
    "e-piano": "e",
    "fm": "e",
    "string": "s",
    "strings": "s",
    "guitar": "s",
    "harpsichord": "s",
    "sample": "samp",
    "sampler": "samp",
    "samples": "samp",
    "beep": "beeper",
}

DEFAULT_CONFIG_FILES = ("pysynth.json", "tomita.json")
LEGACY_SOUND_FLAGS = {
    "--syn_b": "b",
    "--syn_c": "c",
    "--syn_d": "d",
    "--syn_e": "e",
    "--syn_p": "p",
    "--syn_s": "s",
    "--syn_samp": "samp",
}

_NOTE_RE = re.compile(r"^(-?\d+(?:\.\d+)?)([A-Ga-grR][#b]?\d?\*?)$")


class SynthConfig(object):
    """Configuration for selecting a PySynth variant and progress behavior."""

    def __init__(self, sound="a", progress=None, sample_path=None):
        self.sound = normalize_sound(sound)
        self.progress = ProgressConfig.from_value(progress)
        self.sample_path = sample_path

    @classmethod
    def from_file(cls, filename):
        with open(filename) as fh:
            data = json.load(fh)
        return cls(
            sound=data.get("sound", "a"),
            progress=data.get("progress"),
            sample_path=data.get("sample_path"),
        )

    @classmethod
    def from_defaults(cls):
        for filename in DEFAULT_CONFIG_FILES:
            if os.path.exists(filename):
                return cls.from_file(filename)
        return cls()

    def to_dict(self):
        data = {
            "sound": self.sound,
            "progress": {
                "enabled": self.progress.enabled,
                "small_threshold": self.progress.small_threshold,
                "max_updates": self.progress.max_updates,
                "show_time": self.progress.show_time,
            },
        }
        if self.progress.every is not None:
            data["progress"]["every"] = self.progress.every
        if self.progress.percent is not None:
            data["progress"]["percent"] = self.progress.percent
        if self.sample_path:
            data["sample_path"] = self.sample_path
        return data


def available_sounds():
    return sorted(SOUND_MODULES.keys())


def sound_aliases(sound):
    sound = normalize_sound(sound)
    aliases = [alias for alias, value in SOUND_ALIASES.items() if value == sound]
    return sorted(aliases)


def sound_description(sound):
    return SOUND_DESCRIPTIONS[normalize_sound(sound)]


def sound_rows():
    rows = []
    for sound in available_sounds():
        rows.append(
            {
                "sound": sound,
                "description": sound_description(sound),
                "aliases": sound_aliases(sound),
            }
        )
    return rows


def normalize_sound(sound):
    sound = (sound or "a").strip().lower().replace("_", "-")
    sound = SOUND_ALIASES.get(sound, sound)
    if sound not in SOUND_MODULES:
        choices = ", ".join(available_sounds())
        raise ValueError("unknown sound %r; choose one of: %s" % (sound, choices))
    return sound


def get_synth_module(sound):
    return importlib.import_module(SOUND_MODULES[normalize_sound(sound)])


def config_from_args(args):
    args = list(args)
    config_path = None
    for idx, arg in enumerate(args):
        if arg.startswith("--config="):
            config_path = arg.split("=", 1)[1]
        elif arg == "--config" and idx + 1 < len(args):
            config_path = args[idx + 1]

    config = SynthConfig.from_file(config_path) if config_path else SynthConfig.from_defaults()
    sound = config.sound
    sample_path = config.sample_path
    for flag, flag_sound in LEGACY_SOUND_FLAGS.items():
        if flag in args:
            sound = flag_sound
    for idx, arg in enumerate(args):
        if arg.startswith("--sound="):
            sound = arg.split("=", 1)[1]
        elif arg == "--sound" and idx + 1 < len(args):
            sound = args[idx + 1]
        elif arg.startswith("--sample-path="):
            sample_path = arg.split("=", 1)[1]
        elif arg == "--sample-path" and idx + 1 < len(args):
            sample_path = args[idx + 1]
    return SynthConfig(sound=sound, progress=config.progress, sample_path=sample_path)


def make_wav(song, config=None, sound=None, progress=None, **kwargs):
    """Render a song with the configured PySynth variant."""

    config = config or SynthConfig.from_defaults()
    sound = normalize_sound(sound or config.sound)
    progress = config.progress if progress is None else ProgressConfig.from_value(progress)
    sample_path = kwargs.pop("sample_path", None)

    module = get_synth_module(sound)
    kwargs.setdefault("progress", progress)

    if sound == "beeper":
        if "bpm" in kwargs and "tempo" not in kwargs:
            kwargs["tempo"] = kwargs.pop("bpm")
        repeat = int(kwargs.pop("repeat", 0))
        kwargs.pop("boost", None)
        kwargs.pop("pause", None)
        kwargs.pop("leg_stac", None)
        if repeat:
            song = list(song) * (repeat + 1)
    elif sound == "samp" and (sample_path or config.sample_path):
        kwargs.setdefault("sample_path", sample_path or config.sample_path)

    return module.make_wav(song, **kwargs)


def progress_from_options(
    base,
    every=None,
    percent=None,
    max_updates=None,
    small_threshold=None,
    show_time=None,
):
    base = ProgressConfig.from_value(base)
    if (
        every is None
        and percent is None
        and max_updates is None
        and small_threshold is None
        and show_time is None
    ):
        return base
    selected_every = every if every is not None else base.every
    selected_percent = percent if percent is not None else base.percent
    if every is not None:
        selected_percent = None
    if percent is not None:
        selected_every = None
    return ProgressConfig(
        enabled=base.enabled,
        every=selected_every,
        percent=selected_percent,
        max_updates=max_updates if max_updates is not None else base.max_updates,
        small_threshold=(
            small_threshold if small_threshold is not None else base.small_threshold
        ),
        show_time=show_time if show_time is not None else base.show_time,
    )


def parse_song(text):
    """Parse simple interactive PySynth notation like ``4c4 4d4 2e4``."""

    song = []
    for token in shlex.split(text):
        match = _NOTE_RE.match(token)
        if not match:
            raise ValueError("invalid note token %r" % token)
        duration, note = match.groups()
        duration = float(duration)
        if duration.is_integer():
            duration = int(duration)
        note = note.lower()
        if note.startswith("r"):
            note = "r"
        song.append((note, duration))
    return song
