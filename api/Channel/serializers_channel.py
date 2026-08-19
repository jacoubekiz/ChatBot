from rest_framework import serializers
from api.Channel.models_channel import Channle


class ChannleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channle
        fields = '__all__'
        extra_kwargs = {
            'account_id':{'read_only':True},
            'type_channle':{
                'error_messages':{
                    'required': 'Channel type is required',
                    'invalid_choice': 'Invalid channel type. Must be WhatsApp'
                }
            },
            'tocken':{
                'error_messages':{
                    'required': 'Token is required',
                    'blank': 'Token cannot be blank',
                    'max_length': 'Token cannot exceed 600 characters'
                }
            },
            'phone_number':{
                'error_messages':{
                    'required': 'Phone number is required',
                    'invalid': 'Invalid phone number format'
                }
            },
            'phone_number_id':{
                'error_messages':{
                    'required': 'Phone number ID is required',
                    'invalid': 'Invalid phone number ID format'
                }
            },
            'organization_id':{
                'error_messages':{
                    'required': 'Organization ID is required',
                    'invalid': 'Invalid organization ID format'
                }
            },
            'name':{
                'error_messages':{
                    'required': 'Channel name is required',
                    'blank': 'Channel name cannot be blank',
                    'max_length': 'Channel name cannot exceed 50 characters'
                }
            },
            'flows':{'read_only':True},
            'created_at':{'read_only':True},
            'updated_at':{'read_only':True},
        }

    def update(self, instance, validated_data):
        instance.type_channle = validated_data.get('type_channle', instance.type_channle)
        instance.tocken = validated_data.get('tocken', instance.tocken)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.phone_number_id = validated_data.get('phone_number_id', instance.phone_number_id)
        instance.organization_id = validated_data.get('organization_id', instance.organization_id)
        instance.name = validated_data.get('name', instance.name)
        instance.save()
        return instance
