# CRIU Live Migration for MPI Process

## 文件结构

- `server.py`：服务端守护进程
- `slave.py`：子节点守护进程
- `console.py`：控制台
- `utils.py`：工具函数
- `00-installer-config.yaml`：网卡配置文件模板


## 配置要求

所有节点都有两张网卡，分别在两个不同子网内

所有节点都安装好criu，需要使用源码编译最新版本（3.18）

一个子网用于本工具控制（对应`00-installer-config.yaml`中的`ens3`），另一个子网用于运行 MPI 进程（对应`00-installer-config.yaml`中的`ens8`）。（这样设计的原因是，CRIU的迁移具有局限性，跨节点迁移建立 TCP 连接的进程需要保证迁移前后节点建立连接的 IP 地址保持不变，因此需要在迁移时动态修改 IP）

所有节点都建立好 ssh 免密登录

所有节点需要配置好控制子网的 IP 地址，且保持不变

运行 MPI 进程时，所有节点的可执行文件和所有进程打开的文件都在同一路径下

## 运行

将本项目所有文件复制到所有节点的同一目录下

确定 MPI 子网的网段，在本例中为 `192.168.100.0/24`，修改 `server.py` 中的  `MPI_IP_PREFIX` 
修改 `server.py` 中的  `MPI_INTERFACE` 为 MPI 子网所用的网卡 

在主节点运行 `python server.py`

修改 `slave.py` 和 `console.py` 中的 `host` 和 `port` 至主节点地址和监听端口

在每个节点运行 `python slave.py <real_ip_addres>`，其中 `<real_ip_address>` 为该节点的控制子网所在网卡的 IP 地址，运行之后，该节点会被分配一个 MPI 子网的 IP 地址

在任意一个节点运行 `python console.py`，可以在里面发出指令。

## 指令

指令使用 JSON 格式。暂时只支持两个指令：`run` 和 `migrate`

#### run 指令

格式：

```json
{"type": "run", "slaves" : ["192.168.122.11", "192.168.122.12"], "command" : "bash /root/workspace/test.sh"}
```

`slaves` 参数为运行节点的 IP 地址列表，注意是控制子网的 IP 地址。

`command` 参数为 MPI 指令。

运行后，可在 server 窗口下查看运行情况。

#### migrate 指令

```json
{"type": "migrate", "source" : "192.168.122.12", "dest": "192.168.122.13"}
```
`source` 参数为迁出节点，`dest` 参数为迁入节点。需要保证迁出节点正在运行 MPI 进程而迁入节点没有。

## 外部接口

控制台的本质是将 json 指令传输到服务端，因此也可以在外部工具中和服务端建立 TCP 连接传递指令。

## 目前存在问题

服务端所在节点上运行的 MPI 进程无法被迁移，正在寻找解决方式，但不影响使用。