import unittest
from unittest.mock import Mock, patch

import scraper


class ScraperParserTests(unittest.TestCase):
    def test_workana_parser_reads_server_rendered_results(self):
        html = '''
        <search :results-initials='{"results":[{"slug":"app-web-123",
        "title":"<a href=\\"/job/app-web-123\\">App web</a>",
        "authorName":"Empresa", "description":"<p>Descrição</p>",
        "skills":[{"anchorText":"React"}], "budget":"USD 100 - 250",
        "publishedDate":"Publicado: Hoje"}]}'></search>
        '''
        with patch.object(scraper, "translate_to_pt", side_effect=lambda text: text):
            jobs = scraper.parse_workana_response(html)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["source"], "workana")
        self.assertEqual(jobs[0]["external_id"], "app-web-123")
        self.assertEqual(jobs[0]["url"], "https://www.workana.com/job/app-web-123")
        self.assertEqual(jobs[0]["tags"], "React")

    def test_99freelas_parser_reads_project_cards(self):
        html = '''
        <li class="result-item" data-id="780266">
          <h1 class="title"><a href="/project/site-780266?fs=t">Site responsivo</a></h1>
          <p class="information">Desenvolvimento Web | Iniciante | Publicado:</p>
          <div class="description" data-content="Criar um site simples."></div>
        </li>
        '''
        with patch.object(scraper, "translate_to_pt", side_effect=lambda text: text):
            jobs = scraper.parse_99freelas_response(html)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["source"], "99freelas")
        self.assertEqual(jobs[0]["external_id"], "780266")
        self.assertEqual(jobs[0]["tags"], "Desenvolvimento Web")
        self.assertTrue(jobs[0]["url"].startswith("https://www.99freelas.com.br/project/"))

    def test_fetchers_use_requests_and_raise_http_errors(self):
        response = Mock(status_code=200, text="<html></html>")
        response.raise_for_status.return_value = None
        with patch.object(scraper.requests, "get", return_value=response) as get:
            scraper.fetch_workana_jobs()
            scraper.fetch_99freelas_jobs()
        self.assertEqual(get.call_count, 2)
        self.assertTrue(get.call_args_list[0].kwargs["headers"]["User-Agent"].startswith("Mozilla"))


if __name__ == "__main__":
    unittest.main()
