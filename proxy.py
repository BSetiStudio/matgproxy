import os
import secrets
import subprocess
import sys


def run_command(command):
    """Вспомогательная функция для запуска системных команд."""
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды: {e}")
        sys.exit(1)


def main():
    print("--- Настройка MTProto Прокси для Telegram ---")

    # 1. Проверяем, установлен ли docker
    if subprocess.run("command -v docker", shell=True, capture_output=True).returncode != 0:
        print("Docker не найден. Устанавливаем Docker...")
        run_command("sudo apt-get update")
        run_command("sudo apt-get install -y docker.io")
    else:
        print("Docker уже установлен.")

    # 2. Генерируем случайный секретный ключ (32 символа в hex)
    secret = secrets.token_hex(16)
    
    # Порт, на котором будет работать прокси (можно изменить)
    port = 443 

    print(f"Генерируем секрет: {secret}")
    print(f"Настраиваем порт: {port}")

# 3. Запускаем официальный Docker-контейнер MTProto
    # Скачиваем образ и запускаем его в фоновом режиме (-d)
    docker_cmd = (
        f"sudo docker run -d -p {port}:443 --name telegram-proxy --restart=always "
        f"-e SECRET={secret} telegrammessenger/proxy:latest"
    )
    
    print("Запускаем Docker-контейнер...")
    run_command(docker_cmd)

    # 4. Получаем внешний IP-адрес сервера для создания ссылки
    try:
        ip = subprocess.check_output("curl -s ifconfig.me", shell=True).decode('utf-8').strip()
    except Exception:
        ip = "ВАШ_IP_АДРЕС"

    # 5. Выводим красивую ссылку для подключения
    tg_link = f"https://t.me/proxy?server={ip}&port={port}&secret={secret}"
    
    print("\n" + "="*50)
    print("ПРОКСИ УСПЕШНО ЗАПУЩЕН!")
    print("="*50)
    print(f"Ссылка для подключения в Telegram:\n{tg_link}")
    print("="*50)


if __name__ == "__main__":
    main()
