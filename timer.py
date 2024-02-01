#!/usr/bin/env python3
"""Start a timer and display elapsed time on stdout

Pause by suspending the process (CTRL+Z)
Stop with KeyboardInterrupt (CTRL+C)
`timer.py --help` for commandline documentation
"""
import argparse
import datetime
from time import sleep
from typing import NamedTuple


########################
# constants / defaults #
########################

DEFAULT_INITIAL_TIME: str = "0:0:0.0"  # hours:minutes:seconds.microseconds
DEFAULT_UPDATE_INTERVAL: float = 0.01  # seconds
DEFAULT_OUTPUT_FORMAT: str = "{hours:02d}h : {minutes:02d}m : {seconds:02d}s : {microseconds}ms"
START_OF_CURRENT_LINE: str = "\r"  # carriage return
START_OF_PREV_LINE: str = "\033[F"  # ANSI escape code CPL (Cursor Previous Line)
# https://en.wikipedia.org/wiki/ANSI_escape_code#CSI_(Control_Sequence_Introducer)_sequences


#########
# timer #
#########

class TimeInfo(NamedTuple):
    """A named tuple containing (days, hours, minutes, seconds, microseconds).

    Initialise using one of:
        TimeInfo(days, hours, minutes, seconds, microseconds)
        TimeInfo.from_timedelta(timedelta)
        TimeInfo.from_timestr(str(timedelta))
    """
    days: int
    hours: int
    minutes: int
    seconds: int
    microseconds: int

    @classmethod
    def from_timedelta(cls, timedelta: datetime.timedelta) -> 'TimeInfo':
        """TimeInfo from datetime.timedelta

        This method avoids the additional string conversion overhead entailed by calling
        `TimeInfo.from_timestr(str(timedelta))`
        The modular arithmetic is the same used internally by timedelta for string conversion.
        """
        minutes, seconds = divmod(timedelta.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return TimeInfo(
            days=timedelta.days,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            microseconds=timedelta.microseconds,
        )

    @classmethod
    def from_timestr(cls, timestr: str) -> 'TimeInfo':
        """TimeInfo from string in the format of str(datetime.timedelta())

        The string format is 'DDD days, HH:MM:SS.microseconds'
        e.g. '12448 days, 16:04:53.742775'
        """
        for char in timestr:
            assert char in "01234567890:,. days"
        original_timestr = timestr  # copy for error handling
        default = "0"
        # days
        days_sep = " days, "
        if days_sep in timestr:
            days, _, timestr = timestr.partition(days_sep)
        else:
            days = default
        # hours, minutes, seconds
        colon_count = timestr.count(":")
        if colon_count == 0:
            hours, minutes, seconds = default, default, timestr
        elif colon_count == 1:
            hours = default
            minutes, seconds = timestr.split(":")
        elif colon_count == 2:
            hours, minutes, seconds = timestr.split(":")
        else:
            raise ValueError(
                f"Invalid number of ':' in timestr {original_timestr} ({colon_count})"
                ", may not be more than 2"
            )
        # microseconds
        if "." in seconds:
            seconds, _, microseconds = seconds.partition(".")
        else:
            microseconds = "0"
        timeinfo = cls(
            days=int(days),
            hours=int(hours),
            minutes=int(minutes),
            seconds=int(seconds),
            microseconds=int(microseconds),
        )
        return timeinfo


def timedelta_from_timestr(timestr: str) -> datetime.timedelta:
    timeinfo = TimeInfo.from_timestr(timestr)
    return datetime.timedelta(**timeinfo._asdict())


def timer(
    initial_time: datetime.timedelta = None,
    update_interval: float = None,
    suspend_margin: float = None,
    output_format: str = None,
    final_only: bool = False,
) -> datetime.timedelta:
    """Run until receiving a keyboard interrupt, continuously printing the elapsed time.

    `initial_time` the initially elapsed time
    `update_interval` how long to sleep for between prints
    `suspend_margin`
        if the actual duration between two prints is > update_interval + suspend_margin,
        then it is assumed that the program was suspended, so the elapsed time isn't counted
    `output_format`
        is a string ready to have output_format.format(...) called
        the variables provided to `format` are:
            days, hours, minutes, seconds, microseconds
    `final_only`
        if true, don't print continuously, instead only once when receiving a keyboard interrupt
    """
    if update_interval is None:
        update_interval = DEFAULT_UPDATE_INTERVAL
    if suspend_margin is None:
        suspend_margin = update_interval
    assert suspend_margin >= 0
    if output_format is None:
        output_format = DEFAULT_OUTPUT_FORMAT

    def msg(template=output_format, skip_printing=final_only):
        if skip_printing:
            return
        print(
            START_OF_PREV_LINE
            + template.format(
                **TimeInfo.from_timedelta(elapsed)._asdict()
            )
        )

    likely_suspended_timedelta = datetime.timedelta(seconds=update_interval + suspend_margin)
    elapsed = datetime.timedelta() if initial_time is None else initial_time
    start = datetime.datetime.now()
    if not final_only:
        # we print at the start of the prev line, to end on \n for shell job stopped msg
        # so we need an additional blank line to work with
        print()
    try:
        while True:
            sleep(update_interval)
            end = datetime.datetime.now()
            interval = end - start
            start = end

            # handle pausing the timer while the program is suspended
            # (with an acceptable margin of error)
            if interval > likely_suspended_timedelta:  # likely suspended
                if not final_only:
                    print()  # avoid overwriting shell job resume message
            else:  # not suspended
                elapsed += interval
            msg()
    except KeyboardInterrupt:
        if final_only:
            print()  # blank line for msg, which prints on previous line
        msg(skip_printing=False)  # overwrites ugly CTRL+C in output
        if not final_only:
            print("KeyboardInterrupt: exiting")  # line below time output
        return elapsed


#########################
# commandline interface #
#########################

def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--initial-time",
        type=timedelta_from_timestr,
        default=DEFAULT_INITIAL_TIME,
        metavar="STR",
        help="Initial time in the format: [DD days, ]HH:MM:SS.MS",
    )
    parser.add_argument(
        "-o",
        "--output-format",
        type=str,
        default=DEFAULT_OUTPUT_FORMAT,
        metavar="STR",
        help="STR.format will be called with hours, minutes, seconds, etc.",
    )
    parser.add_argument(
        "-u",
        "--update-interval",
        type=float,
        default=DEFAULT_UPDATE_INTERVAL,
        metavar="FLOAT",
        help="Sleep duration between prints.",
    )
    parser.add_argument(
        "-s",
        "--suspend-margin",
        type=float,
        default=None,
        metavar="FLOAT",
        help="If this duration elapses between prints, the process will assume\nit has been suspended. Defaults to double the update interval.",
    )
    parser.add_argument(
        "-f",
        "--final-only",
        action="store_true",
        help="If this flag is set, the timer will run silently until it receives\na keyboard interrupt, after which it will emit the elapsed time on stdout.",
    )
    return parser


########
# main #
########

def main():
    parser = get_parser()
    args = parser.parse_args()
    timer(**vars(args))


if __name__ == "__main__":
    main()
