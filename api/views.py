from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from rest_framework.generics import GenericAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.core.files.storage import default_storage
from .models import *
from .configure_api import *
from .handel_time import *
from rest_framework import viewsets
import hashlib
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import *
from .utils import *
global client
from langdetect import detect
import langid
import datetime
import os
import redis
import json


class ClientsViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    queryset = Client.objects.all()

class BotAPI(APIView):
    def post(self, request, *args, **kwargs):
        # f = open('log.txt', 'a')
        # f.write(str(request.data) + 'n')
        try:
            conversation = request.data['conversation']
            source_id = conversation['contact_inbox']['source_id']
            platform = 'whatsapp'

        except:
            source_id = request.data.get('entry')[0]['changes'][0]['value']['messages'][0]['from']
            platform = 'beam'
        client_id_hashed = request.GET.get('client')
        client_id = [c.id for c in Client.objects.all() if client_id_hashed == hashlib.sha256(str(c.id).encode()).hexdigest()][0]
        try:
            client = Client.objects.get(Q(id = client_id))
        except:
            pass
        reset_flow = False
        restart_keyword = RestartKeyword.objects.filter(client=client.id)
        for rest in restart_keyword:
            if rest.keyword == request.data['content']:
                reset_flow = True
                flows = rest.client.flow.all()
                for flow in flows:
                    ch = Chat.objects.filter(Q(conversation_id = source_id) & Q(client_id = client.id) & Q(flow=flow)).first()
                    if ch :
                        ch.update_state('end')
                        ch.isSent = False
                        ch.save()
                    continue
                break

        
        try:
            flow = client.flow.get(trigger__trigger=request.data['content'])
            chats = Chat.objects.filter(Q(conversation_id = source_id) & Q(client_id = client.id) & ~Q(flow = flow))
            for c in chats:
                c.update_state('end')
                c.isSent = False
                c.save()
        except:
            ch = Chat.objects.filter(Q(conversation_id = source_id) & Q(client_id = client.id) & ~Q(state = 'end')).first()
            if ch:
                flow = ch.flow
            else:
                flow = None
            
        if not flow:
            flow = client.flow.get(is_default = True)
        file_path = default_storage.path(flow.flow.name)
        chat_flow = read_json(file_path)
        if chat_flow and source_id:
            chat, isCreated = Chat.objects.get_or_create(conversation_id = source_id, client_id = client.id, flow=flow )
            questions = chat_flow['payload']['questions']
            if not bool(chat.state) or chat.state == 'end' or chat.state == '':
                chat.update_state('start')
            while True:
                next_question_id = None
                if chat.state == 'start':
                    if reset_flow:
                        question = questions[0]
                        if question['type'] == 'detect_language':
                            print(questions.index(questions[0]))
                            question = questions[int(questions.index(questions[0]) + 1)]

                    else:
                        question = questions[0]
                #         lang = langid.classify(request.data['content'])
                #         language = lang[0]
                #         # print(language)
                #         for ques in questions:
                #             try:
                #                 print(ques['type_language'])
                #                 ques_lang_type = ques['type_language']
                #             except:
                #                 ques_lang_type = ''
                #             if ques_lang_type  == language:
                #                     print('hello')
                #                     question = ques
                #                     break
                else:
                    for item in questions:
                        if item['id'] == chat.state:
                            question = item
                            break
                        
                message, next_question_id, choices_with_next, choices, r_type, attribute_name = show_response(question, questions)

                if r_type == 'detect_language':
                    lang = langid.classify(request.data['content'])
                    language = lang[0]
                    next_options = [(option['value'], option['next']['target']) for option in question['options']]
                    detect = False
                    for options in next_options:
                        for opt in options:
                            if opt == language:
                                detect = True
                                next_question_id = options[1]
                                break
                    if not detect:
                        next_question_id = next_options[-1][1]
                if r_type == 'button' or r_type == 'list':
                    
                    if not chat.isSent:
                        chat.isSent = True
                        chat.save()
                        
                        if r_type == 'list':
                            send_message(message_content=message,
                                        choices = choices,
                                        type='interactive', 
                                        interaction_type='list',
                                        footer=question['footer'],
                                        header=question['header'],
                                        to = chat.conversation_id,
                                        bearer_token=client.token,
                                        wa_id=client.wa_id,
                                        chat_id=chat.id,
                                        platform=platform,
                                        question=question)
                        
                        else:
                            send_message(message_content=message,
                                        choices = choices,
                                        type='interactive', 
                                        interaction_type='button',
                                        to=chat.conversation_id,
                                        bearer_token=client.token,
                                        wa_id=client.wa_id,
                                        chat_id=chat.id,
                                        platform=platform,
                                        question=question)
                            
                        return Response(
                            {"Message" : "BOT has interacted successfully."},
                            status=status.HTTP_200_OK
                        )
                        
                    else:
                        try:
                            user_reply = request.data['content'] #If this raises an error then it means that the response has come from Beam not Whatsapp
                        except:
                            user_reply = request.data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']
                            
                            # except:
                            #     user_reply = request.data['entry'][0]['changes'][0]['value']['messages'][0]['reply_to']['button_title']
                            
                        if user_reply not in choices or user_reply == '':
                            error_message = question['message']['error']
                            
                            send_message(message_content=error_message,
                                            to=chat.conversation_id,
                                            bearer_token=client.token,
                                            wa_id=client.wa_id,
                                            chat_id=chat.id,
                                            platform=platform,
                                            question=question)
                            
                            return Response(
                                {"Message" : "BOT has interacted successfully."},
                                status=status.HTTP_200_OK
                            )
                        
                        else:
                            next_question_id = [c[2] for c in choices_with_next if user_reply == c[0]][0]
                            chat.update_state(next_question_id)
                            chat.isSent = False
                            chat.save()
                
                elif r_type == 'smart_question' and choices_with_next:
                    if not chat.isSent:
                        chat.isSent = True
                        chat.save()
                        
                        send_message(message_content=message,
                                    to = chat.conversation_id,
                                    bearer_token=client.token, 
                                    wa_id=client.wa_id,
                                    chat_id=chat.id,
                                    platform=platform,
                                    question=question)
                        return Response(
                            {"Message" : "BOT has interacted successfully."},
                            status=status.HTTP_200_OK
                        )
                    
                    else:
                        try:
                            user_reply = request.data['content'] #If this raises an error then it means that the response has come from Beam not Whatsapp                        
                        except:
                            
                            try: #If this raises an error then this means that it is a beam user reply not normal beam text message reply
                                user_reply = request.data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']
                            
                            except:
                                user_reply = request.data['entry'][0]['changes'][0]['value']['messages'][0]['reply_to']['button_title']
                                
                        
                        attr, created = Attribute.objects.get_or_create(key=attribute_name, chat_id=chat.id)
                        attr.value = user_reply
                        attr.save()
                        
                        for option in choices_with_next:
                            matchingType = option[3]
                            if matchingType == 'CONTAIN':
                    
                                if any(string in user_reply for string in option[4]):
                                    next_question_id = option[2]
                                    break
                    
                            elif matchingType == 'EXACT':
                                if any(string == user_reply for string in option[4]):
                                    next_question_id = option[2]
                                    break
                    
                        chat.update_state(next_question_id)
                        chat.isSent = False
                        chat.save()
                # for handel component calender
                    
                elif question['type'] == 'calendar':
                    headers = {
                            'Content-Type': 'application/json',
                        }
                    day = Attribute.objects.filter(key='day', chat=chat.id).first()
                    hour = Attribute.objects.filter(key='hour', chat=chat.id).first()
                    if not day or day == None:
                        if not chat.isSent:
                            chat.isSent = True
                            chat.save()
                            url = f"https://chatbot.ics.me/get-first-ten-days/?date=&key={question['key']}"
                            response = requests.get(url , headers=headers)
                            result = response.json()
                            choice = next(iter(result.values()))
                            choice.append('next')
                            NextTenDay.objects.create(chat=chat, day=choice[0], day_end=choice[-2])
                            chat.update_state(question['id'])
                            send_message(message_content=question['day-message'],
                                    choices = choice,
                                    type='interactive',
                                    interaction_type='button',
                                    to=chat.conversation_id,
                                    bearer_token=client.token,
                                    wa_id=client.wa_id,
                                    chat_id=chat.id,
                                    platform=platform,
                                    question=question
                                )
                            return Response({"Message" : "BOT has interacted successfully."},status=status.HTTP_200_OK)
                        else:
                            day = NextTenDay.objects.filter(chat=chat.id).first()
                            url = f"https://chatbot.ics.me/get-first-ten-days/?date={day.day}&key={question['key']}"
                            response = requests.get(url , headers=headers)
                            result = response.json()
                            choices = next(iter(result.values()))
                            print(len(choices))
                            # if len(choices) > 9:
                            choices.append('next')
                            # else:
                            #     print('I am her')
                            #     day.day = choices[-1]
                            #     day.save()
                            # print(choices)
                            user_reply = request.data['content']
                            if user_reply not in choices:
                                error_message = question['error-Message']
                                send_message(message_content=error_message,
                                                to=chat.conversation_id,
                                                bearer_token=client.token,
                                                wa_id=client.wa_id,
                                                chat_id=chat.id,
                                                platform=platform,
                                                question=question)
                                return Response(
                                    {"Message" : "BOT has interacted successfully."},
                                    status=status.HTTP_200_OK
                                )
                            # print(user_reply)
                            
                            if user_reply == "next" and chat.isSent:
                                # day = NextTenDay.objects.filter(chat=chat.id).first()
                                chat.isSent = True
                                chat.save()
                                url = f"https://chatbot.ics.me/get-first-ten-days/?date={day.day_end}&key={question['key']}"
                                response = requests.get(url , headers=headers)
                                result = response.json()
                                chat.update_state(question['id'])
                                ch = next(iter(result.values()))
                                if len(ch) >= 9:
                                    ch.append('next')
                                    day.day_end = ch[-2]
                                day.day = ch[0]
                                day.save()
                                send_message(message_content=question['day-message'],
                                        choices = ch,
                                        type='interactive',
                                        interaction_type='button',
                                        to=chat.conversation_id,
                                        bearer_token=client.token,
                                        wa_id=client.wa_id,
                                        chat_id=chat.id,
                                        platform=platform,
                                        question=question
                                    )
                                return Response({"Message" : "BOT has interacted successfully."},status=status.HTTP_200_OK)                            

                            
                            attr, created = Attribute.objects.get_or_create(key='day', chat_id=chat.id)
                            attr.value = user_reply
                            attr.save()
                            next_question_id = question['id']
                            chat.isSent = False
                            chat.save()
                    elif not hour or hour == None:
                        if not chat.isSent:
                            chat.isSent = True
                            chat.save()
                            url = f"https://chatbot.ics.me/get-hours-free/?date={day.value}&key={question['key']}"
                            response = requests.get(url , headers=headers)
                            result = response.json()
                            chat.update_state(question['id'])
                            choices = next(iter(result.values()))
                            try:
                                ch = choices[:9]
                                ch.append('next')
                                NextTime.objects.create(chat=chat, time=ch[-2])
                            except:
                                ch=choices
                            send_message(message_content=question['appointment-message'],
                                    choices = ch,
                                    type='interactive',
                                    interaction_type='button',
                                    to=chat.conversation_id,
                                    bearer_token=client.token,
                                    wa_id=client.wa_id,
                                    chat_id=chat.id,
                                    platform=platform,
                                    question=question
                                )
                            return Response({"Message" : "BOT has interacted successfully."},status=status.HTTP_200_OK)
                        else:
                            time_day = NextTime.objects.filter(chat=chat.id).first()
                            url = f"https://chatbot.ics.me/get-hours-free/?date={day.value}&key={question['key']}"
                            response = requests.get(url , headers=headers)
                            result = response.json()
                            choices = next(iter(result.values()))
                            choices.append('next')
                            user_reply = request.data['content']
                            if user_reply not in choices:
                                error_message = question['error-Message']
                                send_message(message_content=error_message,
                                                to=chat.conversation_id,
                                                bearer_token=client.token,
                                                wa_id=client.wa_id,
                                                chat_id=chat.id,
                                                platform=platform,
                                                question=question)
                                return Response(
                                    {"Message" : "BOT has interacted successfully."},
                                    status=status.HTTP_200_OK
                                )
                            if user_reply == "next" and chat.isSent:
                                chat.isSent = True
                                chat.save()
                                url = f"https://chatbot.ics.me/get-hours-free/?date={day.value}&key={question['key']}"
                                response = requests.get(url , headers=headers)
                                result = response.json()
                                chat.update_state(question['id'])
                                choices = next(iter(result.values()))
                                try:
                                    print(str(time_day.time)[:-3])
                                    index_time = choices.index(str(time_day.time)[:-3])
                                    print(index_time)
                                    ch = choices[index_time:index_time+9]
                                    time_day.time = ch[-2]
                                    time_day.save()
                                except:
                                    ch = choices
                                send_message(message_content=question['appointment-message'],
                                        choices = ch,
                                        type='interactive',
                                        interaction_type='button',
                                        to=chat.conversation_id,
                                        bearer_token=client.token,
                                        wa_id=client.wa_id,
                                        chat_id=chat.id,
                                        platform=platform,
                                        question=question
                                    )
                                return Response({"Message" : "BOT has interacted successfully."},status=status.HTTP_200_OK) 
                            user_reply = request.data['content']
                            attr, created = Attribute.objects.get_or_create(key='hour', chat_id=chat.id)
                            attr.value = user_reply
                            attr.save()
                            next_question_id = question['id']
                            chat.isSent = False
                            chat.save()
                    else:
                        calendar = Calendar.objects.get(key=question['key'])
                        duration = calendar.duration
                        user = calendar.user
                        print(user.id)
                        data = {
                            "user":user.id,
                            "day":day.value,
                            "duration":f"{duration}",
                            "hour":f"{hour.value}",
                            "details":f"{question['parameters'][1]['value']}",
                            "patientName":f"{question['parameters'][0]['value']}"
                        } 
                        url = "https://chatbot.ics.me/create-book-an-appointment/"
                        response = requests.post(url , headers=headers, json=data)

                        for option in choices_with_next:
                            for state in option:
                                if str(response.status_code) == str(state):
                                    next_question_id = option[1]
                        day.delete()
                        hour.delete()
                        NextTenDay.objects.get(chat=chat).delete()
                        NextTime.objects.get(chat=chat).delete()
                # for handle api in flow
                elif r_type == 'api':
                        url = question['url']
                        headers = {
                                'Content-Type': 'application/json',
                            }
                        
                        data = question['body']
                        for key, value in data.items():
                            if isinstance(value, (int, float)):
                                continue
                            data[key] = change_occurences(value, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)

                        response = requests.post(url , headers=headers, json=data)
                        for option in choices_with_next:
                            for state in option:
                                if str(response.status_code) == str(state):
                                    next_question_id = option[2]
                
                elif r_type == 'name' or \
                    r_type == 'phone' or \
                    r_type == 'email' or \
                    r_type == 'question' or \
                    r_type == 'number' :

                    if not chat.isSent:
                        chat.isSent = True
                        chat.save()
                
                        send_message(message_content=message,
                                        to=chat.conversation_id,
                                        bearer_token=client.token,
                                        wa_id=client.wa_id,
                                        chat_id=chat.id,
                                        platform=platform,
                                        question=question)
                
                        return Response(
                            {"Message" : "BOT has interacted successfully."},
                            status=status.HTTP_200_OK
                        )
                
                    else:
                        user_reply = ''
                    
                        try:
                            user_reply = request.data['content'] #If this raises an error then it means that the response has come from Beam not Whatsapp
                    
                        except:
                            
                            try: #If this raises an error then this means that it is a beam user reply not normal beam text message reply
                                user_reply = request.data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']
                            
                            except:
                                user_reply = request.data['entry'][0]['changes'][0]['value']['messages'][0]['reply_to']['button_title']
                        
                        restart_keywords = [r.keyword for r in RestartKeyword.objects.filter(client_id = client.id)]
                        
                        if user_reply in restart_keywords:
                            chat.isSent = False
                            chat.save()
                            chat.update_state('start')
                            
                        elif r_type == 'name' and len(user_reply) > question['maxRange']:
                            error_message = question['message']['error']
                            send_message(message_content=error_message,
                                            to=chat.conversation_id,
                                            bearer_token=client.token,
                                            wa_id=client.wa_id,
                                            chat_id=chat.id,
                                            platform=platform,
                                            question=question)
                            return Response(
                                {"Message" : "BOT has interacted successfully."},
                                status=status.HTTP_200_OK
                            )
                        
                        elif r_type == 'phone' and not validate_phone_number(user_reply):
                            error_message = question['message']['error']
                            send_message(message_content=error_message,
                                            to=chat.conversation_id,
                                            bearer_token=client.token,
                                            wa_id=client.wa_id,
                                            chat_id=chat.id,
                                            platform=platform,
                                            question=question)
                            return Response(
                                {"Message" : "BOT has interacted successfully."},
                                status=status.HTTP_200_OK
                            )
                        
                        elif r_type == 'email' and not validate_email(user_reply):
                            error_message = question['message']['error']
                            send_message(message_content=error_message,
                                            to=chat.conversation_id,
                                            bearer_token=client.token,
                                            wa_id=client.wa_id,
                                            chat_id=chat.id,
                                            platform=platform,
                                            question=question)
                            return Response(
                                {"Message" : "BOT has interacted successfully."},
                                status=status.HTTP_200_OK
                            )
                        
                        elif r_type == 'number' and not str(user_reply).isdigit():
                            error_message = question['message']['error']
                            send_message(message_content=error_message,
                                            to=chat.conversation_id,
                                            bearer_token=client.token,
                                            wa_id=client.wa_id,
                                            chat_id=chat.id,
                                            platform=platform,
                                            question=question)
                            return Response(
                                {"Message" : "BOT has interacted successfully."},
                                status=status.HTTP_200_OK
                            )
                        
                        else:
                            # add attribute name 
                            # attr, created = Attribute.objects.get_or_create(key=r_type, chat_id=chat.id)
                            attr, created = Attribute.objects.get_or_create(key=attribute_name, chat_id=chat.id)
                            attr.value = user_reply
                            chat.update_state(next_question_id)
                            chat.isSent = False
                            attr.save()
                            chat.save()
                
                elif r_type == 'document':
                    send_message(message_content=message,
                                    to=chat.conversation_id,
                                    bearer_token=client.token,
                                    type='document',
                                    source=question['source'],
                                    beem_media_id=question.get('beem_media_id'),
                                    wa_id=client.wa_id,
                                    chat_id=chat.id,
                                    platform=platform,
                                    question=question)
                
                elif r_type == 'image':
                    send_message(message_content=message,
                                    to=chat.conversation_id,
                                    bearer_token=client.token, type='image',
                                    source=question['source'],
                                    beem_media_id=question.get('beem_media_id'), 
                                    wa_id=client.wa_id,
                                    chat_id=chat.id,
                                    platform=platform,
                                    question=question)

                
                elif r_type == 'audio' or r_type == 'sticker' or r_type == 'video':

                    send_message(message_content=message,
                                    to=chat.conversation_id,
                                    bearer_token=client.token, type=r_type,
                                    source=question['source'], 
                                    wa_id=client.wa_id,
                                    chat_id=chat.id,
                                    platform=platform,
                                    question=question)

                
                elif r_type == 'contact' or r_type == 'location':
                    send_message(message_content=message,
                                    to=chat.conversation_id,
                                    bearer_token=client.token, type=r_type,
                                    wa_id=client.wa_id,
                                    chat_id=chat.id,
                                    platform=platform,
                                    question=question)

                
                
                elif r_type == 'Condition' and choices_with_next or r_type == 'condition' and choices_with_next:
                    
                    for c in choices_with_next:
                        condition = c[0][0]
                        default_state = ''
                        condition = change_occurences(condition, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)
                    
                        if not condition == 'Default':
                    
                            if check_sql_condition(condition):
                                next_question_id = c[3]
                                break
                    
                        else:
                            default_state = c[3]
                    
                    if not next_question_id in [c[3] for c in choices_with_next]: #This means if the next question wasn't changed with any conditions then it'll take the default value
                        next_question_id = default_state
                elif r_type == 'detect_language':
                    pass    
                else:
                    # if chat.state == 'start':
                    #     print(detect(request.data['content']))
                    send_message(message_content=message,
                                    to=chat.conversation_id,
                                    bearer_token=client.token,
                                    wa_id=client.wa_id,
                                    chat_id=chat.id,
                                    platform=platform,
                                    question=question,
                                    )
                
                chat.update_state(next_question_id)
                if not next_question_id or next_question_id == 'end':
                
                    return Response(
                        {"Message" : "BOT has interacted successfully."},
                        status=status.HTTP_200_OK
                    )
        else:
            return Response(
                {'Message' : 'Please make sure you have provided client info and source_id.'},
                status = status.HTTP_400_BAD_REQUEST
            )
    


    

