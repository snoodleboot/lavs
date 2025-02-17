FROM python:3.12-bookworm

COPY app .
COPY poetry.lock .
COPY pyproject.toml .EMV

ENV POETRY_VIRTUALENVS_CREATE=false

RUN pip install pipx
RUN pipx ensurepath
RUN pipx install poetry==2.1
# RUN poetry config virtualenvs.create false
RUN poetry install

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]