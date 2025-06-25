from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from rest_framework.generics import GenericAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
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
from .permissions import UserIsAdmin
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django_redis import get_redis_connection
from django.utils.decorators import method_decorator
import threading
from .send_email import *
import openpyxl
from .pagination import *
from django.http import HttpResponse

def write_inside_excel(data):
        response = data['response']
        time_meeting = data['time_meeting']
        phonenumber = data['phonenumber']
        try:
            workbook =  openpyxl.load_workbook('media/Seamless_DXB.xlsx')
            
        except FileNotFoundError:
            workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet['A1'] = 'client name'
        sheet['B1'] = 'phone number'
        sheet['C1'] = 'time_meeting'
        last_row = sheet.max_row
        new_data = [response, phonenumber, time_meeting]
        sheet.cell(row=last_row + 1, column=1, value=new_data[0])
        sheet.cell(row=last_row + 1, column=2, value=new_data[1])
        sheet.cell(row=last_row + 1, column=3, value=new_data[2])
        workbook.save('media/Seamless_DXB.xlsx')

class RegisterResponseClient(APIView):
    def post(self, request):
        data = request.data
        thread = threading.Thread(target=write_inside_excel(data))
        thread.start()
        return Response(status=status.HTTP_200_OK)

class ClientsViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    queryset = Client.objects.all()

class BotAPI(APIView):
    def post(self, request, *args, **kwargs):
        f = open('log.txt', 'a')
        f.write(str(request.data) + 'n')
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
    



class SendEmailView(APIView):
    def post(self, request):
        data= {'to_email':request.data['email'], 'email_subject':'','message': request.data['message']}
        Utlil.send_email(data)
        return Response(status=status.HTTP_200_OK)
# --------------------------------------------------------------------------------------------------------------
class ListCreateTeamView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Team.objects.all()
    serializer_class = TeamSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['account_id'] = self.kwargs['account_id']
        # context['team_id'] = self.kwargs['team_id']
        return context
    
    def get_queryset(self):
        account_id = Account.objects.get(account_id=self.kwargs['account_id'])
        return account_id.team_set.all()

class AssigningPermissions(APIView):
    def post(self, request, user_id):
        user = CustomUser.objects.get(id=user_id)
        role = request.data['role']
        add = request.GET.get('add')
        print(add)
        content_type = ContentType.objects.get_for_model(CustomUser)
        permission = Permission.objects.get(
            codename= role,
            content_type=content_type
        )
        if add == 'True':
            user.user_permissions.add(permission)
        else:
            user.user_permissions.remove(permission)
        return Response(status=status.HTTP_200_OK)
    
# class ListCreateTeamMemberView(ListCreateAPIView):
#     permission_classes = [IsAuthenticated]
#     queryset = CustomUser.objects.all()
#     serializer_class = AddUserSerializer

#     def get_serializer_context(self):
#         context = super().get_serializer_context()
#         context['request'] = self.request
#         context['role'] = self.request.data['role']
#         context['team_id'] = self.kwargs['team_id']
#         return context
    
#     def get_queryset(self):
#         team_id = Team.objects.get(team_id=self.kwargs['team_id'])
#         return team_id.members


