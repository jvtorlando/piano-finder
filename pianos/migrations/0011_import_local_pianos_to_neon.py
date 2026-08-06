import os
from datetime import datetime, timezone

from django.db import migrations


PIANOS = [
    {
        "nome_local": "Shopping Villa Lobbos",
        "endereco": "Av. Dra. Ruth Cardoso, 4777",
        "cidade": "São Paulo",
        "estado": "SP",
        "esta_funcionando": True,
        "aprovado": True,
        "tipo": "armario",
        "foto_url": "https://res.cloudinary.com/ddbzojwrt/image/upload/v1775276328/pianos/ahpph5wpyrby0wvhs3jo.jpg",
        "foto_url_2": None,
        "foto_url_3": None,
        "descricao": "O piano fica no primeiro andar do shopping, em frente à loja Zara. Livre para tocar.",
        "ordem": 0,
        "likes": 1,
        "dislikes": 0,
        "estrelas": 5.0,
        "total_avaliacoes": 1,
        "destaque": True,
        "data_cadastro": datetime(2026, 4, 4, 4, 18, 49, 356000, tzinfo=timezone.utc),
    },
    {
        "nome_local": "Livraria Martins Fontes Av. Paulista",
        "endereco": "Av. Paulista, 509",
        "cidade": "São Paulo",
        "estado": "SP",
        "esta_funcionando": True,
        "aprovado": True,
        "tipo": "armario",
        "foto_url": "https://res.cloudinary.com/ddbzojwrt/image/upload/v1775276635/pianos/oub402yrauxaqwipqblm.jpg",
        "foto_url_2": None,
        "foto_url_3": None,
        "descricao": "O piano fica no terceiro andar da livraria. Livre para uso.",
        "ordem": 0,
        "likes": 1,
        "dislikes": 0,
        "estrelas": 3.0,
        "total_avaliacoes": 2,
        "destaque": True,
        "data_cadastro": datetime(2026, 4, 4, 4, 23, 56, 208000, tzinfo=timezone.utc),
    },
    {
        "nome_local": "Galeria Magalu Av. Paulista",
        "endereco": "Av. Paulista, 2073",
        "cidade": "São Paulo",
        "estado": "SP",
        "esta_funcionando": True,
        "aprovado": True,
        "tipo": "digital",
        "foto_url": "https://res.cloudinary.com/ddbzojwrt/image/upload/v1775505637/pianos/hxpovyr0ru55hgtyzllc.jpg",
        "foto_url_2": None,
        "foto_url_3": None,
        "descricao": "Um piano digital, inspirado em pianos de cauda acústico. Livre para tocar.",
        "ordem": 0,
        "likes": 1,
        "dislikes": 0,
        "estrelas": 4.0,
        "total_avaliacoes": 2,
        "destaque": True,
        "data_cadastro": datetime(2026, 4, 6, 20, 0, 38, 276000, tzinfo=timezone.utc),
    },
]


def import_local_pianos(apps, schema_editor):
    # This is a one-time production transfer from the former local SQLite DB.
    # Skipping outside Vercel production keeps development and test DBs empty.
    if os.environ.get("VERCEL_ENV") != "production":
        return

    Piano = apps.get_model("pianos", "Piano")

    for piano_data in PIANOS:
        data = piano_data.copy()
        data_cadastro = data.pop("data_cadastro")
        piano, created = Piano.objects.get_or_create(
            nome_local=data.pop("nome_local"),
            endereco=data.pop("endereco"),
            defaults=data,
        )
        if created:
            Piano.objects.filter(pk=piano.pk).update(data_cadastro=data_cadastro)


class Migration(migrations.Migration):
    dependencies = [
        ("pianos", "0010_alter_piano_options_piano_destaque_piano_dislikes_and_more"),
    ]

    operations = [
        migrations.RunPython(import_local_pianos, migrations.RunPython.noop),
    ]
