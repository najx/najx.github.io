# najx.dev 

Delighted to welcome you to my little corner of the web.

## Pre-requisites
- Ruby 3.2.x — the same version the GitHub Actions build uses
  (`.github/workflows/jekyll.yml`), so local builds match CI.

Installation of Ruby version 3.2:
```
rvm install 3.2
rvm use 3.2 --default
```

## Build & Test locally:
```
bundle install
bundle exec jekyll serve
```

## newsbot

The site also has a Python part: `tools/newsbot` collects AI headlines,
ranks them, and drafts the weekly article. It is documented in
[`docs/newsbot.md`](docs/newsbot.md).

- Python ≥ 3.10
```
pip install -e './tools/newsbot[dev]'
pytest
```
  134 tests, ~0.5s.
- Driven by two GitHub Actions workflows
  (`.github/workflows/ai-news-collect.yml`, `ai-news-article.yml`), which
  need three repository secrets: `NEWSBOT_TOKEN`, `TYPESAFE_API_KEY`,
  `ANTHROPIC_API_KEY`.
