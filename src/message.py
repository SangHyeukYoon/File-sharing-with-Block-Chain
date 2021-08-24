import os
import sys
import socket
import json
import struct
import io


class Message:
    '''
        message format: {fixed json header size, message information as json, data}
    '''
    def __init__(self, sock, defaultDir=''):
        self.sock = sock
        self.defaultDir = defaultDir

        self.dataLength = 0

        self._recv_buffer = b''
        self._send_buffer = b''
    
    def Send(self, message, msgType='message'):
        # change message to json
        data = {'data': message}
        data = json.dumps(data, ensure_ascii=False).encode('utf-8')

        jsonHeader = {
            'dataLength': len(data),
            'msgType': msgType
        }
        jsonHeader = json.dumps(jsonHeader, ensure_ascii=False).encode('utf-8')

        # convert header size to bytes
        messageHdr = struct.pack('>H', len(jsonHeader))

        self._send_buffer = messageHdr + jsonHeader + data

        # send all data
        sendBufferSize = len(self._send_buffer)
        totalSent = 0
        while totalSent < sendBufferSize:
            sent = self.sock.send(self._send_buffer)
            self._send_buffer = self._send_buffer[sent:]

            totalSent += sent
    
    def Receive(self, timeOut=None):
        data = b''

        # header length is fixed at 2 bytes. 
        hdrLen = 2
        jsonHdrLen = 0
        dataLen = 0

        self.sock.settimeout(timeOut)

        while True:
            # receive if recv buffer is empty. 
            if not self._recv_buffer:
                try:
                    self._recv_buffer += self.sock.recv(4096)
                except socket.timeout:
                    return None, None

            # processing hdrLen if recv buffer is over 2 bytes. 
            if hdrLen <= len(self._recv_buffer) and jsonHdrLen == 0:
                jsonHdrLen = struct.unpack('>H', self._recv_buffer[:hdrLen])[0]
                self._recv_buffer = self._recv_buffer[hdrLen:]

            # processing jsonHeadr if recv buffer is over json header length. 
            if jsonHdrLen <= len(self._recv_buffer) and dataLen == 0:
                jsonHeader = self._json_decode(self._recv_buffer[:jsonHdrLen], 'utf-8')
                self._recv_buffer = self._recv_buffer[jsonHdrLen:]
                dataLen = jsonHeader['dataLength']

            # processing data if recv buffer is over data size. 
            if dataLen <= len(self._recv_buffer) and dataLen != 0:
                data = self._recv_buffer[:dataLen]
                data = self._json_decode(data, 'utf-8')
                data = data['data']

                self._recv_buffer = self._recv_buffer[dataLen:]

                self.sock.settimeout(None)

                return data, jsonHeader
    
    def SendFile(self, fileName):
        fileLength = os.path.getsize(self.defaultDir+fileName)

        # send file Information. 
        data = {
            'fileName': fileName,
            'fileLength': fileLength
        }
        data = {'data': data}
        data = json.dumps(data, ensure_ascii=False).encode('utf-8')

        jsonHeader = {
            'dataLength': len(data),
            'msgType': 'fileTrans'
        }
        jsonHeader = json.dumps(jsonHeader, ensure_ascii=False).encode('utf-8')

        messageHdr = struct.pack('>H', len(jsonHeader))

        self._send_buffer = messageHdr + jsonHeader + data

        sendBufferSize = len(self._send_buffer)
        totalSent = 0
        while totalSent < sendBufferSize:
            sent = self.sock.send(self._send_buffer)
            self._send_buffer = self._send_buffer[sent:]

            totalSent += sent

        # send file
        f = open(self.defaultDir+fileName, 'rb')

        while True:
            data = f.read(1024)

            if not data:
                f.close()

                break

            self.sock.send(data)
    
    def ReceiveFile(self, fileName, fileLength):
        # create file
        f = open(self.defaultDir+str(fileName), 'wb')
        receivedBytes = 0

        #print('fileLength: {}'.format(fileLength))

        # receive and write file. 
        while receivedBytes < fileLength:
            if self._recv_buffer:
                data = self._recv_buffer[:fileLength]
                self._recv_buffer = self._recv_buffer[fileLength:]
            else:
                data = self.sock.recv(1024)
            f.write(data)

            receivedBytes += len(data)
        
        f.close()
    
    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(io.BytesIO(json_bytes), encoding=encoding, newline="")
        obj = json.load(tiow)
        tiow.close()

        return obj

