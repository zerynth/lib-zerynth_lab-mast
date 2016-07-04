import streams
import threading
import socket as ssock


_ser = None
_thr = None
_cmd = None
_rst = None
_cmdmode = True
_associated = 0
_lockans = threading.Lock()
_lockcmd = threading.Lock()
_locksock = threading.Lock()
_lockser = threading.Lock()


def _find_sock(ch):
    for i in range(8):
        sk = _sockets[i]
        if sk is not None and sk.channel==ch:
            return sk
    return None


def _handle_wind():
    global _associated,_sockets,_cmdmode
    #print("reading line+")
    line = _ser.readline()
    if line=="\r\n":
        #print("reading line++")
        line=""
        while True:
            if _ser.available():
                line+=_ser.read(1)
                #print("#",line)
                if line.endswith("\n"):
                    break
            else:
                sleep(100)
        #line = _ser.readline()
        #print("handling wind",line)
        pp0 = line.find(":")
        pp1 = line.find(":",pp0+1)
        if pp0>0 and pp1>0:
            wcode = int(line[pp0+1:pp1])
        else:
            return
        if wcode==24:
            _associated=1
        elif wcode>=75 and wcode<=77:
            _associated=-1
        elif wcode==58:
            skn = int(line[23:-2])
            _locksock.acquire()
            sk = _find_sock(skn)
            if sk is not None:
                _sockets[sk.idx]=None
                sk.has_data.set() # unblock recvs
                sk.closed=True
            _locksock.release()
        elif wcode==55: #pending data
            skn = int(line[22:23])
            lnn = int(line[24:-2])
            _locksock.acquire()
            sk = _find_sock(skn)
            if sk is not None:
                sk.qb=lnn
                sk.has_data.set()
                #print("socket data set")
            _locksock.release()
        elif wcode==61:
            #incoming socket
            _sockin.addr=line[32:-2]
        elif wcode==60:
            #incoming socket
            _cmdmode=False
            #print("data mode!")
            while _ser.available():
                thing = _ser.read(_ser.available())
                #print("##",thing)
                _sockin.incoming.extend(thing)
                _sockin.has_data.set()
            #print("BACK")
            _ser.write("at+s.")
        elif wcode==59:
            #incoming socket
            _cmdmode=True
        elif wcode==62:
            #incoming socket gone
            _sockin.addr=None
            pass


def _wait_ready():
    while True:
        #print("reading line+++")
        line = _ser.readline()
        #print(line)
        if ":32:" in line or ":0:" in line:
            break


def _readloop():
    global _cmd
    _wait_ready()
    while True:
        try:
            _lockcmd.acquire()
            if _cmd:
                for x in _cmd[0]:
                    _ser.write(x)
                while _ser.available():
                    _handle_wind()
                _ser.write("\r")
                if _cmd[1] is not None: #send data if present
                    _ser.write(_cmd[1])
                res = []
                flag = False
                while True:
                    #print("reading line+++++")
                    line = _ser.readline()
                    #print("##",line)
                    res.append(line)
                    if line.startswith("OK\r"):
                        flag=True
                        break
                    elif line.startswith("ERROR:"):
                        flag=False
                        break
                    elif line.startswith("+WIND:2:"):
                        pinMode(_rst,OUTPUT)
                        digitalWrite(_rst,0)
                        sleep(6)
                        digitalWrite(_rst,1)
                        _wait_ready()
                        flag=True
                        break
                _cmd[2].append(flag)
                _cmd[2].append(res)
                _cmd = False
                _lockans.release()
            else:
                while _ser.available():
                    _handle_wind()

            _lockcmd.release()
            sleep(100)
        except Exception as e:
            print("----->",e)
            sleep(1000)

def _check(cmd,*query,data=None):
    flag,res = _command(cmd,*query,data=data)
    #print("_check_",flag)
    if not flag:
        raise IOError
    return res

def _command(cmd,*query,data=None):
    global _cmd
    _lockser.acquire()
    _lockcmd.acquire()
    _cmd=[cmd]
    rcmd=[]
    if query:
        _cmd.append("=")
        _cmd.extend(query)
    _cmd = [_cmd,data,rcmd]
    _lockcmd.release()
    _lockans.acquire()
    _lockser.release()
    flag, res = rcmd
    #print("command",cmd,"=",query,flag,res)
    #for y in res:
    #    print("-->",y)
    return flag,res

