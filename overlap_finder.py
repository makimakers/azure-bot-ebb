import re
import dateutil.parser as dtp
from datetime import datetime as dt
from datetime import timedelta
from intervaltree import Interval, IntervalTree
from warnings import warn


FORMAT_MSG = ("Expected format : '<NAME>: <DATE> <TIME> <INTERVAL END>;'.\n\n"
              "For TIME, the hours and mins MUST be separated by ':' or time will "
              "be interpreted wrongly.\n\n"
              "Type 'example' for a formatted example input.\n\n")

EXAMPLE_MSG = ("Bob: 02 feb 10:00 + 2h15m;\n\n"
               "Bob: 02 feb 13:00-16:30;\n\n"
               "Joe: 2 feb 2:00pm-4:00pm;\n\n"
               "Sally: 02 feb 3:00p - 03 feb 1:00a")


def find_all_common_intervals(interval_list):
    """
    Finds common intervals (overlapping regions) and labels common intervals with
    intersecting intervals' data attribute (e.g. the user id)
    :param interval_list: list of Interval objects
    :return: a dict (key: Interval, value: set of user_ids which share that interval)
    """
    overlap_dict = dict()
    interval_tree = IntervalTree(interval_list)
    
    for interval in interval_tree.items():
        other_intervals = find_other_intervals_which_overlap(interval_tree, interval)
        for other_interval in other_intervals:
            add_new_overlap_to_dict(interval, other_interval, overlap_dict)

    return overlap_dict


def find_other_intervals_which_overlap(tree, interval):
    """
    Find intervals in tree that intersect with interval.
    :param tree: Interval Tree
    :param interval: Interval Object
    :return: set of Interval objects that intersect with interval
    """
    tree.remove(interval)
    result = tree.search(interval.begin, interval.end) # returns a set
    return result


def add_new_overlap_to_dict(interval_a, interval_b, overlap_dict):
    """
    Modifies overlap_dict to contain the overlapping region between interval_a and
    interval b.
    :param interval_a: Interval
    :param interval_b: Interval
    :param overlap_dict: dict where key is Interval representing overlap, value is set of
    data attributes associated with that overlap.
    :return:
    """
    overlap = find_overlap(interval_a, interval_b)
    if overlap is None:
        return

    if overlap in overlap_dict.keys():
        overlap_data = overlap_dict[overlap]
        overlap_data |= {interval_a.data, interval_b.data}  # update set
    else:
        overlap_dict[overlap] = {interval_a.data, interval_b.data}


def find_overlap(interval_a, interval_b):
    """
    Find overlapping region between two intervals.
    :param interval_a: Interval
    :param interval_b: Interval
    :return: Interval that represents the overlapping region.
    """
    a_begin = interval_a.begin
    a_end = interval_a.end
    b_begin = interval_b.begin
    b_end = interval_b.end
    
    if a_end < a_begin:
        a_begin, a_end = a_end, a_begin
        warn("interval_a: interval end is before begin")
    if b_end < b_begin:
        b_begin, b_end = b_end, b_begin
        warn("interval_b: interval end is before begin")

    if b_end < a_begin or a_end < b_begin:
        return None
    common_begin = max(a_begin, b_begin)
    common_end = min(a_end, b_end)
    return Interval(common_begin, common_end)


def sortby_start(interval_keys):
    """
    Sort keys based on start of interval, in ascending order
    :param interval_keys: list of keys.
    :return: sorted keys list.
    """
    ref = []
    for interval in interval_keys:
        ref.append(interval.begin)
    zipped = zip(ref, interval_keys)
    sorted_keys = [x for _, x in sorted(zipped)]  # sorts based on ref.

    return sorted_keys


def format_overlaps(overlap_dict):
    """
    Formats a string representation of a dict where the key is a Datetime Interval
    and the value is the set of associated user names.
    Note that this renders v different on the Bot Emulator and on Telegram.

    :param overlap_dict. key is Datetime Interval, value is set of userids.
    :return: string.
    """
    sorted_keys = sortby_start(overlap_dict.keys())
    # TODO: include other sort options. e.g. sort by duration.
    lines = []
    lines.append("Common dates & times:\n\n")
    
    for interval in sorted_keys:

        userids = ", ".join(overlap_dict[interval])
        dur = interval.end - interval.begin
        dur_in_min = dur.total_seconds() / 60

        lines.append(f"{interval.begin.strftime('**%d %b, %I:%M%p')}"
                     f" - {interval.end.strftime('%d %b, %I:%M%p')}"
                     f" ({dur_in_min:.0f}mins)**")

        lines.append(f"   IDs: {str(userids)}")
    fstring = "\n\n".join(lines)
    
    return fstring


