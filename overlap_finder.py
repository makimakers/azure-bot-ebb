import re
import dateutil.parser as dtp
from datetime import datetime as dt
from datetime import timedelta
from intervaltree import Interval, IntervalTree
from warnings import warn

HELP_MSG = ("Hi! I can help you find ALL the common time slots from a list of free time "
            "slots tagged to each named person.\n\n")

FORMAT_MSG = ("Expected format:\n"
              "NAME1: DATE TIME_SLOT1, DATE TIME_SLOT2.\n"
              "NAME2: DATE TIME_SLOT1, DATE TIME_SLOT2.\n\n"
              "For TIME, hours and mins MUST be separated by ':' or time will "
              "be interpreted wrongly.\n"
              "Type 'example' for example input. Copy-paste example input to see what "
              "I can do! You can specify ur timeslots in many ways :).\n")

EXAMPLE_MSG = ("Amy-likes-12h:\n"
               "1 may 1:00pm-4:30pm,\n"
               "2 may 10:00am-12:00pm,\n"
               "3 may 6:00pm-7:00pm.\n"
               "Bob-is-Vague:\n"
               "2 may afternoon,\n"
               "2 may supper.\n"
               "Cat-is-Soldier:\n"
               "2 may 11:00-15:00,\n"
               "2 may 19:00-20:00.\n"
               "Dan-likes-Relativity:\n"
               "2 may 13:00+2h30m.\n"
               "Elf-is-American:\n"
               "may 2 1:00pm-3:30pm."
               )

GENERAL_TIMESLOTS = {'breakfast', 'brunch', 'lunch', 'dinner', 'supper', 'morning',
                     'afternoon', 'night'}

