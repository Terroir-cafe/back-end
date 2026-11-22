from hashlib import sha256
from uuid import uuid4

from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from core.models import Compra, OperacaoOffline, Produto, User
from core.models.notificacao import DispositivoPush, EntregaPush


class SincronizacaoTests(APITestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('cliente@example.com')
        self.produto = Produto.objects.create(nome='Café', preco='20.00', quantidade=3)
        self.client.force_authenticate(self.usuario)
        self.url = reverse('sincronizar')
        self.operacao = {
            'chave': str(uuid4()),
            'conta': self.usuario.pk,
            'tipo': 'adicionar',
            'produto': self.produto.pk,
            'quantidade': 1,
        }

    def test_reenvio_aplica_a_adicao_e_notifica_uma_vez(self):
        for _ in range(2):
            resposta = self.client.post(self.url, self.operacao, format='json')
            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(resposta.data['itens'][0]['quantidade'], 1)

        self.assertEqual(OperacaoOffline.objects.count(), 1)
        self.assertEqual(self.usuario.notificacoes.count(), 1)

    def test_rejeicao_preserva_o_carrinho_e_nao_grava_recibo(self):
        resposta = self.client.post(self.url, {**self.operacao, 'quantidade': 4}, format='json')
        self.assertEqual(resposta.status_code, 400)
        self.assertFalse(OperacaoOffline.objects.exists())
        self.assertFalse(Compra.objects.exists())

    @override_settings(WEB_PUSH_PUBLIC_KEY='publica', WEB_PUSH_PRIVATE_KEY='privada', WEB_PUSH_SUBJECT='mailto:teste@example.com')
    def test_push_ignora_dispositivo_de_origem_sem_perder_notificacao(self):
        outra_conta = User.objects.create_user('outro@example.com')
        for nome, usuario in [('origem', self.usuario), ('destino', self.usuario), ('outro', outra_conta)]:
            endpoint = f'https://fcm.googleapis.com/fcm/send/{nome}'
            DispositivoPush.objects.create(
                usuario=usuario, endpoint=endpoint, identificador=sha256(endpoint.encode()).hexdigest(),
            )

        cabecalhos = {'X-Push-Endpoint': 'https://fcm.googleapis.com/fcm/send/origem'}
        self.assertEqual(self.client.post(self.url, self.operacao, format='json', headers=cabecalhos).status_code, 200)
        aumento = {**self.operacao, 'chave': str(uuid4()), 'tipo': 'quantidade', 'quantidade': 2}
        self.assertEqual(self.client.post(self.url, aumento, format='json', headers=cabecalhos).status_code, 200)
        compra = Compra.objects.get(usuario=self.usuario)
        finalizar = reverse('compras-finalizar', args=[compra.pk])
        self.assertEqual(self.client.post(finalizar, headers=cabecalhos).status_code, 200)

        self.assertEqual(self.usuario.notificacoes.count(), 3)
        self.assertFalse(outra_conta.notificacoes.exists())
        self.assertEqual(
            list(EntregaPush.objects.values_list('dispositivo__endpoint', flat=True)),
            ['https://fcm.googleapis.com/fcm/send/destino'] * 3,
        )

    def test_fila_de_outra_conta_e_finalizacao_sao_rejeitadas(self):
        outro = User.objects.create_user('outro@example.com')
        resposta = self.client.post(self.url, {**self.operacao, 'conta': outro.pk}, format='json')
        self.assertEqual(resposta.status_code, 403)
        resposta = self.client.post(self.url, {**self.operacao, 'tipo': 'finalizar'}, format='json')
        self.assertEqual(resposta.status_code, 400)
        self.assertFalse(Compra.objects.exists())
