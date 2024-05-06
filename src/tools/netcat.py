import socket
import argparse
import shlex
import subprocess
import sys
import textwrap
import threading

'''
A network client and server.
Can be used to push files, or a listener 
that gives you command line access.
'''

#  TODO  Validation, Error-Handling, Socket-Cleanup

def execute(cmd):
    cmd = cmd.strip()
    if not cmd:
        return
    output = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)
    return output.decode()


class NetCat:
    def __init__(self, arguments, input_data=None):
        self.args = arguments
        self.buffer = input_data
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        self.listen() if self.args.listen else self.send()

    def send(self):
        self.socket.connect((self.args.target, self.args.port))
        if self.buffer:
            self.socket.send(self.buffer)
        try:
            while True:
                recv_len = 1
                response = ''
                while recv_len:
                    data = self.socket.recv(4096)
                    recv_len = len(data)
                    response += data.decode()
                    if recv_len < 4096:
                        break
                if response:
                    print(response)
                    buffer_string = input('> ')
                    buffer_string += '\n'
                    self.socket.send(buffer_string.encode())
        except KeyboardInterrupt:
            print('User terminated.')
            self.socket.close()
            sys.exit()

    def listen(self):
        self.socket.bind((self.args.target, self.args.port))
        self.socket.listen(5)
        while True:
            client_socket, _ = self.socket.accept()
            threading.Thread(
                target=self.handle, args=(client_socket,)
            ).start()

    def handle(self, client_socket):
        if self.args.execute:
            output = execute(self.args.execute)
            client_socket.send(output.encode())
        elif self.args.upload:
            file_buffer = b''
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                file_buffer += data

            with open(self.args.upload, mode="wb") as file:
                file.write(file_buffer)
            message = f'Saved file {self.args.upload}'
            client_socket.send(message.encode())
        elif self.args.command:
            cmd_buffer = b''
            while True:
                try:
                    client_socket.send(b'> ')
                    while '\n' not in cmd_buffer.decode():
                        cmd_buffer += client_socket.recv(64)
                    response = execute(cmd_buffer.decode())
                    if response:
                        client_socket.send(response.encode())
                    cmd_buffer = b''
                except Exception as e:
                    print(f'Server killed {e}')
                    self.socket.close()
                    sys.exit()


if __name__ == '__main__':
 
    parser = argparse.ArgumentParser(
        description='A network client and server.'
                    'Can be used to push files, or a listener'
                    'that gives you command line access.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''Examples:
            netcat.py -t 192.168.178.69 -p 5555 -l -c # listen on the command shell                           
            netcat.py -t 192.168.178.69 -p 5555 -l -u=foo.txt # upload to file                
            netcat.py -t 192.168.178.69 -p 5555 -l -e=\"cat /etc/passwd\" # execute command      
            echo 'ABC' | ./netcat.py -t 192.168.178.69 -p 135 # echo text
            netcat.py -t 192.168.178.69 - p 5555 # connect server
            '''))

    parser.add_argument('-c', '--command', action='store_true', help='command shell')
    parser.add_argument('-e', '--execute', help='execute specified command')
    parser.add_argument('-l', '--listen', action='store_true', help='listen')
    parser.add_argument('-p', '--port', type=int, default=4444, help='specified port')
    parser.add_argument('-t', '--target', default='192.168.178.69', help='specified IP')
    parser.add_argument('-u', '--upload', help='upload file')
    args = parser.parse_args()

    buffer = '' if args.listen else sys.stdin.read()
    netcat = NetCat(args, buffer.encode())
    netcat.run()
