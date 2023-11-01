import socket 
import logging
from utils import *

host = '192.168.122.11'
port = 8889

def console_process():
    s = socket.socket()
    s.connect((host, port))
    logging.info(f'Console Connected from {host, port}')
    send(s, {'type': 'console_connect'})
    while True:
        command = input('>')
        if len(command.replace(' ', '')) < 1: continue
        send_comm(s, command)
        ret = recv(s)
        print(ret)

if __name__ == "__main__":
    console_process()