from collections.abc import Mapping
from hashlib import sha256

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.models import Compra, User
from core.models.notificacao import DispositivoPush
from core.push import configurado
from core.serializers import CompraSerializer, UserRegistrationSerializer, UserSerializer
from core.serializers.produto import ProdutoFavoritoSerializer
from core.serializers.user import DispositivoPushSerializer, NotificacaoSerializer


class UserViewSet(ModelViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserRegistrationSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        if self.request.user.is_superuser:
            return self.queryset
        return self.queryset.filter(pk=self.request.user.pk)

    def listar(self, queryset, serializer_class):
        pagina = self.paginate_queryset(queryset)
        serializer = serializer_class(pagina, many=True, context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data)

    @extend_schema(responses=ProdutoFavoritoSerializer(many=True))
    @action(detail=False)
    def favoritos(self, request):
        produtos = request.user.favoritos.com_queda_de_preco().select_related('capa').order_by('nome', 'pk')
        return self.listar(produtos, ProdutoFavoritoSerializer)

    @extend_schema(responses=CompraSerializer(many=True))
    @action(detail=False)
    def historico_compras(self, request):
        compras = (
            request.user.compras.exclude(status=Compra.StatusCompra.CARRINHO)
            .select_related('usuario')
            .prefetch_related('itens__produto__capa')
            .order_by('-data', '-pk')
        )
        return self.listar(compras, CompraSerializer)

    @extend_schema(responses=NotificacaoSerializer(many=True))
    @action(detail=False)
    def notificacoes(self, request):
        return self.listar(request.user.notificacoes.all(), NotificacaoSerializer)

    @extend_schema(request=None, responses=NotificacaoSerializer)
    @action(detail=False, methods=['post'], url_path=r'notificacoes/(?P<notificacao_id>[0-9]+)/ler')
    def ler_notificacao(self, request, notificacao_id):
        notificacoes = request.user.notificacoes.filter(pk=notificacao_id)
        notificacao = get_object_or_404(notificacoes)
        if notificacao.lida_em is None:
            notificacoes.filter(lida_em__isnull=True).update(lida_em=timezone.now())
            notificacao.refresh_from_db()
        return Response(NotificacaoSerializer(notificacao).data)

    @action(detail=False, url_path='notificacoes/nao-lidas')
    def notificacoes_nao_lidas(self, request):
        return Response({'total': request.user.notificacoes.filter(lida_em__isnull=True).count()})

    @action(detail=False, methods=['get', 'put', 'delete'])
    @transaction.atomic
    def push(self, request):
        dispositivos = request.user.dispositivos_push
        if request.method == 'GET':
            identificador = request.query_params.get('dispositivo')
            return Response({
                'chave_publica': settings.WEB_PUSH_PUBLIC_KEY if configurado() else '',
                'ativo': bool(identificador and dispositivos.filter(identificador=identificador).exists()),
            })

        if request.method == 'DELETE':
            identificador = request.data.get('dispositivo') if isinstance(request.data, Mapping) else None
            if isinstance(identificador, str) and len(identificador) == 64:
                dispositivos.filter(identificador=identificador).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        if not configurado():
            return Response({'detail': 'Web Push indisponível.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        serializer = DispositivoPushSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        endpoint = serializer.validated_data['endpoint']
        identificador = sha256(endpoint.encode()).hexdigest()
        dispositivo, criado = DispositivoPush.objects.select_for_update().get_or_create(
            identificador=identificador,
            defaults={'usuario': request.user, 'endpoint': endpoint, **serializer.validated_data['keys']},
        )
        if dispositivo.usuario_id != request.user.pk:
            return Response({'detail': 'A assinatura pertence a outra conta.'}, status=status.HTTP_409_CONFLICT)

        if not criado:
            dispositivos.filter(pk=dispositivo.pk).update(**serializer.validated_data['keys'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary='Dados do usuário autenticado',
        description='Retorna os dados do usuário autenticado.',
        responses={200: UserSerializer, 401: None},
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Retorna os dados do usuário autenticado."""
        user = request.user
        serializer = UserSerializer(user, context=self.get_serializer_context())
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserRegistrationView(CreateAPIView):
    """Endpoint para registro de novos usuários."""

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
