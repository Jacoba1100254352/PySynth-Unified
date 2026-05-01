"""Tests for the unified PySynth/Tomita package."""

from click.testing import CliRunner

from tomita import cli
from tomita.progress import ProgressConfig
from tomita.synth import (
    SynthConfig,
    available_sounds,
    config_from_args,
    make_wav,
    parse_song,
    progress_from_options,
)


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


def test_parse_song():
    assert parse_song("4c4 8d#4 2r") == [("c4", 4), ("d#4", 8), ("r", 2)]


def test_progress_cli_options_override_config_cadence():
    base = ProgressConfig(every=2)
    progress = progress_from_options(base, percent=25)

    assert progress.every is None
    assert progress.percent == 25


def test_progress_cli_time_option_overrides_config():
    progress = progress_from_options(ProgressConfig(), show_time=True)

    assert progress.show_time is True


def test_legacy_sound_flags_use_unified_config():
    assert config_from_args(["read_abc.py", "song.abc", "--syn_e"]).sound == "e"
    assert config_from_args(["read_abc.py", "song.abc", "--sound", "piano"]).sound == "b"


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


def test_command_line_interface_reports_invalid_sound():
    runner = CliRunner()

    result = runner.invoke(cli.main, ["--sound", "nope"])

    assert result.exit_code == 1
    assert "unknown sound" in result.output


def test_list_sounds():
    runner = CliRunner()
    result = runner.invoke(cli.main, ["--list-sounds"])

    assert result.exit_code == 0
    for sound in available_sounds():
        assert sound in result.output
    assert "aliases:" in result.output


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


def test_render_command_accepts_midi_file(tmp_path):
    midi_file = tmp_path / "song.mid"
    output = tmp_path / "song.wav"
    track = bytes.fromhex("00903c4060803c4000ff2f00")
    midi_file.write_bytes(
        b"MThd"
        + (6).to_bytes(4, "big")
        + (0).to_bytes(2, "big")
        + (1).to_bytes(2, "big")
        + (96).to_bytes(2, "big")
        + b"MTrk"
        + len(track).to_bytes(4, "big")
        + track
    )
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
