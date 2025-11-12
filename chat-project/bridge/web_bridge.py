#!/usr/bin/env python3
"""
A small aiohttp app that:
 - serves static/index.html
 - speaks WebSocket at /ws
 - for each ws connection it opens a TCP connection to the TCP chat server,
   forwards messages both ways.

Usage:
  python bridge/web_bridge.py --tcp-host 127.0.0.1 --tcp-port 9009 --http-port 8765
"""

import asyncio
from aiohttp import web, WSMsgType
import argparse
import os

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    params = request.rel_url.query
    username = params.get("username", "web_user")
    tcp_host = request.app["tcp_host"]
    tcp_port = request.app["tcp_port"]

    # connect to TCP chat server
    reader, writer = await asyncio.open_connection(tcp_host, tcp_port)

    # send username (server expects it on connect)
    writer.write((username + "\n").encode())
    await writer.drain()

    async def tcp_to_ws():
        try:
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break
                await ws.send_str(line.decode().rstrip("\n"))
        except Exception:
            pass

    tcp_task = asyncio.create_task(tcp_to_ws())

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                text = msg.data.strip()
                if text == "":
                    continue
                # forward to TCP server (append newline)
                writer.write((text + "\n").encode())
                await writer.drain()
                if text == "/quit":
                    break
            elif msg.type == WSMsgType.ERROR:
                break
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        tcp_task.cancel()
        await ws.close()
    return ws

async def index(request):
    return web.FileResponse(os.path.join(STATIC_DIR, "index.html"))

def run_app(tcp_host, tcp_port, http_port):
    app = web.Application()
    app["tcp_host"] = tcp_host
    app["tcp_port"] = tcp_port
    app.router.add_get("/", index)
    app.router.add_get("/ws", websocket_handler)
    app.router.add_static("/", STATIC_DIR)  # also serve static files
    web.run_app(app, host="0.0.0.0", port=http_port)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--tcp-host", default="127.0.0.1")
    p.add_argument("--tcp-port", type=int, default=9009)
    p.add_argument("--http-port", type=int, default=8765)
    args = p.parse_args()
    run_app(args.tcp_host, args.tcp_port, args.http_port)
