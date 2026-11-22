from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Compra, ItensCompra, OperacaoOffline, Produto, User
from core.serializers import CompraCreateUpdateSerializer, CompraSerializer, UserSerializer
from core.serializers.compra import ItensCompraCreateUpdateSerializer, notificar_adicoes
from uploader.serializers import ImageUploadSerializer


class OperacaoSerializer(serializers.Serializer):
    chave = serializers.UUIDField()
    conta = serializers.IntegerField(min_value=1)
    tipo = serializers.ChoiceField(choices=['adicionar', 'quantidade', 'favorito', 'ler', 'avatar', 'desativar_push'])
    produto = serializers.IntegerField(min_value=1, required=False)
    quantidade = serializers.IntegerField(min_value=0, max_value=2147483647, required=False)
    favorito = serializers.BooleanField(required=False)
    notificacao = serializers.IntegerField(min_value=1, required=False)
    arquivo = serializers.FileField(required=False)
    dispositivo = serializers.RegexField(r'^[a-f0-9]{64}$', required=False)

    def validate(self, attrs):
        campos = {
            'adicionar': ('produto', 'quantidade'),
            'quantidade': ('produto', 'quantidade'),
            'favorito': ('produto', 'favorito'),
            'ler': ('notificacao',),
            'avatar': ('arquivo',),
            'desativar_push': ('dispositivo',),
        }
        faltantes = set(campos[attrs['tipo']]) - attrs.keys()
        if faltantes:
            raise serializers.ValidationError({campo: 'Campo obrigatório.' for campo in faltantes})
        return attrs


class SincronizacaoView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=OperacaoSerializer,
        responses={200: OpenApiTypes.OBJECT, 204: None},
        summary='Sincronizar uma alteração feita offline',
    )
    @transaction.atomic
    def post(self, request):
        serializer = OperacaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data
        if dados['conta'] != request.user.pk:
            return Response(status=status.HTTP_403_FORBIDDEN)

        # A gravação e o recibo têm a mesma transação. Um reenvio não reaplica a operação.
        usuario = User.objects.select_for_update(no_key=True).get(pk=request.user.pk)
        _, nova = OperacaoOffline.objects.get_or_create(usuario=usuario, chave=dados['chave'])
        tipo = dados['tipo']

        if nova:
            if tipo == 'adicionar':
                carrinho = CompraCreateUpdateSerializer(
                    data={'itens': [{'produto': dados['produto'], 'quantidade': dados['quantidade']}]},
                    context={'request': request},
                )
                carrinho.is_valid(raise_exception=True)
                carrinho.save()
            elif tipo == 'quantidade':
                self.alterar_quantidade(usuario, dados)
            elif tipo == 'favorito':
                produto = get_object_or_404(Produto, pk=dados['produto'])
                if dados['favorito']:
                    usuario.favoritos.add(produto)
                else:
                    usuario.favoritos.remove(produto)
            elif tipo == 'ler':
                notificacao = get_object_or_404(usuario.notificacoes, pk=dados['notificacao'])
                usuario.notificacoes.filter(pk=notificacao.pk, lida_em__isnull=True).update(lida_em=timezone.now())
            elif tipo == 'desativar_push':
                usuario.dispositivos_push.filter(identificador=dados['dispositivo']).delete()
            elif tipo == 'avatar':
                imagem = ImageUploadSerializer(data={'file': dados['arquivo']})
                imagem.is_valid(raise_exception=True)
                usuario.foto = imagem.save()
                usuario.save(update_fields=['foto'])

        contexto = {'request': request}
        if tipo in {'adicionar', 'quantidade'}:
            compra = Compra.obter_carrinho(usuario)
            return Response(CompraSerializer(compra, context=contexto).data if compra else {'id': None, 'itens': []})
        if tipo in {'favorito', 'avatar'}:
            return Response(UserSerializer(usuario, context=contexto).data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def alterar_quantidade(self, usuario, dados):
        quantidade = dados['quantidade']
        if quantidade:
            item_serializer = ItensCompraCreateUpdateSerializer(
                data={'produto': dados['produto'], 'quantidade': quantidade},
            )
            item_serializer.is_valid(raise_exception=True)
            produto = item_serializer.validated_data['produto']

        compra = Compra.obter_carrinho(usuario, criar=bool(quantidade))
        if compra is None:
            return

        itens = compra.itens.filter(produto_id=dados['produto'])
        anterior = itens.first()
        if quantidade:
            ItensCompra.objects.update_or_create(
                compra=compra, produto=produto, defaults={'quantidade': quantidade, 'preco': produto.preco},
            )
            notificar_adicoes(compra, [({'produto': produto}, quantidade - (anterior.quantidade if anterior else 0))])
        else:
            itens.delete()
        compra.save(update_fields=['total'])
