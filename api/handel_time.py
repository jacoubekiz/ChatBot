import datetime

days = {
    0: 'الأحد',
    1: 'الإثنين',
    2: 'الثلاثاء',
    3: 'الأربعاء',
    4: 'الخميس',
    5: 'الجمعة',
    6: 'السبت'
}

def get_day_name(date):
    if isinstance(date, str):
        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d').date()
    elif isinstance(date, datetime.date):
        date_obj = date
    else:
        raise ValueError("Invalid input type. Expected str or datetime.date")  
    day_number = date_obj.weekday()
    try:
        day = days[day_number + 1]
    except:
        day = days[0]
    return day