class CreateCalenderView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        serializer = CalenderSerializer(data=data,  context={'request':request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data ,status=status.HTTP_201_CREATED)
    
class GetCalenderView(GenericAPIView):

    def get(self, request, user_id):
        calendar = Calendar.objects.filter(user__id=user_id).all()
        serializer = CalenderSerializer(calendar, many=True)
        book_an_appointment = BookAnAppointment.objects.filter(Q(user__id = user_id) & Q(day__day__gte=timezone.now().day))
        serializer_book = BookAnAppointmentSerializer(book_an_appointment, many=True)
        return Response({'calender':serializer.data, 'busy_tiem':serializer_book.data}, status=status.HTTP_200_OK)
    
class CreateWorkingTimeView(ListCreateAPIView):
    queryset = WorkingTime.objects.all()
    serializer_class = WorkingTimeSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

# class CreateListWorkingHoursPMView(ListCreateAPIView):
#     queryset = WorkingHoursPM.objects.all()
#     serializer_class = WorkingHoursPMSerializer
#     permission_classes = [IsAuthenticated]


class CreateBookAnAppointmentView(ListCreateAPIView):
    queryset = BookAnAppointment.objects.all()
    serializer_class = BookAnAppointmentSerializer

class GetCalendarForUserView(GenericAPIView):

    def get(self, request, calender_key):
        
        calendar = Calendar.objects.filter(key=calender_key).all()
        calendar_serializer = CalenderSerializer(calendar, many=True)
        working_days = []
        calendars = []
        for calendar_user in calendar_serializer.data:
            list_working_days = calendar_user['working_time']
            duration = Duration.objects.get(id=calendar_user['duration'])
            calendars.append({'calendar_id':calendar_user['id'],"api-key":calendar_user['key'], 'duration':duration_string(duration.duration)})

        for work_day in list_working_days:
            working_days.append(work_day['day'])

        data = {
            'working_days':working_days,
            'calendar':calendars
            }
        return Response(data , status=status.HTTP_200_OK)
    

class GetHoursFree(GenericAPIView):

    def get(self, request):
        days = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت']
        # info = request.data
        free_hours = []
        day_number = days.index(get_day_name(request.GET.get('date')))
        if day_number == 0:
            day_number +=1
        calendar = Calendar.objects.filter(key=request.GET.get('key')).first()
        working_time = calendar.working_time.get(day=day_number)
        start_work_am = convert_time_to_timedelta(working_time.starting_time_am)
        start_work_pm = convert_time_to_timedelta(working_time.starting_time_pm)
        end_work_am = convert_time_to_timedelta(working_time.end_time_am)
        end_work_pm = convert_time_to_timedelta(working_time.end_time_pm)
        duration = calendar.duration.duration
        time_slots = []

        user_book_an_appointment = calendar.user.bookanappointment_set.filter(Q(day=request.GET.get('date'))).order_by('day', 'hour')
        if not user_book_an_appointment:
            free_hours.append((convert_timedelta_to_time(start_work_am), convert_timedelta_to_time(end_work_am)))
            free_hours.append((convert_timedelta_to_time(start_work_pm), convert_timedelta_to_time(end_work_pm)))
            for i in free_hours:
                time_slots.extend(split_time(i[0], i[1], duration))
            return Response({'free_hours':time_slots})

        starting_appointment = []
        end_appointment = []
        
        for x in user_book_an_appointment:
            starting_appointment.append((convert_time_to_timedelta(x.hour)))
            end_appointment.append(convert_time_to_timedelta(x.hour) + x.duration)

        starting_appointment.insert(0 , start_work_am)
        starting_appointment.append(end_work_pm)
        end_appointment.insert(0, start_work_am)
        end_appointment.append(end_work_pm)
        # deferance = []
        for item in range(len(starting_appointment)):
            try:
                next_appointment = starting_appointment[item + 1]
            except:
                next_appointment = starting_appointment[item]
            if next_appointment-end_appointment[item] >= duration:
                free_hours.append((convert_timedelta_to_time(end_appointment[item]), convert_timedelta_to_time(next_appointment)))

        for free in free_hours:
            if convert_time_to_timedelta(free[0]) <= end_work_am and convert_time_to_timedelta(free[1]) >= end_work_am:
                free_hours.insert(free_hours.index(free), (free[0], convert_timedelta_to_time(end_work_am)))
                
                if convert_time_to_timedelta(free[1]) - start_work_pm >= duration:
                    free_hours.insert(free_hours.index(free)+1, (convert_timedelta_to_time(start_work_pm), free[1]))
                free_hours.remove(free)

        for i in free_hours:
            time_slots.extend(split_time(i[0], i[1], duration))

        return Response({'free_hours':time_slots},status=status.HTTP_200_OK)

class GetFirstTenDays(APIView):

    def get(self, request):
        days = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت']
        
        # info = request.data
        calendar = Calendar.objects.filter(key=request.GET.get('key')).first()
        free_hours = []
        free_days = set()
        next_days = []
        if request.GET.get('date') == '':
            day = calendar.start_appointment
        else:
            day = datetime.datetime.strptime(request.GET.get('date'), '%Y-%m-%d').date()
        # while len(free_days) <= 10
        
        for d in range(15):
            if day + timedelta(days=d) <= calendar.end_appointment :
                next_days.append(day + timedelta(days=d))
        for next_day in next_days:
            if len(free_days) == 9:
                break
            day_number = days.index(get_day_name(next_day))
            if day_number == 0:
                day_number +=1
            if day_number == 6 or day_number == 5:
                continue
            
            working_time = calendar.working_time.get(day=day_number)
            start_work_am = convert_time_to_timedelta(working_time.starting_time_am)
            end_work_am = convert_time_to_timedelta(working_time.end_time_am)
            end_work_pm = convert_time_to_timedelta(working_time.end_time_pm)
            duration = calendar.duration.duration
            user_book_an_appointment = calendar.user.bookanappointment_set.filter(Q(day=next_day)).order_by('day', 'hour')
            if not user_book_an_appointment:
                free_days.add( next_day)
                continue
            starting_appointment = []
            end_appointment = []
            
            for x in user_book_an_appointment:
                starting_appointment.append((convert_time_to_timedelta(x.hour)))
                end_appointment.append(convert_time_to_timedelta(x.hour) + x.duration)

            starting_appointment.insert(0 , start_work_am)
            starting_appointment.append(end_work_pm)
            end_appointment.insert(0, start_work_am)
            end_appointment.append(end_work_pm)
            for item in range(len(starting_appointment)):
                try:
                    next_appointment = starting_appointment[item + 1]
                except:
                    next_appointment = starting_appointment[item]
                if next_appointment-end_appointment[item] >= duration:
                    print(next_day)
                    free_days.add(next_day)
                    continue

            for free in free_hours:
                if convert_time_to_timedelta(free[0]) <= end_work_am and convert_time_to_timedelta(free[1]) >= end_work_am:
                    free_days.add(next_day)
                    continue
   
        return Response({'free_days':sorted(list(free_days))},status=status.HTTP_200_OK)


# class GetDoctorsView(APIView):
#     def get(self, request):
#         user = CustomUser.objects.all()
#         serializer_user = SerializerSignUp(user, many=True)
#         data = serializer_user.data

#         return Response({'username':data['username']}, status=status.HTTP_200_OK)
    
class GetDoctorsCalanderView(APIView):
    def get(self, request, doctor_id):
        user = CustomUser.objects.get(id=doctor_id)
        calander = user.calendar_set.all()
        durations = []
        for cal in calander:
            durations.append(convert_timedelta_to_time(cal.duration.duration))

        return Response({'duration':durations}, status=status.HTTP_200_OK)
    

from .send_email import *

class SendEmailView(APIView):
    def post(self, request):
        data= {'to_email':request.data['email'], 'email_subject':'','message': request.data['message']}
        Utlil.send_email(data)
        return Response(status=status.HTTP_200_OK)
# --------------------------------------------------------------------------------------------------------------
from .permissions import UserIsAdmin
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django_redis import get_redis_connection
from django.utils.decorators import method_decorator


class ListCreateUserView(ListCreateAPIView):
    permission_classes = [IsAuthenticated, UserIsAdmin]
    queryset = CustomUser1.objects.all()
    serializer_class = AddUserSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
        
    
class ViewLogin(GenericAPIView):

    def post(self, request):
        data_request = request.data
        serializer = LoginSerializer(data = data_request, many=False)
        serializer.is_valid(raise_exception=True)
        email = data_request['email']
        user = CustomUser1.objects.get(email=email)
        token = RefreshToken.for_user(user)
        tokens = {'refresh':str(token), 'access':str(token.access_token)}
        data = {
            'tokens':tokens,
            'user': {
                'id':user.id,
                'name':user.username,
                'role':user.role
            }
        }
        return Response(data, status=status.HTTP_200_OK)
    
# End Points for Logout User
class LogoutAPIView(APIView):
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated,]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": 'logout true'})
    
