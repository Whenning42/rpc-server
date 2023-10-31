from __future__ import annotations
import copy
import select
import socket
import random
import struct


class ReadStream:
    def __init__(self, protocol: Protocol, socket):
        self.buffer = []
        self.socket = socket

    def __iter__(self):
        return self

    def __next__(self):
        # TODO: Generalize the decoder to arbitrary functions.
        self.buffer += list(self.socket.recv(1024))
        if len(self.buffer) < 16:
            raise StopIteration
        print(self.buffer)
        length, tag, x, y = struct.unpack('IIII', bytes(self.buffer[:16]))
        self.buffer = self.buffer[16:]
        return tag, (x, y)


class WriteStream:
    def __init__(self, protocol: Protocol, socket):
        self.buffer = []
        self.socket = socket

    def write(self, tag: int, args: tuple[int, int]):
        # TODO: Generalize the encoder to arbitrary functions.
        self.buffer += list(struct.pack('IIII', 16, tag, args[0], args[1]))
        self.socket.send(bytes(self.buffer))
        self.buffer = []

class Protocol:
    def __init__(self, api: list[tuple[str, callable]]):
        self.fn_table = {i: f[1] for i, f in enumerate(api)}
        self.fn_ids = {f[0]: i for i, f in enumerate(api)}


class RpcServer:
    def __init__(self):
        pass

    def _init_server(self, protocol: Protocol, address: str) -> RpcServer:
        self.serve_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.serve_socket.bind(address)
        self.serve_socket.listen(10)
        self.sockets = [self.serve_socket]
        self.protocol = protocol
        self.read_streams = {}
        return self
        
    def _init_client(self, protocol: Protocol, api, address: str) -> RpcServer:
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        print(f"Connecting to: {address}")
        self.socket.connect(address)
        self.protocol = protocol
        self.write_stream = WriteStream(self.protocol, self.socket)
        for fname, fn in api:
            # TODO: Generalize the invoker to arbitrary functions.
            def invoker(x: int, y: int):
                tag = self.protocol.fn_ids[fname]
                self.write_stream.write(tag, (x, y))
                print("Client invocation.")
            setattr(self, fname, invoker)
        return self


    @classmethod
    def _build_service(cls, side: str, address: str):
        '''side must be "server" or "client"'''
        api = [(fname, fn) for fname, fn in cls.__dict__.items() if fname[0] != '_']
        protocol = Protocol(api)
        if side == 'server':
            return RpcServer()._init_server(protocol, address)
        else:
            assert side == 'client'
            return RpcServer()._init_client(protocol, api, address)

    @classmethod
    def _serve(cls, address: str) -> None:
        s = cls._build_service(side='server', address=address)
        s._serve_impl(address)

    def _serve_impl(self, address: str) -> None:
        while True:
            for s in self.sockets:
                print(s)
            rlist, _, _ = select.select(self.sockets, [], [])
            for socket in rlist:
                # Accept connections
                if socket is self.serve_socket:
                    con, _ = socket.accept()
                    self.sockets.append(con)
                    self.read_streams[con] = ReadStream(self.protocol, con)
                # Process requests
                else:
                    print(list(self.read_streams.keys()))
                    stream = self.read_streams[socket]
                    for fn_id, fn_args in stream:
                        f = self.protocol.fn_table[fn_id]
                        print(f"fn_args: {fn_args}")
                        f(self, *fn_args)
                        print("Server invocation.")


    @classmethod
    def _client(cls, address: str) -> RpcServer:
        return cls._build_service(side='client', address=address)


class XState(RpcServer):
    def __init__(self):
        self.cursor_x = 0
        self.cursor_y = 0
        # self.register(self.set_cursor_pos)

    def set_cursor_pos(self, x: int, y: int) -> None:
        self.cursor_x = x
        self.cursor_y = y
        print(f"Set the cursor pos to {x}, {y}")

if __name__ == '__main__':
    i = random.randint(0, 10000)
    print(f"Starting server on channel: {i}")
    XState._serve(f'/tmp/server_state_{i}')
