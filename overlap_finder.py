import re
from datetime import datetime as dt
from datetime import timedelta
from intervaltree import Interval, IntervalTree
from warnings import warn

# TODO: move test cases to another module.

# one interval
tc_0 = [Interval(1, 3, "aaron")]

# no overlap
tc_1 = [Interval(1, 2, "aaron"), Interval(3, 4, "ben"), Interval(5, 6, "charlotte")]

# separate overlaps
tc_2 = [Interval(1, 3, "aaron"), Interval(2, 4, "ben"), Interval(3, 5, "charlotte")]

# shared overlap
tc_3 = [Interval(1, 3, "aaron"), Interval(2, 4, "ben"), Interval(2, 5, "charlotte")]

# 4 intervals
tc_4 = [Interval(1, 3, "aaron"), Interval(2, 4, "ben"),
        Interval(3, 5, "charlotte"), Interval(1, 6, "dan")]

# more test cases
#----------------

# input: no overlap
# expected: no common interval
tc_5 = [
    Interval(dt(year=2018, month=1, day=1, hour=0), dt(year=2018, month=1, day=2, hour=0), "user_1"),
    Interval(dt(year=2018, month=1, day=2, hour=0), dt(year=2018, month=1, day=3, hour=0), "user_2"),
    Interval(dt(year=2018, month=1, day=3, hour=0), dt(year=2018, month=1, day=4, hour=0), "user_3")
]

# input: two overlap
# expected: common interval at 2018, 1, 2, 0 - 2018, 1, 3, 0, for all users
# common interval at 2018, 1, 2, 0 - 2018, 1, 4, 0, for user_1 and user_3.
tc_6 = [
    Interval(dt(year=2018, month=1, day=1, hour=0), dt(year=2018, month=1, day=4, hour=0), "user_1"),
    Interval(dt(year=2018, month=1, day=2, hour=0), dt(year=2018, month=1, day=3, hour=0), "user_2"),
    Interval(dt(year=2018, month=1, day=2, hour=0), dt(year=2018, month=1, day=5, hour=0), "user_3")
]

# input: complete overlap
# expected: one common interval at 2018, 1, 1, 0 - 2018, 1, 4, 0, for all users
tc_7 = [
    Interval(dt(year=2018, month=1, day=1, hour=0), dt(year=2018, month=1, day=4, hour=0), "user_1"),
    Interval(dt(year=2018, month=1, day=1, hour=0), dt(year=2018, month=1, day=4, hour=0), "user_2"),
    Interval(dt(year=2018, month=1, day=1, hour=0), dt(year=2018, month=1, day=4, hour=0), "user_3")
]

# input: user 1 has 2 different intervals
# expected: two common intervals at [2018, 1, 1, 0 - 2018, 1, 2, 0] and [2018, 1, 4, 0 - 2018, 1, 5, 0] 
tc_8 = [
    Interval(dt(year=2018, month=1, day=1, hour=0), dt(year=2018, month=1, day=2, hour=0), "user_1"),
    Interval(dt(year=2018, month=1, day=4, hour=0), dt(year=2018, month=1, day=5, hour=0), "user_1"),
    Interval(dt(year=2018, month=1, day=1, hour=0), dt(year=2018, month=1, day=8, hour=0), "user_2"),
]

# input: many users with many intervals each
# expected: many common intervals 
tc_9 = [
    Interval(dt(year=2018, month=1, day=1, hour=10), dt(year=2018, month=1, day=1, hour=12), "user_1"),
    Interval(dt(year=2018, month=1, day=3, hour=10), dt(year=2018, month=1, day=3, hour=12), "user_1"),
    Interval(dt(year=2018, month=1, day=1, hour=11), dt(year=2018, month=1, day=1, hour=13), "user_2"),
    Interval(dt(year=2018, month=1, day=3, hour=11), dt(year=2018, month=1, day=3, hour=13), "user_2"),
    Interval(dt(year=2018, month=1, day=1, hour=8), dt(year=2018, month=1, day=1, hour=18), "user_3"),
    Interval(dt(year=2018, month=1, day=2, hour=8), dt(year=2018, month=1, day=2, hour=18), "user_3"),
    Interval(dt(year=2019, month=1, day=1, hour=8), dt(year=2019, month=1, day=1, hour=18), "user_4"),
    Interval(dt(year=2019, month=1, day=5, hour=0), dt(year=2019, month=1, day=6, hour=0), "user_4"),
    Interval(dt(year=2019, month=1, day=5, hour=0), dt(year=2019, month=1, day=6, hour=0), "user_5"),
    Interval(dt(year=2019, month=1, day=5, hour=0), dt(year=2019, month=1, day=6, hour=0), "user_5"),
    Interval(dt(year=2019, month=1, day=5, hour=0), dt(year=2019, month=1, day=6, hour=0), "user_6")
]        


# Input: A list of Intervals
# Output: A dictionary (key: overlap, value: set of user_ids which share the overlap)
def find_all_common_intervals(interval_list):
    overlap_dict = dict()
    interval_tree = IntervalTree(interval_list)
    
    for interval in interval_tree.items(): # create a copy of the tree to iterate over
        # check interval against overlap_dict
        for overlap in overlap_dict.keys():
            add_overlap_to_dict(overlap, interval, overlap_dict)
            
        # check interval against other intervals in the tree to find overlapping regions
        other_intervals = find_other_intervals_which_overlap(interval_tree, interval)
        for other_interval in other_intervals:
            add_new_overlap_to_dict(interval, other_interval, overlap_dict)         
    # TODO: sort dict by start datetime.     
    return overlap_dict


