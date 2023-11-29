import sys, getopt
import socket
import struct
import heapq
from datetime import datetime

# def getoptions(argv):
   
#    opts, _ = getopt.getopt(argv,"p:o:")
#    opts = dict(opts)

#    return (int(opts['-p']), opts['-o'])

# def printPacketInformation(packet_type, recv_time, sender_address, sender_port, seq_no, length, payload = ""):
#    print("{} Packet".format(packet_type))
#    print("recv time:\t{}".format(recv_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]))
#    print("sender addr:\t{}:{}".format(sender_address, sender_port))
#    print("sequence:\t{}".format(seq_no))
#    print("length:\t\t{}".format(length))
#    print("payload:\t{}\n".format(payload if packet_type == "DATA" else 0))
#    return

# def printSummary(sender_address, sender_port, data_packets, data_bytes, time):
#    print("Summary")
#    print("sender addr:\t\t{}:{}".format(sender_address, sender_port))
#    print("Total Data packets:\t{}".format(data_packets))
#    print("Total Data bytes:\t{}".format(data_bytes))
#    print("Average packets/second:\t{}".format(int(1e6 * data_packets / time)))
#    print("Duration of the test:\t{} ms\n".format(int(time / 1000)))
#    return

if __name__ == "__main__":
   # port, file_name = getoptions(sys.argv[1:])

   opts, _ = getopt.getopt(sys.argv[1:],"p:o:")
   opts = dict(opts)

   port, file_name = int(opts['-p']), opts['-o']

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
   senders = dict()
   while h:
      # Pop an element from the heap
      sender = heapq.heappop(h)

      senders[(socket.gethostbyname(sender[1]), sender[2])] = []
      
      # Building the REQUEST packet
      packet = struct.pack("!cII", bytes("R", "utf-8"), 0, 0) + file_name.encode()
      # Sending the REQUEST packet
      socket_object.sendto(packet, (socket.gethostbyname(sender[1]), sender[2]))

   # receive the packet
   # Packet from sender
   while file_chunks != 0:
      full_packet, sender_address = socket_object.recvfrom(1024)
      recv_time = datetime.now()

      packet_header = full_packet[:9]
      packet_header = struct.unpack("!cII", packet_header)
      packet_type = packet_header[0].decode()
      seq_no = socket.ntohl(packet_header[1])
      length = packet_header[2]
      
      payload = full_packet[9:].decode()

      if packet_type == "D":
         senders[sender_address].append([recv_time, length, payload])
         # printPacketInformation("DATA", recv_time, sender_address[0], sender_address[1], seq_no, length, payload[:4])
         print("{} Packet".format("DATA"))
         print("recv time:\t{}".format(recv_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]))
         print("sender addr:\t{}:{}".format(sender_address[0], sender_address[1]))
         print("sequence:\t{}".format(seq_no))
         print("length:\t\t{}".format(length))
         print("payload:\t{}\n".format(payload[:4]))
      else:
         file_chunks -= 1
         # printPacketInformation("END", recv_time, sender_address[0], sender_address[1], seq_no, length)
         print("{} Packet".format("END"))
         print("recv time:\t{}".format(recv_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]))
         print("sender addr:\t{}:{}".format(sender_address[0], sender_address[1]))
         print("sequence:\t{}".format(seq_no))
         print("length:\t\t{}".format(length))
         print("payload:\t0\n")
         
         # printSummary(sender_address[0], sender_address[1], len(senders[sender_address]), sum(packet[2] for packet in senders[sender_address]), (recv_time - senders[sender_address][0][0]).microseconds)
         data_packets = len(senders[sender_address])
         total_time = (recv_time.timestamp() - senders[sender_address][0][0].timestamp())
         print("Summary")
         print("sender addr:\t\t{}:{}".format(sender_address[0], sender_address[1]))
         print("Total Data packets:\t{}".format(data_packets))
         print("Total Data bytes:\t{}".format(sum(packet[1] for packet in senders[sender_address])))
         print("Average packets/second:\t{}".format(round(data_packets / total_time)))
         print("Duration of the test:\t{} ms\n".format(int(total_time * 1000)))

   # Building the file
   with open(file_name, "w") as f:
      for sender in senders:
         for file_chunk in senders[sender]:
            f.write(file_chunk[2])
      
      f.close()