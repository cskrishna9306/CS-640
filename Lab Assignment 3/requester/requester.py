import sys, getopt
import socket
import struct
import heapq
from datetime import datetime
import ipaddress

if __name__ == "__main__":

   opts, _ = getopt.getopt(sys.argv[1:],"p:o:f:e:w:")
   opts = dict(opts)

   port, file_name, f_hostname, f_port, window = int(opts['-p']), opts['-o'], opts['-f'], int(opts['-e']), int(opts['-w'])

   if not 2049 < port < 65536:
      print("Error: Port number not between the range 2049 and 65536")
      exit(1)

   h = []
   file_chunks = 0

   # Read from tracker.txt to search for the specific file <file_name>
   with open("tracker.txt") as f:
      for line in f:
         file = line.strip().split(" ")
         if file[0] == file_name:
            heapq.heappush(h, (int(file[1]), file[2], int(file[3])))
            file_chunks += 1

   # Binding the socket at the specified port number
   socket_object = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   socket_object.bind((socket.gethostbyname(socket.gethostname()), port))

   # Maintain a hieararchy based on ID (using a prioriy queue heapq)
   senders = {}
   while h:
      # Pop an element from the heap
      sender = heapq.heappop(h)

      senders[(socket.gethostbyname(sender[1]), sender[2])] = {}

      # Building the REQUEST packet
      packet = struct.pack("!BIHIHIcII", 30, int(ipaddress.ip_address(socket.gethostbyname(socket.gethostname()))), port, int(ipaddress.ip_address(socket.gethostbyname(sender[1]))), sender[2], 9 + len(file_name.encode()), bytes("R", "utf-8"), 0, window) + file_name.encode()
      # Sending the REQUEST packet
      socket_object.sendto(packet, (socket.gethostbyname(f_hostname), f_port))

   # Receiving packets from the sender
   while file_chunks != 0:
      full_packet, sender_address = socket_object.recvfrom(1024)
      recv_time = datetime.now()

      packet_header = struct.unpack("!BIHIHIcII", full_packet[:26])
      
      src_ip_address = str(ipaddress.ip_address(int(packet_header[1])))
      src_port = packet_header[2]

      dest_ip_address = str(ipaddress.ip_address(int(packet_header[3])))
      dest_port = packet_header[4]
      
      packet_type = packet_header[6].decode()
      seq_no = socket.ntohl(packet_header[7])
      length = packet_header[8]
      
      payload = full_packet[26:].decode()

      # Check if the packet's destination address matches
      if (dest_ip_address, dest_port) != (socket.gethostbyname(socket.gethostname()), port):
         continue
      
      # Igoring hello messages, link state messages, and route trace packets
      if packet_type == "D":
         # Building the ACK packet
         ack_packet = struct.pack("!BIHIHIcII", 30, int(ipaddress.ip_address(socket.gethostbyname(socket.gethostname()))), port, int(ipaddress.ip_address(src_ip_address)), src_port, 9, bytes("A", "utf-8"), socket.htonl(seq_no), 0) + "".encode()
         # Sending the ACK packet
         socket_object.sendto(ack_packet, (socket.gethostbyname(f_hostname), f_port))
         # Avoiding duplicate packets
         if seq_no not in senders[(src_ip_address, src_port)]:
            senders[(src_ip_address, src_port)][seq_no] = [recv_time, length, payload]
      elif packet_type == "E":
         file_chunks -= 1
         
         # Printing END packet details
         print("{} Packet".format("END"))
         print("recv time:\t{}".format(recv_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]))
         print("sender addr:\t{}:{}".format(src_ip_address, src_port))
         print("sequence:\t{}".format(seq_no))
         print("length:\t\t{}".format(length))
         print("payload:\t0\n")
         
         # Printing Summary
         keys = list(senders[(src_ip_address, src_port)].keys())
         data_packets = len(senders[(src_ip_address, src_port)])
         total_time = (recv_time.timestamp() - senders[(src_ip_address, src_port)][keys[1]][0].timestamp())
         print("Summary")
         print("sender addr:\t\t{}:{}".format(src_ip_address, src_port))
         print("Total Data packets:\t{}".format(data_packets))
         print("Average packets/second:\t{}".format(round(data_packets / total_time)))
         print("Duration of the test:\t{} ms\n".format(int(total_time * 1000)))

   # Building the file
   with open(file_name, "w") as f:
      for sender in senders:
         # Arranging the file chunks by sequency number
         for seq_no in dict(sorted(senders[sender].items())):
            f.write(senders[sender][seq_no][2])
      
      f.close()