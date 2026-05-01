"""Console script for the unified PySynth renderer."""

from __future__ import print_function

import json
import os
import sys
import time
import wave
from pathlib import Path

import click

from tomita.progress import format_duration
from tomita.synth import (
    SynthConfig,
    available_sounds,
    make_wav,
    normalize_sound,
    parse_song,
    progress_from_options,
    sound_rows,
)


DEMO_SETTINGS = {
    "scale": ("song1", {}),
    "anthem": ("song2", {"bpm": 95, "boost": 1.2}),
    "chopin": ("song3", {"bpm": 66, "pause": 0.0, "boost": 1.1}),
    "bach-rh": (
        "song4_rh",
        {"bpm": 130, "transpose": 1, "pause": 0.1, "boost": 1.15, "repeat": 1},
    ),
    "bach-lh": (
        "song4_lh",
        {"bpm": 130, "transpose": 1, "pause": 0.1, "boost": 1.15, "repeat": 1},
    ),
}

DEFAULT_PREVIEW_SOUNDS = ("a", "b", "e", "s", "beeper")


def _demo_song(name):
    from tomita.legacy import demosongs

    attr, defaults = DEMO_SETTINGS[name]
    return getattr(demosongs, attr), defaults.copy()


def _render_options(func):
    options = [
        click.option(
            "--config",
            "config_path",
            type=click.Path(exists=True, dir_okay=False),
            help="JSON config file with sound/progress settings.",
        ),
        click.option(
            "--sound",
            help="PySynth sound variant or alias to render with.",
        ),
        click.option("--song", help="Inline song, for example: '4c4 4d4 2e4'."),
        click.option(
            "--demo",
            type=click.Choice(sorted(DEMO_SETTINGS.keys())),
            default="anthem",
            show_default=True,
            help="Built-in demo song to render when no source or --song is given.",
        ),
        click.option(
            "--format",
            "source_format",
            type=click.Choice(["auto", "abc", "midi"]),
            default="auto",
            show_default=True,
            help="Input source format.",
        ),
        click.option(
            "--abc-song-number",
            type=int,
            default=1,
            show_default=True,
            help="Tune number to render from an ABC file.",
        ),
        click.option(
            "--track",
            type=int,
            help="MIDI track index to render; defaults to the first non-empty track.",
        ),
        click.option("-o", "--output", help="Output WAV filename."),
        click.option("--bpm", type=float, help="Beats per minute override."),
        click.option("--transpose", type=int, help="Octave transpose value."),
        click.option("--repeat", type=int, help="Repeat count."),
        click.option("--sample-path", help="Directory containing samp piano WAV files."),
        click.option("--progress-every", type=int, help="Print progress every N notes."),
        click.option(
            "--progress-percent",
            type=float,
            help="Print progress every N percent of the song.",
        ),
        click.option(
            "--progress-max-updates",
            type=int,
            help="Approximate maximum progress updates in automatic mode.",
        ),
        click.option(
            "--progress-small-threshold",
            type=int,
            help="Song length at or below which every note is reported.",
        ),
        click.option(
            "--progress-time/--no-progress-time",
            default=None,
            help="Show elapsed and estimated remaining time in progress output.",
        ),
        click.option("--quiet", is_flag=True, help="Suppress progress output."),
        click.option(
            "--summary/--no-summary",
            default=True,
            help="Print an output summary after rendering.",
        ),
    ]
    for option in reversed(options):
        func = option(func)
    return func


def _load_config(config_path):
    return SynthConfig.from_file(config_path) if config_path else SynthConfig.from_defaults()


def _detect_format(source, source_format):
    if source_format != "auto":
        return source_format
    suffixes = "".join(Path(source).suffixes).lower()
    if suffixes.endswith(".abc") or suffixes.endswith(".abc.txt") or suffixes.endswith(".txt"):
        return "abc"
    if suffixes.endswith(".mid") or suffixes.endswith(".midi"):
        return "midi"
    raise ValueError("cannot infer input format for %s; pass --format abc or --format midi" % source)


