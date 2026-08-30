"""
Scraper de vagas de dev freelancer/remoto.

Busca RemoteOK, Workana e 99Freelas. RemoteOK expõe um endpoint JSON
público; Workana e 99Freelas entregam as vagas no HTML inicial, sem
login. Cada fonte segue a mesma interface e retorna dicts no formato
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

import html
import json
import re
from datetime import UTC, datetime

import requests
from bs4 import BeautifulSoup

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
    except Exception as e:  # noqa: BLE001 - tradução nunca pode derrubar o scraping
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

WORKANA_URL = "https://www.workana.com/jobs?category=it-programming"
NINETY_NINE_FREELAS_URL = "https://www.99freelas.com.br/projects?q=desenvolvimento"

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

def _absolute_url(base: str, value: str) -> str:
    if value.startswith(("http://", "https://")):
        return value
    return f"{base.rstrip('/')}/{value.lstrip('/')}"


def _title_from_workana_html(raw_title: str) -> tuple[str, str]:
    fragment = BeautifulSoup(raw_title or "", "html.parser")
    anchor = fragment.find("a")
    title = anchor.get_text(" ", strip=True) if anchor else fragment.get_text(" ", strip=True)
    return " ".join(title.split()), anchor.get("href", "") if anchor else ""


def parse_workana_response(raw_html: str) -> list[dict]:
    """Extrai as vagas do JSON SSR embutido no HTML do Workana."""
    soup = BeautifulSoup(raw_html, "html.parser")
    search = soup.find("search", attrs={":results-initials": True})
    if search is None:
        return []
    try:
        payload = json.loads(html.unescape(search[":results-initials"]))
    except (KeyError, TypeError, json.JSONDecodeError):
        return []
    jobs: list[dict] = []
    for item in payload.get("results", []):
        if not isinstance(item, dict) or not item.get("slug"):
            continue
        title, relative_url = _title_from_workana_html(str(item.get("title", "")))
        skills = item.get("skills", []) or []
        tags = [str(skill.get("anchorText", "")).strip() for skill in skills if isinstance(skill, dict)]
        jobs.append({
            "source": "workana",
            "external_id": str(item["slug"]),
            "title": title,
            "company": str(item.get("authorName", "") or ""),
            "description": translate_to_pt(_clean_html(str(item.get("description", "") or ""))),
            "url": _absolute_url("https://www.workana.com", relative_url or f"/job/{item['slug']}"),
            "tags": ", ".join(tag for tag in tags if tag),
            "budget": str(item.get("budget", "") or ""),
            "posted_at": str(item.get("publishedDate", item.get("postedDate", "")) or ""),
        })
    return jobs


def fetch_workana_jobs(timeout: int = 15) -> list[dict]:
    """Busca vagas de TI do Workana usando o HTML servido pelo site."""
    response = requests.get(WORKANA_URL, headers=BROWSER_HEADERS, timeout=timeout)
    response.raise_for_status()
    return parse_workana_response(response.text)


def _timestamp_text(value: str | None) -> str:
    if not value or not value.isdigit():
        return ""
    return datetime.fromtimestamp(int(value) / 1000, tz=UTC).isoformat()


def parse_99freelas_response(raw_html: str) -> list[dict]:
    """Extrai projetos de desenvolvimento da listagem HTML do 99Freelas."""
    soup = BeautifulSoup(raw_html, "html.parser")
    jobs: list[dict] = []
    for item in soup.select("li.result-item[data-id]"):
        project_id = item.get("data-id")
        anchor = item.select_one("h1.title a")
        if not project_id or anchor is None:
            continue
        info = item.select_one(".information")
        parts = [part.strip() for part in info.get_text("|", strip=True).split("|")] if info else []
        category = parts[0] if parts else ""
        description_node = item.select_one(".description")
        raw_description = (
            description_node.get("data-content")
            if description_node is not None and description_node.get("data-content")
            else description_node.decode_contents() if description_node is not None else ""
        )
        posted = item.select_one(".datetime")
        jobs.append({
            "source": "99freelas",
            "external_id": str(project_id),
            "title": " ".join(anchor.get_text(" ", strip=True).split()),
            "company": "",
            "description": translate_to_pt(_clean_html(html.unescape(str(raw_description or "")))),
            "url": _absolute_url("https://www.99freelas.com.br", str(anchor.get("href", ""))),
            "tags": category,
            "budget": "",
            "posted_at": _timestamp_text(posted.get("cp-datetime") if posted else None),
        })
    return jobs


def fetch_99freelas_jobs(timeout: int = 15) -> list[dict]:
    """Busca projetos de desenvolvimento do 99Freelas em HTML público."""
    response = requests.get(
        NINETY_NINE_FREELAS_URL, headers=BROWSER_HEADERS, timeout=timeout
    )
    response.raise_for_status()
    return parse_99freelas_response(response.text)


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
