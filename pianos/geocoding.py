"""Converte endereços em coordenadas usando o Nominatim (OpenStreetMap).

Política de uso do Nominatim: no máximo 1 requisição por segundo e um
User-Agent que identifique a aplicação. Por isso a busca só é feita pelo
admin (ao salvar um piano ou pela ação em lote), nunca no formulário público.
https://operations.osmfoundation.org/policies/nominatim/
"""

import json
import logging
import time
from decimal import Decimal
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
USER_AGENT = 'PianoFinder/1.1 (+https://www.pianofinder.com.br)'
TIMEOUT_SEGUNDOS = 6
INTERVALO_MINIMO = 1.1  # segundos entre requisições, pela política de uso

_ultima_requisicao = 0.0


def _consultar(consulta):
    global _ultima_requisicao
    espera = INTERVALO_MINIMO - (time.monotonic() - _ultima_requisicao)
    if espera > 0:
        time.sleep(espera)

    parametros = urlencode({
        'q': consulta,
        'format': 'jsonv2',
        'limit': 1,
        'countrycodes': 'br',
        'accept-language': 'pt-BR',
    })
    requisicao = Request(f'{NOMINATIM_URL}?{parametros}', headers={'User-Agent': USER_AGENT})
    try:
        with urlopen(requisicao, timeout=TIMEOUT_SEGUNDOS) as resposta:
            return json.load(resposta)
    finally:
        _ultima_requisicao = time.monotonic()


def geocodificar(piano):
    """Devolve (latitude, longitude) como Decimal, ou None se não encontrar.

    Tenta primeiro o nome do local junto com o endereço (bom para shoppings,
    estações e livrarias) e depois só o endereço.
    """
    local = f'{piano.cidade}, {piano.estado}, Brasil'
    consultas = [
        f'{piano.nome_local}, {piano.endereco}, {local}',
        f'{piano.endereco}, {local}',
    ]
    for consulta in consultas:
        try:
            resultados = _consultar(consulta)
        except (URLError, TimeoutError, ValueError) as erro:
            logger.warning('Falha ao geocodificar %r: %s', consulta, erro)
            return None
        if resultados:
            primeiro = resultados[0]
            return (
                Decimal(primeiro['lat']).quantize(Decimal('0.000001')),
                Decimal(primeiro['lon']).quantize(Decimal('0.000001')),
            )
    return None
