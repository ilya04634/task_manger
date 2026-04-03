# Используем официальный образ Python (версия 3.12, как у тебя)
FROM python:3.12-slim

# Устанавливаем переменные окружения, чтобы Python не писал .pyc файлы и не буферизировал вывод
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Рабочая директория внутри контейнера
WORKDIR /app

# Устанавливаем системные зависимости (нужны для сборки psycopg2)
RUN apt-get update && apt-get install -y libpq-dev gcc netcat-traditional

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем весь код проекта
COPY . /app/

# Собираем статические файлы (для админки и Swagger)
RUN python manage.py collectstatic --noinput