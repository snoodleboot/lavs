FROM docker.io/python:3.12-bookworm

WORKDIR app
COPY app app/
COPY poetry.lock app/
COPY pyproject.toml app/

ENV POETRY_VIRTUALENVS_CREATE=false
ENV PIPX_BIN_DIR=/usr/local/bin
ENV PIPX_HOME=/usr/local/share/pipx/venvs

RUN pip install pipx && pipx ensurepath && pipx install poetry==2.1 && poetry install


CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]