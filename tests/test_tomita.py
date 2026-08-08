"""Tests for the unified PySynth/Tomita package."""

import json
import subprocess
import sys
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

import pysynth
import pysynth.cli as pysynth_cli
import tomita
import tomita.synth as synth_module
from tomita import cli
from tomita.legacy import read_abc as legacy_read_abc
from tomita.legacy import readmidi as legacy_readmidi
from tomita.legacy.read_abc import abc_to_song
from tomita.legacy.readmidi import midi_to_song
from tomita.progress import ProgressConfig, ProgressReporter, format_duration
from tomita.synth import (
    SynthConfig,
    available_sounds,
    config_from_args,
    make_wav,
    parse_song,
    progress_from_options,
    sound_aliases,
    sound_description,
)


def _write_midi(path, tracks):
    data = [
        b"MThd",
        (6).to_bytes(4, "big"),
        (1 if len(tracks) > 1 else 0).to_bytes(2, "big"),
        len(tracks).to_bytes(2, "big"),
        (96).to_bytes(2, "big"),
    ]
    for track in tracks:
        data.extend([b"MTrk", len(track).to_bytes(4, "big"), track])
    path.write_bytes(b"".join(data))


def _single_note_track(note_off_event=b"\x80\x3c\x40"):
    return b"\x00\x90\x3c\x40\x60" + note_off_event + b"\x00\xff\x2f\x00"


def test_package_metadata_matches_public_fork():
    repo_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [sys.executable, "setup.py", "--name", "--version", "--url"],
        cwd=str(repo_root),
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == [
        "pysynth-unified",
        tomita.__version__,
        "https://github.com/Jacoba1100254352/PySynth-Unified",
    ]


def test_progress_reports_every_note_for_short_songs():
    progress = ProgressConfig()

    assert [n for n in range(1, 5) if progress.should_report(n, 4)] == [1, 2, 3, 4]


def test_progress_auto_throttles_and_keeps_last_update():
    progress = ProgressConfig(max_updates=6)

    assert [n for n in range(1, 26) if progress.should_report(n, 25)] == [
        1,
        5,
        10,
        15,
        20,
        25,
    ]


def test_progress_can_be_disabled():
    progress = ProgressConfig(enabled=False)

    assert [n for n in range(1, 5) if progress.should_report(n, 4)] == []


@pytest.mark.parametrize(
    "value,message",
    [
        ({"every": 0}, "progress every must be at least 1"),
        ({"percent": 0}, "progress percent must be greater than 0"),
        ("sometimes", "unsupported progress config"),
    ],
)
def test_progress_rejects_invalid_values(value, message):
    with pytest.raises((TypeError, ValueError), match=message):
        ProgressConfig.from_value(value)


@pytest.mark.parametrize(
    "value,message",
    [
        ({"enabled": "false"}, "enabled must be true or false"),
        ({"show_time": 1}, "show_time must be true or false"),
        ({"every": 2, "percent": 50}, "cannot both be set"),
        ({"percent": 101}, "at most 100"),
        ({"max_updates": 0}, "must be at least 1"),
        ({"small_threshold": -1}, "cannot be negative"),
        ({"typo": 1}, "unknown progress option"),
    ],
)
def test_progress_rejects_ambiguous_or_mistyped_config(value, message):
    with pytest.raises(ValueError, match=message):
        ProgressConfig.from_value(value)


def test_progress_from_value_accepts_common_shortcuts():
    every = ProgressConfig.from_value(2)
    percent = ProgressConfig.from_value(25.0)

    assert every.every == 2
    assert percent.percent == 25.0
    assert every.interval(1) == 1
    assert every.should_report(0, 4) is False
    assert every.should_report(1, 0) is False


def test_progress_percent_cadence_keeps_first_and_last_update():
    progress = ProgressConfig(percent=30)

    assert [n for n in range(1, 11) if progress.should_report(n, 10)] == [
        1,
        3,
        6,
        9,
        10,
    ]


