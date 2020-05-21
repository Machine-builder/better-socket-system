# The work of MACHINE_BUILDER
# DO NOT CLAIM AS YOUR OWN

import socket, sys
from socket import error as sockerror
import pickle
import select
import errno

def getLocalIP():
    s = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
    s.connect( ('8.8.8.8', 80), )
    ip = s.getsockname()[0]
    s.close()
    return ip

class UTIL():
    @staticmethod
    def is_pickled_object(data):
        '''tests if 'data' is a pickled object. if it is, returns the unpickled object, otherwise returns None'''
        try: return pickle.loads(data)
        except: return None
    @staticmethod
    def is_json_object(data):
        '''tests if 'data' is a stringified json object. if it is, returns the loaded json object, otherwise returns None'''
        try: return json.loads(data)
        except: return None
    @staticmethod
    def dump_pickle_object(obj):
        '''dumps an object using the pickle library. returns the data'''
        return pickle.dumps(obj)

class SOCKETBASE():
    '''The base class for both the SERVER and CLIENT sockets'''
    def __init__(self, conn):
        self.conn = conn
    
    def recv(self, buffersize = 512):
        '''recieves a payload of the provided buffersize'''
        return self.conn.recv( buffersize )

    def confirm_is_bytes(self, data=b''):
        '''checks if data is bytes, if it is not, convert it into a bytes-like object'''
        if type(data) != bytes:
            data = str( data ).encode()
        return data

    def is_int(self, n = 0):
        '''checks if 'n' is an integer. If it is, returns int(n), else, returns None'''
        try:
            return int(n)
        except:
            return None

    def send(self, data = b''):
        '''sends byte data'''
        data = self.confirm_is_bytes(data)
        self.conn.send(data)

    def sendto(self, data = b'', client = None):
        '''sends byte data to a specific connection'''
        data = self.confirm_is_bytes(data)
        client.send( data )

    def recvfrom(self, buffersize = 34, client = None):
        '''receives a buffer of size 'buffersize' from specified client'''
        if not client: client = self.conn
        return client.recv( buffersize )
    
    def sendall(self, data = b''):
        '''sends byte data to all connected clients'''
        data = self.confirm_is_bytes(data)
        self.conn.send( data )

    def any_type_join(self,l=[],j='-'):
        return str(j).join( list([str(x) for x in l]) )

    
    def generate_header(self, data = b'', headersize = 16):
        '''generates a header'''
        data = self.confirm_is_bytes(data)
        buffersize = len(data)
        return str( buffersize ).rjust(headersize, '0').encode()

    def headersend(self, data = b'', sending_socket = None, headersize = 16):
        '''uses a smart system to send data, using headers'''
        if not sending_socket: sending_socket = self
        try:
            data = self.confirm_is_bytes(data)
            final_msg = self.generate_header(data, headersize) + data
            sending_socket.send( final_msg )
            return True
        except:
            return False

    def headerrecv(self, recv_socket = None, headersize = 16):
        '''uses a smart system to receive data, using headers'''
        if not recv_socket: recv_socket = self
        headerbuffer = headersize
        d = recv_socket.recv( headerbuffer )
        header = int( d.decode() )
        message = recv_socket.recv( header )
        return message

    def headerrecv_sep(self, recv_socket = None, headersize = 16):
        '''uses a smart system to receive data, using headers'''
        if not recv_socket: recv_socket = self
        headerbuffer = headersize
        header_data = recv_socket.recv( headerbuffer )
        header = int( header_data.decode() )
        message = recv_socket.recv( header )
        return (header_data, message)

    def header_send_object(self, data = {}, sending_socket = None, headersize = 16):
        '''uses a smart header system, and sends a python object, using pickle'''
        pickled = UTIL.dump_pickle_object( data )
        return self.headersend( pickled, sending_socket, headersize )

    hrecv = headerrecv
    hsend = headersend
    hrecv_s = headerrecv_sep
    hsend_o = header_send_object


class SERVER(SOCKETBASE):
    '''A class used to handle socket connections.
    
    this is the server.'''
    def __init__(self, bind_to = (), store_clients = True):
        if isinstance( bind_to, int ):
            bind_to = ( getLocalIP(), bind_to )
        self.addr = bind_to
        self.conn = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        self.conn.bind( self.addr, )
        self.store_clients = store_clients

        if self.store_clients:
            self.clients = []
            self.last_checked_client_addresses = []

        SOCKETBASE.__init__( self, self.conn )

    def listen(self, backlog = 1):
        '''listens for incoming connections, backlog argument is the backlog for the socket listen call'''
        # self.conn.listen( backlog )
        self.conn.listen( 1 )

    def accept(self):
        '''accepts one incoming connection, and saves the (conn, addr) into the clients list, also returns (conn, addr)'''
        conn, addr = self.conn.accept()
        if self.store_clients:
            self.clients.append( (conn,addr), )
        return (conn, addr)

    def get_new_clients(self):
        '''gets a list of the new clients connected since this function was last run'''
        if self.store_clients:
            new_clients = list([ x for x in self.clients if not self.any_type_join( x[1] ) in self.last_checked_client_addresses ])
            self.last_checked_client_addresses.extend( list([ self.any_type_join( x[1] ) for x in new_clients ]) )
            return new_clients
        raise Exception('get_new_clients() cannot be run unless server.store_clients was set to True during init function')