def set_baud(rst,ser,baud=115200,tobaud=9600):
    pinMode(rst,OUTPUT)
    digitalWrite(rst,0)
    sleep(6)
    s = streams.serial(ser,baud=baud,set_default=False)
    digitalWrite(rst,1)
    cnt=0
    while cnt<10:
        if not s.available():
            cnt+=1
            sleep(100)
            continue
        line = s.readline()
        #print("@",line)
        if ":32:" in line or ":0:" in line:
            break
    s.write("AT+S.SCFG=console1_speed,"+str(tobaud)+"\r")
    sleep(3000)
    s.write("AT&W\r")
    sleep(3000)
    s.write("AT+CFUN=0\r")
    sleep(3000)
    s.close()


def init(rst,ser,baud=9600):
    global _ser,_rst
    _lockans.acquire()
    _rst=rst
    pinMode(rst,OUTPUT)
    digitalWrite(rst,0)
    sleep(6)
    _ser = streams.serial(ser,baud=baud,set_default=False)
    _thr = thread(_readloop)
    digitalWrite(rst,1)
    __builtins__.__default_net["wifi"] = __module__
    __builtins__.__default_net["sock"][0] = __module__ #AF_INET


def _get_cfg(var):
    res = _check("AT+S.GCFG",var)
    pq = res[-3].find("=")
    return res[-3][pq+2:-2]

def _get_sts(var):
    res = _check("AT+S.STS",var)
    pq = res[-3].find("=")
    return res[-3][pq+2:-2]


def link(ssid,sec,password):
    global _associated
    _sec=(0,1,2,2)
    _check("AT+S.SSIDTXT",ssid)
    _check("AT+S.SCFG","wifi_ssid_len,",str(len(ssid)))
    _check("AT+S.SCFG","wifi_priv_mode,",str(_sec[sec]))
    #if sec!=0:
    #    _check("AT+S.SCFG","wifi_wpa_psk_text,",password)
    _check("AT+S.SCFG","wifi_mode,1")
    _check("AT+S.SCFG","ip_use_httpd,0")
    _check("AT&W")
    _associated = 0
    _check("AT+CFUN","1")
    cnt=0
    while _associated==0:
        #print("Checking association",_associated)
        sleep(1000)
        if is_linked():
            #print("Checking is_linked ok")
            _associated=1
            return True
        cnt+=1
        if cnt>=30:
            raise IOError
        #print("Checking is_linked cnt",cnt)
    if _associated<0:
        raise IOError
    return True

def is_linked():
    #print("Checking is_linked")
    return _get_sts("wifi_state")=="10"

def unlink():
    global _associated
    _check("AT+S.SCFG","wifi_mode,0")
    _check("AT&W")
    _associated=0
    _check("AT+CFUN","1")

def link_info():
    ip = _get_sts("ip_ipaddr")
    nm = _get_sts("ip_netmask")
    gw = _get_sts("ip_gw")
    dns = _get_sts("ip_dns")
    mac = _get_cfg("nv_wifi_macaddr")
    mcf = mac.split(":")
    mac = bytearray(6)
    for i in range(6):
        mac[i]=int(mcf[i],16)
    return (ip,nm,gw,dns,mac)

####SOCKETS

# an entry in the _sockets vector
class _sockdata():
    def __init__(self,proto,idx):
        self.proto = proto
        self.has_data = threading.Event()
        self.qb=0
        self.channel=None
        self.idx = idx
        self.closed=False
        self.buffer=bytearray()

_sockets = [None]*8  # 8 sockets max
_sockin = None

def socket(family,type,proto):
    global _sockets
    _locksock.acquire()
    res = None
    for i,sock in enumerate(_sockets):
        if sock is None:
            if type==ssock.SOCK_DGRAM:
                proto = ssock.IPPROTO_UDP
            else:
                proto = ssock.IPPROTO_TCP
            _sockets[i]=_sockdata(proto,i)
            res = i
            break
    _locksock.release()
    if res is not None:
        return res
    raise IOError

# def setsockopt(sock,level,optname,value):
#     pass


def close(sock):
    global _sockets
    _locksock.acquire()
    ss = _sockets[sock]
    if ss:
        ss.has_data.set() #wake up blocked recv
        _sockets[sock]=None
    _locksock.release()
    if ss.channel is not None:
        _command("AT+S.SOCKC",str(ss.channel))

def sendto(sock,buf,addr,flags=0):
    _locksock.acquire()
    ss = _sockets[sock]
    _locksock.release()
    if ss is None or ss.channel is None or ss.closed:
        raise IOError


def _send(sock,buf):
    _locksock.acquire()
    ss = _sockets[sock]
    _locksock.release()

    if ss is None or ss.channel is None or ss.closed:
        raise IOError

    _check("AT+S.SOCKW",str(ss.channel),",",str(len(buf)),data=buf)

