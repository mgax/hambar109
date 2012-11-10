import os
import socket


def invoke_tika(data_file, buffer_size=16384):
    host = '127.0.0.1'
    port = int(os.environ['PUBDOCS_TIKA_PORT'])

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    while True:
        chunk = data_file.read(buffer_size)
        if not chunk:
            break
        sock.send(chunk)
    sock.shutdown(socket.SHUT_WR)
    while True:
        chunk = sock.recv(buffer_size)
        if not chunk:
            break
        yield chunk
    sock.close()
