import os
import socket 
import threading
import logging
from utils import *

host = '192.168.122.11'
port = 8889


def clear():
    pwd = os.getcwd()
    ckpt_dir = os.path.join(pwd, 'ckpt')
    try:
        os.system(f'rm -rf {ckpt_dir}*')
    except:
        pass
    tar = os.path.join(pwd, "ckpt.tar.gz")
    try:
        os.remove(tar)
    except:
        pass     
    return {'type': 'success', 'ret': 0}
def dump():
    pwd = os.getcwd()
    ckpt_dir = os.path.join(pwd, 'ckpt')
    try:
        os.system(f'rm -rf {ckpt_dir}*')
    except:
        pass
    ckpt_dir = os.path.join(pwd, 'ckpt')
    try:
        os.mkdir(ckpt_dir)
    except:
        pass
    try:
        pid = get_pid('/usr/local/bin/hydra_pmi_proxy')
        if pid < 1:
            return {'type': 'error', 'msg': 'No process hydra_pmi_proxy'}
    except:
        return {'type': 'error', 'msg': 'No process hydra_pmi_proxy'}
    ret = os.system(f'criu dump --tree {pid}  --images-dir {ckpt_dir} -v4 -o dump.log --shell-job --tcp-established')
    logging.debug(f'criu dump ret {ret}')
    tar = os.path.join(pwd, "ckpt.tar.gz")
    os.system(f'tar -zcvf {tar} {ckpt_dir}')
    return {'type': 'success', 'ret': ret, 'ckpt_dir' : ckpt_dir}

def migrate(dst: str):
    pwd = os.getcwd()
    tar = os.path.join(pwd, "ckpt.tar.gz")
    ret = os.system(f'scp {tar} root@{dst}:{pwd}')
    return {'type': 'success', 'ret': ret}

def criu_restore(ckpt_dir):
    pwd = os.getcwd()
    os.system(f'setsid criu restore --images-dir {ckpt_dir} -v4 -o rst.log --shell-job --restore-detached --tcp-established')
    return {'type': 'success', 'ret': 0}

def restore(ckpt_dir):
    pwd = os.getcwd()
    tar = os.path.join(pwd, "ckpt.tar.gz")
    os.system(f'tar -zxvf {tar} -C /')
    threading.Thread(target=criu_restore, args=(ckpt_dir,)).start()

def console_process():
    s = socket.socket()
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
    if r['type'] == 'slave_set_success':
        logging.info(f'Slave set success')
    if r['type'] == 'dump':
        logging.info('begin to dump')
        ret = dump()
        logging.info('dump finished')
        send(s, ret)
    if r['type'] == 'clear':
        logging.info('begin to clear')
        ret = clear()
        logging.info('clear finished')
        send(s, ret)
    if r['type'] == 'migrate':
        dst = r['dst']
        ret = migrate(dst)
        logging.info('migrate finished')
        send(s, ret)
    if r['type'] == 'restore':
        logging.info('begin to restore')
        ret = restore(r['ckpt_dir'])
        logging.info('restore finished')
        send(s, ret)

    


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    s = socket.socket()         # 创建 socket 对象
    s.connect((host, port))
    logging.info(f'Connected from {host, port}')
    send(s, {'type': 'slave_connect'})
    while True:
        r = recv(s)
        process_daemon_process(r, s)
