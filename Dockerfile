FROM python:3.8-slim

RUN apt-get update && apt-get install -y git

#COPY ./dist/apihub-0.1.0-py3-none-any.whl /tmp
#RUN pip install /tmp/apihub-0.1.0-py3-none-any.whl
RUN pip install 'poetry==1.1.8'

# expose port for prometheus
EXPOSE 8000

# expose port for server
EXPOSE 5000

ENV PORT=5000 PYTHONPATH=/app

WORKDIR /app

COPY poetry.lock pyproject.toml /app

RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

COPY . /app

CMD ["poetry", "run", "apihub_server"]
