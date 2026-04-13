from rest_framework.serializers import ModelSerializer

from core.models import Estoque


class EstoqueSerializer(ModelSerializer):
    class Meta:
        model = Estoque
        fields = '__all__'