class CLIENT(SOCKETBASE):
    '''A class used to handle socket connections.
    
    this is the client.'''
    def __init__(self):
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        SOCKETBASE.__init__(self, self.conn)

    def connect(self, addr):
        self.conn.connect( addr, )
        self.connected = True

class ServerClientSystemCLIENT(CLIENT):
    '''A class used to handle socket connections.
    
    this is the client - specifically designed to be used with the ServerClientSystem() as a server'''
    def __init__(self):
        CLIENT.__init__(self)

    def connect(self, addr):
        self.conn.connect(addr,)
        self.connected = True
        self.conn.setblocking(False)

    def get_new_messages(self, display_general_errors = False, raise_reading_errors = False):
        '''Gets all new messages from server.
        returns new_messages, connection_open
        new_messages is a list of ServerClientSystemMessage() objects,
        and connection_open is a boolean indicating whether the connection
        is still open or not.'''
        new_messages = []
        connection_open = True
        try:
            while True:
                message = self.hrecv()
                if not len(message):
                    print("No message")
                    connection_open = False
                    return (new_messages, connection_open)
                
                new_messages.append(
                    ServerClientSystemMessage( message )
                )
        
        except IOError as e:
            if raise_reading_errors:
                if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                    raise f"Reading error {str(e)}"
        
        except Exception as e:
            if display_general_errors:
                print(f"General error {str(e)}")

        return (new_messages, connection_open)


class ServerClientSystem():
    '''A class used to handle an entire network of clients
    
    args:

     * server: a connections.SERVER class instance. Used as the main server
    
     * listen_count: how many incoming connections to queue. (default=5)

     '''
    def __init__(self, server = None, **kwargs):
        self.server = server
        self.server.listen( kwargs.get("listen_count", 5) )
        self.socketlist = [self.server.conn]
        self.clients = {}

    def receive_message(self, client_socket):
        try:
            message = self.server.hrecv_s( client_socket )
            if not message: return False
            return {'header': message[0], 'data': message[1]}
        except:
            return False

    def main(self):
        '''Runs the main loop.
        returns
          new_clients > list,
          new_messages > list,
          disconnected_clients > list
        new_clients is in the following form:
        [
            (conn, addr),
            ...
        ]
        disconnected_clients is in the following form:
        [
            (conn, addr),
            ...
        ]
        new_messages is in the following form:
        [
            connections.ServerClientSystemMessage,
            ...
        ]'''
        
        read_sockets, _, exception_sockets = select.select( self.socketlist, [], self.socketlist )

        new_clients = []
        new_messages = []
        disconnected_clients = []

        for notified_socket in read_sockets:
            if notified_socket == self.server.conn:
                client_socket, client_address = self.server.accept()
                self.socketlist.append( client_socket )
                self.clients[ client_socket ] = client_address
                # accepted new connection
                new_clients.append( (client_socket, client_address), )
            
            else:
                message = self.receive_message(notified_socket)

                if message is False:
                    disconnected_clients.append( (notified_socket, self.clients[notified_socket]) )
                    self.remove_client(notified_socket)
                    continue

                actual_message = ServerClientSystemMessage( message )
                new_messages.append(actual_message)

        for notified_socket in exception_sockets:
            disconnected_clients.append( (notified_socket, self.clients[notified_socket]) )
            self.remove_client(notified_socket)

        return new_clients, new_messages, disconnected_clients

    def remove_client(self, client_socket):
        '''removes a client from the clients dict and socketlist list'''
        self.socketlist.remove(client_socket)
        del self.clients[client_socket]
    
    def send_msg_to_client(self, client, msg):
        '''sends byte data to all clients'''
        client.send( msg )
    
    def send_to_clients(self, obj):
        '''sends a python object to all clients'''
        data = UTIL.dump_pickle_object( obj )
        for client_socket in self.clients:
            header = self.server.generate_header( data )
            self.send_msg_to_client( client_socket, header+data )

class ServerClientSystemMessage():
    '''A ServerClientSystem message,
    has attributes is_pickled, header & data.
    data is the actual object of the message.'''
    def __init__(self, data):
        self.header = None
        if type(data)==dict:
            if 'data' in data:
                self.header = data['header']
                data = data['data']
        pickled = UTIL.is_pickled_object( data )
        self.is_pickled = pickled!=None
        self.data = pickled or data
        self.is_dict = type(self.data) == dict



SCS_CLIENT = ServerClientSystemCLIENT
SCS = ServerClientSystem
SCS_MESSAGE = ServerClientSystemMessage




if __name__ == '__main__':
    pass