def _default_output(source, demo):
    if source:
        return str(Path(source).with_suffix(".wav"))
    return "pysynth_%s.wav" % demo.replace("-", "_")


def _load_render_source(source, source_format, song, demo, abc_song_number, track):
    if source and song:
        raise ValueError("pass either a source file or --song, not both")
    if song:
        return parse_song(song), {"fn": "pysynth_output.wav"}, "inline"
    if source:
        detected = _detect_format(source, source_format)
        if detected == "abc":
            from tomita.legacy.read_abc import abc_to_song

            notes, bpm, meta = abc_to_song(source, abc_song_number)
            return notes, {"bpm": bpm, "meta": meta}, "abc"
        if detected == "midi":
            from tomita.legacy.readmidi import midi_to_song

            notes, tempo = midi_to_song(source, tracknum=track)
            return notes, {"bpm": tempo}, "midi"
    notes, render_options = _demo_song(demo)
    return notes, render_options, "demo"


def _apply_render_overrides(render_options, output, bpm, transpose, repeat, sample_path):
    if output:
        render_options["fn"] = output
    if bpm is not None:
        render_options["bpm"] = bpm
    if transpose is not None:
        render_options["transpose"] = transpose
    if repeat is not None:
        render_options["repeat"] = repeat
    if sample_path:
        render_options["sample_path"] = sample_path
    render_options.pop("meta", None)
    return render_options


def _wav_summary(filename, elapsed):
    size = os.path.getsize(filename)
    with wave.open(filename, "rb") as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
        channels = wav.getnchannels()
        duration = frames / float(rate) if rate else 0.0
    return (
        "Rendered %s: %.2f s audio, %s Hz, %u channel%s, %s, elapsed %s"
        % (
            filename,
            duration,
            rate,
            channels,
            "" if channels == 1 else "s",
            _format_size(size),
            format_duration(elapsed),
        )
    )


def _format_size(size):
    units = ("B", "KB", "MB", "GB")
    size = float(size)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            return "%.1f %s" % (size, unit) if unit != "B" else "%u B" % int(size)
        size /= 1024.0


def _render_impl(
    source=None,
    config_path=None,
    sound=None,
    song=None,
    demo="anthem",
    source_format="auto",
    abc_song_number=1,
    track=1,
    output=None,
    bpm=None,
    transpose=None,
    repeat=None,
    sample_path=None,
    progress_every=None,
    progress_percent=None,
    progress_max_updates=None,
    progress_small_threshold=None,
    progress_time=None,
    quiet=False,
    summary=True,
):
    config = _load_config(config_path)
    sound = normalize_sound(sound) if sound is not None else None
    if sample_path:
        config.sample_path = sample_path
    progress = progress_from_options(
        config.progress,
        every=progress_every,
        percent=progress_percent,
        max_updates=progress_max_updates,
        small_threshold=progress_small_threshold,
        show_time=progress_time,
    )

    notes, render_options, _source_kind = _load_render_source(
        source,
        source_format,
        song,
        demo,
        abc_song_number,
        track,
    )
    render_options.setdefault("fn", output or _default_output(source, demo if not song else "output"))
    render_options = _apply_render_overrides(
        render_options,
        output,
        bpm,
        transpose,
        repeat,
        sample_path,
    )

    started = time.monotonic()
    make_wav(
        notes,
        config=config,
        sound=sound,
        progress=progress,
        silent=quiet,
        **render_options
    )
    if summary and not quiet:
        click.echo(_wav_summary(render_options["fn"], time.monotonic() - started))
    return render_options["fn"]


def _print_sound_rows():
    for row in sound_rows():
        aliases = ", ".join(row["aliases"]) if row["aliases"] else "-"
        click.echo("%-7s %s (aliases: %s)" % (row["sound"], row["description"], aliases))


