import re
from django.db import connection
from django.db.models import Q
from api.Flow.models_flow import Attribute, Custome_attribute, Chat


def show_response(question, questions, chat_id):
    """Process flow question and return response details."""
    current_response = ''
    choices_with_next = None
    next_question_id = None
    choices = None
    r_type = None
    current_response += question['label'] + '\n'
    try:
        options = question['options']
    except:
        options = None
    
    if options:
        if question['type'] == 'smart_question':
            choices_with_next = [(option['value'], option['id'], option['next']['target'], option['keywordType'], option['smartKeywords']) for option in question['options']]
        
        elif question['type'] == 'condition' or question['type'] == 'Condition':
            choices_with_next = [(option['ConditionValue'], option['value'], option['id'], option['next']['target']) for option in question['options']]

        elif question['type'] == 'button':
            choices_with_next = [(option['value'], option['id'], option['next']['target']) for option in question['options']]
            choices = [c[0] for c in choices_with_next]
        
        elif question['type'] == 'list':
            choices_with_next = [(option['value'], option['id'], option['next']['target']) for option in question['options']]
            choices = [c[0] for c in choices_with_next]
            
        elif question['type'] == 'api':
            choices_with_next = [(option['value'], option['id'], option['next']['target']) for option in question['options']]
            next_id = [next_question['next']['target'] for next_question in question['options']]
            choices = [c[0] for c in choices_with_next]
            
        elif question['type'] == 'calendar':
            choices_with_next = [(option['value'], option['next']['target']) for option in question['options']]
            choices = [c[0] for c in choices_with_next]

        elif question['type'] == 'detect_language':
            choices_with_next = [(option['value'], option['next']['target']) for option in question['options']]
            choices = [c[0] for c in choices_with_next]
        
    elif question['type'] == 'if-else':
        branches = question['ifElse']['branches']
        for branch in branches:
            orGroups = branch['if']['orGroups']
            for orGroup in orGroups:
                conditions = orGroup['conditions']
                attr = Attribute.objects.filter(Q(key=conditions[0]['customAttribute'])).first()
                operator = conditions[0]['operator']
                value = conditions[0]['value']
                customAttribute = Custome_attribute.objects.filter(Q(attribute=attr) & Q(chat=chat_id)).first()
                if customAttribute:
                    customAttributeValue = customAttribute.value
                    if operator == 'equals' and customAttributeValue == value:
                        next_question_id = branch['if']['target']
                        break
                    elif operator == 'not_equals' and customAttributeValue != value:
                        next_question_id = branch['if']['target']
                        break
                    elif operator == 'contains' and value in customAttributeValue:
                        next_question_id = branch['if']['target']
                        break
                    elif operator == 'not_contains' and value not in customAttributeValue:
                        next_question_id = branch['if']['target']
                        break
            if next_question_id != None:
                break
        if next_question_id == None:
            next_question_id = question['next']['target']

    else:
        next_question_id = question['next']['target']

    r_type = question['type']
    try:
        question_attribute = question['attributeName']
    except:
        question_attribute = ''
    if current_response:
        return current_response, next_question_id, choices_with_next, choices, r_type, question_attribute
    else:
        return 'Chat Ended'


def change_occurences(content, pattern, chat_id, sql=False):
    """Replace template variables with actual values from custom attributes."""
    matches = re.findall(pattern, content)
    for match in matches:
        try:
            attr_ = Attribute.objects.filter(key=match).first()
            attr = Custome_attribute.objects.filter(attribute=attr_, chat_id=chat_id).first()
            if sql:
                if not attr.value.isdigit():
                    replacement_word = f'{attr.value}'
                else:
                    replacement_word = attr.value
            else:
                replacement_word = attr.value
            content = content.replace(f'{{{{{match}}}}}', replacement_word)
        except:
            if sql:
                if match == "phone":
                    chat = Chat.objects.get(id=chat_id)
                    content = content.replace(f'{{{{{match}}}}}', chat.conversation_id)
    return content


def check_sql_condition(sql_condition):
    """Check if SQL condition evaluates to true."""
    with connection.cursor() as cursor:
        try:
            cursor.execute(f"SELECT CASE WHEN {sql_condition} THEN 1 ELSE 0 END")
            result = cursor.fetchone()[0]
            return bool(result)
        except Exception as e:
            return f"Error executing SQL condition: {e}"
