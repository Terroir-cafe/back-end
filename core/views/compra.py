from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.models import Compra, Produto
from core.serializers import CompraCreateUpdateSerializer, CompraListSerializer, CompraSerializer


class CompraViewSet(ModelViewSet):
    # Qualquer usuário logado pode montar o próprio carrinho
    # (o get_queryset já garante que ele só enxerga as próprias compras).
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user
        compras = Compra.objects.all()
        if self.action in {'update', 'partial_update', 'finalizar', 'destroy'}:
            compras = compras.select_for_update()
        if usuario.is_superuser or usuario.groups.filter(name='administradores').exists():
            return compras
        return compras.filter(usuario=usuario)

    def get_serializer_class(self):
        if self.action == 'list':
            return CompraListSerializer
        if self.action in {'create', 'update', 'partial_update'}:
            return CompraCreateUpdateSerializer
        return CompraSerializer

    @extend_schema(
        request=None,
        responses={200: CompraSerializer},
        description='Retorna o carrinho em aberto do usuário logado (ou um carrinho vazio, sem criar nada).',
        summary='Carrinho atual',
    )
    @action(detail=False, methods=['get'])
    def carrinho(self, request):
        compra = Compra.obter_carrinho(request.user)
        if compra is None:
            return Response({'id': None, 'status': 'Carrinho', 'total': '0.00', 'data': None, 'itens': []})
        return Response(CompraSerializer(compra, context={'request': request}).data)

    @extend_schema(responses={201: CompraSerializer}, summary='Adicionar itens ao carrinho')
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        compra = serializer.save()
        # devolve o carrinho completo e atualizado, pronto para o front renderizar
        return Response(CompraSerializer(compra, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: CompraSerializer}, summary='Substituir os itens do carrinho')
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        compra = self.get_object()
        if compra.status != Compra.StatusCompra.CARRINHO:
            raise ValidationError({'status': 'Só é possível alterar itens de uma compra que ainda é carrinho.'})
        serializer = self.get_serializer(compra, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        compra = serializer.save()
        return Response(CompraSerializer(compra, context={'request': request}).data)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        compra = self.get_object()
        if compra.status != Compra.StatusCompra.CARRINHO:
            raise ValidationError({'status': 'A compra faz parte do histórico.'})
        self.perform_destroy(compra)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=None,
        responses={200: None},
        description='Gera um relatório de vendas do mês atual.',
        summary='Relatório de vendas do mês',
    )
    @action(detail=False, methods=['get'])
    def relatorio_vendas_mes(self, request):
        agora = timezone.now()
        inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        compras = Compra.objects.filter(status=Compra.StatusCompra.FINALIZADO, data__gte=inicio_mes)

        total_vendas = sum(compra.total for compra in compras)
        quantidade_vendas = compras.count()

        return Response(
            {
                'status': 'Relatório de vendas deste mês',
                'total_vendas': total_vendas,
                'quantidade_vendas': quantidade_vendas,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=None,
        responses={200: None, 400: None},
        description='Finaliza a compra, atualizando o estoque dos produtos.',
        summary='Finalizar compra',
    )
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def finalizar(self, request, pk=None):
        compra = self.get_object()

        if compra.status != Compra.StatusCompra.CARRINHO:
            raise ValidationError({'status': 'A compra já foi finalizada.'})

        itens = list(compra.itens.all())
        if not itens:
            raise ValidationError({'status': 'Adicione produtos antes de finalizar a compra.'})

        produtos = {
            produto.pk: produto
            for produto in Produto.objects.select_for_update()
            .filter(pk__in=[item.produto_id for item in itens]).order_by('pk')
        }

        for item in itens:
            produto = produtos[item.produto_id]
            if item.quantidade > produto.quantidade:
                raise ValidationError({
                    'status': 'Quantidade insuficiente',
                    'produto': produto.nome,
                    'quantidade_disponivel': produto.quantidade,
                })
            produto.quantidade -= item.quantidade

        for produto in produtos.values():
            produto.save(update_fields=['quantidade'])

        # Finaliza a compra: atualiza status
        compra.status = Compra.StatusCompra.FINALIZADO
        compra.save(endpoint_origem=request.headers.get('X-Push-Endpoint'))

        return Response(status=status.HTTP_200_OK, data={'status': 'Compra finalizada'})
