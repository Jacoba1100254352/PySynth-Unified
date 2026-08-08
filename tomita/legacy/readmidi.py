#!/usr/bin/env python

# Read MIDI file track and synthesize with PySynth A

# Usage:

# python readmidi.py file.mid [tracknum] [file.wav] [--sound=a|b|c|d|e|p|s|samp|beeper] [--config=pysynth.json]

# Based on code from https://github.com/osakared/midifile.py
# which appears to be based on
# https://github.com/gasman/jasmid/blob/master/midifile.js

# Original license:

"""
Copyright (c) 2014, Thomas J. Webb
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import io
import struct

from tomita.synth import config_from_args, make_wav


class Note(object):
    "Represents a single MIDI note"

    note_names = ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"]

    def __init__(self, channel, pitch, velocity, start, duration=0):
        self.channel = channel
        self.pitch = pitch
        self.velocity = velocity
        self.start = start
        self.duration = duration

    def __str__(self):
        s = Note.note_names[(self.pitch - 9) % 12]
        s += str(self.pitch // 12 - 1)
        s += " " + str(self.velocity)
        s += " " + str(self.start) + " " + str(self.start + self.duration) + " "
        return s

    def get_end(self):
        return self.start + self.duration


class MidiFile(object):
    "Represents the notes in a MIDI file"

    def read_byte(self, file):
        data = file.read(1)
        if len(data) != 1:
            raise ValueError("unexpected end of file")
        return data[0]

    def read_exact(self, file, length):
        data = file.read(length)
        if len(data) != length:
            raise ValueError("unexpected end of file")
        return data

    def read_variable_length(self, file, counter):
        if counter < 1:
            raise ValueError("truncated variable-length value")
        num = self.read_byte(file)
        counter -= 1
        byte_count = 1

        if num & 0x80:
            num = num & 0x7F
            while True:
                if counter < 1 or byte_count >= 4:
                    raise ValueError("invalid variable-length value")
                byte_count += 1
                counter -= 1
                c = self.read_byte(file)
                num = (num << 7) + (c & 0x7F)
                if not (c & 0x80):
                    break

        return (num, counter)

    def __init__(self, file_name, verbose=False):
        self.tempo = 120
        self.file_name = file_name
        self.format = 0
        self.track_count = 0
        self.time_division = 0
        self.tracks = []
        try:
            with open(file_name, "rb") as file:
                self._read(file, verbose)
        except OSError:
            raise
        except (
            IndexError,
            TypeError,
            ValueError,
            ZeroDivisionError,
            struct.error,
        ) as exc:
            raise ValueError(
                "cannot parse MIDI file %s: %s" % (file_name, exc)
            ) from exc

    def _read(self, file, verbose):
        if self.read_exact(file, 4) != b"MThd":
            raise ValueError("missing MThd header")
        size = struct.unpack(">I", self.read_exact(file, 4))[0]
        if size != 6:
            raise ValueError("header size is %u instead of 6" % size)
        self.format = struct.unpack(">H", self.read_exact(file, 2))[0]
        self.track_count = struct.unpack(">H", self.read_exact(file, 2))[0]
        self.time_division = struct.unpack(">H", self.read_exact(file, 2))[0]
        if self.format not in (0, 1, 2):
            raise ValueError("unsupported MIDI format %u" % self.format)
        if self.time_division == 0:
            raise ValueError("time division cannot be zero")
        if self.time_division & 0x8000:
            raise ValueError("SMPTE time division is not supported")

        self.tracks = [[] for _ in range(self.track_count)]
        for track_number, track in enumerate(self.tracks):
            if self.read_exact(file, 4) != b"MTrk":
                raise ValueError(
                    "track %u is missing its MTrk header" % track_number
                )
            size = struct.unpack(">I", self.read_exact(file, 4))[0]
            data = self.read_exact(file, size)
            self._read_track(io.BytesIO(data), track, verbose)

    def _read_track(self, file, track, verbose):
        abs_time = 0.0
        remaining = len(file.getbuffer())
        last_flag = None
        while remaining > 0:
            delta, remaining = self.read_variable_length(file, remaining)
            abs_time += delta / float(self.time_division)

            if remaining < 1:
                raise ValueError("track ends before an event")
            flag = self.read_byte(file)
            remaining -= 1

            if flag in (0xF0, 0xF7):
                length, remaining = self.read_variable_length(file, remaining)
                if length > remaining:
                    raise ValueError("system-exclusive event exceeds its track")
                self.read_exact(file, length)
                remaining -= length
                continue

            if flag == 0xFF:
                if remaining < 1:
                    raise ValueError("meta event has no type")
                event_type = self.read_byte(file)
                remaining -= 1
                length, remaining = self.read_variable_length(file, remaining)
                if length > remaining:
                    raise ValueError("meta event exceeds its track")
                message = self.read_exact(file, length)
                remaining -= length
                if event_type == 0x2F:
                    if length != 0:
                        raise ValueError("end-of-track event has data")
                    break
                if event_type == 0x51:
                    if length != 3:
                        raise ValueError("tempo event must contain three bytes")
                    microseconds = int.from_bytes(message, "big")
                    if microseconds == 0:
                        raise ValueError("tempo event cannot be zero")
                    self.tempo = 60000000.0 / microseconds
                    if verbose:
                        print("tempo =", self.tempo, "bpm")
                elif verbose:
                    print("Meta:", event_type, length, message)
                continue

            if flag & 0x80:
                if flag >= 0xF0:
                    raise ValueError("unsupported system event 0x%02x" % flag)
                type_and_channel = flag
                last_flag = flag
                if remaining < 1:
                    raise ValueError("channel event has no data")
                param1 = self.read_byte(file)
                remaining -= 1
            else:
                if last_flag is None:
                    raise ValueError("running status appears before a channel event")
                type_and_channel = last_flag
                param1 = flag

            if param1 & 0x80:
                raise ValueError("channel event data byte has its status bit set")

            event_type = (type_and_channel & 0xF0) >> 4
            channel = type_and_channel & 0xF
            if event_type in (0xC, 0xD):
                if verbose and event_type == 0xC:
                    print("program change, channel", channel, "=", param1)
                continue
            if remaining < 1:
                raise ValueError("channel event is missing its second data byte")
            param2 = self.read_byte(file)
            remaining -= 1
            if param2 & 0x80:
                raise ValueError("channel event data byte has its status bit set")

            if event_type == 0x9:
                track.append(Note(channel, param1, param2, abs_time))
            elif event_type == 0x8:
                for note in reversed(track):
                    if note.channel == channel and note.pitch == param1:
                        note.duration = abs_time - note.start
                        break

    def __str__(self):
        s = ""
        for i, track in enumerate(self.tracks):
            s += "Track " + str(i + 1) + "\n"
            for note in track:
                s += str(note) + "\n"
        return s


def getdur(a, b):
    "Calculate note length for PySynth"
    if b <= a:
        raise ValueError("MIDI note duration must be positive")
    return 4 / (b - a)


def midi_to_song(file_name, tracknum=None, verbose=False):
    m = MidiFile(file_name, verbose=verbose)
    if tracknum is None:
        tracknum = next((idx for idx, track in enumerate(m.tracks) if track), None)
        if tracknum is None:
            raise ValueError("no note tracks found in %s" % file_name)
    if tracknum < 0 or tracknum >= len(m.tracks):
        raise ValueError(
            "track %d not found; file has %u tracks" % (tracknum, len(m.tracks))
        )
    if not m.tracks[tracknum]:
        raise ValueError("track %u contains no notes" % tracknum)

    if verbose:
        print()
        print("Track first notes")
        for t, n in enumerate(m.tracks):
            if len(n) > 0:
                print(t, n[0], len(n))

    song = []
    notes = {}

    def getnote(q):
        for x in q.keys():
            if q[x] >= 0:
                return x
        return None

    def gettotal():
        t = 0
        for x, y in song:
            t += 4 / y
        return t

    for n in m.tracks[tracknum]:
        if verbose:
            print(n)
        nn = str(n).split()
        start, stop = float(nn[2]), float(nn[3])

        if start != stop:  # note ends because of NOTE OFF event
            if start - gettotal() > 0:
                song.append(("r", getdur(gettotal(), start)))
                if verbose:
                    print("r1")
            song.append((nn[0].lower(), getdur(start, stop)))
        elif (
            float(nn[1]) == 0 and notes.get(nn[0].lower(), -1) >= 0
        ):  # note ends because of NOTE ON with velocity = 0
            if notes[nn[0].lower()] - gettotal() > 0:
                song.append(("r", getdur(gettotal(), notes[nn[0].lower()])))
                if verbose:
                    print("r2")
            song.append((nn[0].lower(), getdur(notes[nn[0].lower()], start)))
            notes[nn[0].lower()] = -1
        elif (
            float(nn[1]) > 0 and notes.get(nn[0].lower(), -1) == -1
        ):  # note ends because of new note
            old = getnote(notes)
            if old is not None:
                if notes[old] != start:
                    song.append((old, getdur(notes[old], start)))
                notes[old] = -1
            elif start - gettotal() > 0:
                song.append(("r", getdur(gettotal(), start)))
                if verbose:
                    print("r3")
            notes[nn[0].lower()] = start
    if verbose:
        print()
        print("Song")
        print(song)
    return song, m.tempo


def main(argv=None):
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("Usage: readmidi.py file.mid [tracknum] [file.wav] [--sound=...] [--config=pysynth.json]")
    synth_config = config_from_args(["readmidi.py"] + argv)
    if len(argv) > 1 and not argv[1].startswith("--"):
        tracknum = int(argv[1])
    else:
        tracknum = 1
    if len(argv) > 2 and not argv[2].startswith("--"):
        filename = argv[2]
    else:
        filename = "midi.wav"
    song, tempo = midi_to_song(argv[0], tracknum=tracknum, verbose=True)
    make_wav(song, config=synth_config, fn=filename, bpm=tempo)


if __name__ == "__main__":
    main()
