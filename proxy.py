import asyncio
import os
import secrets
import subprocess
import sys

# Путь для сохранения настроек, чтобы они не терялись при перезапуске
CONFIG_FILE = "/etc/tg_proxy_config.txt"
PORT = 2834
USER = "tg_user"
PASSWORD = secrets.token_hex(8)


def load_config():
    """Загрузка сохраненного порта, логина и пароля."""
    global PORT, USER, PASSWORD
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                if len(lines) >= 3:
                    PORT = int(lines[0])
                    USER = lines[1]
                    PASSWORD = lines[2]
        except Exception:
            pass


def save_config():
    """Сохранение текущих настроек в файл."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(f"{PORT}\n{USER}\n{PASSWORD}\n")
    except Exception as e:
        print(f"Ошибка сохранения конфига: {e}")


# Загружаем настройки, если они уже есть
load_config()


async def handle_client(reader, writer):
    """Асинхронная обработка трафика SOCKS5."""
    try:
        header = await reader.readexactly(2)
        if header[0] != 0x05:
            writer.close()
            return

        nmethods = header[1]
        methods = await reader.readexactly(nmethods)

        if 0x02 not in methods:
            writer.write(b"\x05\xff")
            await writer.drain()
            writer.close()
            return

        writer.write(b"\x05\x02")
        await writer.drain()

        auth_header = await reader.readexactly(2)
        if auth_header[0] != 0x01:
            writer.close()
            return

        user_len = auth_header[1]
        username = (await reader.readexactly(user_len)).decode()
        pass_len = (await reader.readexactly(1))[0]
        password = (await reader.readexactly(pass_len)).decode()

        if username != USER or password != PASSWORD:
            writer.write(b"\x01\x01")
            await writer.drain()
            writer.close()
            return

        writer.write(b"\x01\x00")
        await writer.drain()

        req_header = await reader.readexactly(4)
        cmd = req_header[1]
        atyp = req_header[3]

        if cmd != 0x01:
            writer.write(b"\x05\x07")
            await writer.drain()
            writer.close()
            return

        if atyp == 0x01:
            dest_addr = ".".join(str(b) for b in await reader.readexactly(4))
        elif atyp == 0x03:
            domain_len = (await reader.readexactly(1))[0]
            dest_addr = (await reader.readexactly(domain_len)).decode()
        else:
            writer.close()
            return

        dest_port = int.from_bytes(await reader.readexactly(2), "big")

        try:
            remote_reader, remote_writer = await asyncio.open_connection(
                dest_addr, dest_port
            )
        except Exception:
            writer.write(b"\x05\x01")
            await writer.drain()
            writer.close()
            return

        writer.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        await writer.drain()

        async def tunnel(src, dst):
            try:
                while True:
                    data = await src.read(4096)
                    if not data:
                        break
                    dst.write(data)
                    await dst.drain()
            except Exception:
                pass
            finally:
                dst.close()

        asyncio.create_task(tunnel(reader, remote_writer))
        asyncio.create_task(tunnel(remote_reader, writer))

    except Exception:
        writer.close()


def setup_systemd_and_cli():
    """Регистрация службы systemd и создание глобальной команды matg."""
    script_path = os.path.abspath(__file__)

    service_content = f"""[Unit]
Description=Telegram SOCKS5 Proxy Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={os.path.dirname(script_path)}
ExecStart=/usr/bin/python3 {script_path} --daemon
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    try:
        with open("/etc/systemd/system/tg-proxy.service", "w") as f:
            f.write(service_content)

        subprocess.run("sudo systemctl daemon-reload", shell=True, check=True)
        subprocess.run(
            "sudo systemctl enable tg-proxy.service", shell=True, check=True
        )

        # Создаем ярлык для вызова через 'matg' из любой папки
        cli_path = "/usr/local/bin/matg"
        with open(cli_path, "w") as f:
            f.write(f"#!/bin/bash\nsudo python3 {script_path}\n")
        subprocess.run(f"sudo chmod +x {cli_path}", shell=True, check=True)

    except Exception as e:
        print(f"Ошибка инициализации системных файлов: {e}")


