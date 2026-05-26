import asyncio
import os
import secrets
import subprocess
import sys
import time
import urllib.request

CONFIG_FILE = "/etc/tg_proxy_config.txt"
PORT = 2834
USER = "tg_user"
PASSWORD = secrets.token_hex(8)
LANG = "ru"  # по умолчанию

# Локализация (Языковые пакеты)
STRINGS = {
    "ru": {
        "title": "         УПРАВЛЕНИЕ ТЕЛЕГРАМ ПРОКСИ [matg]        ",
        "status": " Текущий статус службы: ",
        "active": "РАБОТАЕТ (ПОРТ: {})",
        "inactive": "ОСТАНОВЛЕН",
        "login": " Текущий Логин:  {}",
        "pass": " Текущий Пароль: {}",
        "opt1": " 1. Показать ссылку для подключения в Telegram",
        "opt2": " 2. Изменить ПОРТ прокси",
        "opt3": " 3. Изменить ЛОГИН",
        "opt4": " 4. Изменить ПАРОЛЬ",
        "opt5": " 5. Сгенерировать новый случайный пароль",
        "opt6": " 6. Запустить / Перезапустить прокси",
        "opt7": " 7. Остановить прокси",
        "opt8": " 8. Тест скорости и пинга до Telegram",
        "opt9": " 9. ПОЛНОЕ УДАЛЕНИЕ (Деинсталляция)",
        "opt0": " 0. Выйти из меню",
        "choice": "Выберите действие (0-9): ",
        "link_title": "\n Ссылка для Telegram:",
        "press_enter": "\nНажмите Enter для возврата в меню...",
        "enter_port": "\nВведите новый порт (сейчас {}): ",
        "port_changed": " Порт изменен. Не забудьте перезапустить прокси (пункт 6).",
        "enter_login": "\nВведите новый логин (сейчас {}): ",
        "login_changed": " Логин изменен.",
        "enter_pass": "\nВведите новый пароль (сейчас {}): ",
        "pass_changed": " Пароль изменен.",
        "new_pass_gen": " Сгенерирован новый пароль: {}",
        "restarting": "\n Перезапуск службы...",
        "restarted": " Прокси успешно перезапущен!",
        "stopping": "\n Остановка службы...",
        "stopped": " Прокси остановлен.",
        "testing": "\nТестирование скорости соединения с Telegram...",
        "test_res": " Результаты теста:\n   - Пинг: {:.1f} мс\n   - Скорость скачивания: {:.2f} Мбит/с",
        "test_fail": " Ошибка теста: Серверы Telegram недоступны с этого VPS.",
        "uninstalling": "\nНачинаем полное удаление прокси из системы...",
        "uninstalled": "Прокси полностью удален. Команда matg больше недоступна.",
        "init_done": "\n Настройка завершена! Команда 'matg' зарегистрирована.",
    },
    "en": {
        "title": "         TELEGRAM PROXY MANAGEMENT [matg]        ",
        "status": " Current service status: ",
        "active": "RUNNING (PORT: {})",
        "inactive": "STOPPED",
        "login": " Current Username: {}",
        "pass": " Current Password: {}",
        "opt1": " 1. Show Telegram connection link",
        "opt2": " 2. Change proxy PORT",
        "opt3": " 3. Change USERNAME",
        "opt4": " 4. Change PASSWORD",
        "opt5": " 5. Generate new random password",
        "opt6": " 6. Start / Restart proxy",
        "opt7": " 7. Stop proxy",
        "opt8": " 8. Speed and Ping test to Telegram",
        "opt9": " 9. FULL UNINSTALL (Remove completely)",
        "opt0": " 0. Exit menu",
        "choice": "Select action (0-9): ",
        "link_title": "\n Telegram Link:",
        "press_enter": "\nPress Enter to return to menu...",
        "enter_port": "\nEnter new port (current {}): ",
        "port_changed": " Port changed. Don't forget to restart proxy (option 6).",
        "enter_login": "\nEnter new username (current {}): ",
        "login_changed": " Username changed.",
        "enter_pass": "\nEnter new password (current {}): ",
        "pass_changed": " Password changed.",
        "new_pass_gen": " New password generated: {}",
        "restarting": "\n Restarting service...",
        "restarted": " Proxy successfully restarted!",
        "stopping": "\n Stopping service...",
        "stopped": " Proxy stopped.",
        "testing": "\nTesting speed and ping to Telegram...",
        "test_res": " Test Results:\n   - Ping: {:.1f} ms\n   - Download Speed: {:.2f} Mbps",
        "test_fail": " Test failed: Telegram cores are unreachable from this VPS.",
        "uninstalling": "\nStarting full uninstallation from the system...",
        "uninstalled": "Proxy completely removed. The 'matg' command is now disabled.",
        "init_done": "\n Setup complete! Command 'matg' is registered.",
    },
}


def load_config():
    global PORT, USER, PASSWORD, LANG
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                if len(lines) >= 4:
                    PORT = int(lines[0])
                    USER = lines[1]
                    PASSWORD = lines[2]
                    LANG = lines[3]
        except Exception:
            pass


def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(f"{PORT}\n{USER}\n{PASSWORD}\n{LANG}\n")
    except Exception as e:
        print(f"Error saving config: {e}")


load_config()


async def handle_client(reader, writer):
    """Асинхронный SOCKS5 движок."""
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
        cli_path = "/usr/local/bin/matg"
        with open(cli_path, "w") as f:
            f.write(f"#!/bin/bash\nsudo python3 {script_path}\n")
        subprocess.run(f"sudo chmod +x {cli_path}", shell=True, check=True)
    except Exception as e:
        print(f"System setup error: {e}")


def full_uninstall():
    """Полное удаление всех следов скрипта из системы."""
    txt = STRINGS[LANG]
    print(txt["uninstalling"])
    subprocess.run("sudo systemctl stop tg-proxy.service 2>/dev/null", shell=True)
    subprocess.run(
        "sudo systemctl disable tg-proxy.service 2>/dev/null", shell=True
    )
    subprocess.run("sudo rm /etc/systemd/system/tg-proxy.service", shell=True)
    subprocess.run("sudo systemctl daemon-reload", shell=True)
    subprocess.run("sudo rm /usr/local/bin/matg 2>/dev/null", shell=True)
    subprocess.run(f"sudo rm {CONFIG_FILE} 2>/dev/null", shell=True)
    print(txt["uninstalled"])
    # Самоудаление самого файла скрипта (опционально, но чисто корчует всё)
    try:
        os.remove(os.path.abspath(__file__))
    except Exception:
        pass
    sys.exit(0)


def test_telegram_speed():
    """Замер пинга и скорости скачивания напрямую с серверов Telegram."""
    txt = STRINGS[LANG]
    print(txt["testing"])
    test_url = "https://core.telegram.org/cleanhtml"
    pings = []

    # 1. Замеряем пинг
    for _ in range(3):
        try:
            t0 = time.time()
            req = urllib.request.Request(test_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as r:
                r.read(100)
            pings.append((time.time() - t0) * 1000)
        except Exception:
            pass

    if not pings:
        print(txt["test_fail"])
        return

    avg_ping = sum(pings) / len(pings)

    # 2. Замеряем скорость загрузки
    try:
        t0 = time.time()
        req = urllib.request.Request(test_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = r.read()
        duration = time.time() - t0
        data_size_bits = len(data) * 8
        speed_mbps = (data_size_bits / duration) / (1024 * 1024)
    except Exception:
        speed_mbps = 0.0

    print("\n" + "=" * 40)
    print(txt["test_res"].format(avg_ping, speed_mbps))
    print("=" * 40)
