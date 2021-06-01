FROM python:3.8-slim

RUN apt-get update && apt-get install -y git

#RUN pip install apihub
COPY . /code
RUN pip install /code/dist/apihub-0.1.0-py3-none-any.whl

# expose port for prometheus
EXPOSE 8000

# expose port for server
EXPOSE 5000

ENV PORT 5000

CMD ["apihub_server"]