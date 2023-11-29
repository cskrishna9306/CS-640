import sys, getopt
import socket
import struct
from datetime import datetime
import time

def main(argv):
   
   opts, _ = getopt.getopt(argv,"p:g:r:q:l:")
   opts = dict(opts)

   return (int(opts['-p']), int(opts['-g']), int(opts['-r']), int(opts['-q']), int(opts['-l']))


def printPacketInformation(packet_type, send_time, requester_address, requester_port, seq_no, payload = ""):
   print("{} Packet".format(packet_type))
   print("send time:\t{}".format(send_time))
   print("requester addr:\t{}:{}".format(requester_address, requester_port))
   print("Sequence num:\t{}".format(seq_no))
   print("payload:\t{}\n".format(payload))
   return


if __name__ == "__main__":
   port, requester_port, rate, seq_no, length = main(sys.argv[1:])
   
   socket_object = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   socket_object.bind((socket.gethostbyname(socket.gethostname()), port))
   
   # Packet from requester
   full_packet, requester_address = socket_object.recvfrom(1024)
   file_name = full_packet[9:].decode()

   prev_time = 0
   # send Data packets
   with open(file_name, 'rb') as f:
     # convert to bytes
     while (byte := f.read(length)):
         # build packet
         packet = struct.pack("!cII", bytes("D", "utf-8"), seq_no, len(byte)) + byte
         # send packet
         if prev_time != 0:
            if datetime.now().timestamp() - prev_time < (1 / rate):
                time.sleep((1 / rate) - (datetime.now().timestamp() - prev_time)) 

         socket_object.sendto(packet, (requester_address[0], requester_port))

         prev_time = datetime.now().timestamp()
         printPacketInformation("DATA", datetime.now(), requester_address[0], requester_port, seq_no, byte[:4].decode())

         # increment seq_no
         seq_no += len(byte)
   
   # send the End packet
   packet = struct.pack("!cII", bytes("E", "utf-8"), seq_no, 0) + "".encode()


   if prev_time != 0:
      if datetime.now().timestamp() - prev_time < (1 / rate):
         time.sleep((1 / rate) - (datetime.now().timestamp() - prev_time))
                
   socket_object.sendto(packet, (requester_address[0], requester_port))

   printPacketInformation("END", datetime.now(), requester_address[0], requester_port, seq_no)
