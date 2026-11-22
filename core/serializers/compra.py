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

from core.models import Compra, ItensCompra, Notificacao

from .produto import ProdutoListSerializer


class ItensCompraSerializer(ModelSerializer):
    produto = ProdutoListSerializer(read_only=True)
    total = SerializerMethodField()

    def get_total(self, instance):
        return instance.quantidade * instance.preco

    class Meta:
        model = ItensCompra
        fields = ('produto', 'quantidade', 'preco', 'total')


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

    def validate_itens(self, itens):
        if len({item['produto'].pk for item in itens}) != len(itens):
            raise ValidationError('Informe cada produto uma única vez.')
        return itens

    class Meta:
        model = Compra
        fields = ('usuario', 'itens')  # 'id' saiu daqui na parte 39

    def notificar_adicoes(self, compra, adicoes):
        request = self.context.get('request')
        origem = request.headers.get('X-Push-Endpoint') if request else None
        notificar_adicoes(compra, adicoes, endpoint_origem=origem)

    @transaction.atomic
    def create(self, validated_data):
        itens = validated_data.pop('itens')
        usuario = validated_data['usuario']

        # só existe 1 carrinho (status CARRINHO) por usuário
        compra = Compra.obter_carrinho(usuario, criar=True)

        for item in itens:
            item_existente = compra.itens.filter(produto=item['produto']).first()

            if item_existente:
                # produto já está no carrinho: só incrementa a quantidade
                nova_quantidade = item_existente.quantidade + item['quantidade']
                if nova_quantidade > item['produto'].quantidade:
                    raise ValidationError(
                        f'Estoque insuficiente para "{item["produto"].nome}": '
                        f'há apenas {item["produto"].quantidade} unidade(s) disponível(is).'
                    )
                item_existente.quantidade = nova_quantidade
                item_existente.preco = item['produto'].preco
                item_existente.save()
            else:
                item['preco'] = item['produto'].preco
                ItensCompra.objects.create(compra=compra, **item)

        self.notificar_adicoes(compra, ((item, item['quantidade']) for item in itens))
        compra.save()  # recalcula e grava o campo "total" (parte 40)
        return compra

    @transaction.atomic
    def update(self, compra, validated_data):
        validated_data.pop('usuario', None)
        itens = validated_data.pop('itens', None)
        if itens is not None:
            anteriores = dict(compra.itens.values_list('produto_id', 'quantidade'))
            compra.itens.all().delete()
            for item in itens:
                item['preco'] = item['produto'].preco
                ItensCompra.objects.create(compra=compra, **item)

            self.notificar_adicoes(
                compra,
                ((item, item['quantidade'] - anteriores.get(item['produto'].pk, 0)) for item in itens),
            )

        return super().update(compra, validated_data)


def notificar_adicoes(compra, adicoes, *, endpoint_origem=None):
    notificacoes = (
        Notificacao(
            usuario_id=compra.usuario_id,
            tipo=Notificacao.Tipo.CARRINHO,
            produto=item['produto'],
            mensagem=f'Adicionado ao carrinho: {item["produto"].nome} × {quantidade}.',
        )
        for item, quantidade in adicoes if quantidade > 0
    )
    Notificacao.objects.registrar(notificacoes, endpoint_origem=endpoint_origem)


class CompraListSerializer(ModelSerializer):
    usuario = CharField(source='usuario.email', read_only=True)
    itens = ItensCompraListSerializer(many=True, read_only=True)

    class Meta:
        model = Compra
        fields = ('id', 'usuario', 'itens')