def test_progress_reporter_can_include_elapsed_time(capsys):
    reporter = ProgressReporter("song.wav", ProgressConfig(show_time=True))

    reporter.start()
    reporter.step(1, 2)
    reporter.finish()

    output = capsys.readouterr().out
    assert "Writing to file song.wav" in output
    assert "[1/2] elapsed" in output
    assert "eta" in output


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (-1, "0:00"),
        (65, "1:05"),
        (3661, "1:01:01"),
    ],
)
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected


def test_parse_song():
    assert parse_song("4c4 8d#4 2r") == [("c4", 4), ("d#4", 8), ("r", 2)]


def test_parse_song_normalizes_case_rests_and_float_durations():
    assert parse_song("4C4 8Bb3 2R 1.5f#5*") == [
        ("c4", 4),
        ("bb3", 8),
        ("r", 2),
        ("f#5*", 1.5),
    ]


def test_parse_song_rejects_invalid_tokens():
    with pytest.raises(ValueError, match="invalid note token"):
        parse_song("quarter-note")


@pytest.mark.parametrize(
    "text,message",
    [
        ("", "at least one note"),
        ("0c4", "duration must be non-zero"),
        ("4r#", "invalid note token"),
    ],
)
def test_parse_song_rejects_empty_or_invalid_values(text, message):
    with pytest.raises(ValueError, match=message):
        parse_song(text)


def test_progress_cli_options_override_config_cadence():
    base = ProgressConfig(every=2)
    progress = progress_from_options(base, percent=25)

    assert progress.every is None
    assert progress.percent == 25


def test_progress_cli_time_option_overrides_config():
    progress = progress_from_options(ProgressConfig(), show_time=True)

    assert progress.show_time is True


def test_progress_options_preserve_base_when_no_overrides():
    base = ProgressConfig(every=3, show_time=True)

    assert progress_from_options(base) is base


def test_sound_aliases_descriptions_and_public_facades():
    assert "e" in available_sounds()
    assert "epiano" in sound_aliases("e")
    assert "piano" in sound_description("b")
    assert pysynth.available_sounds() == available_sounds()
    assert pysynth.SynthConfig(sound="piano").sound == "b"
    assert pysynth.__version__ == tomita.__version__


def test_legacy_sound_flags_use_unified_config():
    assert config_from_args(["read_abc.py", "song.abc", "--syn_e"]).sound == "e"
    assert config_from_args(["read_abc.py", "song.abc", "--sound", "piano"]).sound == "b"


def test_config_from_args_uses_file_then_cli_overrides(tmp_path, monkeypatch):
    config_path = tmp_path / "pysynth.json"
    config_path.write_text(
        json.dumps(
            {
                "sound": "a",
                "sample_path": "/config/samples",
                "progress": {"every": 3},
            }
        )
    )
    monkeypatch.chdir(tmp_path)

    config = config_from_args(
        [
            "read_abc.py",
            "song.abc",
            "--config",
            str(config_path),
            "--sound",
            "e-piano",
            "--sample-path",
            "/cli/samples",
        ]
    )

    assert config.sound == "e"
    assert config.sample_path == "/cli/samples"
    assert config.progress.every == 3


def test_config_from_args_accepts_equals_form(tmp_path):
    config_path = tmp_path / "pysynth.json"
    config_path.write_text(json.dumps({"sound": "a", "progress": {"percent": 50}}))

    config = config_from_args(
        [
            "readmidi.py",
            "song.mid",
            "--config=%s" % config_path,
            "--sound=organ",
            "--sample-path=/samples",
        ]
    )

    assert config.sound == "a"
    assert config.sample_path == "/samples"
    assert config.progress.percent == 50


def test_synth_config_defaults_and_to_dict_include_optional_fields(tmp_path, monkeypatch):
    config_path = tmp_path / "pysynth.json"
    config_path.write_text(
        json.dumps(
            {
                "sound": "e",
                "sample_path": "/samples",
                "progress": {"percent": 25, "show_time": True},
            }
        )
    )
    monkeypatch.chdir(tmp_path)

    config = SynthConfig.from_defaults()

    assert config.sound == "e"
    assert config.to_dict()["sample_path"] == "/samples"
    assert config.to_dict()["progress"]["percent"] == 25


def test_synth_config_rejects_unknown_sound():
    with pytest.raises(ValueError, match="unknown sound"):
        SynthConfig(sound="not-real")


