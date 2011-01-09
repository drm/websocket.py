import websocket


class MyWebSocketServer(websocket.BaseWebSocketServer):
    pass
            
class MyWebSocketHandler(websocket.BaseWebSocketHandler):
    _debugging = True

    def on_message(self, msg):
        print("Got message '", msg, "'", sep="")
        if msg == "CLOSEME":
            print("Client requested connection to close")
            return False
        else:
            self.server.broadcast("pong")
            return True


bind = ('127.0.0.1', 8888)
        
if __name__ == "__main__":
    server = MyWebSocketServer(
        bind, 
        MyWebSocketHandler
    );
    print("Listening on %s:%s" % bind)
    try:
        server.serve_forever()
    finally:
        server.shutdown()
