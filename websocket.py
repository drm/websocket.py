"""A draft76 HTML5 WebSocket server and request handler based on http.server

This code is Python3 only, but can easily be adapted for Python2.

Author: Gerard van Helden <drm@melp.nl>
More information: http://github.com/drm/websocket.py
"""

import http.server
import socket

CLOSE_FRAME = b'\xff\x00'

class ProtocolError(Exception):
    """Base class for websocket protocol errors"""
    pass

class ChallengeError(Exception):
    """This exception is raised whenever the client's challenge doesn't meet the specifications"""
    pass
    
class UnsupportedException(Exception):
    """Raised when a protocol or request header is sent by the client, that isn't supported by 
    this server"""
    pass

class BaseWebSocketHandler(http.server.BaseHTTPRequestHandler):
    """A base request handler for WebSocket requests. The handshake 
    is performed by do_GET(), and an on_message() function is called 
    every time the client sends a message. write_message() can be
    called to send a message back to the client."""

    def do_GET(self):
        "Implementation of BaseHTTPRequestHandler.do_GET, performing a Websocket handshake"
        
        if self.headers['Connection'] == 'Upgrade' and self.headers['Upgrade'] == 'WebSocket':
        
            #TODO detect incompatible clients and throw UnsupportedException
        
            self.send_response(101, 'Web Socket Protocol Handshake')
            self.send_header('Upgrade', 'WebSocket')
            self.send_header('Connection', 'Upgrade')
            self.send_header('Sec-WebSocket-Origin', self.headers['Origin'])
            self.send_header('Sec-WebSocket-Location', 'ws://localhost:8888/')
            self.send_header('Sec-WebSocket-Protocol', self.headers['Sec-WebSocket-Protocol'])
            self.end_headers()

            self.wfile.write(self._challenge());
            
            try:
                hasClosed = self.run()
                
                if hasClosed:
                    print("Client closed connection")
                else:
                    print("Closing connection")
                    self.wfile.write(CLOSE_FRAME)
            except socket.error:
                # Client disconnected, hand control back to server
                return
        else:
            # TODO, does 400 as a status code make sense? 
            self.send_error(400, "Bad request") 
            
    def _challenge(self):
        "Constructs the Websocket challenge/response key, based on draft 76"
    
        from struct import pack
        from hashlib import md5
        
        def _hash(key):
            """Counts all spaces, concatenates all numeric characters and
            returns the division of the integral value of latter by the former.
            
            Raises ChallengeError if the key contains errors"""

            spaceCount = 0;
            num = '';
            
            for i in range(0, len(key)):
                if key[i] == " ":
                    spaceCount += 1
                elif key[i].isnumeric():
                    num += key[i]
            num = int(num)
            if spaceCount == 0:
                raise ChallengeError("Number of spaces is zero")
            if num == 0:
                raise ChallengeError("Number is zero")
            if num % spaceCount != 0:
                raise ChallengeError("Number is not divisible by number of spaces")

            return pack('!I', int(int(num) / spaceCount))
        
        ret = md5()
        # add the two hashes based on the Sec-WebSocket-Key headers
        for i in ["1", "2"]:
            ret.update(_hash(self.headers['Sec-WebSocket-Key' + i]))
        # add the first 8 characters from the request body token
        ret.update(self.rfile.read(8));
        
        return ret.digest()
        
        
    def write_message(self, data): 
        """Write a delimited message block to the client"""
        self.wfile.write(b'\x00')
        self.wfile.write(data.encode())
        self.wfile.write(b'\xff')
        self.wfile.flush() #TODO is this really needed?
        
    def on_message(self, data): 
        """Called whenever a message is received from the client. Return True to close connection"""
        return True
        
    def run(self):
        """Runs while the connection is not closed. If the client requests closing connection, 
        the closing is acknowledged by replying with the closing frame. Other frame types or not
        (yet) supported
        
        The method returns True if the client was notified of closing the connection, and False
        if not"""
        while True:
            msg = b''
            start = self.rfile.read(1)
            if start == b'\x00':
                while msg[-1:] != b'\xff':
                    msg += self.rfile.read(1)
                cont = self.on_message(msg[:-1].decode())
                if not cont:
                    return False
            else: #TODO handle frame types
                # echo the message back, to acknowledge closing connection
                self.wfile.write(start) 
                return True