def test_make_wav_uses_sound_config(tmp_path):
    output = tmp_path / "configured.wav"

    make_wav(
        [("c4", 4), ("d4", 4)],
        config=SynthConfig(sound="a", progress=False),
        fn=str(output),
        silent=True,
    )

    assert output.exists()
    assert output.stat().st_size > 44


def test_numpy_backed_sound_renders(tmp_path):
    output = tmp_path / "piano.wav"

    make_wav(
        [("c4", 4), ("e4", 4), ("g4", 4), ("c5", 2)],
        config=SynthConfig(sound="b", progress=False),
        fn=str(output),
        silent=True,
    )

    assert output.exists()
    assert output.stat().st_size > 44


def test_public_pysynth_facade_renders_student_style_code(tmp_path):
    output = tmp_path / "student.wav"
    song = [
        ("c4", 4),
        ("d4", 4),
        ("e4", 4),
        ("g4", 4),
        ("c5", 2),
    ]

    pysynth.make_wav(song, sound="e", bpm=120, fn=str(output), progress=False)

    assert output.exists()
    assert output.stat().st_size > 44


def test_beeper_sound_renders_with_bpm_and_repeat(tmp_path):
    output = tmp_path / "beeper.wav"

    make_wav(
        [("c4", 4), ("r", 4)],
        sound="beeper",
        bpm=240,
        repeat=1,
        fn=str(output),
        progress=False,
    )

    with wave.open(str(output), "rb") as wav:
        assert wav.getframerate() == 44100
        assert wav.getnframes() > 0


def test_beeper_normalizes_flats_dotted_values_and_repeats(monkeypatch):
    captured = {}

    def fake_make_wav(song, **kwargs):
        captured["song"] = song
        captured["kwargs"] = kwargs

    fake_module = SimpleNamespace(PITCHHZ={"a#3": 233.08}, make_wav=fake_make_wav)
    monkeypatch.setattr(synth_module, "get_synth_module", lambda _sound: fake_module)

    make_wav(
        [("Bb3", -4), ("R", -8)],
        sound="beeper",
        bpm=120,
        repeat=1,
        progress=False,
    )

    assert captured["song"] == [
        ("a#3", pytest.approx(8 / 3)),
        ("r", pytest.approx(16 / 3)),
    ] * 2
    assert captured["kwargs"]["tempo"] == 120


@pytest.mark.parametrize(
    "song,message",
    [
        ([], "at least one note"),
        ([("c4", 0)], "finite and non-zero"),
        ([("c9", 4)], "outside sound a's range"),
        ([("c4", float("inf"))], "finite and non-zero"),
        ("4c4", r"iterable of \(note, duration\) pairs"),
    ],
)
def test_make_wav_validates_song_before_opening_output(tmp_path, song, message):
    output = tmp_path / "existing.wav"
    output.write_bytes(b"keep me")

    with pytest.raises(ValueError, match=message):
        make_wav(song, sound="a", fn=str(output), progress=False)

    assert output.read_bytes() == b"keep me"


def test_sample_path_is_harmless_for_non_sample_sounds(tmp_path):
    output = tmp_path / "not_sample.wav"

    make_wav(
        [("c4", 4)],
        sound="a",
        sample_path=str(tmp_path / "samples"),
        fn=str(output),
        progress=False,
        silent=True,
    )

    assert output.exists()


def test_sample_backed_sound_requires_sample_path(tmp_path):
    with pytest.raises(ValueError, match="requires Salamander"):
        make_wav(
            [("c4", 4)],
            sound="samp",
            config=SynthConfig(sound="samp", sample_path=str(tmp_path / "missing")),
            fn=str(tmp_path / "samp.wav"),
            progress=False,
        )


