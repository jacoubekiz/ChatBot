"""
API handler functions for bot integration.
"""
import json
import requests
from asgiref.sync import sync_to_async
from api.utils import change_occurences
from .database_helpers import DatabaseHelpers


class APIHandlers:
    """Helper class for API operations."""
    
    @staticmethod
    async def execute_api_call(api, chat, choices_with_next):
        """Execute an API call and handle response."""
        api_parameter_headers, api_parameter_params = await DatabaseHelpers.get_api_parameter_header(api)
        
        headers = {
            'Content-Type': 'application/json',
        }
        headers_ = await DatabaseHelpers.get_new_header(headers, api_parameter_headers, chat)
        
        data = json.loads(api.body) if api.body else {}
        endpoint = api.endpoint
        endpoint_ = await DatabaseHelpers.get_new_endpoint(endpoint, api_parameter_params, chat)
        
        try:
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    continue
                data[key] = await sync_to_async(change_occurences)(value, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)
        except:
            data = {}
        
        response = requests.post(endpoint_, headers=headers_, json=data)
        
        api_log = await DatabaseHelpers.create_api_log(
            api=api,
            response=json.loads(response.content) if response.content else {},
            status_request=response.status_code
        )
        
        custome_attrs = await DatabaseHelpers.get_custome_attrs(api)
        await DatabaseHelpers.save_api_response_in_custome_attribute(custome_attrs, response, chat)
        
        next_question_id = await APIHandlers._handle_api_response(response, choices_with_next, chat)
        return next_question_id
    
    @staticmethod
    async def _handle_api_response(response, choices_with_next, chat):
        """Handle API response and determine next question."""
        next_question_id = None
        
        for option in choices_with_next:
            for state in option:
                if str(response.status_code) == str(state):
                    next_question_id = option[2]
                    await DatabaseHelpers.update_chat_status(chat, next_question_id)
                    return next_question_id
        
        return next_question_id
