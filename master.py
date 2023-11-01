import os
import socket 
import threading
import json
import logging
import sys
from utils import *

host = '192.168.122.11'
port = 8889

def console_process():
    s = socket.socket()         # 创建 socket 对象
    s.connect((host, port))
    logging.info(f'Console Connected from {host, port}')
    send(s, {'type': 'console_connect'})
    while True:
        command = input('>')
        send_comm(s, command)

def process_daemon_process(r, s:socket.socket):
    if r['type'] == 'set_mpi_ip':
        logging.info(f'Set MPI ip')
        set_mpi_ip(r['ip'])
        send(s, {'type': 'success'})
    if r['type'] == 'master_set_success':
        logging.info(f'Master set success')
        threading.Thread(target=console_process, args=()).start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    s = socket.socket()         # 创建 socket 对象
    s.connect((host, port))
    logging.info(f'Connected from {host, port}')
    send(s, {'type': 'master_connect'})
    while True:
        r = recv(s)
        process_daemon_process(r, s)
