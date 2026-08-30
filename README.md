# Vagas Freelancer — Dev

Programa que busca vagas de dev freelancer/remoto (RemoteOK, Workana e
99Freelas), guarda num banco local sem duplicar, e mostra numa telinha web onde você clica em
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

1. Clique em **"Buscar vagas novas"** — o backend consulta as fontes
   disponíveis, filtra vagas de dev e salva as que ainda não tinha visto.
2. Use o campo de busca pra filtrar por palavra-chave (ex: `python`, `react`,
   `django`).
3. Clique em **"Enviar"** numa vaga: ela é marcada como aplicada no banco
   (fica com opacidade reduzida e não aparece mais se você marcar "ocultar
   já enviadas") e o link da vaga abre numa aba nova pra você aplicar.

## Adicionando novas fontes de vaga

As fontes implementadas são RemoteOK, Workana e 99Freelas (`backend/scraper.py`).
Workana e 99Freelas são lidos do HTML inicial servido publicamente, sem
Playwright ou navegador headless. Para adicionar outra fonte:

1. Escreva uma função `fetch_workana_jobs()` (ou similar) em `scraper.py`
   que devolve uma lista de dicts no mesmo formato que `fetch_remoteok_jobs`
   já usa (`source`, `external_id`, `title`, `company`, `description`,
   `url`, `tags`, `budget`, `posted_at`).
2. Chame essa função dentro de `fetch_all_jobs()`, junto com a do RemoteOK.
3. Não precisa mexer em mais nada — o banco e a API já lidam com qualquer
   fonte que siga esse formato.

As URLs consultadas são `https://www.workana.com/jobs?category=it-programming`
e `https://www.99freelas.com.br/projects?q=desenvolvimento`. A estrutura HTML
dos sites pode mudar; se isso acontecer, a função de parsing correspondente
deve ser atualizada. Vale checar os termos de uso de cada site antes.

## Publicando no GitHub

O repositório já vem pronto: `git init` feito, primeiro commit feito,
remote `origin` já apontando pra `https://github.com/kauecpu/soluctions.git`
e a tag `v1.0.0` já criada localmente. Só falta um comando:

```bash
git push -u origin main --tags
```

Isso manda o código e a tag de uma vez só. Assim que terminar, o workflow
em `.github/workflows/build.yml` roda sozinho na aba **Actions** do repo
e, por causa da tag, também publica os três executáveis na aba
**Releases** — não precisa fazer mais nada depois desse push.

## Observação importante

As buscas ao vivo das três fontes são feitas com `requests`. Se alguma fonte
bloquear ou alterar a estrutura da página, o endpoint retorna zero vagas para
ela e registra o erro no backend; ajuste o parser correspondente em
`backend/scraper.py` quando necessário.

O workflow do GitHub Actions (`.github/workflows/build.yml`) também não
pôde ser executado de verdade daqui — só validei a sintaxe do YAML.
Testei manualmente a arquitetura que ele empacota (backend servindo os
arquivos estáticos do frontend + API na mesma porta) simulando um build
do frontend, e funcionou. Ainda assim, é normal builds de PyInstaller
darem algum ajuste na primeira tentativa em CI (ex: um import que falta
declarar) — se o Actions falhar, me manda o log da aba Actions que eu
ajusto.
