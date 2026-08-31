from django.db import transaction
from rest_framework.serializers import (
    CharField,
    CurrentUserDefault,
    HiddenField,
    ModelSerializer,
    SerializerMethodField,
    ValidationError,
)

from core.models import Compra, ItensCompra


class ItensCompraCreateUpdateSerializer(ModelSerializer):
    class Meta:
        model = ItensCompra
        fields = ('produto', 'quantidade', 'preco')  # mudou

    def validate_quantidade(self, quantidade):
        if quantidade <= 0:
            raise ValidationError('A quantidade deve ser maior do que zero.')
        return quantidade

    def validate(self, item):
        if item['quantidade'] > item['produto'].quantidade:
            raise ValidationError('Quantidade de itens maior do que a quantidade em estoque.')
        return item


class ItensCompraSerializer(ModelSerializer):
    total = SerializerMethodField()

    def get_total(self, instance):
        return instance.quantidade * instance.preco

    class Meta:
        model = ItensCompra
        fields = ('produto', 'quantidade', 'total', 'preco')
        depth = 1


class ItensCompraListSerializer(ModelSerializer):
    produto = CharField(source='produto.nome', read_only=True)

    class Meta:
        model = ItensCompra
        fields = ('quantidade', 'produto', 'preco')
        depth = 1


class CompraListSerializer(ModelSerializer):
    usuario = CharField(source='usuario.email', read_only=True)
    itens = ItensCompraListSerializer(many=True, read_only=True)

    class Meta:
        model = Compra
        fields = ('id', 'usuario', 'itens')


class CompraCreateUpdateSerializer(ModelSerializer):
    usuario = HiddenField(default=CurrentUserDefault())

    class Meta:
        model = Compra
        fields = ('id', 'usuario', 'itens')

    @transaction.atomic
    def create(self, validated_data):
        itens = validated_data.pop('itens')
        compra = Compra.objects.create(**validated_data)
        for item in itens:
            item['preco'] = item['produto'].preco  # preço do produto no momento da compra
            ItensCompra.objects.create(compra=compra, **item)
        compra.save()
        return compra

    @transaction.atomic
    def update(self, compra, validated_data):
        itens = validated_data.pop('itens')
        if itens:
            compra.itens.all().delete()
            for item in itens:
                item['preco'] = item['livro'].preco  # grava o preço histórico
                ItensCompra.objects.create(compra=compra, **item)
        compra.save()
        return super().update(compra, validated_data)


class CompraSerializer(ModelSerializer):
    usuario = CharField(source='usuario.email', read_only=True)  # inclua essa linha
    itens = ItensCompraSerializer(many=True, read_only=True)
    status = CharField(source='get_status_display', read_only=True)  # inclua essa linha

    class Meta:
        model = Compra
        fields = ('id', 'usuario', 'status', 'total', 'itens')