ZERO_DUR = timedelta()


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
        for overlap in list(overlap_dict):
            # compare interval against existing overlaps.
            add_overlap_to_dict(interval, overlap, overlap_dict)

        other_intervals = find_other_intervals_which_overlap(interval_tree, interval)
        for other_interval in other_intervals:
            # compare interval against other original intervals in the tree.
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
    :param interval_a: Interval whose data attribute is not None.
    :param interval_b: Interval whose data attribute is not None.
    :param overlap_dict: dict where key is Interval representing overlap, value is set of
    data attributes associated with that overlap.
    :return:
    """
    if interval_a.data != interval_b.data:
        overlap = find_overlap(interval_a, interval_b)
        if overlap is None or (overlap.end - overlap.begin) == ZERO_DUR:  # 0 duration
            return

        if overlap in overlap_dict.keys():
            overlap_data = overlap_dict[overlap]
            overlap_data |= {interval_a.data, interval_b.data}  # update set
        else:
            overlap_dict[overlap] = {interval_a.data, interval_b.data}  # create entry


def add_overlap_to_dict(interval, overlap, overlap_dict):
    """
    Compare interval to existing overlap. Then modify overlap_dict.
    :param interval: Interval whose data attribute is not None.
    :param overlap: Interval that is in overlap_dict and whose data attribute is None.
    :param overlap_dict: dict where key is Interval representing overlap, value is set of
    data attributes associated with that overlap.
    :return:
    """
    # TODO: return status code or overlap
    updated_set = {interval.data}
    updated_set |= overlap_dict[overlap]
    if is_contained(interval, overlap) and updated_set == overlap_dict[overlap]:
        # because adding would be adding redundant information.
        return
    else:
        common = find_overlap(overlap, interval)
        if common is None or (common.end - common.begin) == ZERO_DUR:
            return
        overlap_dict[common] = updated_set


def is_contained(interval_a: Interval, interval_b: Interval):
    """
    Returns True if interval_a is wholly contained by interval_b.
    :param interval_a:
    :param interval_b:
    :return:
    """
    if interval_a.end > interval_b.end:
        return False
    elif interval_a.begin < interval_b.begin:
        return False
    else:
        return True


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
    Note that this renders v different on the Bot Emulator and on Telegram, depending
    on the Activity.text_format field.

    :param overlap_dict. key is Datetime Interval, value is set of userids.
    :return: string.
    """
    sorted_keys = sortby_start(overlap_dict.keys())
    # TODO: include other sort options. e.g. sort by duration.
    blocks = []
    header = "Common dates & times:\n"
    
    for interval in sorted_keys:
        sorted_ids = sorted(overlap_dict[interval])
        userids = ", ".join(sorted_ids)
        dur = interval.end - interval.begin
        dur_in_min = dur.total_seconds() / 60
        dur_in_hours = dur_in_min / 60

        if interval.begin.date() == interval.end.date():
            blocks.append(f"{interval.begin.strftime('**%d %b, %I:%M%p')}"
                          f" - {interval.end.strftime('%I:%M%p')}"
                          f" ({dur_in_hours:.1f}h)**\n")
        else:
            blocks.append(f"{interval.begin.strftime('**%d %b, %I:%M%p')}"
                          f" - {interval.end.strftime('%d %b, %I:%M%p')}"
                          f" ({dur_in_hours:.1f}h)**\n")

        blocks[-1] = blocks[-1] + f"   ppl: {str(userids)}\n"
    empty_line = "\n"
    fstring = header + empty_line.join(blocks)

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

    For TIME, the hour and min MUST be separated by ':', e.g. "15:00". not "15.00"
    See EXAMPLE for possible full formats.

    :param s: string.
    :returns: list of Intervals.
    """
    intervals = []
    # https://dateutil.readthedocs.io/en/stable/parser.html
    parser_info = dtp.parserinfo(dayfirst=True)
    try:
        groups = s.split('.')
        for group in groups:
            if group in ['']:
                continue
            k, v = group.split(':', 1)
            name = k.strip()
            interval_strings = v.split(',')
            for interval_str in interval_strings:
                if interval_str in ['']:
                    continue
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
                    interval_parts = interval_str.split()
                    timeslot = interval_parts[-1].strip().lower()
                    start_dt_str = interval_parts[0] + ' ' + interval_parts[1]
                    start_dt = dtp.parse(start_dt_str, parserinfo=parser_info)
                    start_dt = start_dt.replace(year=dt.today().year)
                    if timeslot not in GENERAL_TIMESLOTS:
                        raise ValueError(FORMAT_MSG)
                    elif timeslot == 'breakfast':
                        start_dt = start_dt.replace(hour=8)
                        delta = timedelta(hours=2,minutes=30)
                    elif timeslot == 'brunch':
                        start_dt = start_dt.replace(hour=11)
                        delta = timedelta(hours=2,minutes=30)
                    elif timeslot == 'lunch':
                        start_dt = start_dt.replace(hour=12)
                        delta = timedelta(hours=2,minutes=30)
                    elif timeslot == 'dinner':
                        start_dt = start_dt.replace(hour=18)
                        delta = timedelta(hours=2,minutes=30)
                    elif timeslot == 'supper':
                        start_dt = start_dt.replace(hour=21)
                        delta = timedelta(hours=2,minutes=30)
                    elif timeslot == 'morning':
                        start_dt = start_dt.replace(hour=8)
                        delta = timedelta(hours=4)
                    elif timeslot == 'afternoon':
                        start_dt = start_dt.replace(hour=12)
                        delta = timedelta(hours=6)
                    elif timeslot == 'night':
                        start_dt = start_dt.replace(hour=19)
                        delta = timedelta(hours=5)
                    end_dt = start_dt + delta

                    # auto set year
                    if dt.today().month > start_dt.month:
                        # user likely referring to next year
                        start_dt = start_dt.replace(year=dt.today().year + 1)
                        end_dt = end_dt.replace(year=dt.today().year + 1)
                    else:
                        start_dt = start_dt.replace(year=dt.today().year)
                        end_dt = end_dt.replace(year=dt.today().year)

                interval = Interval(start_dt, end_dt, name)
                print(interval)  # debugging statement
                print()
                intervals.append(interval)
    except IndexError:
        raise IndexError(FORMAT_MSG)

    return intervals


def help_msg():
    return HELP_MSG + FORMAT_MSG


def example_msg():
    return EXAMPLE_MSG
