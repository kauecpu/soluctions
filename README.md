# Vagas Freelancer — Dev

Programa que busca vagas de dev freelancer/remoto (hoje: RemoteOK), guarda
num banco local sem duplicar, e mostra numa telinha web onde você clica em
"Enviar" pra marcar a vaga como aplicada e abrir o link pra aplicar.

## Estrutura

```
backend/    API em Flask + SQLite + scraper
frontend/   Interface em React (Vite)
```

## Opção 1: baixar o executável pronto (recomendado, sem instalar nada)

Toda vez que uma tag de versão (ex: `v1.0.0`) é enviada pro GitHub, o
GitHub Actions builda sozinho um executável de duplo clique pra Windows,
Mac e Linux e publica na aba **Releases** do repositório. Basta baixar o
arquivo do seu sistema e dar duplo clique — ele já sobe o programa e abre
o navegador em `http://localhost:5000` sozinho.

- Windows: `vagas-freelancer-dev-windows.exe`
- Mac: `vagas-freelancer-dev-macos` (na primeira vez, o macOS vai bloquear
  por ser um app não assinado — clique com o botão direito → Abrir, ou
  libere em Ajustes → Privacidade e Segurança)
- Linux: `vagas-freelancer-dev-linux` (dê permissão de execução antes:
  `chmod +x vagas-freelancer-dev-linux`)

Como gerar uma nova versão: `git tag v1.0.0 && git push origin v1.0.0`.

## Opção 2: rodar a partir do código fonte (pra desenvolver/mexer no código)

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Isso sobe a API em `http://localhost:5000`. Na primeira vez que rodar, ele
cria automaticamente o arquivo `jobs.db` (SQLite) na pasta `backend/`.

### 2. Frontend

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Isso sobe a interface em `http://localhost:5173` (o Vite faz proxy de
`/api` pro backend na porta 5000 automaticamente). Abra essa URL no
navegador.

### 3. Usar

1. Clique em **"Buscar vagas novas"** — o backend vai no RemoteOK, filtra
   vagas de dev e salva as que ainda não tinha visto.
2. Use o campo de busca pra filtrar por palavra-chave (ex: `python`, `react`,
   `django`).
3. Clique em **"Enviar"** numa vaga: ela é marcada como aplicada no banco
   (fica com opacidade reduzida e não aparece mais se você marcar "ocultar
   já enviadas") e o link da vaga abre numa aba nova pra você aplicar.

## Adicionando novas fontes de vaga

Hoje só o RemoteOK está implementado (`backend/scraper.py`,
`fetch_remoteok_jobs`), porque é o mais simples de acessar sem login. Pra
adicionar Workana ou 99Freelas:

1. Escreva uma função `fetch_workana_jobs()` (ou similar) em `scraper.py`
   que devolve uma lista de dicts no mesmo formato que `fetch_remoteok_jobs`
   já usa (`source`, `external_id`, `title`, `company`, `description`,
   `url`, `tags`, `budget`, `posted_at`).
2. Chame essa função dentro de `fetch_all_jobs()`, junto com a do RemoteOK.
3. Não precisa mexer em mais nada — o banco e a API já lidam com qualquer
   fonte que siga esse formato.

Workana e 99Freelas não têm uma API pública como o RemoteOK, então essa
parte provavelmente vai exigir raspar o HTML da página de vagas (com
`requests` + `BeautifulSoup`, ou `Playwright` se a página carregar o
conteúdo via JavaScript). Vale checar os termos de uso de cada site antes.

## Publicando no GitHub

O repositório já vem com `git init` feito e o primeiro commit pronto.
Pra subir:

```bash
git remote add origin https://github.com/SEU-USUARIO/SEU-REPO.git
git branch -M main
git push -u origin main
```

Depois de criar o repositório vazio no GitHub (sem README, sem
.gitignore — já tem tudo aqui) e trocar `SEU-USUARIO/SEU-REPO` pela URL
real. Assim que o push terminar, o workflow em
`.github/workflows/build.yml` já aparece na aba **Actions** do repo. Ele
builda a cada push na `main`, mas só publica na aba **Releases** quando
você criar uma tag `v*` (ex: `git tag v1.0.0 && git push origin v1.0.0`).

## Observação importante

Este projeto foi desenvolvido num ambiente sem acesso à internet externa,
então a busca ao vivo no RemoteOK (`/api/scrape`) não pôde ser testada
contra o site real — só a lógica de parsing foi validada com dados de
exemplo. O restante (banco de dados, endpoints da API, filtro, marcar como
aplicada) foi testado de ponta a ponta e está funcionando. Ao rodar
localmente, onde você tem internet normal, vale rodar `python app.py` e
clicar em "Buscar vagas novas" pra confirmar que a busca ao vivo também
funciona — se a estrutura do RemoteOK tiver mudado, é só ajustar os nomes
dos campos em `parse_remoteok_response`.

O workflow do GitHub Actions (`.github/workflows/build.yml`) também não
pôde ser executado de verdade daqui — só validei a sintaxe do YAML.
Testei manualmente a arquitetura que ele empacota (backend servindo os
arquivos estáticos do frontend + API na mesma porta) simulando um build
do frontend, e funcionou. Ainda assim, é normal builds de PyInstaller
darem algum ajuste na primeira tentativa em CI (ex: um import que falta
declarar) — se o Actions falhar, me manda o log da aba Actions que eu
ajusto.
