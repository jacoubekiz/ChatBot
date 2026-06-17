from rest_framework import serializers
from api.Channel.models_channel import Channle


class ChannleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channle
        fields = '__all__'
        extra_kwargs = {
            'account_id':{'read_only':True},
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
