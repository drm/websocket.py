import http.server
import socketserver
import threading
from websocket import BaseWebSocketHandler

class MyWebSocketServer(socketserver.ThreadingTCPServer):
    pass
            
class MyWebSocketHandler(BaseWebSocketHandler):
    def on_message(self, msg):
        print("Got message '", msg, "'", sep="")
        if msg == "CLOSEME":
            print("Client requested connection to close")
            return False
        else:
            self.write_message("pong")
            print("Writing message 'pong'")
            return True


settings = {
    'address': '127.0.0.1',
    'port': 8888
}
        
if __name__ == "__main__":
    
    server = MyWebSocketServer(
        (settings["address"], settings["port"]), 
        MyWebSocketHandler
    );
    print("Listening on %(address)s:%(port)s" % settings)
    try:
        server.serve_forever()
    finally:
        server.shutdown()
