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
            "description": _clean_html(item.get("description", "")),
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


def fetch_all_jobs() -> list[dict]:
    """Ponto único que o backend chama. Fontes futuras (Workana, 99Freelas)
    entram aqui, cada uma numa função própria, igual fetch_remoteok_jobs."""
    all_jobs: list[dict] = []
    try:
        all_jobs += fetch_remoteok_jobs()
    except requests.RequestException as e:
        print(f"[scraper] falha ao buscar RemoteOK: {e}")
    return all_jobs
