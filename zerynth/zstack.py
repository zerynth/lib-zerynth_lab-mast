import socket
import json
import threading
import streams
import queue
import timers

class Device():
    def __init__(self,uid,addr,port,methods={}):
        self.uid = uid
        self._sock = None
        self._rth = None
        self._hth = None
        self._wth = None
        #self._wlck = threading.Lock()
        self.logged = False
        self.reconnecting = False
        self.wq = queue.Queue(maxsize=2)
        self.addr = addr
        self.port = port
        self.methods=methods

    def _getmsg(self):
        print(timers.now(),"Getting message")
        line = self._client.readline()
        print(timers.now(),"Got message",line)
        if not line:
            raise IOError
        msg = json.loads(line)
        print(msg)
        return msg

    def _closeall(self):
        try:
            self._sock.close()
        except:
            pass
    
    def login(self):
        print("Trying to login as",self.uid)
        self._sock = socket.socket()
        #self._sock.setsockopt(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
        #self._sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_KEEPIDLE,20000)
        #self._sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_KEEPINTVL,5)
        #self._sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_KEEPCNT,3)
        self._client = streams.SocketStream(self._sock)
        try:
            self._sock.connect((self.addr,self.port))
        except:
            print("Can't connect")
            self._closeall()
            return False
        try:
            self._send({"uid":self.uid})
            msg = self._getmsg()
            if "err" in msg:
                print("oops, error")
                self._closeall()
                return False
        except:
            print("Login exception")
            self._closeall()
            return False
        return True

    def _readloop(self):
        while True:
            while self.reconnecting:
                sleep(1000)
            try:
                msg = self._getmsg()
                if "cmd" in msg and msg["cmd"]=="CALL" and "method" in msg and msg["method"] in self.methods and "id" in msg:
                    if "args" in msg:
                        args=msg["args"]
                    else:
                        args=[]
                    try:
                        print(timers.now(),"calling",msg["method"])
                        res = self.methods[msg["method"]](*args)
                        print(timers.now(),"called",msg["method"])
                    except Exception as e:
                        self.send({"cmd":"RETN","id":msg["id"],"error":str(e)})
                    else:
                        self.send({"cmd":"RETN","id":msg["id"],"result":res})
                    res=None
            except:
                print("Exception in readloop")
                self._reconnect()

    def _reconnect(self):
        if self.reconnecting:
            return
        self.reconnecting=True
        if self.logged:
            self._closeall()
            self.logged = False
        self.start()

    def _send(self,msg):
        try:
            bb = json.dumps(msg)
            print(timers.now(),"raw",bb)
            self._client.write(bb)
            self._client.write("\n")
        except Exception as e:
            print("Exception in send",e,msg)

    def send(self,msg):
        self.wq.put(msg,False,1000)

    def _htbm(self):
        while True:
            while self.reconnecting:
                sleep(1000)
            sleep(60000)
            try:
                self.send({"cmd":"HTBM"})
            except:
                print("Exception in htbm")
                self._reconnect()

    def _writeloop(self):
        while True:
            while self.reconnecting:
                sleep(1000)
            try:
                msg = self.wq.get()
                self._send(msg)
            except Exception as e:
                print("Exception in writeloop",e)
                self._reconnect()


    def start(self):
        while not self.logged:
            self.logged = self.login()
            sleep(5000)
        if self._rth is None:
            self._rth = thread(self._readloop)
        if self._hth is None:
            self._hth = thread(self._htbm)
        if self._wth is None:
            self._wth = thread(self._writeloop)
        self.reconnecting=False
