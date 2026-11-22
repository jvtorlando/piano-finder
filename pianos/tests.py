import os
from decimal import Decimal
from unittest.mock import ANY, patch
from urllib.error import URLError

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse

from mapapianos.settings import database_config

from .admin import PianoAdmin
from .forms_admin import MAX_IMAGE_SIZE, PianoAdminForm
from .forms import PianoForm
from .geocoding import geocodificar
from .models import Comentario, Piano


@override_settings(
    DEBUG=True,
    SECURE_SSL_REDIRECT=False,
    ALLOWED_HOSTS=['testserver'],
    CLOUDINARY_STORAGE={
        'CLOUD_NAME': 'piano-finder-tests',
        'API_KEY': 'test',
        'API_SECRET': 'test',
    },
)
class PianoFinderTests(TestCase):
    def setUp(self):
        cache.clear()

    def criar_piano(self, **dados):
        defaults = {
            'nome_local': 'Centro Cultural',
            'endereco': 'Rua da Música, 10',
            'cidade': 'São Paulo',
            'estado': 'SP',
            'tipo': 'armario',
            'aprovado': True,
        }
        defaults.update(dados)
        return Piano.objects.create(**defaults)

    def dados_cadastro(self, **dados):
        defaults = {
            'nome_local': 'Biblioteca Municipal',
            'endereco': 'Avenida Central, 100',
            'cidade': 'Campinas',
            'estado': 'sp',
            'tipo': 'digital',
            'esta_funcionando': 'on',
            'descricao': 'Disponível durante o horário de funcionamento.',
        }
        defaults.update(dados)
        return defaults

    def test_home_lista_apenas_aprovados_e_aplica_filtros(self):
        esperado = self.criar_piano(nome_local='Piano esperado', tipo='digital')
        self.criar_piano(nome_local='Outro estado', estado='RJ', tipo='digital')
        self.criar_piano(nome_local='Não aprovado', aprovado=False, tipo='digital')

        resposta = self.client.get(reverse('home'), {
            'estado': 'sp',
            'cidade': 'paulo',
            'tipo': 'digital',
        })

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(list(resposta.context['pianos']), [esperado])
        self.assertTrue(resposta.context['filtros_ativos'])

    def test_filtro_via_htmx_devolve_so_os_resultados(self):
        self.criar_piano(nome_local='Piano de Campinas', cidade='Campinas')
        self.criar_piano(nome_local='Piano do Rio', cidade='Rio de Janeiro', estado='RJ')

        resposta = self.client.get(
            reverse('home'), {'cidade': 'campinas'}, headers={'HX-Request': 'true'},
        )

        self.assertEqual(resposta.status_code, 200)
        conteudo = resposta.content.decode()
        self.assertTrue(conteudo.lstrip().startswith('<section id="resultados"'))
        self.assertIn('Piano de Campinas', conteudo)
        self.assertNotIn('Piano do Rio', conteudo)
        self.assertNotIn('<html', conteudo)
        self.assertIn('HX-Request', resposta['Vary'])

    def test_lista_mostra_filtros_removiveis(self):
        self.criar_piano(cidade='Campinas')

        resposta = self.client.get(reverse('home'), {'tipo': 'armario', 'estado': 'SP'})

        rotulos = {f['rotulo']: f['remover_url'] for f in resposta.context['filtros_aplicados']}
        self.assertEqual(rotulos['Armário'], reverse('home') + '?estado=SP')
        self.assertEqual(rotulos['São Paulo'], reverse('home') + '?tipo=armario')

    def test_comentario_via_htmx_devolve_formulario_limpo_com_aviso(self):
        piano = self.criar_piano()

        resposta = self.client.post(
            reverse('detalhe_piano', args=[piano.id]),
            {'nome': 'Ana', 'texto': 'Que piano lindo!'},
            headers={'HX-Request': 'true'},
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Comentário recebido.')
        self.assertContains(resposta, 'id="form-comentario"')
        self.assertNotContains(resposta, 'Que piano lindo!')
        self.assertNotContains(resposta, '<html')
        self.assertFalse(Comentario.objects.get().aprovado)

    def test_comentario_invalido_via_htmx_mostra_erro_sem_salvar(self):
        piano = self.criar_piano()

        resposta = self.client.post(
            reverse('detalhe_piano', args=[piano.id]),
            {'nome': 'Ana', 'texto': ''},
            headers={'HX-Request': 'true'},
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertNotContains(resposta, 'Comentário recebido.')
        self.assertContains(resposta, 'text-danger')
        self.assertFalse(Comentario.objects.exists())

    def test_detalhe_nao_expoe_piano_pendente(self):
        piano = self.criar_piano(aprovado=False)

        resposta = self.client.get(reverse('detalhe_piano', args=[piano.id]))

        self.assertEqual(resposta.status_code, 404)

    def test_cadastro_salva_tipo_estado_e_urls_validados(self):
        cloud_name = settings.CLOUDINARY_STORAGE['CLOUD_NAME']
        foto = f'https://res.cloudinary.com/{cloud_name}/image/upload/v1/pianos/teste.jpg'

        resposta = self.client.post(
            reverse('adicionar_piano'),
            self.dados_cadastro(foto_url_1=foto),
        )

        self.assertRedirects(resposta, reverse('home'))
        piano = Piano.objects.get(nome_local='Biblioteca Municipal')
        self.assertEqual(piano.tipo, 'digital')
        self.assertEqual(piano.estado, 'SP')
        self.assertEqual(piano.foto_url, foto)
        self.assertFalse(piano.aprovado)

    def test_cadastro_rejeita_tipo_e_uf_invalidos(self):
        resposta = self.client.post(
            reverse('adicionar_piano'),
            self.dados_cadastro(tipo='órgão', estado='XX'),
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Piano.objects.exists())
        self.assertIn('tipo', resposta.context['form'].errors)
        self.assertContains(resposta, 'Informe uma UF brasileira válida')

    def test_cadastro_rejeita_url_de_foto_externa(self):
        resposta = self.client.post(
            reverse('adicionar_piano'),
            self.dados_cadastro(foto_url_1='https://example.com/foto.jpg'),
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Piano.objects.exists())
        self.assertContains(resposta, 'não pertence ao Cloudinary do Piano Finder')

    def test_formulario_expoe_configuracao_publica_do_upload(self):
        resposta = self.client.get(reverse('adicionar_piano'))

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            resposta.context['cloudinary_cloud_name'],
            settings.CLOUDINARY_STORAGE['CLOUD_NAME'],
        )
        self.assertContains(resposta, settings.CLOUDINARY_UPLOAD_PRESET)

    def test_formulario_publico_carrega_recorte_compartilhado_16_10(self):
        resposta = self.client.get(reverse('adicionar_piano'))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'pianos/image-cropper.css')
        self.assertContains(resposta, 'pianos/image-cropper.js')
        self.assertContains(resposta, 'A foto será ajustada no formato 16:10')

    def test_admin_configura_recorte_compartilhado_no_upload(self):
        piano_admin = PianoAdmin(Piano, AdminSite())
        media = piano_admin.media
        widget = PianoAdminForm().fields['upload_foto'].widget

        self.assertIn('pianos/image-cropper.css', media._css['all'])
        self.assertIn('pianos/image-cropper.js', media._js)
        self.assertIn('pianos/admin-image-crop.js', media._js)
        self.assertEqual(
            widget.attrs.get('data-piano-image-cropper'),
            'true',
        )
        self.assertIn('16:10', PianoAdminForm().fields['upload_foto'].help_text)

    @patch('pianos.admin.cloudinary.uploader.unsigned_upload')
    def test_admin_envia_foto_com_o_preset_unsigned(self, upload):
        upload.return_value = {
            'secure_url': 'https://res.cloudinary.com/piano-finder-tests/image/upload/admin.jpg',
        }
        foto = SimpleUploadedFile(
            'piano.jpg',
            b'imagem-de-teste',
            content_type='image/jpeg',
        )
        request = RequestFactory().post('/admin/pianos/piano/add/', {
            'upload_foto': foto,
        })
        piano = Piano(
            nome_local='Piano pelo admin',
            endereco='Rua do Admin, 1',
            cidade='Sao Paulo',
            estado='SP',
        )

        PianoAdmin(Piano, AdminSite()).save_model(
            request,
            piano,
            form=None,
            change=False,
        )

        upload.assert_called_once_with(
            ANY,
            settings.CLOUDINARY_UPLOAD_PRESET,
            cloud_name=settings.CLOUDINARY_STORAGE['CLOUD_NAME'],
            resource_type='image',
        )
        self.assertEqual(upload.call_args.args[0].name, foto.name)
        self.assertEqual(piano.foto_url, upload.return_value['secure_url'])
        self.assertTrue(Piano.objects.filter(pk=piano.pk).exists())

    def test_formulario_admin_valida_arquivo_de_imagem(self):
        gif_um_pixel = (
            b'GIF89a\x01\x00\x01\x00\x80\x00\x00'
            b'\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00'
            b',\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        )
        foto = SimpleUploadedFile(
            'piano.gif',
            gif_um_pixel,
            content_type='image/gif',
        )
        form = PianoAdminForm(
            data={
                'nome_local': 'Piano com imagem',
                'endereco': 'Rua da Imagem, 1',
                'cidade': 'Sao Paulo',
                'estado': 'SP',
                'tipo': 'acustico',
                'ordem': 0,
                'likes': 0,
                'dislikes': 0,
                'estrelas': 0,
                'total_avaliacoes': 0,
            },
            files={'upload_foto': foto},
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_formulario_admin_rejeita_imagem_acima_de_10_mb(self):
        gif_um_pixel = (
            b'GIF89a\x01\x00\x01\x00\x80\x00\x00'
            b'\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00'
            b',\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        )
        foto = SimpleUploadedFile(
            'piano-grande.gif',
            gif_um_pixel + b'0' * MAX_IMAGE_SIZE,
            content_type='image/gif',
        )
        form = PianoAdminForm(
            data={
                'nome_local': 'Piano com imagem grande',
                'endereco': 'Rua da Imagem, 1',
                'cidade': 'Sao Paulo',
                'estado': 'SP',
                'tipo': 'acustico',
                'ordem': 0,
                'likes': 0,
                'dislikes': 0,
                'estrelas': 0,
                'total_avaliacoes': 0,
            },
            files={'upload_foto': foto},
        )

        self.assertFalse(form.is_valid())
        self.assertIn('A imagem deve ter no máximo 10 MB.', form.errors['upload_foto'])

    def test_comentario_valido_fica_pendente_de_moderacao(self):
        piano = self.criar_piano()

        resposta = self.client.post(
            reverse('detalhe_piano', args=[piano.id]),
            {'nome': 'Ana', 'texto': 'Piano muito bem cuidado.'},
        )

        self.assertRedirects(
            resposta,
            reverse('detalhe_piano', args=[piano.id]),
        )
        comentario = Comentario.objects.get(piano=piano)
        self.assertEqual(comentario.nome, 'Ana')
        self.assertFalse(comentario.aprovado)

    def test_like_alterna_sem_ficar_negativo(self):
        piano = self.criar_piano()
        url = reverse('like_piano', args=[piano.id])

        primeira = self.client.post(url, {'acao': 'like'})
        segunda = self.client.post(url, {'acao': 'like'})

        self.assertEqual(primeira.status_code, 200)
        self.assertEqual(primeira.json()['likes'], 1)
        self.assertEqual(segunda.json()['likes'], 0)
        piano.refresh_from_db()
        self.assertEqual(piano.likes, 0)
        self.assertEqual(piano.dislikes, 0)

    def test_troca_de_dislike_para_like_atualiza_ambos_contadores(self):
        piano = self.criar_piano()
        url = reverse('like_piano', args=[piano.id])

        self.client.post(url, {'acao': 'dislike'})
        resposta = self.client.post(url, {'acao': 'like'})

        piano.refresh_from_db()
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(piano.likes, 1)
        self.assertEqual(piano.dislikes, 0)
        self.assertTrue(piano.destaque)

    def test_acao_de_voto_invalida_retorna_400_sem_alterar_dados(self):
        piano = self.criar_piano(likes=3)

        resposta = self.client.post(
            reverse('like_piano', args=[piano.id]),
            {'acao': 'qualquer'},
        )

        self.assertEqual(resposta.status_code, 400)
        piano.refresh_from_db()
        self.assertEqual(piano.likes, 3)

    def test_avaliacao_valida_so_pode_ser_feita_uma_vez_por_sessao(self):
        piano = self.criar_piano()
        url = reverse('avaliar_piano', args=[piano.id])

        primeira = self.client.post(url, {'estrelas': 5})
        segunda = self.client.post(url, {'estrelas': 2})

        self.assertEqual(primeira.status_code, 200)
        self.assertEqual(segunda.status_code, 400)
        piano.refresh_from_db()
        self.assertEqual(piano.estrelas, 5.0)
        self.assertEqual(piano.total_avaliacoes, 1)

    def test_avaliacao_invalida_retorna_400(self):
        piano = self.criar_piano()

        resposta = self.client.post(
            reverse('avaliar_piano', args=[piano.id]),
            {'estrelas': 8},
        )

        self.assertEqual(resposta.status_code, 400)
        piano.refresh_from_db()
        self.assertEqual(piano.total_avaliacoes, 0)

    @override_settings(DEBUG=False)
    def test_rate_limit_bloqueia_sexto_cadastro_por_hora(self):
        url = reverse('adicionar_piano')
        for _ in range(5):
            resposta = self.client.post(url, {}, secure=True)
            self.assertEqual(resposta.status_code, 200)

        bloqueada = self.client.post(url, {}, secure=True)

        self.assertEqual(bloqueada.status_code, 429)
        self.assertContains(
            bloqueada,
            'Muitas',
            status_code=429,
        )


class PianoFormTests(TestCase):
    def test_estado_e_normalizado_para_maiusculas(self):
        form = PianoForm({
            'nome_local': 'Teatro',
            'endereco': 'Rua A, 1',
            'cidade': 'Curitiba',
            'estado': 'pr',
            'tipo': 'cauda',
            'esta_funcionando': 'on',
            'descricao': '',
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['estado'], 'PR')


@override_settings(
    DEBUG=True,
    SECURE_SSL_REDIRECT=False,
    ALLOWED_HOSTS=['testserver'],
)
class AdminTests(TestCase):
    def setUp(self):
        # Nenhum teste deve chamar o Nominatim de verdade.
        geocoder = patch('pianos.admin.geocodificar', return_value=(Decimal('-23.5'), Decimal('-46.6')))
        self.geocodificar = geocoder.start()
        self.addCleanup(geocoder.stop)
        admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'senha-de-teste')
        self.client.force_login(admin_user)
        self.publicado = Piano.objects.create(
            nome_local='Teatro Municipal', endereco='Praça Ramos, 1',
            cidade='São Paulo', estado='SP', tipo='cauda', aprovado=True, likes=3,
            foto_url='https://res.cloudinary.com/piano-finder-tests/image/upload/a.jpg',
        )
        self.pendente = Piano.objects.create(
            nome_local='Estação da Luz', endereco='Praça da Luz, 1',
            cidade='São Paulo', estado='SP', tipo='armario',
        )
        Comentario.objects.create(piano=self.publicado, texto='Precisa afinar.')

    def test_painel_mostra_filas_de_moderacao(self):
        resposta = self.client.get(reverse('admin:index'))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Pianos aguardando aprovação')
        self.assertContains(resposta, 'Estação da Luz')
        self.assertContains(resposta, 'Precisa afinar.')

    def test_listas_e_formularios_do_admin_carregam(self):
        urls = [
            reverse('admin:pianos_piano_changelist'),
            reverse('admin:pianos_piano_changelist') + '?aprovado__exact=0',
            reverse('admin:pianos_piano_change', args=[self.publicado.pk]),
            reverse('admin:pianos_piano_add'),
            reverse('admin:pianos_comentario_changelist'),
            reverse('admin:auth_user_changelist'),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_botao_aprovar_so_aparece_em_piano_pendente(self):
        url_acao = reverse('admin:pianos_piano_aprovar_este', args=[self.pendente.pk])

        pendente = self.client.get(reverse('admin:pianos_piano_change', args=[self.pendente.pk]))
        publicado = self.client.get(reverse('admin:pianos_piano_change', args=[self.publicado.pk]))

        self.assertContains(pendente, url_acao)
        self.assertNotContains(publicado, 'Aprovar e publicar')

    def test_acao_aprovar_so_publica_apos_confirmacao_por_post(self):
        url = reverse('admin:pianos_piano_aprovar_este', args=[self.pendente.pk])

        confirmacao = self.client.get(url)
        self.pendente.refresh_from_db()
        self.assertEqual(confirmacao.status_code, 200)
        self.assertFalse(self.pendente.aprovado)

        self.client.post(url, {'_form_submitted': 'on'})
        self.pendente.refresh_from_db()
        self.assertTrue(self.pendente.aprovado)


    def test_salvar_piano_sem_coordenadas_busca_no_mapa(self):
        url = reverse('admin:pianos_piano_change', args=[self.pendente.pk])
        dados = {
            'nome_local': self.pendente.nome_local, 'endereco': self.pendente.endereco,
            'cidade': 'São Paulo', 'estado': 'SP', 'tipo': 'armario', 'ordem': 0,
            'esta_funcionando': 'on',
            'comentarios-TOTAL_FORMS': 0, 'comentarios-INITIAL_FORMS': 0,
            'comentarios-MIN_NUM_FORMS': 0, 'comentarios-MAX_NUM_FORMS': 1000,
        }

        resposta = self.client.post(url, dados)

        self.assertEqual(resposta.status_code, 302, getattr(resposta, 'context', None) and resposta.context['adminform'].form.errors)
        self.pendente.refresh_from_db()
        self.assertEqual(self.pendente.latitude, Decimal('-23.5'))
        self.geocodificar.assert_called_once()

    def test_coordenadas_digitadas_a_mao_nao_sao_sobrescritas(self):
        url = reverse('admin:pianos_piano_change', args=[self.pendente.pk])
        dados = {
            'nome_local': self.pendente.nome_local, 'endereco': 'Novo endereço, 10',
            'cidade': 'São Paulo', 'estado': 'SP', 'tipo': 'armario', 'ordem': 0,
            'latitude': '-22.900000', 'longitude': '-43.200000',
            'comentarios-TOTAL_FORMS': 0, 'comentarios-INITIAL_FORMS': 0,
            'comentarios-MIN_NUM_FORMS': 0, 'comentarios-MAX_NUM_FORMS': 1000,
        }

        self.client.post(url, dados)

        self.pendente.refresh_from_db()
        self.assertEqual(self.pendente.latitude, Decimal('-22.900000'))
        self.geocodificar.assert_not_called()

    def test_acao_em_lote_busca_coordenadas_que_faltam(self):
        self.client.post(reverse('admin:pianos_piano_changelist'), {
            'action': 'buscar_coordenadas',
            '_selected_action': [self.publicado.pk, self.pendente.pk],
        })

        self.assertEqual(Piano.objects.filter(latitude__isnull=False).count(), 2)
        self.assertEqual(self.geocodificar.call_count, 2)


@override_settings(DEBUG=True, SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'])
class PaginasPublicasTests(TestCase):
    def test_analytics_da_vercel_so_aparece_quando_ativado(self):
        with override_settings(VERCEL_ANALYTICS=False):
            sem = self.client.get(reverse('home'))
        with override_settings(VERCEL_ANALYTICS=True):
            com = self.client.get(reverse('home'))

        self.assertNotContains(sem, '/_vercel/insights/script.js')
        self.assertContains(com, '/_vercel/insights/script.js')
        self.assertContains(com, '/_vercel/speed-insights/script.js')

    @override_settings(STATIC_VERSION='abc123')
    def test_scripts_do_site_levam_a_versao_do_deploy(self):
        resposta = self.client.get(reverse('home'))

        self.assertContains(resposta, 'pianos/js/site.js?v=abc123')

    def test_cadastro_oferece_os_quatro_tipos_com_armario_marcado(self):
        resposta = self.client.get(reverse('adicionar_piano'))

        conteudo = resposta.content.decode()
        for tipo in ('armario', 'cauda', 'digital', 'hibrido'):
            self.assertIn(f'name="tipo" value="{tipo}"', conteudo)
        self.assertNotIn('name="tipo" value="acustico"', conteudo)
        self.assertIn('name="tipo" value="armario" class="peer sr-only" checked', conteudo)

    def test_estrelas_mostram_a_media_com_fracao(self):
        piano = Piano.objects.create(
            nome_local='Teatro', endereco='Rua A, 1', aprovado=True, estrelas=3.5, total_avaliacoes=2,
        )

        resposta = self.client.get(reverse('detalhe_piano', args=[piano.id]))

        self.assertContains(resposta, 'style="width: 70%"')
        self.assertContains(resposta, '(2 avaliações)')


@override_settings(DEBUG=True, SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'])
class MapaTests(TestCase):
    def test_mapa_mostra_so_pianos_publicados_com_coordenadas(self):
        Piano.objects.create(
            nome_local='No mapa', endereco='Rua A, 1', aprovado=True,
            latitude=Decimal('-23.55'), longitude=Decimal('-46.63'),
        )
        Piano.objects.create(nome_local='Sem coordenadas', endereco='Rua B, 2', aprovado=True)
        Piano.objects.create(
            nome_local='Pendente', endereco='Rua C, 3', aprovado=False,
            latitude=Decimal('-22.9'), longitude=Decimal('-43.2'),
        )

        resposta = self.client.get(reverse('mapa'))

        self.assertEqual(resposta.status_code, 200)
        pontos = resposta.context['pontos']
        self.assertEqual([p['nome'] for p in pontos], ['No mapa'])
        self.assertEqual(pontos[0]['lat'], -23.55)
        self.assertEqual(resposta.context['fora_do_mapa'], 1)
        self.assertContains(resposta, 'id="pontos-mapa"')
        self.assertNotContains(resposta, 'Pendente')

    def test_detalhe_mostra_mapinha_so_com_coordenadas(self):
        com = Piano.objects.create(
            nome_local='Com', endereco='Rua A, 1', aprovado=True,
            latitude=Decimal('-23.55'), longitude=Decimal('-46.63'),
        )
        sem = Piano.objects.create(nome_local='Sem', endereco='Rua B, 2', aprovado=True)

        self.assertContains(self.client.get(reverse('detalhe_piano', args=[com.id])), 'id="mapa-piano"')
        self.assertNotContains(self.client.get(reverse('detalhe_piano', args=[sem.id])), 'id="mapa-piano"')


class GeocodingTests(SimpleTestCase):
    def setUp(self):
        self.piano = Piano(nome_local='Livraria', endereco='Av. Paulista, 509', cidade='São Paulo', estado='SP')

    @patch('pianos.geocoding._consultar')
    def test_usa_o_primeiro_resultado_e_arredonda(self, consultar):
        consultar.return_value = [{'lat': '-23.5678901234', 'lon': '-46.6543210987'}]

        self.assertEqual(geocodificar(self.piano), (Decimal('-23.567890'), Decimal('-46.654321')))
        self.assertIn('Livraria', consultar.call_args.args[0])

    @patch('pianos.geocoding._consultar')
    def test_tenta_so_o_endereco_quando_o_nome_nao_e_encontrado(self, consultar):
        consultar.side_effect = [[], [{'lat': '-23.5', 'lon': '-46.6'}]]

        self.assertEqual(geocodificar(self.piano), (Decimal('-23.500000'), Decimal('-46.600000')))
        self.assertNotIn('Livraria', consultar.call_args.args[0])

    @patch('pianos.geocoding._consultar', side_effect=URLError('sem rede'))
    def test_falha_de_rede_devolve_none(self, consultar):
        self.assertIsNone(geocodificar(self.piano))


class DatabaseConfigTests(SimpleTestCase):
    def test_database_url_vazia_usa_sqlite(self):
        for valor in ('', '   '):
            with self.subTest(valor=valor), patch.dict(os.environ, {'DATABASE_URL': valor}):
                config = database_config()
                self.assertEqual(config['ENGINE'], 'django.db.backends.sqlite3')
                self.assertTrue(str(config['NAME']).endswith('db.sqlite3'))

    def test_database_url_preenchida_e_respeitada(self):
        url = 'postgres://usuario:senha@localhost:5432/pianos'
        with patch.dict(os.environ, {'DATABASE_URL': url}):
            config = database_config()
        self.assertEqual(config['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(config['NAME'], 'pianos')
