from django.conf import settings
from django.db import models


class OperacaoOffline(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    chave = models.UUIDField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['usuario', 'chave'], name='operacao_offline_unica')]
