import sys, getopt
import socket
import struct
from datetime import datetime
import time

def getoptions(argv):
   
   opts, _ = getopt.getopt(argv,"p:g:r:q:l:")
   opts = dict(opts)

   return int(opts['-p']), int(opts['-g']), int(opts['-r']), int(opts['-q']), int(opts['-l'])

def sendPacket(socket_object, packet_type, send_time, requester_address, requester_port, rate, seq_no, payload):
   # Building the packet
   packet = struct.pack("!cII", packet_type.encode(), socket.htonl(seq_no), len(byte) if packet_type == "D" else 0) + payload

   # Managing the rate of the packets sent
   if send_time != 0:
      if datetime.now().timestamp() - send_time < (1 / rate):
         time.sleep((1 / rate) - (datetime.now().timestamp() - send_time))
                
   # Sending the packet
   socket_object.sendto(packet, (requester_address, requester_port))
   send_time = datetime.now()

   # Printing the metadata of the packets
   print("{} Packet".format(packet_type))
   print("send time:\t{}".format(send_time))
   print("requester addr:\t{}:{}".format(requester_address, requester_port))
   print("Sequence num:\t{}".format(seq_no))
   print("payload:\t{}\n".format(payload[:4].decode()))
   
   return (seq_no + len(payload)), send_time.timestamp()


if __name__ == "__main__":
   # port, requester_port, rate, seq_no, length = getoptions(sys.argv[1:])

   opts, _ = getopt.getopt(sys.argv[1:],"p:g:r:q:l:")
   opts = dict(opts)

   port, requester_port, rate, seq_no, length = int(opts['-p']), int(opts['-g']), int(opts['-r']), int(opts['-q']), int(opts['-l'])
   
   if (not 2049 < port < 65536) or (not 2049 < requester_port < 65536):
      print("Error: Port number not between the range 2049 and 65536")
      exit(1)

   # Binding the socket at the specified port number
   socket_object = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   socket_object.bind((socket.gethostbyname(socket.gethostname()), port))
   
   # Receiving the packet from the requester
   full_packet, requester_address = socket_object.recvfrom(1024)
   file_name = full_packet[9:].decode()

   # Sending DATA packets to the requester
   prev_time = 0
   send_time = 0
   with open(file_name, 'rb') as f: # Opening the file in byte mode
     while (byte := f.read(length)):   # Reading bytes at the specified length
         # Building the DATA packet
         packet = struct.pack("!cII", bytes("D", "utf-8"), socket.htonl(seq_no), len(byte)) + byte
         
         # Managing the rate of DATA packets sent
         if prev_time != 0:
            curr_time = datetime.now().timestamp()
            if curr_time - prev_time < (1 / rate):
                time.sleep((1 / rate) - (curr_time - prev_time)) 

         # Sending the DATA packet
         socket_object.sendto(packet, (requester_address[0], requester_port))
         prev_time = datetime.now().timestamp()

         # Printing the metadata of the DATA packet 
         print("{} Packet".format("DATA"))
         print("send time:\t{}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]))
         print("requester addr:\t{}:{}".format(requester_address[0], requester_port))
         print("Sequence num:\t{}".format(seq_no))
         print("payload:\t{}\n".format(byte[:4].decode()))

         # Incementing the sequence number
         seq_no += len(byte)
         # seq_no, send_time = sendPacket(socket_object, "DATA", send_time, requester_address[0], requester_port, rate, seq_no, byte)
   
   # Building the END packet
   packet = struct.pack("!cII", bytes("E", "utf-8"), socket.htonl(seq_no), 0) + "".encode()

   # Managing the rate of the END packet sent
   if prev_time != 0:
      curr_time = datetime.now().timestamp()
      if curr_time - prev_time < (1 / rate):
         time.sleep((1 / rate) - (curr_time - prev_time))
                
   # Sending the END packet
   socket_object.sendto(packet, (requester_address[0], requester_port))

   print("{} Packet".format("END"))
   print("send time:\t{}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]))
   print("requester addr:\t{}:{}".format(requester_address[0], requester_port))
   print("Sequence num:\t{}".format(seq_no))
   print("payload:\n")
   # sendPacket(socket_object, "END", send_time, requester_address[0], requester_port, rate, seq_no, "".encode())
