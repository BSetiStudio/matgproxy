# Telegram MTProto Proxy on Python & Docker

Простой скрипт на Python для автоматического развертывания персонального MTProto прокси для Telegram на сервере Ubuntu.

## Требования
* VPS с операционной системой Ubuntu (тестировалось на Ubuntu 22.04).
* Открытый порт `443` (убедитесь, что в настройках вашего хостинга/файрвола этот порт не заблокирован).

## Как запустить

1. Подключитесь к вашему VPS по SSH.
2. Склонируйте этот репозиторий или просто скачайте скрипт:
   ```bash
   curl -O [https://raw.githubusercontent.com/BSetiStudio/matgproxy/main/proxy.py](https://raw.githubusercontent.com/BSetiStudio/matgproxy/main/proxy.py)
