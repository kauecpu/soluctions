"""
Scraper de vagas de dev freelancer/remoto.

Por enquanto busca só o RemoteOK, que expõe um endpoint JSON público
(não é bem uma API oficial documentada, mas é estável e não exige login).
A ideia é adicionar Workana e 99Freelas depois, seguindo a mesma
interface: uma função que retorna uma lista de dicts no formato
padronizado abaixo.

Formato padronizado de cada vaga:
{
    "source": "remoteok",
    "external_id": "...",   # id único dentro da fonte
    "title": "...",
    "company": "...",
    "description": "...",
    "url": "...",
    "tags": "python, django, ...",
    "budget": "...",        # texto livre (nem toda vaga tem valor)
    "posted_at": "...",     # data em texto/ISO
}
"""
from __future__ import annotations

import re
import requests

try:
    from deep_translator import GoogleTranslator
except ImportError:  # lib pode não estar instalada ainda (ver requirements.txt)
    GoogleTranslator = None

REMOTEOK_API_URL = "https://remoteok.com/api"
REMOTEOK_HEADERS = {
    # o RemoteOK bloqueia requests sem User-Agent de navegador
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# palavras-chave usadas pra filtrar só vagas de desenvolvimento
DEV_KEYWORDS = [
    "dev", "developer", "engineer", "engineering", "programmer",
    "software", "backend", "frontend", "full stack", "fullstack",
    "python", "javascript", "typescript", "react", "node", "java",
    "golang", "php", "ruby", "ios", "android", "mobile", "web",
    "data engineer", "devops", "sre", "qa", "swe",
]


def _looks_like_dev_job(position: str, tags: list[str]) -> bool:
    haystack = (position or "").lower() + " " + " ".join(t.lower() for t in tags)
    return any(kw in haystack for kw in DEV_KEYWORDS)


def _clean_html(raw_html: str, max_len: int = 600) -> str:
    """Remove tags HTML básico da descrição pra ficar legível no frontend."""
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len] + ("..." if len(text) > max_len else "")


def translate_to_pt(text: str) -> str:
    """Traduz a descrição da vaga pra português. Se a lib não estiver
    instalada, se não houver internet, ou se o texto já estiver em
    português (fontes como Workana/99Freelas), devolve o texto original
    sem travar o scraping por causa disso."""
    if not text or GoogleTranslator is None:
        return text
    try:
        translated = GoogleTranslator(source="auto", target="pt").translate(text)
        return translated or text
    except Exception as e:  # qualquer falha de rede/lib não pode derrubar o scrape
        print(f"[scraper] falha ao traduzir descrição: {e}")
        return text


def parse_remoteok_response(raw_jobs: list[dict]) -> list[dict]:
    """Transforma a resposta crua da API do RemoteOK no formato padronizado.
    Separado do fetch pra dar pra testar sem precisar de rede."""
    jobs = []
    for item in raw_jobs:
        # o primeiro item da lista é sempre um aviso legal, sem vaga de verdade
        if not isinstance(item, dict) or "id" not in item or "position" not in item:
            continue

        position = item.get("position", "")
        tags = item.get("tags", []) or []
        if not _looks_like_dev_job(position, tags):
            continue

        salary_min = item.get("salary_min")
        salary_max = item.get("salary_max")
        budget = ""
        if salary_min and salary_max:
            budget = f"${salary_min:,} - ${salary_max:,} /ano".replace(",", ".")

        url = item.get("url") or item.get("apply_url") or ""
        if url and url.startswith("/"):
            url = f"https://remoteok.com{url}"

        jobs.append({
            "source": "remoteok",
            "external_id": item["id"],
            "title": position,
            "company": item.get("company", ""),
            "description": translate_to_pt(_clean_html(item.get("description", ""))),
            "url": url,
            "tags": ", ".join(tags),
            "budget": budget,
            "posted_at": item.get("date", ""),
        })
    return jobs


def fetch_remoteok_jobs(timeout: int = 15) -> list[dict]:
    """Busca vagas ao vivo no RemoteOK e já filtra/normaliza pra dev."""
    resp = requests.get(REMOTEOK_API_URL, headers=REMOTEOK_HEADERS, timeout=timeout)
    resp.raise_for_status()
    raw_jobs = resp.json()
    return parse_remoteok_response(raw_jobs)


BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
}

# URLs confirmadas manualmente (navegador, sem login) em 30/08/2026:
# - Workana: https://www.workana.com/jobs?category=it-programming
#   Lista renderizada com título, descrição resumida, tags e faixa de
#   orçamento (USD). Tem paginação ("Próxima"), aparenta ser HTML
#   servido pronto (não SPA pura) — mas ISSO PRECISA SER CONFIRMADO com
#   um requests.get() cru antes de confiar 100% (ver TODO abaixo).
# - 99Freelas: https://www.99freelas.com.br/projects?q=desenvolvimento
#   Lista com 232 resultados no momento do teste, paginação numerada
#   (padrão de app com paginação no servidor). Categorias relevantes:
#   "Desenvolvimento Web", "Desenvolvimento Mobile",
#   "Desenvolvimento de Games", "Criação & Integração com IA".
# Nenhum dos dois pediu login pra ver a listagem.

def fetch_workana_jobs(timeout: int = 15) -> list[dict]:
    """TODO: implementar de verdade. A URL e a ausência de login já foram
    confirmadas manualmente (ver comentário acima) — falta:
    1. Confirmar com requests.get(...) cru se o HTML já vem com as vagas
       (senão, vai precisar de outra estratégia, tipo Playwright — nesse
       caso, avisar antes de seguir, por causa do empacotamento em .exe).
    2. Inspecionar as classes/seletores reais do HTML (abrir "Ver código
       fonte" no navegador ou inspecionar elemento) e escrever o parser
       com BeautifulSoup, devolvendo o mesmo formato padronizado das
       outras funções (não esquecer de passar a description por
       translate_to_pt, já que a maioria já vem em português — nesse caso
       a função só retorna o texto original, sem custo)."""
    raise NotImplementedError("fetch_workana_jobs ainda não foi implementado")


def fetch_99freelas_jobs(timeout: int = 15) -> list[dict]:
    """TODO: implementar de verdade — mesma orientação de fetch_workana_jobs,
    usando a URL https://www.99freelas.com.br/projects?q=desenvolvimento
    (ou trocar a query pelas categorias de dev listadas no comentário acima)."""
    raise NotImplementedError("fetch_99freelas_jobs ainda não foi implementado")


# Registro central de fontes: chave usada pelo parâmetro ?source= da API
# e pelo seletor do frontend -> função que busca e normaliza as vagas.
SOURCE_FETCHERS = {
    "remoteok": fetch_remoteok_jobs,
    "workana": fetch_workana_jobs,
    "99freelas": fetch_99freelas_jobs,
}


def fetch_all_jobs(sources: list[str] | None = None) -> list[dict]:
    """Ponto único que o backend chama. Sem argumento, busca de todas as
    fontes registradas; com uma lista de chaves (ex: ["workana"]), busca
    só dessas. Uma fonte falhando não derruba as outras."""
    keys = sources if sources else list(SOURCE_FETCHERS.keys())
    all_jobs: list[dict] = []
    for key in keys:
        fetcher = SOURCE_FETCHERS.get(key)
        if fetcher is None:
            print(f"[scraper] fonte desconhecida ignorada: {key}")
            continue
        try:
            all_jobs += fetcher()
        except NotImplementedError:
            print(f"[scraper] fonte ainda não implementada: {key}")
        except requests.RequestException as e:
            print(f"[scraper] falha ao buscar {key}: {e}")
    return all_jobs