def test_command_line_interface(tmp_path):
    output = tmp_path / "cli.wav"
    runner = CliRunner()

    result = runner.invoke(
        cli.main,
        [
            "--song",
            "4c4 4d4 4e4 4f4",
            "--output",
            str(output),
            "--sound",
            "a",
            "--progress-every",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert output.exists()
    assert "[4/4]" in result.output


def test_command_line_interface_accepts_sound_alias(tmp_path):
    output = tmp_path / "alias.wav"
    runner = CliRunner()

    result = runner.invoke(
        cli.main,
        [
            "--song",
            "4c4 4e4",
            "--output",
            str(output),
            "--sound",
            "piano",
            "--quiet",
        ],
    )

    assert result.exit_code == 0
    assert output.exists()


def test_command_line_quiet_suppresses_progress_and_summary(tmp_path):
    output = tmp_path / "quiet.wav"
    runner = CliRunner()

    result = runner.invoke(
        cli.main,
        [
            "--song",
            "4c4 4d4",
            "--output",
            str(output),
            "--quiet",
        ],
    )

    assert result.exit_code == 0
    assert output.exists()
    assert "Writing to file" not in result.output
    assert "Rendered" not in result.output


def test_command_line_can_suppress_summary_without_hiding_progress(tmp_path):
    output = tmp_path / "no_summary.wav"
    runner = CliRunner()

    result = runner.invoke(
        cli.main,
        [
            "--song",
            "4c4 4d4",
            "--output",
            str(output),
            "--no-summary",
        ],
    )

    assert result.exit_code == 0
    assert "Writing to file" in result.output
    assert "Rendered" not in result.output


def test_pysynth_cli_module_exports_same_command():
    runner = CliRunner()

    result = runner.invoke(pysynth_cli.main, ["list-sounds"])

    assert result.exit_code == 0
    assert "beeper" in result.output


def test_command_line_interface_reports_invalid_sound():
    runner = CliRunner()

    result = runner.invoke(cli.main, ["--sound", "nope"])

    assert result.exit_code == 1
    assert "unknown sound" in result.output


@pytest.mark.parametrize(
    "song,message",
    [
        ("", "at least one note"),
        ("0c4", "duration must be non-zero"),
        ("4c9", "outside sound a's range"),
    ],
)
def test_command_line_reports_invalid_inline_song_without_partial_output(
    tmp_path, song, message
):
    output = tmp_path / "invalid.wav"
    runner = CliRunner()

    result = runner.invoke(
        cli.main,
        ["--song", song, "--output", str(output), "--quiet"],
    )

    assert result.exit_code == 1
    assert message in result.output
    assert not output.exists()


def test_list_sounds():
    runner = CliRunner()
    result = runner.invoke(cli.main, ["--list-sounds"])

    assert result.exit_code == 0
    for sound in available_sounds():
        assert sound in result.output
    assert "aliases:" in result.output


def test_list_sounds_subcommand():
    runner = CliRunner()

    result = runner.invoke(cli.main, ["list-sounds"])

    assert result.exit_code == 0
    assert "epiano" in result.output


def test_render_command_rejects_source_and_inline_song(tmp_path):
    source = tmp_path / "song.abc"
    source.write_text("X:1\nK:C\nC|\n")
    runner = CliRunner()

    result = runner.invoke(cli.main, ["render", str(source), "--song", "4c4"])

    assert result.exit_code == 1
    assert "pass either a source file or --song" in result.output


def test_render_command_requires_format_for_unknown_extension(tmp_path):
    source = tmp_path / "song.music"
    source.write_text("X:1\nK:C\nC|\n")
    runner = CliRunner()

    result = runner.invoke(cli.main, ["render", str(source), "--quiet"])

    assert result.exit_code == 1
    assert "cannot infer input format" in result.output


def test_render_command_accepts_explicit_format_for_unknown_extension(tmp_path):
    source = tmp_path / "song.music"
    output = tmp_path / "song.wav"
    source.write_text("X:1\nT:Test\nM:4/4\nL:1/4\nK:C\nC|\n")
    runner = CliRunner()

    result = runner.invoke(
        cli.main,
        [
            "render",
            str(source),
            "--format",
            "abc",
            "--output",
            str(output),
            "--quiet",
        ],
    )

    assert result.exit_code == 0
    assert output.exists()


def test_render_command_uses_source_default_output(tmp_path):
    source = tmp_path / "default.abc"
    source.write_text("X:1\nT:Test\nM:4/4\nL:1/4\nK:C\nC|\n")
    runner = CliRunner()

    result = runner.invoke(cli.main, ["render", str(source), "--quiet"])

    assert result.exit_code == 0
    assert source.with_suffix(".wav").exists()


def test_render_command_accepts_sample_path_for_non_sample_sound(tmp_path):
    output = tmp_path / "sample_path_ignored.wav"
    runner = CliRunner()

    result = runner.invoke(
        cli.main,
        [
            "--song",
            "4c4",
            "--sound",
            "a",
            "--sample-path",
            str(tmp_path / "samples"),
            "--output",
            str(output),
            "--quiet",
        ],
    )

    assert result.exit_code == 0
    assert output.exists()


def test_render_command_accepts_abc_file(tmp_path):
    abc_file = tmp_path / "song.abc"
    output = tmp_path / "song.wav"
    abc_file.write_text("X:1\nT:Test\nM:4/4\nL:1/4\nQ:120\nK:C\nC D E F|\n")
    runner = CliRunner()

    result = runner.invoke(
        cli.main,
        [
            "render",
            str(abc_file),
            "--output",
            str(output),
            "--sound",
            "a",
            "--quiet",
        ],
    )

    assert result.exit_code == 0
    assert output.exists()


def test_render_command_reports_malformed_abc_cleanly(tmp_path):
    abc_file = tmp_path / "broken.abc"
    abc_file.write_text("X:1\nK:C\n|")
    runner = CliRunner()

    result = runner.invoke(cli.main, ["render", str(abc_file), "--quiet"])

    assert result.exit_code == 1
    assert "cannot parse ABC file" in result.output


def test_abc_reader_selects_requested_song_and_resets_state(tmp_path):
    abc_file = tmp_path / "songs.abc"
    abc_file.write_text(
        "X:1\nT:One\nM:4/4\nL:1/4\nK:C\nC|\n\n"
        "X:2\nT:Two\nM:4/4\nL:1/4\nK:G\nF|\n"
    )

    first_song, _first_bpm, first_meta = abc_to_song(str(abc_file), 1)
    second_song, _second_bpm, second_meta = abc_to_song(str(abc_file), 2)

    assert first_meta["key"] == "C"
    assert second_meta["key"] == "G"
    assert first_song != second_song


def test_abc_reader_reports_missing_song(tmp_path):
    abc_file = tmp_path / "song.abc"
    abc_file.write_text("X:1\nT:One\nM:4/4\nL:1/4\nK:C\nC|\n")

    with pytest.raises(ValueError, match="song 2 not found"):
        abc_to_song(str(abc_file), 2)


def test_render_command_accepts_midi_file(tmp_path):
    midi_file = tmp_path / "song.mid"
    output = tmp_path / "song.wav"
    _write_midi(midi_file, [_single_note_track()])
    runner = CliRunner()

    result = runner.invoke(
        cli.main,
        [
            "render",
            str(midi_file),
            "--output",
            str(output),
            "--sound",
            "a",
            "--quiet",
        ],
    )

    assert result.exit_code == 0
    assert output.exists()


def test_midi_reader_auto_selects_first_non_empty_track(tmp_path):
    midi_file = tmp_path / "song.mid"
    _write_midi(midi_file, [b"\x00\xff\x2f\x00", _single_note_track()])

    song, tempo = midi_to_song(str(midi_file), tracknum=None)

    assert tempo == 120
    assert song == [("c4", 4.0)]


def test_midi_reader_handles_note_on_velocity_zero_as_note_off(tmp_path):
    midi_file = tmp_path / "velocity_zero.mid"
    _write_midi(midi_file, [_single_note_track(note_off_event=b"\x90\x3c\x00")])

    song, _tempo = midi_to_song(str(midi_file), tracknum=0)

    assert song == [("c4", 4.0)]


def test_midi_reader_handles_running_status(tmp_path):
    midi_file = tmp_path / "running_status.mid"
    track = b"\x00\x90\x3c\x40\x60\x3c\x00\x00\xff\x2f\x00"
    _write_midi(midi_file, [track])

    song, _tempo = midi_to_song(str(midi_file), tracknum=0)

    assert song == [("c4", 4.0)]


def test_midi_reader_skips_length_prefixed_sysex_and_program_change(tmp_path):
    midi_file = tmp_path / "events.mid"
    sysex = b"\x00\xf0\x02\x01\xf7"
    program_change = b"\x00\xc0\x05"
    _write_midi(midi_file, [sysex + program_change + _single_note_track()])

    song, _tempo = midi_to_song(str(midi_file), tracknum=0)

    assert song == [("c4", 4.0)]


def test_midi_reader_rejects_running_status_without_prior_event(tmp_path):
    midi_file = tmp_path / "bad_running_status.mid"
    _write_midi(midi_file, [b"\x00\x3c\x40\x00\xff\x2f\x00"])

    with pytest.raises(ValueError, match="running status appears before"):
        midi_to_song(str(midi_file), tracknum=0)


def test_midi_reader_rejects_zero_length_notes_cleanly(tmp_path):
    midi_file = tmp_path / "zero_length.mid"
    track = b"\x00\x90\x3c\x40\x00\x90\x3c\x00\x00\xff\x2f\x00"
    _write_midi(midi_file, [track])

    with pytest.raises(ValueError, match="duration must be positive"):
        midi_to_song(str(midi_file), tracknum=0)


def test_midi_reader_reports_missing_tracks(tmp_path):
    midi_file = tmp_path / "empty.mid"
    _write_midi(midi_file, [b"\x00\xff\x2f\x00"])

    with pytest.raises(ValueError, match="no note tracks"):
        midi_to_song(str(midi_file), tracknum=None)

    with pytest.raises(ValueError, match="track 3 not found"):
        midi_to_song(str(midi_file), tracknum=3)

    with pytest.raises(ValueError, match="track 0 contains no notes"):
        midi_to_song(str(midi_file), tracknum=0)


def test_render_command_keeps_quiet_for_midi_metadata(tmp_path):
    midi_file = tmp_path / "tempo.mid"
    output = tmp_path / "tempo.wav"
    tempo_event = b"\x00\xff\x51\x03\x07\xa1\x20"
    _write_midi(midi_file, [tempo_event + _single_note_track()])
    runner = CliRunner()

    result = runner.invoke(
        cli.main,
        ["render", str(midi_file), "--output", str(output), "--quiet"],
    )

    assert result.exit_code == 0
    assert result.output == ""
    assert output.exists()


def test_render_command_reports_malformed_midi_cleanly(tmp_path):
    midi_file = tmp_path / "broken.mid"
    midi_file.write_bytes(b"not a midi file")
    runner = CliRunner()

    result = runner.invoke(cli.main, ["render", str(midi_file), "--quiet"])

    assert result.exit_code == 1
    assert "cannot parse MIDI file" in result.output
    assert "missing MThd header" in result.output


def test_config_helpers(tmp_path):
    config_path = tmp_path / "pysynth.json"
    runner = CliRunner()

    init_result = runner.invoke(cli.main, ["config", "init", str(config_path)])
    validate_result = runner.invoke(cli.main, ["config", "validate", str(config_path)])
    show_result = runner.invoke(cli.main, ["config", "show", str(config_path)])

    assert init_result.exit_code == 0
    assert validate_result.exit_code == 0
    assert show_result.exit_code == 0
    assert '"sound": "b"' in show_result.output


def test_config_init_refuses_overwrite_without_force(tmp_path):
    config_path = tmp_path / "pysynth.json"
    config_path.write_text("{}")
    runner = CliRunner()

    result = runner.invoke(cli.main, ["config", "init", str(config_path)])
    forced = runner.invoke(cli.main, ["config", "init", "--force", str(config_path)])

    assert result.exit_code == 1
    assert "already exists" in result.output
    assert forced.exit_code == 0


def test_config_validate_reports_invalid_sound(tmp_path):
    config_path = tmp_path / "pysynth.json"
    config_path.write_text(json.dumps({"sound": "invalid"}))
    runner = CliRunner()

    result = runner.invoke(cli.main, ["config", "validate", str(config_path)])

    assert result.exit_code == 1
    assert "unknown sound" in result.output


@pytest.mark.parametrize(
    "payload,message",
    [
        ([], "must be a JSON object"),
        ({"sound": 1}, "sound must be a string"),
        ({"sample_path": 1}, "sample_path must be a path string"),
        ({"progress": {"enabled": "false"}}, "enabled must be true or false"),
        ({"sounds": "a"}, "unknown option"),
    ],
)
def test_config_validate_reports_structural_errors(tmp_path, payload, message):
    config_path = tmp_path / "invalid.json"
    config_path.write_text(json.dumps(payload))
    runner = CliRunner()

    result = runner.invoke(cli.main, ["config", "validate", str(config_path)])

    assert result.exit_code == 1
    assert message in result.output


def test_config_show_reports_missing_file(tmp_path):
    runner = CliRunner()

    result = runner.invoke(cli.main, ["config", "show", str(tmp_path / "missing.json")])

    assert result.exit_code == 1
    assert "No such file" in result.output


def test_config_init_writes_custom_sound_and_sample_path(tmp_path):
    config_path = tmp_path / "pysynth.json"
    runner = CliRunner()

    result = runner.invoke(
        cli.main,
        [
            "config",
            "init",
            str(config_path),
            "--sound",
            "e-piano",
            "--sample-path",
            "/samples",
        ],
    )
    data = json.loads(config_path.read_text())

    assert result.exit_code == 0
    assert data["sound"] == "e"
    assert data["sample_path"] == "/samples"


def test_preview_command_renders_selected_sound(tmp_path):
    output_dir = tmp_path / "preview"
    runner = CliRunner()

    result = runner.invoke(
        cli.main,
        [
            "preview",
            "--sound",
            "a",
            "--output-dir",
            str(output_dir),
            "--quiet",
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "preview_a.wav").exists()


def test_preview_all_skips_missing_sample_sound(tmp_path):
    output_dir = tmp_path / "preview"
    runner = CliRunner()

    result = runner.invoke(
        cli.main,
        [
            "preview",
            "--all",
            "--output-dir",
            str(output_dir),
            "--quiet",
        ],
    )

    assert result.exit_code == 0
    assert "Skipping samp" in result.output
    assert (output_dir / "preview_a.wav").exists()
    assert (output_dir / "preview_beeper.wav").exists()
    assert not (output_dir / "preview_samp.wav").exists()


def test_preview_reports_invalid_non_sample_sound(tmp_path):
    runner = CliRunner()

    result = runner.invoke(
        cli.main,
        ["preview", "--sound", "not-real", "--output-dir", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert "unknown sound" in result.output


def test_legacy_abc_entrypoint_routes_through_unified_renderer(
    tmp_path, monkeypatch
):
    abc_file = tmp_path / "legacy.abc"
    config_path = tmp_path / "legacy.json"
    abc_file.write_text("X:1\nT:Legacy\nM:4/4\nL:1/4\nK:C\nC|\n")
    config_path.write_text(
        json.dumps({"sound": "a", "sample_path": "/configured/samples"})
    )
    captured = {}

    def fake_make_wav(song, **kwargs):
        captured["song"] = song
        captured["kwargs"] = kwargs

    monkeypatch.setattr(legacy_read_abc, "make_wav", fake_make_wav)

    legacy_read_abc.main(
        [str(abc_file), "--config", str(config_path), "--sound", "beeper"]
    )

    assert captured["song"]
    assert captured["kwargs"]["config"].sound == "beeper"
    assert captured["kwargs"]["config"].sample_path == "/configured/samples"


def test_legacy_midi_entrypoint_routes_through_unified_renderer(
    tmp_path, monkeypatch
):
    midi_file = tmp_path / "legacy.mid"
    output = tmp_path / "legacy.wav"
    _write_midi(midi_file, [_single_note_track()])
    captured = {}

    def fake_make_wav(song, **kwargs):
        captured["song"] = song
        captured["kwargs"] = kwargs

    monkeypatch.setattr(legacy_readmidi, "make_wav", fake_make_wav)

    legacy_readmidi.main(
        [str(midi_file), "0", str(output), "--sound", "beeper"]
    )

    assert captured["song"] == [("c4", 4.0)]
    assert captured["kwargs"]["config"].sound == "beeper"
    assert captured["kwargs"]["fn"] == str(output)
