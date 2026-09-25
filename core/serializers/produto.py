from rest_framework.serializers import (
    DecimalField,
    IntegerField,
    ModelSerializer,
    Serializer,
    SlugRelatedField,
    ValidationError,
)

from core.models import Produto
from uploader.models import Image
from uploader.serializers import ImageSerializer


class ProdutoSerializer(ModelSerializer):
    capa_attachment_key = SlugRelatedField(
        source='capa',
        queryset=Image.objects.all(),
        slug_field='attachment_key',
        required=False,
        write_only=True,
    )
    capa = ImageSerializer(required=False, read_only=True)

    class Meta:
        model = Produto
        fields = '__all__'


class ProdutoAlterarPrecoSerializer(Serializer):
    preco = DecimalField(max_digits=7, decimal_places=2)

    def validate_preco(self, preco):
        """Valida se o preço é um valor positivo."""
        if preco <= 0:
            raise ValidationError('O preço deve ser um valor positivo.')
        return preco


class ProdutoListSerializer(ModelSerializer):
    capa_attachment_key = SlugRelatedField(
        source='capa',
        queryset=Image.objects.all(),
        slug_field='attachment_key',
        required=False,
        write_only=True,
    )
    capa = ImageSerializer(required=False, read_only=True)

    class Meta:
        model = Produto
        fields = '__all__'


class ProdutoRetrieveSerializer(ModelSerializer):
    capa = ImageSerializer(required=False)

    class Meta:
        model = Produto
        fields = '__all__'
        depth = 1


class ProdutoMaisVendidoSerializer(ModelSerializer):
    total_vendidos = IntegerField()

    class Meta:
        model = Produto
        fields = ('id', 'nome', 'total_vendidos')