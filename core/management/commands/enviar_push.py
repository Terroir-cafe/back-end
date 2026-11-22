from time import sleep

from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from core.push import configurado, enviar_pendentes


class Command(BaseCommand):
    help = 'Envia as notificações Web Push pendentes.'

    def add_arguments(self, parser):
        parser.add_argument('--continuo', action='store_true', help='Consulta a fila a cada cinco segundos.')

    def handle(self, *args, **options):
        if not configurado():
            raise CommandError('Configure WEB_PUSH_PUBLIC_KEY, WEB_PUSH_PRIVATE_KEY e WEB_PUSH_SUBJECT.')
        while True:
            close_old_connections()
            try:
                enviar_pendentes()
            except ModuleNotFoundError as erro:
                if erro.name != 'pywebpush':
                    raise
                raise CommandError('Instale pywebpush no ambiente do worker com requirements-push.txt.') from erro
            if not options['continuo']:
                break
            sleep(5)
