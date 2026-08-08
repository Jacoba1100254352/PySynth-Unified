"""Unified PySynth sound selection and rendering API."""

from __future__ import print_function

import importlib
import json
import math
import numbers
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

_NOTE_RE = re.compile(r"^(-?\d+(?:\.\d+)?)((?:[rR]|[A-Ga-g][#b]?\d?)\*?)$")
_NOTE_NAME_RE = re.compile(r"^(?:r|[a-g](?:#|b)?\d?)(?:\*)?$")
_CONFIG_KEYS = frozenset(("sound", "progress", "sample_path"))


class SynthConfig(object):
    """Configuration for selecting a PySynth variant and progress behavior."""

    def __init__(self, sound="a", progress=None, sample_path=None):
        self.sound = normalize_sound(sound)
        self.progress = ProgressConfig.from_value(progress)
        self.sample_path = _normalize_sample_path(sample_path)

    @classmethod
    def from_mapping(cls, data, source="config"):
        if not isinstance(data, dict):
            raise ValueError("%s must be a JSON object" % source)
        unknown = sorted(str(key) for key in data if key not in _CONFIG_KEYS)
        if unknown:
            raise ValueError(
                "%s has unknown option%s: %s"
                % (source, "s" if len(unknown) > 1 else "", ", ".join(unknown))
            )
        return cls(
            sound=data.get("sound", "a"),
            progress=data.get("progress"),
            sample_path=data.get("sample_path"),
        )

    @classmethod
    def from_file(cls, filename):
        with open(filename, encoding="utf-8") as fh:
            data = json.load(fh)
        return cls.from_mapping(data, "config file %s" % filename)

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
    if sound is None:
        sound = "a"
    if not isinstance(sound, str):
        raise ValueError("sound must be a string")
    sound = sound.strip().lower().replace("_", "-")
    sound = SOUND_ALIASES.get(sound, sound)
    if sound not in SOUND_MODULES:
        choices = ", ".join(available_sounds())
        raise ValueError("unknown sound %r; choose one of: %s" % (sound, choices))
    return sound


def get_synth_module(sound):
    return importlib.import_module(SOUND_MODULES[normalize_sound(sound)])


def _normalize_sample_path(value):
    if value is None:
        return None
    try:
        value = os.fsdecode(os.fspath(value))
    except TypeError:
        raise ValueError("sample_path must be a path string") from None
    return value or None


def _normalize_duration(value, position):
    if isinstance(value, bool) or isinstance(value, (str, bytes)):
        raise ValueError("duration at position %u must be a number" % position)
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("duration at position %u must be a number" % position) from None
    if not math.isfinite(value) or value == 0:
        raise ValueError("duration at position %u must be finite and non-zero" % position)
    if value < 0:
        value = -2.0 * value / 3.0
    return int(value) if value.is_integer() else value


def _enharmonic_sharp(note):
    match = re.match(r"^([a-g])([#b]?)(\d)$", note)
    if not match:
        return note
    letter, accidental, octave = match.groups()
    semitone = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}[letter]
    semitone += {"": 0, "#": 1, "b": -1}[accidental]
    midi_note = (int(octave) + 1) * 12 + semitone
    names = ("c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b")
    return "%s%u" % (names[midi_note % 12], midi_note // 12 - 1)


def _prepare_song(song, sound, module):
    if isinstance(song, (str, bytes)):
        raise ValueError("song must be an iterable of (note, duration) pairs")
    try:
        raw_song = list(song)
    except TypeError:
        raise ValueError("song must be an iterable of (note, duration) pairs") from None
    if not raw_song:
        raise ValueError("song must contain at least one note")

    pitch_table = getattr(module, "pitchhz", getattr(module, "PITCHHZ", None))
    prepared = []
    for position, item in enumerate(raw_song, 1):
        if isinstance(item, (str, bytes)):
            raise ValueError("song item %u must be a (note, duration) pair" % position)
        try:
            note, duration = item
        except (TypeError, ValueError):
            raise ValueError(
                "song item %u must be a (note, duration) pair" % position
            ) from None
        if not isinstance(note, str):
            raise ValueError("note at position %u must be a string" % position)
        note = note.strip().lower()
        if not _NOTE_NAME_RE.match(note):
            raise ValueError("invalid note %r at position %u" % (note, position))

        accented = note.endswith("*")
        base_note = note[:-1] if accented else note
        if base_note == "r":
            normalized_note = "r"
        else:
            if not base_note[-1].isdigit():
                base_note += "4"
            normalized_note = base_note
            if pitch_table is not None and normalized_note not in pitch_table:
                equivalent = _enharmonic_sharp(normalized_note)
                if equivalent in pitch_table:
                    normalized_note = equivalent
                else:
                    raise ValueError(
                        "note %r at position %u is outside sound %s's range"
                        % (note, position, sound)
                    )
            if accented:
                normalized_note += "*"
        prepared.append((normalized_note, _normalize_duration(duration, position)))
    return prepared


def _positive_number(name, value):
    if isinstance(value, bool) or isinstance(value, (str, bytes)):
        raise ValueError("%s must be a positive number" % name)
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("%s must be a positive number" % name) from None
    if not math.isfinite(value) or value <= 0:
        raise ValueError("%s must be a positive number" % name)
    return value


def _nonnegative_integer(name, value):
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise ValueError("%s must be a non-negative integer" % name)
    if value < 0:
        raise ValueError("%s must be a non-negative integer" % name)
    return int(value)


def config_from_args(args):
    args = list(args)
    config_path = None
    for idx, arg in enumerate(args):
        if arg.startswith("--config="):
            config_path = arg.split("=", 1)[1]
        elif arg == "--config" and idx + 1 < len(args):
            config_path = args[idx + 1]

    config = (
        SynthConfig.from_file(config_path)
        if config_path
        else SynthConfig.from_defaults()
    )
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

    if config is None:
        config = SynthConfig.from_defaults()
    elif isinstance(config, dict):
        config = SynthConfig.from_mapping(config)
    elif not isinstance(config, SynthConfig):
        raise TypeError("config must be a SynthConfig or mapping")
    sound = normalize_sound(config.sound if sound is None else sound)
    progress = config.progress if progress is None else ProgressConfig.from_value(progress)
    sample_path = _normalize_sample_path(kwargs.pop("sample_path", None))

    module = get_synth_module(sound)
    song = _prepare_song(song, sound, module)
    kwargs.setdefault("progress", progress)
    for tempo_name in ("bpm", "tempo"):
        if tempo_name in kwargs:
            kwargs[tempo_name] = _positive_number(tempo_name, kwargs[tempo_name])
    if "repeat" in kwargs:
        kwargs["repeat"] = _nonnegative_integer("repeat", kwargs["repeat"])

    if sound == "beeper":
        if "bpm" in kwargs:
            kwargs.setdefault("tempo", kwargs["bpm"])
            kwargs.pop("bpm")
        repeat = kwargs.pop("repeat", 0)
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
        if duration == 0:
            raise ValueError("note duration must be non-zero in token %r" % token)
        if duration.is_integer():
            duration = int(duration)
        note = note.lower()
        if note.startswith("r"):
            note = "r"
        song.append((note, duration))
    if not song:
        raise ValueError("song must contain at least one note")
    return song
