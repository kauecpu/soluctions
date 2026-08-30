import React, { useEffect, useState } from "react";

const API_BASE = "/api";

const SOURCE_LABELS = {
  remoteok: "RemoteOK",
  workana: "Workana",
  "99freelas": "99Freelas",
};

function JobCard({ job, onApply }) {
  const [applying, setApplying] = useState(false);

  const handleApply = async () => {
    setApplying(true);
    try {
      await onApply(job.id);
      window.open(job.url, "_blank", "noopener,noreferrer");
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className={`job-card ${job.applied ? "job-card--applied" : ""}`}>
      <div className="job-card__header">
        <h3>{job.title}</h3>
        <span className="job-card__source">
          {SOURCE_LABELS[job.source] || job.source}
        </span>
      </div>
      {job.company && <p className="job-card__company">{job.company}</p>}
      {job.description && <p className="job-card__description">{job.description}</p>}
      <div className="job-card__meta">
        {job.tags && <span className="job-card__tags">{job.tags}</span>}
        {job.budget && <span className="job-card__budget">{job.budget}</span>}
        {job.posted_at && <span className="job-card__date">{job.posted_at}</span>}
      </div>
      <div className="job-card__actions">
        <a href={job.url} target="_blank" rel="noopener noreferrer">
          Ver vaga
        </a>
        <button onClick={handleApply} disabled={applying || job.applied}>
          {job.applied ? "Enviada ✓" : applying ? "Enviando..." : "Enviar"}
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const [jobs, setJobs] = useState([]);
  const [queryInput, setQueryInput] = useState(""); // o que está digitado no campo
  const [activeQuery, setActiveQuery] = useState(""); // o filtro realmente aplicado
  const [sourceOptions, setSourceOptions] = useState([]);
  const [selectedSource, setSelectedSource] = useState("all");
  const [loading, setLoading] = useState(false);
  const [scraping, setScraping] = useState(false);
  const [hideApplied, setHideApplied] = useState(false);
  const [error, setError] = useState(null);
  const [scrapeMsg, setScrapeMsg] = useState(null);

  const loadJobs = async (q) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (q) params.set("q", q);
      const res = await fetch(`${API_BASE}/jobs?${params.toString()}`);
      if (!res.ok) throw new Error(`Erro ${res.status}`);
      const data = await res.json();
      setJobs(data);
    } catch (err) {
      setError(
        "Não consegui falar com o backend. Confere se ele está rodando em localhost:5000."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs("");
    fetch(`${API_BASE}/sources`)
      .then((res) => (res.ok ? res.json() : []))
      .then((list) => setSourceOptions(Array.isArray(list) ? list : []))
      .catch(() => setSourceOptions([]));
  }, []);

  const handleFiltrar = () => {
    setActiveQuery(queryInput);
    loadJobs(queryInput);
  };

  const handleLimparFiltro = () => {
    setQueryInput("");
    setActiveQuery("");
    loadJobs("");
  };

  const handleFiltroKeyDown = (e) => {
    if (e.key === "Enter") handleFiltrar();
  };

  const handleScrape = async () => {
    setScraping(true);
    setScrapeMsg(null);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (selectedSource !== "all") params.set("source", selectedSource);
      const res = await fetch(`${API_BASE}/scrape?${params.toString()}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error(`Erro ${res.status}`);
      const data = await res.json();
      setScrapeMsg(`Encontradas ${data.found} vagas, ${data.new} novas adicionadas.`);
      await loadJobs(activeQuery);
    } catch (err) {
      setError("Falha ao buscar vagas novas. Confere sua conexão e o backend.");
    } finally {
      setScraping(false);
    }
  };

  const handleApply = async (jobId) => {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/apply`, { method: "POST" });
    if (!res.ok) throw new Error("Falha ao marcar vaga como aplicada");
    setJobs((prev) =>
      prev.map((j) => (j.id === jobId ? { ...j, applied: 1 } : j))
    );
  };

  const visibleJobs = hideApplied ? jobs.filter((j) => !j.applied) : jobs;

  return (
    <div className="app">
      <header className="app__header">
        <h1>Vagas Freelancer — Dev</h1>
      </header>

      <section className="app__panel">
        <h2 className="app__panel-title">Buscar vagas novas na internet</h2>
        <div className="app__panel-row">
          <select
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
            aria-label="Fonte de vagas"
          >
            <option value="all">Todas as fontes</option>
            {sourceOptions.map((src) => (
              <option key={src} value={src}>
                {SOURCE_LABELS[src] || src}
              </option>
            ))}
          </select>
          <button onClick={handleScrape} disabled={scraping}>
            {scraping ? "Buscando..." : "Buscar vagas"}
          </button>
        </div>
        {scrapeMsg && <p className="app__message">{scrapeMsg}</p>}
      </section>

      <section className="app__panel">
        <h2 className="app__panel-title">Filtrar vagas já salvas</h2>
        <div className="app__panel-row">
          <input
            type="text"
            placeholder="Ex: python, react, django..."
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            onKeyDown={handleFiltroKeyDown}
          />
          <button onClick={handleFiltrar}>Filtrar</button>
          {activeQuery && (
            <button className="app__button-secondary" onClick={handleLimparFiltro}>
              Limpar filtro
            </button>
          )}
        </div>
        <label className="app__checkbox">
          <input
            type="checkbox"
            checked={hideApplied}
            onChange={(e) => setHideApplied(e.target.checked)}
          />
          Ocultar já enviadas
        </label>
      </section>

      {error && <p className="app__error">{error}</p>}
      {loading && <p className="app__message">Carregando...</p>}
      {!loading && visibleJobs.length === 0 && !error && (
        <p className="app__message">
          Nenhuma vaga encontrada ainda. Clique em "Buscar vagas".
        </p>
      )}

      <div className="job-list">
        {visibleJobs.map((job) => (
          <JobCard key={job.id} job={job} onApply={handleApply} />
        ))}
      </div>
    </div>
  );
}