@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--list-sounds", is_flag=True, help="Print sound variants and exit.")
@_render_options
@click.pass_context
def main(ctx, list_sounds=False, **kwargs):
    """Render WAV files using PySynth sound variants."""

    try:
        if list_sounds:
            _print_sound_rows()
            return 0
        if ctx.invoked_subcommand is None:
            _render_impl(**kwargs)
    except (OSError, TypeError, ValueError) as exc:
        raise click.ClickException(str(exc))
    return 0


@main.command()
@click.argument("source", required=False)
@_render_options
def render(source=None, **kwargs):
    """Render an inline song, demo, ABC file, or MIDI file."""

    try:
        _render_impl(source=source, **kwargs)
    except (OSError, TypeError, ValueError) as exc:
        raise click.ClickException(str(exc))


@main.command("list-sounds")
def list_sounds_command():
    """Show sound variants, descriptions, and aliases."""

    _print_sound_rows()


@main.command()
@click.option("--sound", "sounds", multiple=True, help="Sound to preview; repeatable.")
@click.option("--all", "all_sounds", is_flag=True, help="Preview every sound variant.")
@click.option("--song", default="4c4 4e4 4g4 2c5", show_default=True)
@click.option("--output-dir", default="pysynth_preview", show_default=True)
@click.option("--config", "config_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--sample-path", help="Directory containing samp piano WAV files.")
@click.option("--quiet", is_flag=True, help="Suppress render progress.")
def preview(sounds, all_sounds, song, output_dir, config_path=None, sample_path=None, quiet=False):
    """Render short comparison WAVs for multiple sound variants."""

    try:
        selected = available_sounds() if all_sounds else list(sounds or DEFAULT_PREVIEW_SOUNDS)
        selected = [normalize_sound(sound) for sound in selected]
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        for sound in selected:
            filename = output_path / ("preview_%s.wav" % sound)
            try:
                _render_impl(
                    song=song,
                    output=str(filename),
                    sound=sound,
                    config_path=config_path,
                    sample_path=sample_path,
                    quiet=quiet,
                    summary=not quiet,
                )
            except ValueError as exc:
                if sound == "samp":
                    click.echo("Skipping samp: %s" % exc)
                else:
                    raise
    except (OSError, TypeError, ValueError) as exc:
        raise click.ClickException(str(exc))


@main.group()
def config():
    """Create, show, and validate PySynth config files."""


@config.command("init")
@click.argument("path", required=False, default="pysynth.json")
@click.option("--force", is_flag=True, help="Overwrite an existing config file.")
@click.option("--sound", default="b", show_default=True, help="Default sound.")
@click.option("--sample-path", help="Optional samp sample directory.")
def config_init(path, force=False, sound="b", sample_path=None):
    """Create a starter config file."""

    try:
        if os.path.exists(path) and not force:
            raise ValueError("%s already exists; pass --force to overwrite it" % path)
        data = SynthConfig(sound=sound, sample_path=sample_path).to_dict()
        with open(path, "w") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
        click.echo("Wrote %s" % path)
    except (OSError, TypeError, ValueError) as exc:
        raise click.ClickException(str(exc))


@config.command("show")
@click.argument("path", required=False, default="pysynth.json")
def config_show(path):
    """Print the effective config as JSON."""

    try:
        config = SynthConfig.from_file(path)
        click.echo(json.dumps(config.to_dict(), indent=2))
    except (OSError, TypeError, ValueError) as exc:
        raise click.ClickException(str(exc))


@config.command("validate")
@click.argument("path", required=False, default="pysynth.json")
def config_validate(path):
    """Validate a config file."""

    try:
        SynthConfig.from_file(path)
        click.echo("%s is valid" % path)
    except (OSError, TypeError, ValueError) as exc:
        raise click.ClickException(str(exc))


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
