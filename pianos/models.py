from django.db import models

TIPO_PIANO_CHOICES = [
    ('acustico', 'Acústico'),
    ('cauda', 'Cauda'),
    ('armario', 'Armário'),
    ('digital', 'Digital'),
    ('hibrido', 'Híbrido'),
]

class Piano(models.Model):
    nome_local = models.CharField(max_length=100)
    endereco = models.CharField(max_length=200)
    cidade = models.CharField(max_length=100, default="São Paulo")
    estado = models.CharField(max_length=2, default="SP")
    esta_funcionando = models.BooleanField(default=True)
    aprovado = models.BooleanField(default=False)
    tipo = models.CharField(max_length=20, choices=TIPO_PIANO_CHOICES, default='acustico', verbose_name="Tipo de piano")
    foto_url = models.URLField(max_length=500, blank=True, null=True)
    foto_url_2 = models.URLField(max_length=500, blank=True, null=True)
    foto_url_3 = models.URLField(max_length=500, blank=True, null=True)
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    ordem = models.PositiveIntegerField(default=0, verbose_name="Ordem")
    likes = models.PositiveIntegerField(default=0, verbose_name="Likes")
    dislikes = models.PositiveIntegerField(default=0, verbose_name="Dislikes")
    estrelas = models.FloatField(default=0.0, verbose_name="Média de estrelas")
    total_avaliacoes = models.PositiveIntegerField(default=0, verbose_name="Total de avaliações")
    destaque = models.BooleanField(default=False, verbose_name="Em destaque")
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ordem', '-data_cadastro']
        verbose_name = "Piano"
        verbose_name_plural = "Pianos"

    def __str__(self):
        return f"{self.nome_local} - {self.cidade}/{self.estado}"

    def fotos(self):
        return [f for f in [self.foto_url, self.foto_url_2, self.foto_url_3] if f]

    def estrelas_display(self):
        """Retorna estrelas arredondadas para 0.5"""
        return round(self.estrelas * 2) / 2


class Comentario(models.Model):
    piano = models.ForeignKey(Piano, on_delete=models.CASCADE, related_name='comentarios')
    nome = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nome (opcional)")
    texto = models.TextField(verbose_name="Comentário")
    aprovado = models.BooleanField(default=False)
    data = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comentário em {self.piano.nome_local} — {self.nome or 'Anônimo'}"

    class Meta:
        verbose_name = "Comentário"
        verbose_name_plural = "Comentários"
        ordering = ['-data']