import urllib.request
import urllib.parse
import json
import urllib.error

SUPABASE_URL = "https://wihqlysyfdcakmuirdeu.supabase.co"
SUPABASE_KEY = "sb_publishable_bAoTS-Y_ooiKEZ9rKD1Dow__FeFlUhK"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}


def _request(method, path, body=None):
    url = SUPABASE_URL + "/rest/v1/" + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        print(f"[Supabase] HTTP {e.code}: {e.read().decode()}")
        return None
    except Exception as e:
        print(f"[Supabase] Erro: {e}")
        return None


def buscar_pedidos_novos(ultimo_id_impresso=None):
    """
    Busca pedidos com status='novo' que ainda nao foram impressos.
    Retorna lista de pedidos ordenados por created_at.
    """
    params = "pedidos?status=eq.novo&impresso=eq.false&order=created_at.asc&select=*"
    resultado = _request("GET", params)
    if resultado is None:
        return []
    return resultado


def marcar_como_impresso(pedido_id):
    """
    Marca pedido como impresso para nao reimprimir.
    """
    path = f"pedidos?id=eq.{pedido_id}"
    resultado = _request("PATCH", path, {"impresso": True})
    return resultado is not None


def adicionar_coluna_impresso():
    """
    Verifica se coluna 'impresso' existe — se nao, instrui usuario.
    (A coluna precisa ser criada manualmente no Supabase)
    """
    pass


def testar_conexao():
    """
    Testa se consegue conectar no Supabase.
    Retorna True/False.
    """
    result = _request("GET", "configuracoes_restaurante?select=nome_restaurante&limit=1")
    return result is not None
