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

    # 1. Проверяем и останавливаем старый контейнер, если он существует
    print("Очищаем старые контейнеры (если они были)...")
    subprocess.run("sudo docker stop telegram-proxy 2>/dev/null", shell=True)
    subprocess.run("sudo docker rm telegram-proxy 2>/dev/null", shell=True)

    # 2. Проверяем, установлен ли docker
    if subprocess.run("command -v docker", shell=True, capture_output=True).returncode != 0:
        print("Docker не найден. Устанавливаем Docker...")
        run_command("sudo apt-get update")
        run_command("sudo apt-get install -y docker.io")
    else:
        print("Docker уже установлен.")

    # 3. Генерируем случайный секретный ключ (32 символа в hex)
    secret_raw = secrets.token_hex(16)
    
    # НАСТРОЙКА ПОРТА: Твой проверенный рабочий порт
    port = 2834 

    print(f"Генерируем чистый секрет: {secret_raw}")
    print(f"Настраиваем порт: {port}")

    # 4. Запускаем продвинутый Docker-контейнер mtproto-proxy
    # Этот образ идеально работает на любых портах и поддерживает Fake TLS (dd-префикс)
    docker_cmd = (
        f"sudo docker run -d -p {port}:443 --name telegram-proxy --restart=always "
        f"-e SECRET={secret_raw} seriyps/mtproto-proxy:latest"
    )
    
    print("Запускаем Docker-контейнер...")
    run_command(docker_cmd)

    # 5. Получаем внешний IP-адрес сервера
    try:
        ip = subprocess.check_output("curl -s ifconfig.me", shell=True).decode('utf-8').strip()
    except Exception:
        ip = "31.76.225.186"  # Твой IP как запасной вариант

    # 6. Формируем ссылку СРАЗУ с префиксом dd для глубокой маскировки
    tg_link = f"https://t.me/proxy?server={ip}&port={port}&secret=dd{secret_raw}"
    
    print("\n" + "="*50)
    print("ПРОКСИ УСПЕШНО ЗАПУЩЕН!")
    print("="*50)
    print(f"Ссылка для подключения в Telegram (уже включает dd-префикс):\n{tg_link}")
    print("="*50)


if __name__ == "__main__":
    main()
