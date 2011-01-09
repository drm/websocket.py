import socketserver
import http.server
import threading
from struct import pack
import hashlib

class BaseWebSocketServer(socketserver.ThreadingTCPServer):
    _lock = threading.Lock()
    clients = []
    is_shutdown = False
    def server_activate(self):
        self.socket.settimeout(0.1)
        print("Timeout set!")
        socketserver.ThreadingTCPServer.server_activate(self)
    
    def register_client(self, client):
        self.clients.append(client)
        
    def unregister_client(self, client):
        self.clients.remove(client)

    def broadcast(self, message):
        with self._lock:
            for client in self.clients:
                client.write_message(message)

    def shutdown(self):
        with self._lock:
            self.is_shutdown = True
            for client in self.clients:
                client.close()
        socketserver.ThreadingTCPServer.shutdown(self);

class BaseWebSocketHandler(http.server.BaseHTTPRequestHandler):
    _debugging = False
    _close_connection = False
    connected = False
    

    """A simple draft76 implementation for WebSocket servers based on Python's http server"""
    def do_GET(self):
        if self.headers['Connection'] == 'Upgrade':
            self._debug("Connection upgrade requested")

            if self.headers['Upgrade'] == 'WebSocket':
                try:
                    self._handshake()
                except ValueError:
                    self.send_error(400)
                    return
                    
                self._debug("Connection upgraded, now waiting for messages")
                self.connected = True
                self.server.register_client(self)
                print(type(self.rfile.raw))
                while not self.server.is_shutdown:
                    byte = self.rfile.read1(1)
                    
                    if byte == b'\x00':
                        msg = b''
                        while byte != b'\xff':
                            byte = self.rfile.read1(1)
                            msg += byte
                        
                        self.on_message(bytes.decode(msg[:-1]))
                    elif len(byte) == 0:
                        self._debug("Read error, connection was aborted by client")
                        self._close_connection = True
                    else:
                        self._debug("Unknown byte %s" % byte)
                        # drop byte (TODO figure out what to do here)
                        pass
                        
                    if self._close_connection:
                        break
                self.connected = False
                self.server.unregister_client(self)

            else:
                self._debug("Connection upgrade type not %s understood" % self.headers['Upgrade'])
                # Unsupported connection upgrade
                self.send_error(501)
        else:
            # Bad request
            self.send_error(400) 
            
    def close(self):
        self._close_connection = True
        pass
            
    def _handshake(self):
        """Performs the WebSocket connection upgrade handshake"""
        self._debug("Connection upgrade WebSocket, construction challenge response")
        
        key1 = self.headers['Sec-WebSocket-Key1']
        key2 = self.headers['Sec-WebSocket-Key2']
        key3 = self.rfile.read(8)
        
        if key1 == None or key2 == None:
            raise ValueError("Missing challenge keys")

        response = self._challenge_response(key1, key2, key3)
        
        self.send_response(101, "WebSocket Protocol Handshake")
        self.send_header('Connection', 'Upgrade')
        self.send_header('Upgrade', 'WebSocket')
        
        if 'Origin' in self.headers:
            self.send_header('Sec-WebSocket-Origin', self.headers['Origin'])
        if 'Sec-WebSocket-Protocol' in self.headers:
            self.send_header('Sec-WebSocket-Protocol', self.headers['Sec-WebSocket-Protocol'])

        self.send_header('Sec-WebSocket-Location', 'ws://' + self.headers['Host'] + self.path);
        self.end_headers()

        self.wfile.write(response)
        
    def _challenge_response(self, key1, key2, key3):
        """The response to a WebSocket challenge. 
        
        - key1 is the contents of the Sec-WebSocket-Key1 header
        - key1 is the contents of the Sec-WebSocket-Key2 header
        - key3 is the contents of the 8 bytes long request body"""
        def extract_number(key):
            number = ''
            spaces = 0
            for ch in key:
                if ch == " ": 
                    spaces += 1
                elif ch.isdigit(): 
                    number += ch

            number = int(number)
            if spaces > 0 and number > 0 and number % spaces == 0:
                return int(int(number) / spaces)
            raise ValueError("Invalid challenge part %s, can not extract number" % key)

        self._debug("Challenge: \n\t%s\n\t%s\n\t%s" % (key1, key2, key3))

        packed = pack('>L', extract_number(key1))
        packed += pack('>L', extract_number(key2)) 
        packed += key3
        
        response =  hashlib.md5(packed).digest()
        
        self._debug("Response: %s" % response)
        
        return response
        
    def write_message(self, message):
        self._debug("Writing message %s" % message)
        raw_data = str.encode(message)
        self.wfile.write(b'\x00')
        self.wfile.write(raw_data)
        self.wfile.write(b'\xff')
        
    def _debug(self, message):
        self._debugging and print("[DEBUG] %s" % message)

