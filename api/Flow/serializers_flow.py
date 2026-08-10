from rest_framework import serializers
from api.Flow.models_flow import Flow


class SerializerFlows(serializers.ModelSerializer):
    flow_url = serializers.SerializerMethodField()

    class Meta:
        model = Flow
        fields = '__all__'
    
    def get_flow_url(self, obj):
        request = self.context.get('request')
        if obj.flow:
            return request.build_absolute_uri(obj.flow.url)
        return None


class CreateFlowSerializer(serializers.Serializer):
    flow = serializers.FileField(required=True)
    flow_name = serializers.CharField(required=True, max_length=255)


class SetDefaultFlowSerializer(serializers.Serializer):
    flow_id = serializers.CharField(required=True, max_length=255)


class UpdateFlowSerializer(serializers.Serializer):
    flow_name = serializers.CharField(required=True, max_length=255)
    flow = serializers.FileField(required=True)

