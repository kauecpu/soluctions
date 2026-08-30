"""
Backend do programa de vagas de freelancer.

Serve a API E os arquivos estáticos do frontend (build do React) no mesmo
processo/porta, pra funcionar como um programa único de duplo clique quando
empacotado com PyInstaller — sem precisar de dois terminais.

Endpoints:
  GET  /api/jobs?q=<palavra-chave>&applied=<0|1>   -> lista vagas salvas
  POST /api/scrape                                  -> busca vagas novas e salva
  POST /api/jobs/<id>/apply                          -> marca vaga como aplicada

Modo dev (código fonte): python app.py
  - Sobe a API em http://localhost:5000
  - O frontend roda separado via "npm run dev" (Vite, porta 5173), que
    faz proxy de /api pra essa API (ver frontend/vite.config.js).

Modo empacotado (PyInstaller): dá duplo clique no executável
  - Sobe tudo (API + frontend já buildado) em http://localhost:5000 e abre
    o navegador sozinho.
"""
import os
import sys
import threading
import webbrowser

from flask import Flask, jsonify, request, send_from_directory

import db
import scraper


def _frontend_dist_dir() -> str:
    if getattr(sys, "frozen", False):
        # PyInstaller extrai os arquivos de --add-data pra essa pasta temporária
        return os.path.join(sys._MEIPASS, "frontend_dist")
    return os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")


FRONTEND_DIST = _frontend_dist_dir()
FRONTEND_BUILD_EXISTS = os.path.isdir(FRONTEND_DIST)

app = Flask(__name__, static_folder=FRONTEND_DIST if FRONTEND_BUILD_EXISTS else None)


@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    keyword = request.args.get("q") or None
    applied_param = request.args.get("applied")
    applied = None
    if applied_param is not None:
        applied = applied_param == "1"
    jobs = db.list_jobs(keyword=keyword, applied=applied)
    return jsonify(jobs)


@app.route("/api/scrape", methods=["POST"])
def scrape():
    source = request.args.get("source") or None
    sources = [source] if source else None
    fresh_jobs = scraper.fetch_all_jobs(sources=sources)
    inserted = db.upsert_jobs(fresh_jobs)
    return jsonify({
        "found": len(fresh_jobs),
        "new": inserted,
        "source": source or "todas",
    })


@app.route("/api/sources", methods=["GET"])
def sources():
    return jsonify(list(scraper.SOURCE_FETCHERS.keys()))


@app.route("/api/jobs/<int:job_id>/apply", methods=["POST"])
def apply_job(job_id):
    ok = db.mark_applied(job_id)
    if not ok:
        return jsonify({"error": "vaga não encontrada"}), 404
    return jsonify({"ok": True, "id": job_id})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# Serve o frontend buildado (quando existir) pra qualquer rota que não seja /api/*.
# Em modo dev sem build, essa rota não é usada — o Vite serve o frontend na porta 5173.
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if not FRONTEND_BUILD_EXISTS:
        return jsonify({
            "error": "Frontend não buildado. Rode 'npm run build' na pasta frontend/, "
                     "ou use 'npm run dev' separado durante desenvolvimento."
        }), 404
    full_path = os.path.join(FRONTEND_DIST, path)
    if path and os.path.isfile(full_path):
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")


def _open_browser():
    webbrowser.open("http://localhost:5000")


if __name__ == "__main__":
    db.init_db()
    # Só abre o navegador sozinho quando empacotado (duplo clique). Em modo
    # dev isso seria irritante toda vez que o auto-reload do Flask reinicia.
    if getattr(sys, "frozen", False):
        threading.Timer(1.2, _open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=not getattr(sys, "frozen", False))
