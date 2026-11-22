from django.conf import settings
from django.db import models, transaction


class NotificacaoManager(models.Manager):
    @transaction.atomic
    def registrar(self, notificacoes, *, endpoint_origem=None):
        from core.push import enfileirar

        notificacoes = self.bulk_create(notificacoes)
        enfileirar(notificacoes, endpoint_origem=endpoint_origem)


class Notificacao(models.Model):
    class Tipo(models.TextChoices):
        COMPRA = 'compra', 'Status da compra'
        CARRINHO = 'carrinho', 'Item no carrinho'
        PRECO = 'preco', 'Alteração de preço'

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificacoes')
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    mensagem = models.TextField()
    produto = models.ForeignKey('Produto', null=True, blank=True, on_delete=models.SET_NULL)
    criada_em = models.DateTimeField(auto_now_add=True)
    lida_em = models.DateTimeField(null=True, blank=True)

    objects = NotificacaoManager()

    class Meta:
        ordering = ('-criada_em', '-pk')
        indexes = [models.Index(fields=['usuario', 'lida_em'])]


class DispositivoPush(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dispositivos_push')
    identificador = models.CharField(max_length=64, unique=True)
    endpoint = models.TextField()
    p256dh = models.CharField(max_length=88)
    auth = models.CharField(max_length=24)


class EntregaPush(models.Model):
    notificacao = models.ForeignKey(Notificacao, on_delete=models.CASCADE)
    dispositivo = models.ForeignKey(DispositivoPush, on_delete=models.CASCADE)
    tentar_em = models.DateTimeField(db_index=True)
    tentativas = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['notificacao', 'dispositivo'], name='entrega_push_por_dispositivo'),
        ]
