#!/usr/bin/env python

"""
##########################################################################
#                       * * *  PySynth  * * *
#       A very basic audio synthesizer in Python (www.python.org)
#
#          Martin C. Doege, 2017-06-25 (mdoege@compuserve.com)
##########################################################################
# Based on a program by Tyler Eaves (tyler at tylereaves.com) found at
#   http://mail.python.org/pipermail/python-list/2000-August/041308.html
##########################################################################

# 'song' is a Python list (or tuple) in which the song is defined,
#   the format is [['note', value]]

# Notes are 'a' through 'g' of course,
# optionally with '#' or 'b' appended for sharps or flats.
# Finally the octave number (defaults to octave 4 if not given).
# An asterisk at the end makes the note a little louder (useful for the beat).
# 'r' is a rest.

# Note value is a number:
# 1=Whole Note; 2=Half Note; 4=Quarter Note, etc.
# Dotted notes can be written in two ways:
# 1.33 = -2 = dotted half
# 2.66 = -4 = dotted quarter
# 5.33 = -8 = dotted eighth
"""

from __future__ import division

import os
import wave
import numpy as np
from math import sin, cos, pi, log, exp

from tomita.legacy.demosongs import *
from tomita.legacy.mixfiles import mix_files
from tomita.legacy.mkfreq import getfreq, getfn
from tomita.progress import ProgressReporter

pitchhz, keynum = getfreq()

# get filenames for sample layer 10:
fnames = getfn(10)

# path to Salamander piano samples (http://freepats.zenvoid.org/Piano/acoustic-grand-piano.html),
#       48 kHz version:
# patchpath = "/usr/share/sounds/SalamanderGrandPianoV3_48khz24bit/48khz24bit/"
patchpath = "48khz24bit/"


def _load_sample(filename):
    """Decode the left channel of a Salamander 48 kHz, 24-bit stereo WAV."""
    try:
        with wave.open(filename, "rb") as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (2, 3, 48000):
                raise ValueError("expected 48 kHz, 24-bit stereo PCM")
            frames = wav.getnframes()
            raw = wav.readframes(frames)
            if frames == 0 or len(raw) != frames * 6:
                raise ValueError("empty or truncated audio data")
    except (OSError, EOFError, wave.Error, ValueError) as exc:
        raise ValueError("cannot load sample %s: %s" % (filename, exc)) from exc
    octets = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 6).astype(np.int32)
    values = octets[:, 0] | (octets[:, 1] << 8) | (octets[:, 2] << 16)
    values = (values ^ 0x800000) - 0x800000
    return values.astype(np.float64) / 8388608.0


##########################################################################
#### Main program starts below
##########################################################################
# Some parameters:

# Beats (quarters) per minute
# e.g. bpm = 95

# Octave shift (neg. integer -> lower; pos. integer -> higher)
# e.g. transpose = 0

# Playing style (e.g., 0.8 = very legato and e.g., 0.3 = very staccato)
# e.g. leg_stac = 0.6

# Volume boost for asterisk notes (1. = no boost)
# e.g. boost = 1.2

# Output file name
# fn = 'pysynth_output.wav'

##########################################################################


