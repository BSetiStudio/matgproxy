import os
import secrets
import subprocess
import sys


def run_command(command):
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды: {e}")
        sys.exit(1)


def main():
    print("--- Настройка стабильного SOCKS5 Прокси для Telegram ---")

    # 1. Очищаем старый контейнер MTProto
    print("Удаляем старый MTProto контейнер...")
    subprocess.run("sudo docker stop telegram-proxy 2>/dev/null", shell=True)
    subprocess.run("sudo docker rm telegram-proxy 2>/dev/null", shell=True)

    # 2. Генерируем случайный логин и пароль, чтобы прокси был только твоим
    user = "tg_user"
    password = secrets.token_hex(8)  # Случайный безопасный пароль
    
    # Используем твой проверенный открытый порт
    port = 2834 

    print(f"Настраиваем порт: {port}")
    print(f"Создаем пользователя: {user}")
    print(f"Пароль: {password}")

    # 3. Запускаем проверенный и очень легкий SOCKS5 сервер (xkuma/socks5)
    docker_cmd = (
        f"sudo docker run -d -p {port}:1080 --name telegram-proxy --restart=always "
        f"-e USER={user} -e PASS={password} xkuma/socks5:latest"
    )
    
    print("Запускаем Docker-контейнер SOCKS5...")
    run_command(docker_cmd)

    # 4. Получаем IP сервера
    try:
        ip = subprocess.check_output("curl -s ifconfig.me", shell=True).decode('utf-8').strip()
    except Exception:
        ip = "31.76.225.186"

    # 5. Ссылка для Telegram в формате SOCKS5
    tg_link = f"https://t.me/socks?server={ip}&port={port}&user={user}&pass={password}"
    
    print("\n" + "="*50)
    print("SOCKS5 ПРОКСИ УСПЕШНО ЗАПУЩЕН!")
    print("="*50)
    print(f"Ссылка для подключения в Telegram:\n{tg_link}")
    print("="*50)


if __name__ == "__main__":
    main()
