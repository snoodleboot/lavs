FROM docker.io/python:3.12-bookworm

WORKDIR app
COPY app app/
COPY poetry.lock app/
COPY pyproject.toml app/

ENV POETRY_VIRTUALENVS_CREATE=false

RUN pip install pipx && pipx ensurepath --global --prepend && pipx install poetry==2.1
RUN poetry --help
# RUN poetry config virtualenvs.create false
RUN poetry install

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]