from django.db import models, transaction

from .notificacao import Notificacao
from .produto import Produto
from .user import User


class CompraQuerySet(models.QuerySet):
    @transaction.atomic
    def update(self, **kwargs):
        if 'status' not in kwargs:
            return super().update(**kwargs)

        anteriores = dict(self.order_by('pk').select_for_update().values_list('pk', 'status'))
        atualizadas = super().update(**kwargs)
        for compra in self.model.objects.filter(pk__in=anteriores):
            compra.notificar_status(anteriores[compra.pk])
        return atualizadas


class Compra(models.Model):
    class StatusCompra(models.IntegerChoices):
        CARRINHO = 1, 'Carrinho'
        FINALIZADO = 2, 'Finalizado'
        PAGO = 3, 'Pago'
        ENTREGUE = 4, 'Entregue'

    class TipoPagamento(models.IntegerChoices):
        CARTAO_CREDITO = 1, 'Cartão de Crédito'
        CARTAO_DEBITO = 2, 'Cartão de Débito'
        PIX = 3, 'PIX'
        BOLETO = 4, 'Boleto'
        TRANSFERENCIA_BANCARIA = 5, 'Transferência Bancária'
        DINHEIRO = 6, 'Dinheiro'
        OUTRO = 7, 'Outro'

    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name='compras')
    status = models.IntegerField(choices=StatusCompra.choices, default=StatusCompra.CARRINHO)
    data = models.DateTimeField(auto_now_add=True)
    tipo_pagamento = models.IntegerField(choices=TipoPagamento.choices, default=TipoPagamento.CARTAO_CREDITO)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    objects = CompraQuerySet.as_manager()

    @classmethod
    def obter_carrinho(cls, usuario, criar=False):
        """Retorna o carrinho em aberto do usuário (ou None, se não existir).

        Deve haver só um por usuário. Se por algum motivo existir mais de um,
        junta os itens de todos no mais antigo e apaga os extras.
        """
        with transaction.atomic():
            User.objects.select_for_update(no_key=True).get(pk=usuario.pk)
            carrinhos = list(
                cls.objects.select_for_update()
                .filter(usuario=usuario, status=cls.StatusCompra.CARRINHO)
                .order_by('id')
            )

            if not carrinhos:
                return cls.objects.create(usuario=usuario) if criar else None

            principal, *extras = carrinhos
            for extra in extras:
                for item in extra.itens.all():
                    existente = principal.itens.filter(produto=item.produto).first()
                    if existente:
                        existente.quantidade += item.quantidade
                        existente.save()
                    else:
                        item.compra = principal
                        item.save()
                extra.delete()

            if extras:
                principal.save()  # recalcula o total

            return principal

    @transaction.atomic
    def save(self, *args, **kwargs):
        anterior = None
        campos = kwargs.get('update_fields')
        alterando_status = campos is None or 'status' in campos
        if self.pk:
            if alterando_status:
                anterior = (
                    Compra.objects.select_for_update().filter(pk=self.pk).values_list('status', flat=True).first()
                )
            self.total = sum(item.preco * item.quantidade for item in self.itens.all())
        super().save(*args, **kwargs)
        if anterior is not None:
            Compra.objects.get(pk=self.pk).notificar_status(anterior)

    def notificar_status(self, anterior):
        if anterior == self.status:
            return
        status_anterior = dict(self.StatusCompra.choices).get(anterior, anterior)
        Notificacao.objects.registrar([Notificacao(
            usuario_id=self.usuario_id,
            tipo=Notificacao.Tipo.COMPRA,
            mensagem=(
                f'O status da compra #{self.pk} mudou de '
                f'{status_anterior} para {self.get_status_display()}.'
            ),
        )])


class ItensCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='itens_compra')
    quantidade = models.PositiveIntegerField(default=1)
    preco = models.DecimalField(max_digits=7, decimal_places=2, default=0)
