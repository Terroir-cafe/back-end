import json
import logging
from datetime import timedelta
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.utils import timezone

from core.models.notificacao import DispositivoPush, EntregaPush

logger = logging.getLogger(__name__)

SERVICOS_PUSH = (
    'fcm.googleapis.com',
    'updates.push.services.mozilla.com',
    'push.services.mozilla.com',
    'push.apple.com',
    'notify.windows.com',
)

MENSAGENS = {
    'compra': 'Uma compra mudou de status.',
    'carrinho': 'Um item foi adicionado ao seu carrinho.',
    'preco': 'O preço de um produto favorito mudou.',
}


def configurado():
    return bool(settings.WEB_PUSH_PUBLIC_KEY and settings.WEB_PUSH_PRIVATE_KEY and settings.WEB_PUSH_SUBJECT)


def endpoint_permitido(endpoint):
    try:
        url = urlsplit(endpoint)
        host = url.hostname or ''
        return (
            url.scheme == 'https'
            and url.netloc.lower() in {host, f'{host}:443'}
            and url.path.startswith('/')
            and not url.fragment
            and any(host == servico or host.endswith(f'.{servico}') for servico in SERVICOS_PUSH)
        )
    except ValueError:
        return False


def enfileirar(notificacoes, *, endpoint_origem=None):
    if not configurado():
        return
    por_usuario = {}
    for notificacao in notificacoes:
        if notificacao.pk:
            por_usuario.setdefault(notificacao.usuario_id, []).append(notificacao.pk)

    dispositivos = DispositivoPush.objects.filter(usuario_id__in=por_usuario)
    if endpoint_origem:
        dispositivos = dispositivos.exclude(endpoint=endpoint_origem)
    agora = timezone.now()
    EntregaPush.objects.bulk_create(
        EntregaPush(dispositivo_id=dispositivo_id, notificacao_id=notificacao_id, tentar_em=agora)
        for dispositivo_id, usuario_id in dispositivos.values_list('pk', 'usuario_id')
        for notificacao_id in por_usuario[usuario_id]
    )


class SessaoPush(requests.Session):
    def request(self, *args, **kwargs):
        kwargs['allow_redirects'] = False
        return super().request(*args, **kwargs)


def enviar_pendentes(limite=20):
    from pywebpush import WebPushException, webpush

    agora = timezone.now()
    vencimento = agora - timedelta(hours=24)
    EntregaPush.objects.filter(notificacao__criada_em__lt=vencimento).delete()
    prontas = list(
        EntregaPush.objects.filter(tentar_em__lte=agora).order_by('tentar_em', 'pk')
        .values_list('pk', flat=True)[:limite]
    )

    with SessaoPush() as sessao:
        for pk in prontas:
            fila = EntregaPush.objects.filter(pk=pk)
            reserva = timezone.now()
            if not fila.filter(tentar_em__lte=reserva).update(tentar_em=reserva + timedelta(minutes=2)):
                continue
            entrega = fila.select_related('dispositivo', 'notificacao').first()
            if entrega is None:
                continue

            dispositivo = entrega.dispositivo
            if dispositivo.usuario_id != entrega.notificacao.usuario_id or not endpoint_permitido(dispositivo.endpoint):
                fila.delete()
                continue

            try:
                webpush(
                    subscription_info={
                        'endpoint': dispositivo.endpoint,
                        'keys': {'p256dh': dispositivo.p256dh, 'auth': dispositivo.auth},
                    },
                    data=json.dumps({
                        'body': MENSAGENS.get(entrega.notificacao.tipo, 'Você tem uma nova notificação.'),
                        'tag': f'terroir-{entrega.notificacao_id}',
                        'tipo': entrega.notificacao.tipo,
                    }),
                    vapid_private_key=settings.WEB_PUSH_PRIVATE_KEY,
                    vapid_claims={'sub': settings.WEB_PUSH_SUBJECT},
                    ttl=max(1, int((entrega.notificacao.criada_em - vencimento).total_seconds())),
                    timeout=8,
                    requests_session=sessao,
                )
            except WebPushException as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status in {404, 410}:
                    dispositivo.delete()
                elif status is None or status == 429 or status >= 500:
                    reagendar(entrega, fila)
                else:
                    logger.warning('Serviço Web Push retornou HTTP %s para entrega %s.', status, pk)
                    fila.delete()
            except ValueError:
                logger.warning('Chaves Web Push inválidas para entrega %s.', pk)
                fila.delete()
            except requests.RequestException:
                reagendar(entrega, fila)
            else:
                fila.delete()


def reagendar(entrega, fila):
    tentativas = entrega.tentativas + 1
    if tentativas >= 5:
        logger.warning('Limite de tentativas atingido para entrega push %s.', entrega.pk)
        fila.delete()
        return
    fila.update(tentativas=tentativas, tentar_em=timezone.now() + timedelta(minutes=2 ** tentativas))
