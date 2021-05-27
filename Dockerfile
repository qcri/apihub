FROM python:3.8-slim

RUN pip install apihub

# expose port for prometheus
EXPOSE 8000

# expose port for server
EXPOSE 5000

ENV PORT 5000

CMD ["apihub_server"]
