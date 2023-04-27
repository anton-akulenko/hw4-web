FROM python:3.10

WORKDIR /hw4

COPY . .

EXPOSE 3000

ENTRYPOINT ["python", "main.py"]