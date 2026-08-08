"""Progress reporting helpers shared by the PySynth renderers."""

from __future__ import print_function

import math
import numbers
import time


class ProgressConfig(object):
    """Controls how often rendering progress is printed."""

    def __init__(
        self,
        enabled=True,
        every=None,
        percent=None,
        max_updates=6,
        small_threshold=12,
        show_time=False,
    ):
        if not isinstance(enabled, bool):
            raise ValueError("progress enabled must be true or false")
        if not isinstance(show_time, bool):
            raise ValueError("progress show_time must be true or false")
        if every is not None and percent is not None:
            raise ValueError("progress every and percent cannot both be set")
        if every is not None:
            if isinstance(every, bool) or not isinstance(every, numbers.Integral):
                raise ValueError("progress every must be an integer")
            if every < 1:
                raise ValueError("progress every must be at least 1")
            every = int(every)
        if percent is not None:
            if isinstance(percent, bool) or not isinstance(percent, numbers.Real):
                raise ValueError("progress percent must be a number")
            percent = float(percent)
            if not math.isfinite(percent) or percent <= 0 or percent > 100:
                raise ValueError("progress percent must be greater than 0 and at most 100")
        if isinstance(max_updates, bool) or not isinstance(max_updates, numbers.Integral):
            raise ValueError("progress max_updates must be an integer")
        if max_updates < 1:
            raise ValueError("progress max_updates must be at least 1")
        if (
            isinstance(small_threshold, bool)
            or not isinstance(small_threshold, numbers.Integral)
        ):
            raise ValueError("progress small_threshold must be an integer")
        if small_threshold < 0:
            raise ValueError("progress small_threshold cannot be negative")

        self.enabled = enabled
        self.every = every
        self.percent = percent
        self.max_updates = int(max_updates)
        self.small_threshold = int(small_threshold)
        self.show_time = show_time

    @classmethod
    def from_value(cls, value=None):
        if isinstance(value, cls):
            return value
        if value is None:
            return cls()
        if isinstance(value, bool):
            return cls(enabled=value)
        if isinstance(value, numbers.Integral):
            return cls(every=value)
        if isinstance(value, numbers.Real):
            return cls(percent=value)
        if isinstance(value, dict):
            allowed = {
                "enabled",
                "every",
                "percent",
                "max_updates",
                "small_threshold",
                "show_time",
            }
            unknown = sorted(str(key) for key in value if key not in allowed)
            if unknown:
                raise ValueError(
                    "unknown progress option%s: %s"
                    % ("s" if len(unknown) > 1 else "", ", ".join(unknown))
                )
            return cls(**value)
        raise TypeError("unsupported progress config: %r" % (value,))

    def interval(self, total):
        total = max(0, int(total))
        if total <= 1:
            return 1
        if self.every is not None:
            return max(1, int(self.every))
        if self.percent is not None:
            return max(1, int(math.ceil(total * (float(self.percent) / 100.0))))
        if total <= self.small_threshold:
            return 1
        return max(1, int(math.ceil(float(total) / float(self.max_updates))))

    def should_report(self, current, total):
        if not self.enabled:
            return False
        current = int(current)
        total = int(total)
        if current < 1 or total < 1:
            return False
        if current == 1 or current >= total:
            return True
        return current % self.interval(total) == 0


class ProgressReporter(object):
    """Prints PySynth-compatible render progress."""

    def __init__(self, filename, config=None, silent=False):
        self.filename = filename
        self.config = ProgressConfig.from_value(config)
        self.started_at = None
        if silent:
            self.config = ProgressConfig(enabled=False)

    @property
    def enabled(self):
        return self.config.enabled

    def start(self):
        if self.enabled:
            self.started_at = time.monotonic()
            print("Writing to file", self.filename)

    def step(self, current, total):
        if self.config.should_report(current, total):
            line = "[%u/%u]" % (current, total)
            if self.config.show_time and self.started_at and current > 0:
                elapsed = time.monotonic() - self.started_at
                remaining = max(total - current, 0) * (elapsed / float(current))
                line += " elapsed %s eta %s" % (
                    format_duration(elapsed),
                    format_duration(remaining),
                )
            print(line)

    def finish(self):
        if self.enabled:
            print()


def format_duration(seconds):
    seconds = max(0, int(round(seconds)))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return "%u:%02u:%02u" % (hours, minutes, seconds)
    return "%u:%02u" % (minutes, seconds)
