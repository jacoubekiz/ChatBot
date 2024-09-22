from rest_framework.views import APIView
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
from .utils import read_json, show_response, send_message, validate_email, validate_phone_number, change_occurences, check_sql_condition
global client
from langdetect import detect
import langid
import datetime

class ClientsViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    queryset = Client.objects.all()

class BotAPI(APIView):
    def post(self, request, *args, **kwargs):
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

        try:
            flow = client.flow.get(trigger__trigger=request.data['content'])
            chats = Chat.objects.filter(Q(conversation_id = source_id) & Q(client_id = client.id) & ~Q(flow = flow))
            for c in chats:
                c.update_state('end')
                c.isSent = False
                c.save()
            # chate = Chat.objects.get(Q(conversation_id = source_id) & Q(client_id = client.id) & Q(flow = flow))

            # chate.update_state('start')
        except:
            ch = Chat.objects.get(Q(conversation_id = source_id) & Q(client_id = client.id) & ~Q(state = 'end'))
            flow = ch.flow
            
        
        file_path = default_storage.path(flow.flow.name)
        chat_flow = read_json(file_path)
        if chat_flow and source_id:
            chat, isCreated = Chat.objects.get_or_create(conversation_id = source_id, client_id = client.id, flow=flow )
            print(chat.state)
            questions = chat_flow['payload']['questions']
            if not bool(chat.state) or chat.state == 'end' or chat.state == '':
                chat.update_state('start')
            while True:
                next_question_id = None
                if chat.state == 'start':
                    lang = langid.classify(request.data['content'])
                    language = lang[0]
                    for ques in questions:
                        try:
                            ques_lang_type = ques['type_language']
                        except:
                            ques_lang_type = ''
                        if ques_lang_type  == language:
                                question = ques
                                break
                else:
                    for item in questions:
                        if item['id'] == chat.state:
                            question = item
                            break
                        
                message, next_question_id, choices_with_next, choices, r_type, attribute_name = show_response(question, questions)
                if r_type == 'button' or r_type == 'list':
                    
                    if not chat.isSent:
                        chat.isSent = True
                        chat.save()
                        
                        if r_type == 'list':
                            print('is the list?')
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
                            
                            try: #If this raises an error then this means that it is a beam user reply not normal beam text message reply
                                user_reply = request.data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']
                            
                            except:
                                user_reply = request.data['entry'][0]['changes'][0]['value']['messages'][0]['reply_to']['button_title']

                        restart_keywords = [r.keyword for r in RestartKeyword.objects.filter(client_id = client.id)]
                        
                        if user_reply in restart_keywords:
                            chat.isSent = False
                            chat.save()
                            chat.update_state('start')
                            continue
                            
                        elif user_reply not in choices or user_reply == '':
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
                            print('hello jjjjalllallalalalallalalalalallalalallalla')
                        
                        except:
                            
                            try: #If this raises an error then this means that it is a beam user reply not normal beam text message reply
                                user_reply = request.data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']
                            
                            except:
                                user_reply = request.data['entry'][0]['changes'][0]['value']['messages'][0]['reply_to']['button_title']
                                
                        restart_keywords = [r.keyword for r in RestartKeyword.objects.filter(client_id = client.id)]
                        
                        # attr, created = Attribute.objects.get_or_create(key=attribute_name, chat=chat)
                        attr, created = Attribute.objects.get_or_create(key=attribute_name, chat_id=chat.id)
                        attr.value = user_reply
                        attr.save()
                        if user_reply in restart_keywords:
                            chat.isSent = False
                            chat.save()
                            chat.update_state('start')
                            continue
                        #Smart Question user reply validation:
                        #elif user_reply not in choices or user_reply == '':
                        #    error_message = question['message']['error']
                        #    send_message(message_content=error_message, to=chat.conversation_id, bearer_token=client.token)
                        #    return Response(
                        #        {"Message" : "BOT has interacted successfully."},
                        #        status=status.HTTP_200_OK
                        #    )
                        else:
                        
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
                
                # for handle api in flow
                elif r_type == 'api':
                    next_question_id = handle_api(question, choices_with_next)

                
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
    

class ViewSignUp(GenericAPIView):
    # serializer_class = SerializerSignUp

    def post(self, request):
        data = request.data
        serializer = SerializerSignUp(data = data, many=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        user_information = serializer.data
        email = user_information['email']
        user = CustomUser.objects.get(email=email)
        token = RefreshToken.for_user(user)
        user_token = {
            'refresh':str(token),
            'access':str(token.access_token),
        }
        
        user_information['tokens'] = user_token
        return Response(user_information, status=status.HTTP_201_CREATED)
    
class ViewLogin(GenericAPIView):

    def post(self, request):
        data = request.data
        serializer = LoginSerializer(data = data, many=False)
        serializer.is_valid(raise_exception=True)
        user_informatin = serializer.data
        email = user_informatin['username']
        user = CustomUser.objects.get(email=email)
        token = RefreshToken.for_user(user)
        user_informatin['tokens'] = {'refresh':str(token), 'access':str(token.access_token)}
        return Response(user_informatin, status=status.HTTP_200_OK)
    

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
        print(timezone.now().day)
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
        info = request.data
        free_hours = []
        day_number = days.index(get_day_name(info['date']))
        if day_number == 0:
            day_number +=1
        calendar = Calendar.objects.filter(key=info['key']).first()
        working_time = calendar.working_time.get(day=day_number)
        start_work_am = convert_time_to_timedelta(working_time.starting_time_am)
        start_work_pm = convert_time_to_timedelta(working_time.starting_time_pm)
        end_work_am = convert_time_to_timedelta(working_time.end_time_am)
        end_work_pm = convert_time_to_timedelta(working_time.end_time_pm)
        duration = calendar.duration.duration
        time_slots = []

        user_book_an_appointment = calendar.user.bookanappointment_set.filter(Q(day=info['date'])).order_by('day', 'hour')
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
        
        info = request.data
        free_hours = []
        free_days = []
        if info['date'] == '':
            day = timezone.now().date()
        else:
            day = datetime.datetime.strptime(info['date'], '%Y-%m-%d').date()
        next_days = []
        for d in range(10):
            next_days.append(day + timedelta(days=d))
        for next_day in next_days:
            day_number = days.index(get_day_name(next_day))
            if day_number == 0:
                day_number +=1
            if day_number == 6 or day_number == 5:
                continue
            calendar = Calendar.objects.filter(key=info['key']).first()
            working_time = calendar.working_time.get(day=day_number)
            start_work_am = convert_time_to_timedelta(working_time.starting_time_am)
            end_work_am = convert_time_to_timedelta(working_time.end_time_am)
            end_work_pm = convert_time_to_timedelta(working_time.end_time_pm)
            duration = calendar.duration.duration
            user_book_an_appointment = calendar.user.bookanappointment_set.filter(Q(day=next_day)).order_by('day', 'hour')
            if not user_book_an_appointment:
                free_days.append((get_day_name(next_day), next_day))
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
                    free_days.append((get_day_name(next_day), next_day))
                    continue

            for free in free_hours:
                if convert_time_to_timedelta(free[0]) <= end_work_am and convert_time_to_timedelta(free[1]) >= end_work_am:
                    free_days.append((get_day_name(next_day), next_day))
                    continue
   
            print(free_days)
        return Response({'free_days':free_days},status=status.HTTP_200_OK)


class GetDoctorsView(APIView):
    def get(self, request):
        user = CustomUser.objects.all()
        serializer_user = SerializerSignUp(user, many=True)
        data = serializer_user.data

        return Response({'username':data['username']}, status=status.HTTP_200_OK)