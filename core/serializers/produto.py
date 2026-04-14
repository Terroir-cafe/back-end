from rest_framework.serializers import ModelSerializer

from core.models import Produto


class ProdutoSerializer(ModelSerializer):
    class Meta:
        model = Produto
        fields = '__all__'


class ProdutoListRetriverSerializer(ModelSerializer):
    class Meta:
        model = Produto
        fields = '__all__'
        depth = 1
