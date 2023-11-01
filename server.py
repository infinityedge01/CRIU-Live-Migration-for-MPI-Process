import os
import socket 
import threading
import logging
from utils import *
MPI_IP_PREFIX = '192.168.100'
MPI_INTERFACE = 'ens8'
class Node:
    def __init__(self, real_ip, mpi_ip, conn) -> None:
        self.real_ip = real_ip
        self.mpi_ip = mpi_ip
        self.conn = conn
        self.proc = None
        pass

class Server:
    def __init__(self, ) -> None:
        self.slaves = {}
        self.node_sem = threading.Semaphore()
        self.ip_set = set()
        self.ip_set_sem = threading.Semaphore()
        self.console_sem = threading.Semaphore()
        self.is_running = False
        self.running_slaves = set()
        pass
    def alloc_ip(self):
        self.ip_set_sem.acquire()
        start = 21
        while True:
            ip = MPI_IP_PREFIX + '.' + str(start)
            if ip not in self.ip_set:
                self.ip_set.add(ip)
                self.ip_set_sem.release()
                return ip
            start += 1
            if start == 255: start = 11

    def alloc_slaves(self, real_ip, node: Node):
        self.node_sem.acquire()
        self.slaves[real_ip] = node
        self.node_sem.release()


def run_mpi_process_run(server : Server, command):
    os.system(command)
    server.running_slaves.clear()
    server.is_running = False
    logging.info('MPI process finished')


def run_mpi_process(server : Server, command, slaves : list[Node]):
    if server.is_running:
        logging.error(f'MPI process is already running')
        return
    machinefile = os.path.join(os.getcwd(), 'machinefile')
    f = open(machinefile, 'w')
    slaves_ip = []
    for slave in slaves:
        f.write(slave.mpi_ip + ':1\n')
        slaves_ip.append(slave.real_ip)
    f.close()
    logging.info(f'Running slaves mpi ip {slaves_ip}')
    mpi_command = f'mpirun -n {len(slaves)} -f {machinefile} -iface {MPI_INTERFACE} {command}'
    logging.info(f'Run mpi command: {mpi_command}')
    server.is_running = True
    for slave in slaves:
        server.running_slaves.add(slave.real_ip)
    threading.Thread(target=run_mpi_process_run, args=(server, mpi_command)).start()

def process_run_mpi_process(server: Server, command: str, slaves: list[str]):
    run_slaves = []
    for x in slaves:
        slave = server.slaves.get(x)
        if slave == None:
            error_msg = f'Slave {x} is not exist'
            logging.error(error_msg)
            return {"type": "error", "note": error_msg}
        run_slaves.append(slave)
    logging.debug(f'run mpi process {command} on slave {slaves}')
    run_mpi_process(server, command, run_slaves)
    return {"type": "success"}

def process_migrate_process(server: Server, src: str, dst: str):
    if not server.is_running:
        error_msg = 'No MPI process running'
        logging.error(error_msg)
        return {"type": "error", "note": error_msg}
    if src not in server.running_slaves:
        error_msg = f'src node {src} is not in running slaves'
        logging.error(error_msg)
        return {"type": "error", "note": error_msg}
    if server.slaves.get(dst) == None:
        error_msg = f'dst node {dst} is not connected'
        logging.error(error_msg)
        return {"type": "error", "note": error_msg}
    if dst in server.running_slaves:
        error_msg = f'dst node {dst} is in running slaves'
        logging.error(error_msg)
        return {"type": "error", "note": error_msg}
    src_node = server.slaves.get(src)
    dst_node = server.slaves.get(dst)
    send(src_node.conn, {'type': 'dump'})
    succ = recv(src_node.conn)
    ckpt_dir = succ['ckpt_dir']
    logging.debug(f'src node {src} dump successfully')
    send(dst_node.conn, {'type': 'clear'})
    succ = recv(dst_node.conn)
    logging.debug(f'dst node {dst} clear successfully')
    send(src_node.conn, {'type': 'migrate', 'dst': dst})
    succ = recv(src_node.conn)
    logging.debug(f'src node {src} migrate successfully')
    tmp_mpi_ip = '192.168.100.19'
    src_mpi_ip_bak = src_node.mpi_ip
    dst_mpi_ip_bak = dst_node.mpi_ip
    send(src_node.conn, {'type' : 'set_mpi_ip', 'ip': tmp_mpi_ip})
    succ = recv(src_node.conn)
    send(dst_node.conn, {'type' : 'set_mpi_ip', 'ip': src_mpi_ip_bak})
    succ = recv(dst_node.conn)
    send(src_node.conn, {'type' : 'set_mpi_ip', 'ip': dst_mpi_ip_bak})
    succ = recv(src_node.conn)
    src_node.mpi_ip = dst_mpi_ip_bak
    dst_node.mpi_ip = src_mpi_ip_bak
    send(dst_node.conn, {'type': 'restore', 'ckpt_dir': ckpt_dir})
    succ = recv(dst_node.conn)
    server.running_slaves.remove(src)
    server.running_slaves.add(dst)
    logging.debug(f'dst node {dst} restore successfully')
    return {"type": "success"}
    

def process_console_process(server : Server, conn : socket.socket, real_ip, recv):
    server.console_sem.acquire()
    if type(recv) != dict or recv.get('type') == None:
        send(conn, {'type': 'error', 'note': 'invalid command'})
    if recv['type'] == 'run':
        ret = process_run_mpi_process(server, recv["command"], recv["slaves"])
        send(conn, ret)
    elif recv['type'] == 'migrate':
        src = recv['source']
        dst = recv['dest']
        ret = process_migrate_process(server, src, dst)
        send(conn, ret)
    else:
        send(conn, {'type': 'error', 'note': 'invalid command'})

    server.console_sem.release()

   

def process_slave(server: Server, conn : socket.socket, real_ip):
    while True:
        pass


def process_console(server: Server, conn : socket.socket, real_ip):
    while True:
        r = recv(conn)
        process_console_process(server, conn, real_ip, r)


def process_connect(server: Server, conn : socket.socket, addr_info):
    r = recv(conn)
     
    if r['type'] == 'slave_connect':
        logging.info(f'Slave node {addr_info[0]} connect')
        mpi_ip = server.alloc_ip()
        logging.info(f'Slave node {addr_info[0]} allocate ip {mpi_ip}')
        send(conn, {'type' : 'set_mpi_ip', 'ip': mpi_ip})
        succ = recv(conn)   
        slave_node = Node(addr_info[0], mpi_ip, conn)
        server.alloc_slaves(addr_info[0], slave_node)
        send(conn, {'type' : 'slave_set_success'})
        logging.info(f'Slave node {addr_info[0]} set successfully')
        process_slave(server, conn, addr_info[0])
    elif r['type'] == 'console_connect':
        logging.info(f'Console node {addr_info[0]} connect')
        process_console(server, conn, addr_info[0])
    

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    server = Server()
    sv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sv.bind(('', 8889))
    logging.debug(f'Server bind on port {8889}')
    sv.listen(5)
    try:
        while True:
            conn, addr_info = sv.accept()
            logging.info(f'Server accepted connection from {addr_info}')
            threading.Thread(target=process_connect, args=(server, conn, addr_info)).start()
    except:
        sv.close()