import requests
from rest_framework.response import Response
from rest_framework import status
from datetime import time, timedelta, datetime

def handle_api(question, choices_with_next, chat):

    url = question['url']
    type_url = question['type_url']
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
    if type_url == 'post':
        response = requests.post(url , headers=headers, json=data)
    else:
        response = requests.get(url , headers=headers)
    print(response.status_code)
    if str(question['wait_for_response']) == "true":
        if not chat.isSent:
            chat.isSent = True
            chat.save()
            print(choices_with_next)

        for option in choices_with_next:
            for state in option:
                if str(response.status_code) == str(state):
                    print('hello')
                    chat.update_state(option[2])
                    return Response({"Message" : "BOT has interacted successfully."},
                                            status=status.HTTP_200_OK)
    else:
        print('hello hello hello')
        for option in choices_with_next:
            for state in option:
                if str(response.status_code) == str(state):
                    next_question_id = option[2]
                    print(next_question_id)

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