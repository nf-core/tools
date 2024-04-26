from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from rich.text import Text
from toolong.format_parser import FormatParser
from toolong.highlighter import LogHighlighter
from typing_extensions import TypeAlias

ParseResult: TypeAlias = "tuple[Optional[datetime], str, Text]"

MOVE_LOG_LEVEL_COL = True
LOG_LEVELS = {
    "DEBUG": ["dim white on black", "dim"],
    "INFO": ["bold black on green", ""],
    "WARN": ["bold black on yellow", "yellow"],
    "ERROR": ["bold black on red", "red"],
}


class LogFormat:
    def parse(self, line: str) -> ParseResult | None:
        raise NotImplementedError()


class NextflowLogFormat(LogFormat):
    """
    Formatter for regular Nextflow log files.

    Examples:

    Mar-24 00:11:47.302 [main] DEBUG nextflow.util.CustomThreadPool - Creating default thread pool > poolSize: 11; maxThreads: 1000
    Mar-24 00:12:04.942 [Task monitor] INFO  nextflow.Session - Execution cancelled -- Finishing pending tasks before exit
    """

    REGEX = re.compile(
        r"(?P<date>\w+-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) (?P<thread>\[.*\]?) (?P<log_level>\w+)\s+(?P<logger_name>[\w\.]+) - (?P<message>.*?)$"
    )

    highlighter = LogHighlighter()

    def parse(self, line: str) -> ParseResult | None:
        match = self.REGEX.fullmatch(line)
        if match is None:
            return None

        text = Text.from_ansi(line)
        groups = match.groupdict()
        if date := groups.get("date", None):
            timestamp = datetime.strptime(groups["date"], "%b-%d %H:%M:%S.%f")
            text.highlight_words([date], "not bold magenta")
        if thread := groups.get("thread", None):
            text.highlight_words([thread], "blue")
        if log_level := groups.get("log_level", None):
            text.highlight_words([f" {log_level} "], LOG_LEVELS[log_level][0])
        if logger_name := groups.get("logger_name", None):
            text.highlight_words([logger_name], "cyan")
        if process_name := groups.get("process_name", None):
            text.highlight_words([process_name], "bold cyan")
        if message := groups.get("message", None):
            text.highlight_words([message], "dim" if log_level == "DEBUG" else "")

        return timestamp, line, text


class NextflowLogAbortedProcessNames(LogFormat):
    """
    Formatter for process names when a pipeline is aborted.

    Example:

    The following lines:
    [process] NFCORE_RNASEQ:RNASEQ:ALIGN_STAR:STAR_ALIGN
    [process] NFCORE_RNASEQ:RNASEQ:ALIGN_STAR:BAM_SORT_STATS_SAMTOOLS:SAMTOOLS_SORT

    In blocks that look like this:

    Mar-12 23:56:10.538 [SIGINT handler] DEBUG nextflow.Session - Session aborted -- Cause: SIGINT
    Mar-12 23:56:10.572 [SIGINT handler] DEBUG nextflow.Session - The following nodes are still active:
    [process] NFCORE_RNASEQ:RNASEQ:ALIGN_STAR:STAR_ALIGN
      status=ACTIVE
      port 0: (queue) OPEN  ; channel: -
      port 1: (value) bound ; channel: -
      port 2: (value) bound ; channel: -
      port 3: (value) bound ; channel: star_ignore_sjdbgtf
      port 4: (value) bound ; channel: seq_platform
      port 5: (value) bound ; channel: seq_center
      port 6: (cntrl) -     ; channel: $

    [process] NFCORE_RNASEQ:RNASEQ:ALIGN_STAR:BAM_SORT_STATS_SAMTOOLS:SAMTOOLS_SORT
      status=ACTIVE
      port 0: (queue) OPEN  ; channel: -
      port 1: (cntrl) -     ; channel: $
    """

    REGEX = re.compile(r"^(?P<marker>\[process\]) (?P<process>.*?)(?P<process_name>[^:]+?)?$")
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


class NextflowLogAbortedProcessPorts(LogFormat):
    """
    Formatter for process names when a pipeline is aborted.

    Example:

    The following lines:
      port 0: (queue) OPEN  ; channel: -
      port 1: (value) bound ; channel: -
      port 2: (value) bound ; channel: -
      port 3: (value) bound ; channel: star_ignore_sjdbgtf

    In blocks that look like this:

    Mar-12 23:56:10.538 [SIGINT handler] DEBUG nextflow.Session - Session aborted -- Cause: SIGINT
    Mar-12 23:56:10.572 [SIGINT handler] DEBUG nextflow.Session - The following nodes are still active:
    [process] NFCORE_RNASEQ:RNASEQ:ALIGN_STAR:STAR_ALIGN
      status=ACTIVE
      port 0: (queue) OPEN  ; channel: -
      port 1: (value) bound ; channel: -
      port 2: (value) bound ; channel: -
      port 3: (value) bound ; channel: star_ignore_sjdbgtf
      port 4: (value) bound ; channel: seq_platform
      port 5: (value) bound ; channel: seq_center
      port 6: (cntrl) -     ; channel: $

    [process] NFCORE_RNASEQ:RNASEQ:ALIGN_STAR:BAM_SORT_STATS_SAMTOOLS:SAMTOOLS_SORT
      status=ACTIVE
      port 0: (queue) OPEN  ; channel: -
      port 1: (cntrl) -     ; channel: $
    """

    REGEX = re.compile(
        r"  (?P<port>port \d+): (?P<channel_type>\((value|queue|cntrl)\)) (?P<channel_state>\S+)\s+; channel: (?P<channel_name>.*?)$"
    )
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


