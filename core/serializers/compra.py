from django.db import transaction

from rest_framework.serializers import (
    CharField,
    CurrentUserDefault,
    DateTimeField,
    HiddenField,
    ModelSerializer,
    SerializerMethodField,
    ValidationError,
)

from core.models import Compra, ItensCompra


class ItensCompraSerializer(ModelSerializer):
    total = SerializerMethodField()

    def get_total(self, instance):
        return instance.quantidade * instance.preco

    class Meta:
        model = ItensCompra
        fields = ('produto', 'quantidade', 'preco', 'total')
        depth = 1


class ItensCompraCreateUpdateSerializer(ModelSerializer):
    class Meta:
        model = ItensCompra
        fields = ('produto', 'quantidade', 'preco')

    def validate_quantidade(self, quantidade):
        if quantidade <= 0:
            raise ValidationError('A quantidade deve ser maior do que zero.')
        return quantidade

    def validate(self, item):
        produto = item['produto']

        if produto.preco <= 0:
            raise ValidationError('Este produto não pode ser comprado: preço inválido.')

        if item['quantidade'] > produto.quantidade:
            raise ValidationError('Quantidade de itens maior do que a quantidade em estoque.')

        return item


class ItensCompraListSerializer(ModelSerializer):
    produto = CharField(source='produto.titulo', read_only=True)

    class Meta:
        model = ItensCompra
        fields = ('quantidade', 'preco', 'produto')
        depth = 1


class CompraSerializer(ModelSerializer):
    usuario = CharField(source='usuario.email', read_only=True)
    status = CharField(source='get_status_display', read_only=True)
    data = DateTimeField(read_only=True)
    itens = ItensCompraSerializer(many=True, read_only=True)

    class Meta:
        model = Compra
        fields = ('id', 'usuario', 'status', 'total', 'data', 'itens')


class CompraCreateUpdateSerializer(ModelSerializer):
    usuario = HiddenField(default=CurrentUserDefault())
    itens = ItensCompraCreateUpdateSerializer(many=True)

    class Meta:
        model = Compra
        fields = ('usuario', 'itens')  # 'id' saiu daqui na parte 39

    @transaction.atomic
    def create(self, validated_data):
        itens = validated_data.pop('itens')
        usuario = validated_data['usuario']

        # só existe 1 carrinho (status CARRINHO) por usuário
        compra, criada = Compra.objects.get_or_create(
            usuario=usuario, status=Compra.StatusCompra.CARRINHO, defaults=validated_data
        )

        for item in itens:
            item_existente = compra.itens.filter(produto=item['produto']).first()

            if item_existente:
                # produto já está no carrinho: só incrementa a quantidade
                item_existente.quantidade += item['quantidade']
                item_existente.preco = item['produto'].preco
                item_existente.save()
            else:
                item['preco'] = item['produto'].preco
                ItensCompra.objects.create(compra=compra, **item)

        compra.save()  # recalcula e grava o campo "total" (parte 40)
        return compra

    @transaction.atomic
    def update(self, compra, validated_data):
        itens = validated_data.pop('itens', [])
        if itens:
            compra.itens.all().delete()
            for item in itens:
                item['preco'] = item['produto'].preco
                ItensCompra.objects.create(compra=compra, **item)

        return super().update(compra, validated_data)


class CompraListSerializer(ModelSerializer):
    usuario = CharField(source='usuario.email', read_only=True)
    itens = ItensCompraListSerializer(many=True, read_only=True)

    class Meta:
        model = Compra
        fields = ('id', 'usuario', 'itens')