def parse_dur(time_str):
    regex = re.compile(r'((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')
    parts = regex.match(time_str)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in parts.items():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)


def parse_dt_string(s):
    """
    Parses a formatted string into a list of datetime interval objects.
    
    Expected format : "<NAME>: <DATE> <TIME> <ABSOLUTE or RELATIVE INTERVAL END>.
    For TIME, the hour and min MUST be separated by ':', e.g. "15:00". not "15.00"
    Use ';' as a separator between labelled intervals.
    The colons and semicolons are compulsory.

    example:
    "andy: 02 feb, 1pm+2h15m;
    baron: 02 feb, 2:00pm - 3:00pm;
    charmaine: 2 feb 15:15-17:30"

    known issues:
    hours and mins MUST be separated by ':'(dateutil's default).
    '%d%d%d%d' and '%d%d.%d%dpm', e.g. '1500' or '3.00', is not an accepted time format.

    :param s: string.
    :returns: list of Intervals.
    """
    intervals = []

    lines = s.split(';')  # separate lines of labelled datetime intervals.

    try:
        # https://dateutil.readthedocs.io/en/stable/parser.html
        parser_info = dtp.parserinfo(dayfirst=True)
        for line in lines:
            parts = line.strip().split(':', 1)

            name = parts[0].strip()
            interval_str = parts[1].strip()

            if interval_str.find('+') > 0:
                # '+' was found implying relative end-time was specified.
                interval_parts = interval_str.split('+')
                datetime_str = interval_parts[0].strip()
                dur_str = interval_parts[1].strip()
                dur = parse_dur(dur_str)  # timedelta
                start_dt_str = datetime_str
                if start_dt_str.find(':') < 0:
                    raise ValueError(FORMAT_MSG)
                start_dt = dtp.parse(start_dt_str, parserinfo=parser_info)

                # auto set year
                if dt.today().month > start_dt.month:
                    # user likely referring to next year
                    start_dt = start_dt.replace(year=dt.today().year+1)
                else:
                    start_dt = start_dt.replace(year=dt.today().year)
                end_dt = start_dt + dur
            elif interval_str.find('-') > 0:
                # '-' was found implying absolute end-time was specified.
                interval_parts = interval_str.split('-')
                start_dt_str = interval_parts[0].strip()
                if start_dt_str.find(':') < 0:
                    raise ValueError(FORMAT_MSG)
                start_dt = dtp.parse(start_dt_str, parserinfo=parser_info)

                # determine is interval's end was specified as datetime or time.
                end_str = interval_parts[1].strip()
                if end_str.find(' ') > 0:
                    # date was specified. e.g. '2 feb 13:00'
                    end_dt_str = end_str
                    end_dt = dtp.parse(end_dt_str, parserinfo=parser_info)
                else:
                    # only time was specified.
                    if end_str.find(':') < 0:
                        raise ValueError(FORMAT_MSG)
                    tmp_dt = dtp.parse(end_str, parserinfo=parser_info)  # for time.
                    end_dt = start_dt  # for base dt info, which will be replaced.
                    if tmp_dt.hour < start_dt.hour:
                        # end-time refers to next day.
                        end_dt += timedelta(days=1)
                    else:
                        end_dt = end_dt.replace(hour=tmp_dt.hour, minute=tmp_dt.minute)

                # auto set year
                if dt.today().month > start_dt.month:
                    # user likely referring to next year
                    start_dt = start_dt.replace(year=dt.today().year + 1)
                    end_dt = end_dt.replace(year=dt.today().year + 1)
                else:
                    start_dt = start_dt.replace(year=dt.today().year)
                    end_dt = end_dt.replace(year=dt.today().year)
            else:
                raise ValueError(FORMAT_MSG)

            interval = Interval(start_dt, end_dt, name)
            print(interval) # debugging statement
            print()
            intervals.append(interval)
    except IndexError:
        raise IndexError(FORMAT_MSG)

    return intervals


def help_msg():
    msg = ("Hi! I can help you calculate common time slots from a list of free time "
           "slots associated w each named person. As long as 2 or more persons "
           "have a common time slot, I will show you their common time slots!."
           "\n\n\n\n")

    return msg + FORMAT_MSG


def example_msg():
    return EXAMPLE_MSG

