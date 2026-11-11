from django.db import models, transaction

from .produto import Produto
from .user import User


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

    @classmethod
    def obter_carrinho(cls, usuario, criar=False):
        """Retorna o carrinho em aberto do usuário (ou None, se não existir).

        Deve haver só um por usuário. Se por algum motivo existir mais de um,
        junta os itens de todos no mais antigo e apaga os extras.
        """
        with transaction.atomic():
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

    def save(self, *args, **kwargs):
        if self.pk:
            self.total = sum(item.preco * item.quantidade for item in self.itens.all())
        super().save(*args, **kwargs)

    # @property
    # def total(self):
    # return sum(item.preco * item.quantidade for item in self.itens.all())


class ItensCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='itens_compra')
    quantidade = models.PositiveIntegerField(default=1)
    preco = models.DecimalField(max_digits=7, decimal_places=2, default=0)
