#!/usr/bin/env python3
"""
Simple console TCP client to talk to the chat server.
"""

import socket
import threading
import sys

def recv_loop(sock: socket.socket):
    try:
        while True:
            data = sock.recv(4096)
            if not data:
                print("[Disconnected from server]")
                break
            sys.stdout.write(data.decode())
            sys.stdout.flush()
    except Exception as e:
        print("[Receive error]", e)

def main(host="127.0.0.1", port=9009):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    t = threading.Thread(target=recv_loop, args=(sock,), daemon=True)
    t.start()

    try:
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            sock.sendall(line.encode())
            if line.strip() == "/quit":
                break
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=9009)
    args = p.parse_args()
    main(args.host, args.port)
