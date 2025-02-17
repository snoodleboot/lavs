FROM python:3.12-bookwork

COPY app .
COPY poetry.lock
COPY pyproject.toml

RUN pip install pipx && pipx ensurepath && pipx install poetry && poetry install

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]