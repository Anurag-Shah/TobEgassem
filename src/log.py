from typing import Any

from colorama import Fore
from datetime import datetime

from utils import *

_DATE_FORMAT: str = "%Y-%m-%dT%H:%M:%S.%fZ"


class LogLevel:
    name: str
    color: str
    level: int

    def __init__(self, name: str, color: str, level: int) -> None:
        self.name = name
        self.color = color
        self.level = level

    def __str__(self) -> str:
        return self.display()

    def display(self) -> str:
        return self.display_no_reset() + Fore.RESET

    def display_no_reset(self) -> str:
        if not self.color or not self.name:
            return ""
        return self.color + self.name


_ERROR = LogLevel("ERROR", Fore.LIGHTRED_EX, 1)
_WARN = LogLevel(" WARN", Fore.LIGHTYELLOW_EX, 2)
_INFO = LogLevel(" INFO", Fore.LIGHTGREEN_EX, 3)
_DEBUG = LogLevel("DEBUG", Fore.BLUE, 4)
_TRACE = LogLevel("TRACE", Fore.LIGHTMAGENTA_EX, 5)


class Logger:
    use_ansi_colors: bool = False
    log_level: int = 0
    levels: list[LogLevel] = []

    def __init__(self, levels: list[LogLevel]) -> None:
        self.levels = levels
        # for level in levels:
        #     setattr(self, level.name.strip().lower(), self._log_dec(level))

    def set_use_ansi_colors(self, b: Any) -> None:
        self.use_ansi_colors = to_bool(b)

    def set_log_level(self, level: int) -> None:
        level = int(level)
        level = 0 if level < 0 else level
        _max = max([l.level for l in self.levels])
        level = _max if level > _max else level
        self.log_level = level

    # ------------------------------------------- Logs ------------------------------------------- #

    def log(self, level: LogLevel, log: str, trace: str = "") -> None:
        if self.log_level >= level.level:
            _level_str = level.display() if self.use_ansi_colors else level.name
            print(self._time(), _level_str, self._trace(trace), log)

    def error(self, log: str, trace: str = "") -> None:
        self.log(_ERROR, log, trace)

    def warn(self, log: str, trace: str = "") -> None:
        self.log(_WARN, log, trace)

    def info(self, log: str, trace: str = "") -> None:
        self.log(_INFO, log, trace)

    def debug(self, log: str, trace: str = "") -> None:
        self.log(_DEBUG, log, trace)

    def trace(self, log: str, trace: str = "") -> None:
        self.log(_TRACE, log, trace)

    # ------------------------------------------- Utils ------------------------------------------ #

    def _color(self, s: str, c: str) -> str:
        if not self.use_ansi_colors:
            return s
        return c + s + Fore.RESET

    # TODO: Add automatic tracing
    def _trace(self, trace: str = "") -> str:
        trace_ = f"tob::{trace}:" if trace else "tob:"
        return self._color(trace_, Fore.LIGHTBLACK_EX)

    def _time(self) -> str:
        time_ = datetime.now().strftime(_DATE_FORMAT)
        return self._color(time_, Fore.LIGHTBLACK_EX)

    def _log_dec(self, level: LogLevel):
        def _log(self, log: str, trace: str = "") -> None:
            self._log(level, log, trace)

        return _log


_levels = [
    _ERROR,
    _WARN,
    _INFO,
    _DEBUG,
    _TRACE,
]
log = Logger(_levels)
