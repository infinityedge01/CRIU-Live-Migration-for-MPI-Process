import socket
import json
import os
import sys
import time
from subprocess import check_output
def send(conn: socket.socket, data):
    rdata = json.dumps(data)
    conn.send(bytes(rdata, encoding='utf-8'))

def send_comm(conn: socket.socket, rdata):
    conn.send(bytes(rdata, encoding='utf-8'))

def get_pid(name):
    return int(check_output(["pidof","-s",name]))

def recv(conn: socket.socket):
    recv = conn.recv(1024)
    print(recv)
    rrecv = json.loads(recv)
    return rrecv

def set_mpi_ip(ip):
    f = open('00-installer-config.yaml', 'r')
    s = f.read()
    real_ip = sys.argv[1]
    s = s.replace('<real_address>', real_ip)
    s = s.replace('<mpi_address>', ip)
    f = open('/etc/netplan/00-installer-config.yaml', 'w')
    f.write(s)
    f.close()
    os.system('netplan apply')

def get_timestamp():
    return str(int(time.time() * 1000))