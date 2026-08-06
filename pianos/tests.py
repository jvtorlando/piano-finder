from unittest.mock import ANY, patch

from django.contrib.admin.sites import AdminSite
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse

from .admin import PianoAdmin
from .forms_admin import PianoAdminForm
from .forms import PianoForm
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