# Input: An IntervalTree and an Interval in the IntervalTree
# Output: A set containing all other Intervals in the IntervalTree that intersect with the given
#  Interval
def find_other_intervals_which_overlap(tree, interval):
    tree.remove(interval)
    result = tree.search(interval.begin, interval.end) # returns a set
    return result


# Input: Two Intervals and a dictionary (key: Interval; value: set of userids)
# Output: None
# Pre-condition: interval.data is a user id
def add_new_overlap_to_dict(interval_a, interval_b, overlap_dict):
    overlap = find_overlap(interval_a, interval_b)
    if overlap is None:
        return

    if overlap in overlap_dict:
        overlap_data = overlap_dict[overlap]
        overlap_data |= {interval_a.data, interval_b.data}
    else:
        overlap_dict[overlap] = {interval_a.data, interval_b.data}


# Input: Two Intervals and a dictionary (key: Interval; value: set of userids)
# Output: None
# Pre-condition: interval.data is a user id
def add_overlap_to_dict(overlap, current_interval, overlap_dict):
    common = find_overlap(overlap, current_interval)
    if common is None:
        return
    
    if common in overlap_dict:
        overlap_data = overlap_dict[overlap].copy()
        overlap_data |= {current_interval.data} # update set of data
        overlap_dict[common] = overlap_data # update key-value pair

# Input: Two Intervals
# Output: An Interval
def find_overlap(interval_a, interval_b):
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
    :return: sorted list.
    """
    ref = []
    for interval in interval_keys:
        ref.append(interval.begin)
    zipped = zip(ref, interval_keys)
    sorted_list = [x for _, x in sorted(zipped)]  # sorts based on ref.

    return sorted_list


def format_overlaps(overlap_dict):
    """
    Formats a string representation of a dict where the key is a Datetime Interval
    and the value is the set of associated user names.
    Note that this renders v different on the Bot Emulator and on Telegram.

    :param dict. key is Datetime Interval, value is set.
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

        lines.append(f"{interval.begin.strftime('**%d %b, %H%M')}"
                     f" - {interval.end.strftime('%d %b, %H%M')}"
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
    Parses a strictly formatted string into a list of datetime interval objects.
    
    expected format : "<NAME>, %d %b, %H%M + <HOURS>h<MINS>m".
    use ';' as a separator between these labelled intervals.
    see https://strftime.org/ for formatting directives.
    
    example:
    "andy, 02 feb, 1.00pm+2h15m;
    baron, 02 feb, 2.00pm+2h30m;
    charmaine, 02 feb, 1500+2h45m"

    :param s: string.
    :returns: list of Intervals.
    """
    START_DT_FORMAT = "%d %b %I.%M%p"  # e.g. 30 Sep 7.30pm
    intervals = []

    lines = s.split(';')  # unsure if \n works in msft bot framework or emulator...

    try:
        for line in lines:
            parts = line.strip().split(',')

            name = parts[0].strip()
            start_date = parts[1].strip()
            time_and_dur = parts[2].strip()
            time_and_dur = time_and_dur.split('+')
            time = time_and_dur[0].strip()
            dur = time_and_dur[1].strip()
            # print(f'name:{name}, date:{start_date}, time:{time}, dur:{dur}')

            start_dt_str = start_date + " " + time
            start_dt = dt.strptime(start_dt_str, START_DT_FORMAT)

            if dt.today().month > start_dt.month:
                # user likely referring to next year
                start_dt = start_dt.replace(year=dt.today().year+1)
            else:
                start_dt = start_dt.replace(year=dt.today().year)

            tdelta = parse_dur(dur)
            end_dt = start_dt + tdelta

            intervals.append(Interval(start_dt, end_dt, name))
    except IndexError:
        message = ("Incorrect format.\n\nExample:\n\nbob, 02 feb, 1300+2h15m;\n\n"
                   "joe, 02 feb, 1400 + 2h30m;\n\nsally, 02 feb, 1500 + 2h30m")
        raise IndexError(message)

    return intervals


def test_algo(tc, tprint=False):
    """
    prints output of find_all_common_intervals(tc) for inspection.

    :param tc: list of Intervals of Datetimes.
    :param tprint: boolean. Whether to format datetime into string.
    """
    overlap_dict = find_all_common_intervals(tc)
    if tprint == True:
        to_print = format_overlaps(overlap_dict)
        print(to_print)
    else:
        for items in overlap_dict.items():
            print(items)
    print()


def run_tests():
    test_algo(tc_1)
    test_algo(tc_2)
    test_algo(tc_3)
    test_algo(tc_4)
    test_algo(tc_5, tprint=True)
    test_algo(tc_6, tprint=True)
    test_algo(tc_7, tprint=True)
    test_algo(tc_8, tprint=True)
    test_algo(tc_9, tprint=True)


## Test datetime parser.
# test_str = "mel , 02 feb, 1300 + 2h15m;"\
#     + "jon, 02 feb , 1400+2h30m"
#
# results = parse_dt_string(test_str)
# for i in results:
#     print(i)

## Test common time finder algorithm.
# test_algo(results, tprint=True)
