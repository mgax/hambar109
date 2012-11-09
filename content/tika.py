import socket


def invoke_tika(data_file, host='127.0.0.1', port=9999, buffer_size=16384):
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