class ListCreateTeamMemberView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, team_id):
        data_request = request.data
        serializer = AddUserSerializer(data = data_request, many=False, context={'role':request.data['role'], 'team_id':team_id})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, team_id):
        team_id = Team.objects.get(team_id=team_id)
        serializer = AddUserSerializer(team_id.members, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CreateListAccount(GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        data_request = request.data
        serializer = AddAccountSerializer(data = data_request, many=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        email = data_request['email']
        user = CustomUser.objects.get(email=email)
        account = Account.objects.create(
            user=user,
            name=user.username
        )
        return Response(status=status.HTTP_201_CREATED)

    def get(self, request):
        accounts = Account.objects.filter(user__role_user='admin')
        serializer = AccontSerializer(accounts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ListCreateChannelView(ListCreateAPIView):
    
    serializer_class = ChannleSerializer
    permission_classes = [IsAuthenticated,]
    def get_queryset(self):
        account_id = self.kwargs['account_id']
        return Channle.objects.filter(account_id=account_id)
    
    def perform_create(self, serializer):
        account_id = Account.objects.get(account_id=self.kwargs['account_id'])
        serializer.save(account_id=account_id)
    
class CreateNewContact(GenericAPIView):
    def post(self, request, account_id, channel_id):
        data = request.data
        account_id = Account.objects.get(account_id=account_id)
        channel_id = Channle.objects.get(channle_id= channel_id)
        contact = ContactSerializer(data=data, many=False, context = {'account_id': account_id, 'channel_id': channel_id})
        contact.is_valid(raise_exception=True)
        contact.save()
        return Response(contact.data, status=status.HTTP_200_OK)
    
class ViewLogin(GenericAPIView):

    def post(self, request):
        data_request = request.data
        serializer = LoginSerializer(data = data_request, many=False)
        serializer.is_valid(raise_exception=True)
        email = data_request['email']
        try:
            user = CustomUser.objects.get(email=email)
            token = RefreshToken.for_user(user)
            tokens = {'refresh':str(token), 'access':str(token.access_token)}
            data = {
                'tokens':tokens,
                'user': {
                    'id':user.id,
                    'name':user.username,
                    'role':user.role_user
                }
            }
        except:
            user = CustomUser.objects.get(email=email)
            token = RefreshToken.for_user(user)
            tokens = {'refresh':str(token), 'access':str(token.access_token)}
            data = {
                'tokens':tokens,
                'user': {
                    'id':user.id,
                    'name':user.username,
                    # 'role':user.role
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
# class GetTeamView(ListAPIView):
#     queryset = Team.objects.all()
#     serializer_class = TeamSerializer
#     permission_classes = [IsAuthenticated]

class ListContactView(ListAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

class ListConversationView(GenericAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, channel_id):
        conversation = Conversation.objects.filter(channle_id=channel_id)
        serializer = self.get_serializer(conversation, many=True)
        return Response(serializer.data)
    
    def post(self, request, channel_id):
        data = request.data
        channel = Channle.objects.filter(channle_id = channel_id).first()
        contact = Contact.objects.filter(contact_id = channel_id).first()
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

class ListMessgesForSpecificConversation(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPaginatins

    def get(self, request, conversation_id):
        paginator = CustomPaginatins()
        # paginator.page_size = 20
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        messages = conversation.chatmessage_set.all().order_by('-created_at')
        result_page = paginator.paginate_queryset(messages, request)
        messages_serializer = ChatMessageSerializer(result_page, many=True)
        return paginator.get_paginated_response(messages_serializer.data)

@method_decorator(csrf_exempt, name='dispatch')
class WebhookView(APIView):

    def post(self, request):
        try:
            data = request.data
            g = open('o.txt', 'a')
            g.write(f"{data}" + '\n')
            account_id = request.GET.get('account_id')
            # hub_mode = request.GET.get('hub.mode')
            # hub_verify_token = request.GET.get('hub.verify_token')
            # hub_challenge = request.GET.get('hub.challenge')
            thread = threading.Thread(target=handel_request_redis(data, account_id))
            thread.start()
            return Response(status=status.HTTP_200_OK)
        except Exception as e:
            f = open('redis_error.txt', 'a')
            f.write(f"Error processign webhok: {str(e)}" + '\n')
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def get(self, request):
        try:
            data = request.data
            g = open('o.txt', 'a')
            g.write(f"{data}" + '\n')
            account_id = request.GET.get('account_id')
            hub_mode = request.GET.get('hub.mode')
            hub_verify_token = request.GET.get('hub.verify_token')
            hub_challenge = request.GET.get('hub.challenge')
            thread = threading.Thread(target=handel_request_redis(data, account_id))
            thread.start()
            if hub_mode == 'subscribe' and hub_verify_token == TOKEN_ACCOUNTS:
                return HttpResponse(hub_challenge, content_type="text/html")
            
        except Exception as e:
            f = open('redis_error.txt', 'a')
            f.write(f"Error processign webhok: {str(e)}" + '\n')
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

import base64
from django.http import JsonResponse
class ImageToBase64View(APIView):
    def get(self, request):
        image = request.data['image']
        img_data = image.read()
        encoded_img = base64.b64encode(img_data).decode('utf-8')

        return JsonResponse({
            # "success": True,
            "base64_image": encoded_img
        })
    