def get_tg_link():
    """Генерация ссылки для подключения."""
    try:
        import urllib.request

        ip = (
            urllib.request.urlopen("https://ifconfig.me/ip", timeout=3)
            .read()
            .decode()
            .strip()
        )
    except Exception:
        ip = "31.76.225.186"
    return f"https://t.me/socks?server={ip}&port={PORT}&user={USER}&pass={PASSWORD}"


def show_menu():
    """Интерактивное CLI меню для гибкой настройки."""
    global PORT, USER, PASSWORD
    while True:
        os.system("clear")
        print("=" * 50)
        print("         УПРАВЛЕНИЕ ТЕЛЕГРАМ ПРОКСИ [matg]        ")
        print("=" * 50)
        print(f" Текущий статус службы: ", end="")
        status = subprocess.run(
            "systemctl is-active tg-proxy",
            shell=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if status == "active":
            print("\033[92mРАБОТАЕТ (ПОРТ: {})\033[0m".format(PORT))
        else:
            print("\033[91mОСТАНОВЛЕН\033[0m")

        print(f" Текущий Логин:  {USER}")
        print(f" Текущий Пароль: {PASSWORD}")
        print("-" * 50)
        print(" 1. Показать ссылку для подключения в Telegram")
        print(" 2. Изменить ПОРТ прокси")
        print(" 3. Изменить ЛОГИН")
        print(" 4. Изменить ПАРОЛЬ")
        print(" 5. Сгенерировать новый случайный пароль")
        print(" 6. Запустить / Перезапустить прокси")
        print(" 7. Остановить прокси")
        print(" 0. Выйти из меню")
        print("=" * 50)

        choice = input("Выберите действие (0-7): ").strip()

        if choice == "1":
            print("\n Ссылка для Telegram:")
            print(f"\033[94m{get_tg_link()}\033[0m")
            input("\nНажмите Enter для возврата в меню...")
        elif choice == "2":
            new_port = input(f"\nВведите новый порт (сейчас {PORT}): ").strip()
            if new_port.isdigit():
                PORT = int(new_port)
                save_config()
                print(" Порт изменен. Не забудьте перезапустить прокси (пункт 6).")
            input("\nНажмите Enter...")
        elif choice == "3":
            new_user = input(f"\nВведите новый логин (сейчас {USER}): ").strip()
            if new_user:
                USER = new_user
                save_config()
                print(" Логин изменен.")
            input("\nНажмите Enter...")
        elif choice == "4":
            new_pass = input(
                f"\nВведите новый пароль (сейчас {PASSWORD}): "
            ).strip()
            if new_pass:
                PASSWORD = new_pass
                save_config()
                print(" Пароль изменен.")
            input("\nНажмите Enter...")
        elif choice == "5":
            PASSWORD = secrets.token_hex(8)
            save_config()
            print(f" Сгенерирован новый пароль: {PASSWORD}")
            input("\nНажмите Enter...")
        elif choice == "6":
            print("\n Перезапуск службы...")
            save_config()
            setup_systemd_and_cli()
            subprocess.run("sudo systemctl restart tg-proxy", shell=True)
            print(" Прокси успешно перезапущен!")
            input("\nНажмите Enter...")
        elif choice == "7":
            print("\n Остановка службы...")
            subprocess.run("sudo systemctl stop tg-proxy", shell=True)
            print(" Прокси остановлен.")
            input("\nНажмите Enter...")
        elif choice == "0":
            print("\nВыход.")
            break


async def run_server():
    """Запуск бесконечного сервера внутри демона systemd."""
    server = await asyncio.start_server(handle_client, "0.0.0.0", PORT)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        asyncio.run(run_server())
    else:
        # Если запускаем первый раз — создаем окружение и запускаем фон
        if not os.path.exists("/etc/systemd/system/tg-proxy.service"):
            print("Первый запуск: инициализация системы...")
            save_config()
            setup_systemd_and_cli()
            subprocess.run("sudo systemctl start tg-proxy", shell=True)
            print(
                "\n Настройка завершена! Команда 'matg' зарегистрирована в системе."
            )
            print(f" Ваша ссылка для Telegram:\n{get_tg_link()}")
            sys.exit(0)

        # Если система уже инициализирована, то обычный вызов показывает меню
        show_menu()
