import React, { useEffect, useState, useCallback } from "react";

const API_BASE = "/api";

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
        <span className="job-card__source">{job.source}</span>
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
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [scraping, setScraping] = useState(false);
  const [hideApplied, setHideApplied] = useState(false);
  const [error, setError] = useState(null);
  const [scrapeMsg, setScrapeMsg] = useState(null);

  const loadJobs = useCallback(async (q) => {
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
  }, []);

  useEffect(() => {
    loadJobs("");
  }, [loadJobs]);

  useEffect(() => {
    const timeout = setTimeout(() => loadJobs(query), 300);
    return () => clearTimeout(timeout);
  }, [query, loadJobs]);

  const handleScrape = async () => {
    setScraping(true);
    setScrapeMsg(null);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/scrape`, { method: "POST" });
      if (!res.ok) throw new Error(`Erro ${res.status}`);
      const data = await res.json();
      setScrapeMsg(`Encontradas ${data.found} vagas, ${data.new} novas adicionadas.`);
      await loadJobs(query);
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
        <button onClick={handleScrape} disabled={scraping}>
          {scraping ? "Buscando..." : "Buscar vagas novas"}
        </button>
      </header>

      <div className="app__controls">
        <input
          type="text"
          placeholder="Filtrar por palavra-chave (ex: python, react)..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <label className="app__checkbox">
          <input
            type="checkbox"
            checked={hideApplied}
            onChange={(e) => setHideApplied(e.target.checked)}
          />
          Ocultar já enviadas
        </label>
      </div>

      {scrapeMsg && <p className="app__message">{scrapeMsg}</p>}
      {error && <p className="app__error">{error}</p>}
      {loading && <p className="app__message">Carregando...</p>}
      {!loading && visibleJobs.length === 0 && !error && (
        <p className="app__message">
          Nenhuma vaga encontrada ainda. Clique em "Buscar vagas novas".
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
