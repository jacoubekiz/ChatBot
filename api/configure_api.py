import requests
from datetime import time, timedelta, datetime
def handle_api(question, choices_with_next):
    url = question['url']
    headers = {
            'Content-Type': 'application/json',
        }
    data = {
        "key": "EooBU8KZ0YvLXdEO",
        "mobile": "0983034021",
        "occupation": "طباخ",
        "has_experience": "نعم",
        "nationality": "الهند",
        "labore_id":"24"
        }
    response = requests.post(url , headers=headers, json=data)
    for option in choices_with_next:
        for state in option:
            if str(response.status_code) == str(state):
                next_question_id = option[2]

    return next_question_id
    

def convert_timedelta_to_time(tim):
    time_obj = time(
        hour= tim.seconds // 3600 % 24,
        minute=(tim.seconds // 60) % 60,
        second=tim.seconds % 60
    )
    return time_obj

def convert_time_to_timedelta(tim):
    timedelta_obj = timedelta(
        hours=tim.hour,
        minutes=tim.minute,
        seconds=tim.second,
    )
    return timedelta_obj

def convert_str_to_timedelta(hour, minute, second):
    time_obj = time(int(hour), int(minute), int(second))
    timedelta_obj = timedelta(
        hours=time_obj.hour,
        minutes=time_obj.minute,
        seconds=time_obj.second,
    )
    return timedelta_obj


def split_time(start_time, end_time, interval_minutes):



    time_slots = []
    current_time = start_time

    # print(start_time, end_time, interval_minutes)
    while current_time < end_time:
        time_slots.append(current_time.strftime("%H:%M"))
        current_time = (datetime.combine(datetime.now().date(), current_time) + interval_minutes).time()
    
    return time_slots