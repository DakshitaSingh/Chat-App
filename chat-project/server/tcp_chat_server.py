#!/usr/bin/env python3
"""
Asyncio TCP chat server.
Supports:
 - multiple clients
 - broadcast messages
 - private messages with: /pm <username> <message>
 - list users: /list
 - quit: /quit
"""

import asyncio

CLIENTS = {}  # username -> (reader, writer)

async def broadcast(text, sender=None):
    to_remove = []
    for uname, (r, w) in CLIENTS.items():
        try:
            prefix = f"[{sender}] " if sender else ""
            w.write((prefix + text + "\n").encode())
            await w.drain()
        except Exception:
            to_remove.append(uname)
    for u in to_remove:
        CLIENTS.pop(u, None)

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer = writer.get_extra_info('peername')
    writer.write(b"Welcome! Please type your username: ")
    await writer.drain()
    try:
        data = await asyncio.wait_for(reader.readline(), timeout=60.0)
    except asyncio.TimeoutError:
        writer.write(b"Timeout. Closing connection.\n")
        await writer.drain()
        writer.close()
        return

    if not data:
        writer.close()
        return
    username = data.decode().strip()
    if not username:
        writer.write(b"Invalid username. Closing.\n")
        await writer.drain()
        writer.close()
        return
    if username in CLIENTS:
        writer.write(b"Username already taken. Closing.\n")
        await writer.drain()
        writer.close()
        return

    CLIENTS[username] = (reader, writer)
    print(f"{username} connected from {peer}")
    await broadcast(f"*** {username} has joined the chat ***")
    writer.write(b"Commands: /pm <user> <msg> | /list | /quit\n")
    await writer.drain()

    try:
        while True:
            raw = await reader.readline()
            if not raw:
                break
            text = raw.decode().rstrip("\n")
            if not text:
                continue
            if text.startswith("/pm "):
                # private message: /pm target message...
                parts = text.split(" ", 2)
                if len(parts) < 3:
                    writer.write(b"Usage: /pm <user> <message>\n")
                    await writer.drain()
                    continue
                target, msg = parts[1], parts[2]
                if target not in CLIENTS:
                    writer.write(f"User '{target}' not found.\n".encode())
                    await writer.drain()
                    continue
                _, target_writer = CLIENTS[target]
                target_writer.write(f"[PM from {username}] {msg}\n".encode())
                await target_writer.drain()
                writer.write(f"[PM to {target}] {msg}\n".encode())
                await writer.drain()
            elif text == "/list":
                users = ", ".join(CLIENTS.keys())
                writer.write(f"Connected users: {users}\n".encode())
                await writer.drain()
            elif text == "/quit":
                writer.write(b"Goodbye!\n")
                await writer.drain()
                break
            else:
                # broadcast
                await broadcast(text, sender=username)
    except ConnectionResetError:
        pass
    finally:
        # cleanup
        print(f"{username} disconnected")
        CLIENTS.pop(username, None)
        await broadcast(f"*** {username} has left the chat ***")
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

async def main(host="0.0.0.0", port=9009):
    server = await asyncio.start_server(handle_client, host, port)
    addr = server.sockets[0].getsockname()
    print(f"Chat server listening on {addr}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        import argparse
        p = argparse.ArgumentParser()
        p.add_argument("--host", default="0.0.0.0")
        p.add_argument("--port", type=int, default=9009)
        args = p.parse_args()
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        print("Server shutting down.")
