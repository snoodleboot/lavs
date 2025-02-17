FROM python:3.12-bookworm

COPY app .
COPY poetry.lock .
COPY pyproject.toml .

RUN pip install pipx
RUN pipx ensurepath
RUN pipx install poetry==1.4.0
RUN poetry install

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]