from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from rich.text import Text
from toolong import timestamps
from toolong.highlighter import LogHighlighter
from typing_extensions import TypeAlias

ParseResult: TypeAlias = "tuple[Optional[datetime], str, Text]"


class LogFormat:
    def parse(self, line: str) -> ParseResult | None:
        raise NotImplementedError()


class NextflowRegexLogFormatOne(LogFormat):
    REGEX = re.compile(".*?")
    LOG_LEVELS = {
        "DEBUG": ["dim white on black", ""],
        "INFO": ["bold black on green", "on #042C07"],
        "WARN": ["bold black on yellow", "on #44450E"],
        "ERROR": ["bold black on red", "on #470005"],
    }

    highlighter = LogHighlighter()

    def parse(self, line: str) -> ParseResult | None:
        match = self.REGEX.fullmatch(line)
        if match is None:
            return None

        text = Text.from_ansi(line)
        groups = match.groupdict()
        if date := groups.get("date", None):
            _, timestamp = timestamps.parse(groups["date"])
            text.highlight_words([date], "not bold magenta")
        if thread := groups.get("thread", None):
            text.highlight_words([thread], "blue")
        if log_level := groups.get("log_level", None):
            text.highlight_words([f" {log_level} "], self.LOG_LEVELS[log_level][0])
            text.stylize_before(self.LOG_LEVELS[log_level][1])
        if logger_name := groups.get("logger_name", None):
            text.highlight_words([logger_name], "cyan")
        if process_name := groups.get("process_name", None):
            text.highlight_words([process_name], "bold cyan")
        if message := groups.get("message", None):
            text.highlight_words([message], "dim" if log_level == "DEBUG" else "")

        return None, line, text


class NextflowRegexLogFormatTwo(LogFormat):
    REGEX = re.compile(".*?")
    highlighter = LogHighlighter()

    def parse(self, line: str) -> ParseResult | None:
        match = self.REGEX.fullmatch(line)
        if match is None:
            return None

        text = Text.from_ansi(line)
        text.stylize_before("dim")
        groups = match.groupdict()
        if process := groups.get("process", None):
            text.highlight_words([process], "blue not dim")
        if process_name := groups.get("process_name", None):
            text.highlight_words([process_name], "bold cyan not dim")

        return None, line, text


class NextflowRegexLogFormatThree(LogFormat):
    REGEX = re.compile(".*?")
    CHANNEL_TYPES = {
        "(value)": "green",
        "(cntrl)": "yellow",
        "(queue)": "magenta",
    }
    highlighter = LogHighlighter()

    def parse(self, line: str) -> ParseResult | None:
        match = self.REGEX.fullmatch(line)
        if match is None:
            return None

        text = Text.from_ansi(line)
        groups = match.groupdict()
        if port := groups.get("port", None):
            text.highlight_words([port], "blue")
        if channel_type := groups.get("channel_type", None):
            text.highlight_words([channel_type], self.CHANNEL_TYPES[channel_type])
        if channel_state := groups.get("channel_state", None):
            text.highlight_words([channel_state], "cyan" if channel_state == "OPEN" else "yellow")
        text.highlight_words(["; channel:"], "dim")
        if channel_name := groups.get("channel_name", None):
            text.highlight_words([channel_name], "cyan")

        return None, line, text


class NextflowRegexLogFormatFour(LogFormat):
    REGEX = re.compile(".*?")
    highlighter = LogHighlighter()

    def parse(self, line: str) -> ParseResult | None:
        match = self.REGEX.fullmatch(line)
        if match is None:
            return None

        text = Text.from_ansi(line)
        text.stylize_before("dim")
        groups = match.groupdict()
        text.highlight_words(["status="], "dim")
        if status := groups.get("status", None):
            text.highlight_words([status], "cyan not dim")

        return None, line, text


class NextflowRegexLogFormatFive(LogFormat):
    REGEX = re.compile(".*?")
    highlighter = LogHighlighter()

    def parse(self, line: str) -> ParseResult | None:
        match = self.REGEX.fullmatch(line)
        if match is None:
            return None

        text = Text.from_ansi(line)
        text.stylize_before("dim")
        groups = match.groupdict()
        if script_id := groups.get("script_id", None):
            text.highlight_words([script_id], "blue")
        if script_path := groups.get("script_path", None):
            text.highlight_words([script_path], "magenta")

        return None, line, text


class NextflowLogFormat(NextflowRegexLogFormatOne):
    REGEX = re.compile(
        r"(?P<date>\w+-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) (?P<thread>\[.*\]?) (?P<log_level>\w+)\s+(?P<logger_name>[\w\.]+) - (?P<message>.*?)$"
    )


class NextflowLogFormatActiveProcess(NextflowRegexLogFormatTwo):
    REGEX = re.compile(r"^(?P<marker>\[process\]) (?P<process>.*?)(?P<process_name>[^:]+?)?$")


class NextflowLogFormatActiveProcessDetails(NextflowRegexLogFormatThree):
    REGEX = re.compile(
        r"  (?P<port>port \d+): (?P<channel_type>\((value|queue|cntrl)\)) (?P<channel_state>\S+)\s+; channel: (?P<channel_name>.*?)$"
    )


class NextflowLogFormatActiveProcessStatus(NextflowRegexLogFormatFour):
    REGEX = re.compile(r"^  status=(?P<status>.*?)?$")


class NextflowLogFormatScriptParse(NextflowRegexLogFormatFive):
    REGEX = re.compile(r"^  (?P<script_id>Script_\w+:) (?P<script_path>.*?)$")


def nextflow_formatters(formats):
    return [
        NextflowLogFormat(),
        NextflowLogFormatActiveProcess(),
        NextflowLogFormatActiveProcessDetails(),
        NextflowLogFormatActiveProcessStatus(),
        NextflowLogFormatScriptParse(),
    ]


def nextflow_format_parser(format_parser):
    class FormatParser(format_parser):
        """Parses a log line."""

        def __init__(self) -> None:
            super().__init__()
            self._log_status = ""

        def parse(self, line: str) -> ParseResult:
            """Parse a line."""

            for logtype in ["DEBUG", "INFO", "WARN", "ERROR"]:
                if logtype in line:
                    self._log_status = logtype
                    return super().parse(line)
            text = Text(line)
            if text.plain == text.markup:
                if self._log_status == "DEBUG":
                    text.stylize("dim")
                if self._log_status == "WARN":
                    text.stylize("yellow")
                if self._log_status == "ERROR":
                    text.stylize("red")
            return None, line, text

    return FormatParser