class NextflowLogAbortedProcessStatus(LogFormat):
    """
    Formatter for process names when a pipeline is aborted.

    Example:

    The following lines:
      status=ACTIVE

    In blocks that look like this:

    Mar-12 23:56:10.538 [SIGINT handler] DEBUG nextflow.Session - Session aborted -- Cause: SIGINT
    Mar-12 23:56:10.572 [SIGINT handler] DEBUG nextflow.Session - The following nodes are still active:
    [process] NFCORE_RNASEQ:RNASEQ:ALIGN_STAR:STAR_ALIGN
      status=ACTIVE
      port 0: (queue) OPEN  ; channel: -
      port 1: (value) bound ; channel: -
      port 2: (value) bound ; channel: -
      port 3: (value) bound ; channel: star_ignore_sjdbgtf
      port 4: (value) bound ; channel: seq_platform
      port 5: (value) bound ; channel: seq_center
      port 6: (cntrl) -     ; channel: $

    [process] NFCORE_RNASEQ:RNASEQ:ALIGN_STAR:BAM_SORT_STATS_SAMTOOLS:SAMTOOLS_SORT
      status=ACTIVE
      port 0: (queue) OPEN  ; channel: -
      port 1: (cntrl) -     ; channel: $
    """

    REGEX = re.compile(r"^  status=(?P<status>.*?)?$")
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


class NextflowLogParsedScripts(LogFormat):
    """
    Formatter for parsed scriptp names.

    For example:

    Mar-24 00:12:03.547 [main] DEBUG nextflow.script.ScriptRunner - Parsed script files:
      Script_e2630658c898fe40: /Users/ewels/GitHub/nf-core/rnaseq/./workflows/rnaseq/../../modules/local/deseq2_qc/main.nf
      Script_56c7c9e8363ee20a: /Users/ewels/GitHub/nf-core/rnaseq/./workflows/rnaseq/../../subworkflows/local/quantify_pseudo_alignment/../../../modules/nf-core/custom/tx2gene/main.nf
    """

    REGEX = re.compile(r"^  (?P<script_id>Script_\w+:) (?P<script_path>.*?)$")
    highlighter = LogHighlighter()

    def parse(self, line: str) -> ParseResult | None:
        match = self.REGEX.fullmatch(line)
        if match is None:
            return None

        text = Text.from_ansi(line)
        groups = match.groupdict()
        if script_id := groups.get("script_id", None):
            text.highlight_words([script_id], "blue")
        if script_path := groups.get("script_path", None):
            text.highlight_words([script_path], "magenta")

        return None, line, text


def nextflow_format_parser(logfile_obj):
    is_nextflow = logfile_obj.name.startswith(".nextflow.log")

    class NextflowFormatParser(FormatParser):
        """Parses a log line."""

        def __init__(self) -> None:
            super().__init__()
            if is_nextflow:
                self._formats = [
                    NextflowLogFormat(),
                    NextflowLogAbortedProcessNames(),
                    NextflowLogAbortedProcessPorts(),
                    NextflowLogAbortedProcessStatus(),
                    NextflowLogParsedScripts(),
                ]
            self._log_status = ""

        def parse(self, line: str) -> ParseResult:
            """Use the toolong parser with custom formatters."""

            # Return if not a netflow log file
            if not is_nextflow:
                return super().parse(line)

            # Copied from toolong source, but without the default log parser
            if len(line) > 10_000:
                line = line[:10_000]
            parse_result = None
            if line.strip():
                for index, format in enumerate(self._formats):
                    parse_result = format.parse(line)
                    if parse_result is not None:
                        if index:
                            self._formats = [*self._formats[index:], *self._formats[:index]]
                        timestamp, line, text = parse_result
                        break

            if parse_result is None:
                timestamp = None
                line = line
                text = Text(line)

            # Custom formatting with log levels
            for logtype in LOG_LEVELS.keys():
                if logtype in line:
                    # Set log status for next lines, if multi-line
                    self._log_status = logtype
                    # Set the base stlying for this line
                    text.stylize_before(LOG_LEVELS[logtype][1])
                    # Move the "INFO" log level to the start of the line
                    if MOVE_LOG_LEVEL_COL:
                        line = "{} {}".format(
                            logtype,
                            line.replace(f" {logtype} ", ""),
                        )
                        logtype_str = f"[{LOG_LEVELS[logtype][0]}] {logtype: <5} [/] "
                        text = Text.from_markup(
                            logtype_str + text.markup.replace(f" {logtype} ", "[reset] [/]"),
                        )
                    # Return - on to next line
                    return timestamp, line, text

            # Multi-line log message - add colour character at start of line
            for logtype in LOG_LEVELS.keys():
                if self._log_status == logtype:
                    text = Text.from_markup(f"[{LOG_LEVELS[logtype][0]}] [/] " + text.markup)
                    text.stylize_before(LOG_LEVELS[logtype][1])

            return timestamp, line, text

    return NextflowFormatParser()
