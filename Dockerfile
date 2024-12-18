FROM python:3

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем supervisord для управления процессами
RUN apt-get update && apt-get install -y supervisor && apt-get clean

# Копируем конфигурацию supervisord
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Открываем порты для API и вебхука
EXPOSE 5000
EXPOSE 8443

# Указываем команду для запуска контейнера
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
