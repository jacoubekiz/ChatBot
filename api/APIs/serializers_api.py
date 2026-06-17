from rest_framework import serializers
from api.APIs.models_api import API, Parameter, Api_parameter, APILog
from api.Flow.models_flow import Custome_attribute, Attribute



class APISerializer(serializers.ModelSerializer):
    class Meta:
        model = API
        fields = ['api_id', 'api_name', 'endpoint', 'method', 'body', 'parameters', 'response']
        extra_kwargs = {
            'parameters':{'read_only':True},
        }

    def create(self, validated_data):
        parameters = self.context.get('parameters', [])
        account = self.context.get('account')
        validated_data['account_id'] = account
        api = API.objects.create(**validated_data)
        parameter = Parameter.objects.create(account_id=account)
        if parameters:
            for param in parameters:
                Api_parameter.objects.create(
                    parameter=parameter,
                    api=api,
                    type=param.get('type'),
                    key=param.get('key'),
                    value=param.get('value')
                )
        api.parameters.set([parameter])
        api.save()
        custome_attrs = self.context.get('custome_attrs', [])
        if custome_attrs:
            for custome_attr in custome_attrs:
                Custome_attribute.objects.create(
                    attribute=Attribute.objects.filter(id=custome_attr['attr_id']),
                    variable=custome_attr['variable'],
                    api=api
                )
        return api
    
    def update(self, instance, validated_data):
        parameters = self.context.get('parameters', [])
        custome_attrs = self.context.get('custome_attrs', [])
        instance.api_name = validated_data.get('api_name', instance.api_name)
        instance.endpoint = validated_data.get('endpoint', instance.endpoint)
        instance.method = validated_data.get('method', instance.method)
        instance.body = validated_data.get('body', instance.body)
        instance.save()

        if parameters:
            param_ = Api_parameter.objects.filter(api=instance).first()
            parameter_instance = param_.parameter
            Api_parameter.objects.filter(api=instance).delete()
            for param in parameters:
                Api_parameter.objects.create(
                    api=instance,
                    parameter=parameter_instance,
                    type=param.get('type'),
                    key=param.get('key'),
                    value=param.get('value')
                )
        
        if custome_attrs:
            Custome_attribute.objects.filter(api=instance).delete()
            for custome_attr in custome_attrs:
                Custome_attribute.objects.create(
                    attribute=Attribute.objects.filter(id=custome_attr['attr_id']).first(),
                    variable=custome_attr['variable'],
                    api=instance
                )
        return instance


class SerializerCustomeAttributes(serializers.ModelSerializer):
    class Meta:
        model = Custome_attribute
        fields = ['variable', 'attribute']

    def to_representation(self, instance):
        repr = super().to_representation(instance)
        repr['attribute'] = instance.attribute.key
        return repr


class APIParametersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Api_parameter
        fields = ['type', 'key', 'value']


class APILogSerializer(serializers.ModelSerializer):
    body = serializers.CharField(source="api.body", read_only=True)
    endpoint = serializers.CharField(source='api.endpoint', read_only=True)
    method = serializers.CharField(source='api.method', read_only=True)
    
    class Meta:
        model = APILog
        fields = ["apilog_id", "api", "endpoint", "body", "method", "response", "created_at"]


class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = '__all__'

class SerializerAttributes(serializers.ModelSerializer):
    class Meta:
        model = Attribute
        fields = ['id', 'key', 'save_api', 'account']

        extra_kwargs = {
            'account':{'read_only':True},
            'save_api': {'read_only':True}
        }

    def create(self, validated_data):
        account = self.context.get('account')
        validated_data['account'] = account
        validated_data['save_api'] = True
        Attribute.objects.create(**validated_data)
        return True