def make_wav(
    song,
    bpm=120,
    transpose=0,
    leg_stac=0.9,
    boost=1.1,
    repeat=0,
    fn="out.wav",
    silent=False,
    progress=None,
    sample_path=None,
):
    sample_dir = sample_path or os.environ.get("PYSYNTH_SAMPLE_PATH") or patchpath
    if not os.path.isdir(sample_dir):
        raise ValueError(
            "PySynth samp requires Salamander 48 kHz piano samples. "
            "Set sample_path in pysynth.json, pass --sample-path, or set "
            "PYSYNTH_SAMPLE_PATH to the directory containing files like A0v10.wav."
        )

    # Validate and load every required sample before touching the output.
    song = list(song)
    samples = {}
    for note, _duration in song:
        note = note.rstrip("*")
        if note == "r":
            continue
        if not note[-1].isdigit():
            note += "4"
        filename = fnames[keynum[note]][0]
        if filename not in samples:
            samples[filename] = _load_sample(os.path.join(sample_dir, filename))

    bpmfac = 120.0 / bpm

    def length(l):
        return 96000.0 / l * bpmfac

    def render2(a, b, vol, pos, knum, note):
        snd_len = int(b)
        new = samples[fnames[knum][0]]
        factor = fnames[knum][1] * 2.0 ** transpose
        # Salamander samples every third piano key, so other notes
        # are created by playing these samples faster (with linear interpolation):
        positions = np.arange(0, len(new), factor)
        new2 = np.interp(positions, np.arange(len(new)), new)
        raw_note = len(new2)

        dec_ind = max(0, min(raw_note, int(leg_stac * b)))
        new2[dec_ind:] *= np.exp(-np.arange(raw_note - dec_ind) / 3000.0)
        fade_length = min(1001, raw_note)
        new2[-fade_length:] *= np.linspace(1.0, 0.0, fade_length)
        if snd_len > raw_note:
            if progress_reporter.enabled:
                print("Warning, note too long:", snd_len, raw_note)
            snd_len = raw_note
        data[pos : pos + snd_len] += new2[:snd_len] * vol

    ex_pos = 0.0
    t_len = 0
    for y, x in song:
        if x < 0:
            t_len += length(-2.0 * x / 3.0)
        else:
            t_len += length(x)
        if y[-1] == "*":
            y = y[:-1]
        if not y[-1].isdigit():
            y += "4"
    data = np.zeros(int((repeat + 1) * t_len + 480000))

    progress_reporter = ProgressReporter(fn, progress, silent)
    progress_reporter.start()
    total_steps = len(song) * (repeat + 1)
    for rp in range(repeat + 1):
        for nn, x in enumerate(song):
            progress_reporter.step(rp * len(song) + nn + 1, total_steps)
            if x[0] != "r":
                if x[0][-1] == "*":
                    vol = boost
                    note = x[0][:-1]
                else:
                    vol = 1.0
                    note = x[0]
                if not note[-1].isdigit():
                    note += "4"  # default to fourth octave
                a = pitchhz[note]
                kn = keynum[note]
                a = a * 2 ** transpose
                if x[1] < 0:
                    b = length(-2.0 * x[1] / 3.0)
                else:
                    b = length(x[1])

                render2(a, b, vol, int(ex_pos), kn, note)
                ex_pos = ex_pos + b

            if x[0] == "r":
                b = length(x[1])
                ex_pos = ex_pos + b

    ##########################################################################
    # Write to output file (in WAV format)
    ##########################################################################
    peak = np.max(np.abs(data))
    if peak:
        data = data / (peak * 2.0)
    out_len = int(2.0 * 48000.0 + ex_pos + 0.5)
    data2 = np.zeros(out_len, dtype="<i2")
    data2[:] = 32000.0 * data[:out_len]
    with wave.open(fn, "wb") as output:
        output.setparams((1, 2, 48000, 0, "NONE", "Not Compressed"))
        output.writeframes(data2.tobytes())
    progress_reporter.finish()


##########################################################################
# Synthesize demo songs
##########################################################################

if __name__ == "__main__":
    print("*** SAMPLER ***")
    print()
    print("Creating Demo Songs... (this might take about a minute)")
    print()

    # make_wav((('c', 4), ('e', 4), ('g', 4), ('c5', 1)))
    make_wav(song1, fn="pysynth_scale.wav")
    # make_wav((('c1', 1), ('r', 1),('c2', 1), ('r', 1),('c3', 1), ('r', 1), ('c4', 1), ('r', 1),('c5', 1), ('r', 1),('c6', 1), ('r', 1),('c7', 1), ('r', 1),('c8', 1), ('r', 1), ('r', 1), ('r', 1), ('c4', 1),('r', 1), ('c4*', 1), ('r', 1), ('r', 1), ('r', 1), ('c4', 16), ('r', 1), ('c4', 8), ('r', 1),('c4', 4), ('r', 1),('c4', 1), ('r', 1),('c4', 1), ('r', 1)), fn = "all_cs.wav")

    make_wav(
        song4_rh, bpm=130, transpose=1, boost=1.15, repeat=1, fn="pysynth_bach_rh.wav"
    )
    make_wav(
        song4_lh, bpm=130, transpose=1, boost=1.15, repeat=1, fn="pysynth_bach_lh.wav"
    )
    mix_files("pysynth_bach_rh.wav", "pysynth_bach_lh.wav", "pysynth_bach.wav")

    # make_wav(song3, bpm = 132/2, leg_stac = 0.9, boost = 1.1, fn = "pysynth_chopin.wav")
