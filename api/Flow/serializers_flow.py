from rest_framework import serializers
from api.Flow.models_flow import Flow


class SerializerFlows(serializers.ModelSerializer):
    flow_url = serializers.SerializerMethodField()

    class Meta:
        model = Flow
        fields = '__all__'
        extra_kwargs = {
            'flow_name': {
                'error_messages': {
                    'required': 'Flow name is required',
                    'blank': 'Flow name cannot be empty',
                    'max_length': 'Flow name cannot exceed 100 characters'
                }
            },
            'flow': {
                'error_messages': {
                    'required': 'Flow file is required'
                }
            }
        }
    
    def get_flow_url(self, obj):
        request = self.context.get('request')
        if obj.flow:
            return request.build_absolute_uri(obj.flow.url)
        return None

