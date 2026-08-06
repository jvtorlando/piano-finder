from django.db import migrations


TEST_RECORDS = (
    ('we', 'we'),
    ('qw', 'qw'),
    ('wsw', 'sws'),
)


def clean_imported_data(apps, schema_editor):
    Piano = apps.get_model('pianos', 'Piano')

    for nome_local, endereco in TEST_RECORDS:
        Piano.objects.filter(
            nome_local=nome_local,
            endereco=endereco,
            aprovado=False,
        ).delete()

    Piano.objects.filter(
        nome_local='Shopping Villa Lobbos',
        endereco='Av. Dra. Ruth Cardoso, 4777',
    ).update(
        descricao=(
            'O piano fica no primeiro andar do shopping, em frente à loja '
            'Zara. Livre para tocar.'
        ),
    )

    Piano.objects.filter(
        nome_local='Galeria Magalu Av. Paulista',
        endereco='Av. Paulista, 2073',
    ).update(tipo='digital')


class Migration(migrations.Migration):
    dependencies = [
        ('pianos', '0011_import_local_pianos_to_neon'),
    ]

    operations = [
        migrations.RunPython(clean_imported_data, migrations.RunPython.noop),
    ]
