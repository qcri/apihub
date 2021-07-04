FROM python:3.8-slim

RUN apt-get update && apt-get install -y git

#RUN pip install apihub
COPY . /code
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -

# expose port for prometheus
EXPOSE 8000

# expose port for server
EXPOSE 5000

ENV PORT 5000

CMD ["poetry", "apihub_server"]