# End Points for GET all teams
class GetTeamView(ListAPIView):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated]

class ListContactView(ListAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

class ListConversationView(GenericAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversation = Conversation.objects.all()
        serializer = self.get_serializer(conversation, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        data = request.data
        channel = Channle.objects.filter(channle_id = data['channel_id']).first()
        contact = Contact.objects.filter(contact_id = data['contact_id']).first()
        conversation, created = Conversation.objects.get_or_create(contact_id = contact , channle_id = channel)
        conversation_serializer = ConverstionSerializerCreate(conversation, many=False)

            # conversation_serializer = ConverstionSerializerCreate(conversation, many=True)
        # conversation_serializer.is_valid(raise_exception=True)
        # conversation_serializer.save()
        return Response(conversation_serializer.data)


class CreateListCampaignsView(GenericAPIView):
    serializer_class = CampaignsSerilizer
    pagination_class = [IsAuthenticated]

    def get(self, request):
        campaigns = Campaign.objects.all()
        serializer_campaigns = self.get_serializer(campaigns, many=True)
        data = serializer_campaigns.data

        return Response(data, status=status.HTTP_200_OK)
    
    def post(self, request):
        data = request.data
        campaigs = self.get_serializer(data=data, many=False)
        campaigs.is_valid(raise_exception=True)
        campaigs.save()

        return Response(campaigs.data, status=status.HTTP_201_CREATED)
    
class ListReportView(ListAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]


class ListReportView(RetrieveAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]



@method_decorator(csrf_exempt, name='dispatch')
class WebhookView(APIView):
    # @csrf_exempt
    def post(self, request):
        try:
            data = request.data
            redis_client = get_redis_connection()
            redis_client.rpush('data_queue', json.dumps(data))
            f = open('content_redis.txt', 'a')
            f.write(str(data) + '\n')
            return Response(status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error processign webhok: {str(e)}")
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class GetDataFromRedis(APIView):

    def get(self, request):
        redis_client = get_redis_connection()
        raw_data = redis_client.lpop('data_queue')
        # print(raw_data)
        # raw = '''
        # {"event": 
        #     {"value": {
        #         "messaging_product": 
        #             "whatsapp", 
        #             "metadata": {
        #                 "display_phone_number": "966920025589",
        #                 "phone_number_id": "157289147477280"
        #             },
        #         "contacts": [
        #             {
        #                 "profile": {
        #                 "name": "عبدالرحمن"
        #             }, 
        #             "wa_id": "966582752803"}
        #         ], 
        #         "messages": [
        #             {
        #                 "from": "966582752803",
        #                 "id": "wamid.HBgMOTY2NTgyNzUyODAzFQIAEhgUM0FDOEEyQzA2MkM2NTU1NzA5MDMA",
        #                 "timestamp": "1730742922",
        #                 "text": {
        #                     "body":
        #                     "Abdulrhamn.1.8@gmail.com"
        #                     }, 
        #                 "type": "text"
        #             }
        #         ]
        #         }, 
        #         "field": "messages"
        #     }
        # }'''
        # raw = '''{
        #     "event": {
        #         "mid": "wamid.HBgMOTY2NTY3ODY0MjY3FQIAERgSMkI5MzJFRjVDMENDRTU4NjRDAA==",
        #         "status": "read",
        #         "payload": {
        #             "id": "wamid.HBgMOTY2NTY3ODY0MjY3FQIAERgSMkI5MzJFRjVDMENDRTU4NjRDAA==",
        #             "status": "read",
        #             "timestamp": "1730735977",
        #             "recipient_id": "966567864267"
        #             },
        #         "event": {
        #             "value": {
        #                 "messaging_product": "whatsapp",
        #                 "metadata": {
        #                     "display_phone_number": "966920025589",
        #                     "phone_number_id": "157289147477280"
        #                 }, 
        #             "statuses": [
        #                 {
        #                     "id": "wamid.HBgMOTY2NTY3ODY0MjY3FQIAERgSMkI5MzJFRjVDMENDRTU4NjRDAA==",
        #                     "status": "read",
        #                     "timestamp": "1730735977",
        #                     "recipient_id": "966567864267"
        #                 }
        #             ]}, 
        #             "field": "messages"}}}'''
        log_entry = json.loads(raw_data)

        mid = log_entry.get('event', '').get('mid', '')
        contact = log_entry.get('event', '').get('payload', '').get('recipient_id', '')
        contact_id = Contact.objects.filter(phone_number=contact_id).first()
        conversation = Conversation.objects.get()
        message = ChatMessage.objects.get_or_create()



        
        # value = log_entry.get('event', '').get('value', '')
        # if value:
        #     print('hello')
        #     content = log_entry.get('event', {}).get('value', {}).get('messages', '')[0].get('text', '').get('body','')
        #     wamid = log_entry.get('event', {}).get('value', {}).get('messages', '')[0].get('id', '')
        #     content_type = log_entry.get('event', {}).get('value', {}).get('messages', '')[0].get('type', '')
        #     from_user = log_entry.get('event', {}).get('value', {}).get('messages', '')[0].get('from ', '')
        #     timestamp = log_entry.get('event', {}).get('value', {}).get('messages', '')[0].get('timestamp', '')
        #     messaging_product = log_entry.get('event', {}).get('value', {}).get('messaging_product', '')
        #     display_phone_number = log_entry.get('event', {}).get('value', {}).get('metadata', '').get('display_phone_number', '')
        #     phone_number_id = log_entry.get('event', {}).get('value', {}).get('metadata', '').get('phone_number_id', '')
        #     contacts = log_entry.get('event', '').get('value', '').get('contacts', '')
        #     if contacts:
        #         name = log_entry.get('event', '').get('value', '').get('contacts', '')[0].get('profile', '').get('name', '')
        #         wa_id = log_entry.get('event', '').get('value', '').get('contacts', '')[0].get('wa_id', '')
        #         contact, created = Contact.objects.get_or_create(name=name, phone_number=wa_id)
        #         print(contact, wa_id)
        #         conversation, created = Conversation.objects.get_or_create(contact_id=contact, account_id=contact.account_id)
        #         print(conversation, conversation.account_id.name)
                # chat_message = ChatMessage.objects.create(
                #     conversation_id=conversation,
                #     content_type=content_type,
                #     content=content,
                #     wamid=wamid,
                # )
                # url = 'http://127.0.0.1:8000/ws/chat/jacoub/'
                # ws = upgrade_to_websocket(url)
                # # Now you can use the ws object to send and receive messages
                # ws.send("Hello, server!")
                # print(ws.recv())
                # ws.close()
        return Response({'message':raw_data}, status=status.HTTP_200_OK)