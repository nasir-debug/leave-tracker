from datetime import date, timedelta


def parse_date(s):
    return date.fromisoformat(s)


def count_business_days(start, end):
    """Inclusive count of Mon-Fri days between two ISO date strings.

    Simplification: does not exclude public holidays, only weekends.
    """
    d0, d1 = parse_date(start), parse_date(end)
    if d1 < d0:
        raise ValueError("end_date must not be before start_date")
    days = 0
    cur = d0
    while cur <= d1:
        if cur.weekday() < 5:  # 0=Mon .. 6=Sun
            days += 1
        cur += timedelta(days=1)
    return days


def today_iso():
    return date.today().isoformat()


def days_ago_iso(n):
    return (date.today() - timedelta(days=n)).isoformat()
