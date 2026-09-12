"""Exercise legacy engines and release-facing behavior with real WAV files."""

import importlib
import math
import subprocess
import sys
import wave

import numpy as np
import pytest
from click.testing import CliRunner

from tomita import cli
from tomita.synth import SOUND_MODULES, make_wav


@pytest.fixture
def sample_directory(tmp_path):
    samples = tmp_path / "samples"
    samples.mkdir()
    frames = b"".join(
        int(2000000 * math.sin(2 * math.pi * 440 * n / 48000)).to_bytes(
            3, "little", signed=True
        ) * 2
        for n in range(4800)
    )
    with wave.open(str(samples / "C4v10.wav"), "wb") as wav:
        wav.setparams((2, 3, 48000, 0, "NONE", "not compressed"))
        wav.writeframes(frames)
    return samples


@pytest.mark.parametrize("sound", list(SOUND_MODULES))
def test_every_unified_sound_handles_accents_dotted_notes_and_rests(
    tmp_path, sample_directory, capsys, sound
):
    output = tmp_path / (sound + ".wav")
    make_wav(
        [("c4*", -32), ("r", -32)], sound=sound, bpm=120,
        sample_path=sample_directory, fn=str(output), silent=True,
    )
    with wave.open(str(output), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getnframes() > 0
        assert np.any(np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2"))
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("sound", list(SOUND_MODULES))
def test_legacy_engine_import_and_render(tmp_path, sample_directory, sound):
    module = importlib.import_module(SOUND_MODULES[sound])
    output = tmp_path / ("legacy-" + sound + ".wav")
    options = {"sample_path": sample_directory} if sound == "samp" else {}
    module.make_wav([("c4", 32), ("r", 32)], fn=str(output), silent=True, **options)
    with wave.open(str(output), "rb") as wav:
        assert wav.getnframes() > 0


@pytest.mark.parametrize("sound", ["b", "e", "samp"])
def test_demo_articulation_works_with_legato_engines(
    tmp_path, sample_directory, monkeypatch, sound
):
    monkeypatch.setattr(
        cli, "_demo_song", lambda name: ([("c4", 32)], {"pause": 0.1})
    )
    result = CliRunner().invoke(cli.main, [
        "--demo", "bach-rh", "--sound", sound, "--quiet",
        "--sample-path", str(sample_directory), "--output", str(tmp_path / "demo.wav"),
    ])
    assert result.exit_code == 0, result.output


def test_sampler_preserves_signed_audio_and_full_frame_count(tmp_path, sample_directory):
    output = tmp_path / "sample.wav"
    make_wav([("c4", 32)], sound="samp", sample_path=sample_directory,
             fn=str(output), silent=True)
    with wave.open(str(output), "rb") as wav:
        audio = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
    assert audio[20] > 0
    assert audio[80] < 0
    assert np.max(np.abs(audio[1800:2400])) > 1000


@pytest.mark.parametrize("problem", ["missing", "format", "truncated"])
def test_invalid_sample_preserves_existing_output(tmp_path, sample_directory, problem):
    sample = sample_directory / "C4v10.wav"
    if problem == "missing":
        sample.unlink()
    elif problem == "format":
        with wave.open(str(sample), "wb") as wav:
            wav.setparams((1, 2, 44100, 0, "NONE", "not compressed"))
            wav.writeframes(b"\0" * 100)
    else:
        sample.write_bytes(sample.read_bytes()[:-1])
    output = tmp_path / "existing.wav"
    output.write_bytes(b"preserve this output")
    with pytest.raises(ValueError, match="sample"):
        make_wav([("c4", 32)], sound="samp", sample_path=sample_directory,
                 fn=str(output), silent=True)
    assert output.read_bytes() == b"preserve this output"


def test_sampler_renders_silence_without_numeric_warnings(tmp_path, sample_directory):
    output = tmp_path / "rest.wav"
    with np.errstate(all="raise"):
        make_wav([("r", 32)], sound="samp", sample_path=sample_directory,
                 fn=str(output), silent=True)
    with wave.open(str(output), "rb") as wav:
        assert not any(wav.readframes(wav.getnframes()))


def test_sampler_transposes_and_resamples_adjacent_keys(tmp_path, sample_directory):
    crossings = []
    for note, transpose in [("c4", 0), ("c4", 1), ("c#4", 0)]:
        output = tmp_path / ("%s-%s.wav" % (note, transpose))
        make_wav([(note, 32)], sound="samp", sample_path=sample_directory,
                 transpose=transpose, fn=str(output), silent=True)
        with wave.open(str(output), "rb") as wav:
            audio = np.frombuffer(wav.readframes(2000), dtype="<i2")
        crossings.append(np.count_nonzero((audio[:-1] <= 0) & (audio[1:] > 0)))
    assert crossings[1] == pytest.approx(crossings[0] * 2, abs=1)
    assert crossings[2] > crossings[0]


@pytest.mark.parametrize("kind", ["abc", "midi"])
def test_legacy_file_entrypoints_render_in_a_separate_process(tmp_path, kind):
    if kind == "abc":
        source = tmp_path / "tune.abc"
        source.write_text("X:1\nT:Legacy\nM:4/4\nL:1/32\nK:C\nC|\n", encoding="utf-8")
        command = ["tomita.legacy.read_abc", str(source)]
        output = tmp_path / "out.wav"
    else:
        source = tmp_path / "tune.mid"
        track = b"\x00\x90\x3c\x40\x60\x80\x3c\x40\x00\xff\x2f\x00"
        source.write_bytes(
            b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x00\x60MTrk"
            + len(track).to_bytes(4, "big") + track
        )
        output = tmp_path / "midi.wav"
        command = ["tomita.legacy.readmidi", str(source), "0", str(output)]
    result = subprocess.run(
        [sys.executable, "-m"] + command + ["--sound=beeper"],
        cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    with wave.open(str(output), "rb") as wav:
        assert wav.getnframes() > 0
