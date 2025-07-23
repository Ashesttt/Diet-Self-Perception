FROM python:3.9-slim
WORKDIR /app
COPY ./app /app
RUN pip install fastapi uvicorn sqlalchemy jinja2 python-multipart
#RUN pip install jinja2
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--reload"]
