import asyncio
import secrets
import sys

# НАСТРОЙКИ: Твой рабочий порт и логин/пароль
PORT = 2834
USER = b"tg_user"
PASSWORD = secrets.token_hex(8).encode()  # Генерирует случайный пароль


async def handle_client(reader, writer):
    try:
        # 1. Приветствие SOCKS5 (Handshake)
        header = await reader.readexactly(2)
        if header[0] != 0x05:  # Проверка версии SOCKS5
            writer.close()
            return

        nmethods = header[1]
        methods = await reader.readexactly(nmethods)

        # Выбираем метод 0x02 (Авторизация по логину/паролю)
        if 0x02 not in methods:
            writer.write(b"\x05\xff")  # Нет подходящих методов
            await writer.drain()
            writer.close()
            return

        writer.write(b"\x05\x02")  # Отвечаем, что нужна авторизация
        await writer.drain()

        # 2. Проверка логина и пароля
        auth_header = await reader.readexactly(2)
        if auth_header[0] != 0x01:  # Версия суб-переговоров
            writer.close()
            return

        user_len = auth_header[1]
        username = await reader.readexactly(user_len)
        pass_len = (await reader.readexactly(1))[0]
        password = await reader.readexactly(pass_len)

        if username != USER or password != PASSWORD:
            writer.write(b"\x01\x01")  # Ошибка авторизации
            await writer.drain()
            writer.close()
            return

        writer.write(b"\x01\x00")  # Успешная авторизация
        await writer.drain()

        # 3. Запрос на соединение (Request)
        req_header = await reader.readexactly(4)
        cmd = req_header[1]
        atyp = req_header[3]

        if cmd != 0x01:  # Поддерживаем только CONNECT
            writer.write(b"\x05\x07")  # Команда не поддерживается
            await writer.drain()
            writer.close()
            return

        # Читаем адрес назначения (куда Telegram хочет подключиться)
        if atyp == 0x01:  # IPv4
            dest_addr = ".".join(
                str(b) for b in await reader.readexactly(4)
            )
        elif atyp == 0x03:  # Доменное имя
            domain_len = (await reader.readexactly(1))[0]
            dest_addr = (await reader.readexactly(domain_len)).decode()
        elif atyp == 0x04:  # IPv6
            writer.close()
            return
        else:
            writer.close()
            return

        dest_port = int.from_bytes(await reader.readexactly(2), "big")

        # 4. Подключаемся к серверам Telegram
        try:
            remote_reader, remote_writer = await asyncio.open_connection(
                dest_addr, dest_port
            )
        except Exception:
            writer.write(b"\x05\x01")  # Ошибка подключения
            await writer.drain()
            writer.close()
            return

        # Отвечаем клиенту, что всё ок
        writer.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        await writer.drain()

        # 5. Пересылаем данные туда-обратно (Туннелирование)
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


async def main():
    # На всякий случай гасим старый docker, чтобы освободить порт 2834
    import subprocess

    subprocess.run("sudo docker stop telegram-proxy 2>/dev/null", shell=True)
    subprocess.run("sudo docker rm telegram-proxy 2>/dev/null", shell=True)

    server = await asyncio.start_server(handle_client, "0.0.0.0", PORT)
    print("=" * 50)
    print(f"ПРОКСИ ЗАПУЩЕН НА ПОРТУ {PORT}")
    print(f"Логин: {USER.decode()}")
    print(f"Пароль: {PASSWORD.decode()}")
    print("=" * 50)

    # Пытаемся получить внешний IP сервера
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

    link = f"https://t.me/socks?server={ip}&port={PORT}&user={USER.decode()}&pass={PASSWORD.decode()}"
    print(f"Ссылка для клика в Telegram:\n{link}")
    print("=" * 50)
    print("Оставьте этот терминал открытым, чтобы прокси работал.")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПрокси остановлен.")
