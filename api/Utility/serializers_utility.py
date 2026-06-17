from rest_framework import serializers
from api.Utility.models_utility import Report


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['report_id', 'name', 'data']