def send(sock,buf,flags=0):
    tosend = len(buf)
    sent = 0
    while sent<tosend:
        tsnd = min(4096,tosend-sent)  #max is 4096
        _send(sock,buf[sent:sent+tsnd])
        sent+=tsnd
    return sent



def sendall(sock,buf,flags=0):
     return send(sock,buf,flags)


# def recv_into(sock,buf,bufsize,flags=0,ofs=0):
#     rr = 0
#     _locksock.acquire()
#     sk = _sockets[sock]
#     _locksock.release()
#     if sk is None or sk.channel is None:
#         raise IOError

#     while rr<bufsize:
#         print("recv checking tbr")
#         tbr = _check("AT+S.SOCKQ",str(sk.channel))
#         tbr = int(tbr[-3][9:-2])
#         print("recv checking tbr",tbr)

#         toread = min(tbr,bufsize-rr)
#         _locksock.acquire()
#         if sk.qb<=0:
#             sk.has_data.clear()
#         else:
#             sk.qb-=toread
#         if sk.closed:
#             toread=-1
#         _locksock.release()
#         print("recv toread",toread)

#         if toread==0:
#             sk.has_data.wait()
#         elif toread<0:
#             #closed
#             return rr

#         print("recv reading",toread)
#         while toread>0:
#             tr = min(toread,1024)
#             toread-=tr
#             print("recv getting",tr)
#             res = _check("AT+S.SOCKR",str(sk.channel),",",str(tr))
#             for x in range(len(res)-1):
#                 for y in range(len(res[x])):
#                     tr-=1
#                     if tr<0:
#                         break
#                     buf[ofs+rr]=__byte_get(res[x],y)
#                     rr+=1
#     return rr

def _empty_q(sk):
    #print("recv checking tbr")
    tbr = _check("AT+S.SOCKQ",str(sk.channel))
    tbr = int(tbr[-3][9:-2])
    #print("recv checking tbr",tbr)
    if tbr<=0:
        return
    tmp = bytearray(tbr)
    res = _check("AT+S.SOCKR",str(sk.channel),",",str(tbr))
    tt = 0
    for x in range(len(res)-1):
        for y in range(len(res[x])):
            tbr-=1
            if tbr<0:
                break
            tmp[tt]=__byte_get(res[x],y)
            tt+=1
    return tmp

def recv_into(sock,buf,bufsize,flags=0,ofs=0):
    rr = 0
    tbr=1
    _locksock.acquire()
    sk = _sockets[sock]
    _locksock.release()
    if sk is None or sk.channel is None:
        raise IOError

    while rr<bufsize:
        if tbr<=0:
            #print("tbring")
            tmp = _empty_q(sk)
        else:
            #print("not tbring")
            tmp = None
        _locksock.acquire()
        if tmp is not None:
            sk.buffer.extend(tmp)
            sk.qb-=len(tmp)
            tmp=None
        #print("qb",sk.qb)
        if sk.qb<=0:
            sk.has_data.clear()
        tbr=len(sk.buffer)
        #print("eqq",tbr)
        toread = min(tbr,bufsize-rr)
        if sk.closed:
            toread=-1
        _locksock.release()
        #print("recv toread",toread)

        if toread==0:
            sk.has_data.wait()
        if toread<0:
            #closed
            return rr

        #print("recv reading",toread,tbr)
        _locksock.acquire()
        buf[ofs+rr:ofs+rr+toread]=sk.buffer[0:toread]
        sk.buffer=sk.buffer[toread:]
        rr+=toread
        _locksock.release()
        #print("recv read",toread,tbr)
    return rr


# def recvfrom_into(sock,buf,bufsize,flags=0):
#     pass


def bind(sock,addr):
    global _sockin
    if _sockin is not None:
        raise IOError
    _locksock.acquire()
    sk = _sockets[sock]
    _sockin = sk
    sk.incoming=bytearray()
    sk.addr=None
    _locksock.release()

    res = _check("AT+S.SOCKD",str(addr[1]),",","u" if
sk.proto==ssock.IPPROTO_UDP else "t")

# def listen(sock,maxlog=2):
#     pass

# def accept(sock):
#     pass

def connect(sock,addr):
    _locksock.acquire()
    ss = _sockets[sock]
    if ss.proto == ssock.IPPROTO_TCP:
        proto = "t"
    elif ss.proto == ssock.IPPROTO_UDP:
        proto = "u"
    _locksock.release()
    res=_check("AT+S.SOCKON",addr[0],",",str(addr[1]),",",proto,",ind")
    rsp = res[-3]
    ss.channel = int(rsp[6:-2])


def gethostbyname(hostname):
    res=_check("AT+S.PING",hostname)
    return res[-3][14:-2]


# def select(rlist,wist,xlist,timeout):
#     pass
