"""Popula o banco LOCAL com pianos e comentários de exemplo.

Uso: python manage.py carregar_exemplos

Os pianos publicados são os mesmos da carga inicial de produção (migration 0011),
e alguns registros pendentes servem para testar a moderação no admin.
"""

import importlib

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from pianos.models import Comentario, Piano


carga_inicial = importlib.import_module('pianos.migrations.0011_import_local_pianos_to_neon')

PENDENTES = [
    {
        'nome_local': 'Estação da Luz',
        'endereco': 'Praça da Luz, 1',
        'cidade': 'São Paulo',
        'estado': 'SP',
        'tipo': 'armario',
        'descricao': 'Piano no saguão principal, perto das bilheterias.',
    },
    {
        'nome_local': 'Aeroporto Santos Dumont',
        'endereco': 'Praça Senador Salgado Filho, s/n',
        'cidade': 'Rio de Janeiro',
        'estado': 'RJ',
        'tipo': 'cauda',
        'descricao': 'Fica no saguão de embarque. Disponível em horário comercial.',
    },
]

COMENTARIOS = [
    ('Marina', 'Toquei lá ontem, o piano está afinado!', True),
    ('', 'Fica bem cheio no fim de semana, melhor ir cedo.', True),
    ('Pedro', 'Alguém sabe se ainda está funcionando?', False),
    ('Ana', 'Adorei o lugar, o pessoal da loja foi muito simpático.', False),
]


class Command(BaseCommand):
    help = 'Cria pianos e comentários de exemplo no banco local (não roda com DEBUG=False).'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Este comando só pode ser usado em desenvolvimento (DEBUG=True).')

        criados = 0
        for dados in carga_inicial.PIANOS:
            dados = dados.copy()
            dados.pop('data_cadastro')
            _, novo = Piano.objects.get_or_create(
                nome_local=dados.pop('nome_local'),
                endereco=dados.pop('endereco'),
                defaults=dados,
            )
            criados += novo

        for dados in PENDENTES:
            dados = dados.copy()
            _, novo = Piano.objects.get_or_create(
                nome_local=dados.pop('nome_local'),
                endereco=dados.pop('endereco'),
                defaults={**dados, 'aprovado': False},
            )
            criados += novo

        primeiro = Piano.objects.filter(aprovado=True).order_by('pk').first()
        comentarios = 0
        if primeiro:
            for nome, texto, aprovado in COMENTARIOS:
                _, novo = Comentario.objects.get_or_create(
                    piano=primeiro,
                    texto=texto,
                    defaults={'nome': nome or None, 'aprovado': aprovado},
                )
                comentarios += novo

        self.stdout.write(self.style.SUCCESS(
            f'{criados} piano(s) e {comentarios} comentário(s) de exemplo criados.'
        ))
