import socket
import sys
from struct import *
from threading import Thread, Event, Timer
import subprocess
import logging

TIMEOUT = 60
LOCALIP = ('192','138','127')
ONLYLOCAL = True
CHECK_TCP = True
CHECK_UDP = True
CHECK_OTHERS = False

ETH_P_IP = 0x800

#Timer Code is from http://code.activestate.com/recipes/577407-resettable-timer-class-a-little-enhancement-from-p/
def TimerReset(*args, **kwargs):
    """ Global function for Timer """
    return _TimerReset(*args, **kwargs)


class _TimerReset(Thread):
    """Call a function after a specified number of seconds:

    t = TimerReset(30.0, f, args=[], kwargs={})
    t.start()
    t.cancel() # stop the timer's action if it's still waiting
    """

    def __init__(self, interval, function, args=[], kwargs={}):
        Thread.__init__(self)
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.finished = Event()
        self.resetted = True

    def cancel(self):
        """Stop the timer if it hasn't finished yet"""
        self.finished.set()

    def run(self):        
        while self.resetted:            
            self.resetted = False
            self.finished.wait(self.interval)

        if not self.finished.isSet():
            self.function(*self.args, **self.kwargs)
        self.finished.set()        

    def reset(self, interval=None):
        """ Reset the timer """

        if interval:            
            self.interval = interval        
        self.resetted = True
        self.finished.set()
        self.finished.clear()


class connection :
    eth_length = 14    
    def __init__(self,data) :
        self.data = data
        self.source_ip = None
        self.dest_ip = None
        self.source_port = None
        self.dest_port = None
        self.ethprotocol = None
        self.ipprotocol = None
        self.isactive = False
        self.timer = TimerReset(TIMEOUT, self.onTimer)
        self.parseHeader()      
    
    def __eq__(self,other) :
        return self.ipprotocol == other.ipprotocol and self.dest_port == other.dest_port
    
    def startTimer(self,cb,*args) :        
        self.cb = cb
        self.cbargs = args
        self.timer.start()
    
    def resetTimer(self) :
        self.timer.reset()
            
    def onTimer(self):
        self.cb(*self.cbargs)
        self.isactive = False
    
    def isActive(self) :
        return self.isactive
        
    def parseHeader(self) :             
        self.parseEthHeader()
        if self.ethprotocol == 8 : #IP
            self.parseIpHeader()
            if not ONLYLOCAL or (self.source_ip[:3] in LOCALIP and self.dest_ip[:3] in LOCALIP) :                
                if CHECK_TCP and self.ipprotocol == 6 : #TCP
                    self.parseTcpHeader()
                    self.isactive = True
                elif CHECK_UDP and self.ipprotocol == 17 : #UDP
                    self.parseUdpHeader()
                    self.isactive = True
                elif CHECK_OTHERS:
					self.isactive = True
					
                
                    
    def parseEthHeader(self) :      
        eth_header = self.data[:self.eth_length]
        eth = unpack('!6s6sH' , eth_header)
        self.ethprotocol = socket.ntohs(eth[2])
    
    def parseIpHeader(self) :
        #Parse IP header             
        #take first 20 characters for the ip header
        ip_header = self.data[self.eth_length:20+self.eth_length]                
        #now unpack them :)
        iph = unpack('!BBHHHBBH4s4s' , ip_header)
        version_ihl = iph[0]
        version = version_ihl >> 4
        ihl = version_ihl & 0xF
        self.iph_length = ihl * 4
        ttl = iph[5]
        self.ipprotocol = iph[6]
        self.source_ip = socket.inet_ntoa(iph[8]);
        self.dest_ip = socket.inet_ntoa(iph[9]);
    
    def parseTcpHeader(self) :
        t = self.iph_length + self.eth_length
        tcp_header = self.data[t:t+20]
        tcph = unpack('!HHLLBBHHH' , tcp_header)                        
        self.source_port = tcph[0]
        self.dest_port = tcph[1]
    
    def parseUdpHeader(self) :
        u = self.iph_length + self.eth_length
        udph_length = 8
        udp_header = self.data[u:u+8]                       
        udph = unpack('!HHHH' , udp_header)                     
        self.source_port = udph[0]
        self.dest_port = udph[1]
                        
class upstart_ipconnect_bridge :
	#will check on low level network and send event if
	#IP connection is received
	#Event :
	#ipconnectionin
	           #receive when a new connection is received (not same dest addr and not same dest port)
	           #ENV :
	           #PORT : RECEIVING PORT
	           #SOURCE : SOurce address
	           #PROTOCOL : Protocol used (according to this : http://en.wikipedia.org/wiki/List_of_IP_protocol_numbers)
	#ipconnectionto:
	           #ipconnection Timeout : will be emit 60 sec after last connection received for specific connection
			   #ENV :
	           #PORT : RECEIVING PORT
	           #SOURCE : SOurce address
	           #PROTOCOL : Protocol used (according to this : http://en.wikipedia.org/wiki/List_of_IP_protocol_numbers)
    def __init__(self) :
		#start logguer
        logging.basicConfig(filename='/var/log/upstart-ipconnection.log',level=logging.INFO,format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
        logging.info('upstart_ipconnect_bridge started')
        self.stopped = False
        self.sock = None
        self.connections = []
    
    def emit_event(self,event,data=None) :
        cmd = ['initctl','emit',event]
        if data :     
            try :
                for event in data :
                    for key, value in event.items() :
                        cmd.append('%s=%s'%(str(key),str(value)))
            except Exception, e:
                logging.error('Cannot parse data %s : %s'%(str(data),e))
        try :
            subprocess.check_call(cmd)
            logging.info('Send event: %s'%str(cmd))
            print 'send event %s'%str(cmd)
        except Exception, e:
            logging.error('Cannot send event %s : %s'%(str(cmd),e))

    def _createSocket(self) :
        #create a AF_PACKET type raw socket (thats basically packet level)        
        try:
            self.sock = socket.socket( socket.AF_PACKET , socket.SOCK_RAW , socket.ntohs((ETH_P_IP)))
        except socket.error, msg:
            logging.error('Socket could not be created. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            sys.exit()
             
    def monitorConnection(self) :
         self._createSocket()
         while not self.stopped :            
            # receive a packet
            header = self.sock.recvfrom(64)[0]  
            tmp_conn = connection(header)                         
            if tmp_conn.isActive() :
                new_conn = True
                for con in self.connections :
                    if tmp_conn == con :
                        new_conn = False
                        con.resetTimer()
                if new_conn :
                    logging.debug('New Incomming Connection : SOURCE : %s- PORT : %d - PROTOCOL : %d'%(tmp_conn.source_ip,tmp_conn.dest_port,tmp_conn.ipprotocol))
                    self.connections.append(tmp_conn)
                    self.emit_event('ipconnectionin',[{'PORT' : tmp_conn.dest_port},{'SOURCE' : tmp_conn.source_ip},{'PROTOCOL' : tmp_conn.ipprotocol}])
                    tmp_conn.startTimer(self.onConnectionClose,tmp_conn)
                    
    
    def onConnectionClose(self,conn) :
         self.connections.remove(conn)      
         logging.debug('Connection Time out : SOURCE : %s- PORT : %d - PROTOCOL : %d'%(conn.source_ip,conn.dest_port,conn.ipprotocol))
         self.emit_event('ipconnectionto',[{'PORT' : conn.dest_port},{'SOURCE' : conn.source_ip},{'PROTOCOL' : conn.ipprotocol}])
         #print 

##################### main ################
main = upstart_ipconnect_bridge()
main.monitorConnection()
