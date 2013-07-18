xbian-package-upstart-ipconnection-bridge
=================================

bridge between ip connection in and upstart
    
upstart event :
---------------
    will check on low level network and send event if
    IP connection is received
	Event :
	ipconnectionin
	     receive when a new connection is received (not same protocol and not same dest port)
	     ENV :
	           PORT :  dest port
	           SOURCE : Source address
	           PROTOCOL : Protocol used (according to this : http://en.wikipedia.org/wiki/List_of_IP_protocol_numbers)
	ipconnectionto:
	     ipconnection Timeout : will be emit 60 sec after last paquet received for specific connection
	     ENV :
	           PORT : dest PORT
	           SOURCE : SOurce address
	           PROTOCOL : Protocol used (according to this : http://en.wikipedia.org/wiki/List_of_IP_protocol_numbers)
