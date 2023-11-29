import sys, getopt
import socket
import struct
from datetime import datetime
import time
import ipaddress
import select

# Managing the rate of DATA packets sent
def sleep(prev_time, rate):
   if prev_time != 0:
      curr_time = datetime.now().timestamp()
      if curr_time - prev_time < (1 / rate):
         time.sleep((1 / rate) - (curr_time - prev_time))
   return

# Sending the DATA packet
def sendPacket(socket_object, packet, f_hostname, f_port, transmissions):
   socket_object.sendto(packet, (socket.gethostbyname(f_hostname), f_port))
   send_time = datetime.now()
   
   # # Printing the metadata of the packet
   # print("{} Packet".format(packet_type))
   # print("send time:\t{}".format(send_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]))
   # print("requester addr:\t{}:{}".format(src_ip_address, src_port))
   # print("Sequence num:\t{}".format(seq_no))
   # print("payload:\t{}\n".format(packet[:4].decode()))
   
   return send_time.timestamp(), send_time.timestamp(), transmissions + 1


if __name__ == "__main__":

   opts, _ = getopt.getopt(sys.argv[1:],"p:g:r:q:l:f:e:i:t:")
   opts = dict(opts)

   port, requester_port, rate, seq_no, length, f_hostname, f_port, priority, timeout = int(opts['-p']), int(opts['-g']), int(opts['-r']), int(opts['-q']), int(opts['-l']), opts['-f'], int(opts['-e']), int(opts['-i']), int(opts['-t'])
   
   if (not 2049 < port < 65536) or (not 2049 < requester_port < 65536):
      print("Error: Port number not between the range 2049 and 65536")
      exit(1)

   # Binding the socket at the specified port number
   socket_object = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   socket_object.bind((socket.gethostbyname(socket.gethostname()), port))
   socket_object.setblocking(0)
   
   while True:
      # Setting up non-blocking
      ready_to_read, _, _ = select.select([socket_object], [], [], 0)
      
      if ready_to_read:
         # Receiving the REQUEST packet from the requester
         full_packet, _ = socket_object.recvfrom(1024)

         # Unpacking the contents of the REQUEST packet header
         packet_header = struct.unpack("!BIHIHIcII", full_packet[:26])

         src_ip_address = str(ipaddress.ip_address(int(packet_header[1])))
         src_port = packet_header[2]

         dest_ip_address = str(ipaddress.ip_address(int(packet_header[3])))
         dest_port = packet_header[4]

         packet_type = packet_header[6].decode()
         window = packet_header[8]
         file_name = full_packet[26:].decode()
         
         if packet_type == "R":
            break

   retransmissions = 0  # Number of retransmissions
   transmissions = 0    # Number of initial transmissions

   window_buffer = {}   # Initializing the window buffer
   sending = False      # Boolean value responsible for sending packets within a window buffer
   prev_time = 0        # Timestamp of the most recent transmitted packet
   
   # Sending DATA packets to the requester
   with open(file_name, 'rb') as f: # Opening the file in byte mode
      
      file_size = len(f.read()) # Size of the file
      f.seek(0, 0)   # Move back to the start of the file
      
      while (byte := f.read(length)):   # Reading bytes at the specified length
         # Adding packets to a window buffer when window buffer is empty
         if len(window_buffer) < window and not sending:
            # Building the DATA packet
            packet = struct.pack("!BIHIHIcII", priority, int(ipaddress.ip_address(socket.gethostbyname(socket.gethostname()))), port, int(ipaddress.ip_address(src_ip_address)), src_port, 9 + len(byte), bytes("D", "utf-8"), socket.htonl(seq_no), len(byte)) + byte
            # Adding the DATA packet to the window buffer
            window_buffer[seq_no] = [packet, 0, 5]
            # Incementing the sequence number
            seq_no += 1

         # Indicator to start emptying the window (sending packets) when:
         #     a. The window is full
         #     b. Last packet has been added to the window
         sending = True if len(window_buffer) == window or f.tell() == file_size else False
         
         # Sending packets within this window buffer at the given rate
         if sending:
            while window_buffer:
               packets_rm = []
               
               # Managing initial transmissions and retransmissions for each packet in the window
               for sn in window_buffer:
                  if window_buffer[sn][1] == 0: # Initial transmission
                     # Managing the rate of DATA packets sent
                     sleep(prev_time, rate)
                     # Sending the DATA packet
                     prev_time, window_buffer[sn][1], transmissions = sendPacket(socket_object, window_buffer[sn][0], f_hostname, f_port, transmissions)
                  elif (datetime.now().timestamp() - window_buffer[sn][1]) * 1000 > timeout: # Retransmitting the DATA packet
                     if window_buffer[sn][2] > 0:
                        # Managing the rate of DATA packets sent
                        sleep(prev_time, rate)
                        # Sending the DATA packet
                        prev_time, window_buffer[sn][1], retransmissions = sendPacket(socket_object, window_buffer[sn][0], f_hostname, f_port, retransmissions)
                        window_buffer[sn][2] -= 1
                     else: # Dropping the packet if we have reached max retransmissions
                        packets_rm.append(sn)
                        print("--> Packet #{} got dropped".format(sn))

               # Removing packets from the window
               for sn in packets_rm:
                  del window_buffer[sn]

               # Setting up non-blocking
               ready_to_read, _, _ = select.select([socket_object], [], [], 0)
               
               if ready_to_read:
                  # Receiving the ACK packets
                  ack_packet, _ = socket_object.recvfrom(1024)
               
                  # Unpacking the sequence number from the ACK packet header
                  sn = socket.ntohl(struct.unpack("!BIHIHIcII", ack_packet[:26])[7])

                  # Removing ACK'd packets from the window
                  if sn in window_buffer:     
                     del window_buffer[sn]
              
            sending = False   # Indicator to start building the window

   # Building the END packet
   packet = struct.pack("!BIHIHIcII", priority, int(ipaddress.ip_address(socket.gethostbyname(socket.gethostname()))), port, int(ipaddress.ip_address(src_ip_address)), src_port, 9, bytes("E", "utf-8"), socket.htonl(seq_no), 0) + "".encode()

   # Managing the rate of the END packet sent
   sleep(prev_time, rate)
                
   # Sending the END packet
   socket_object.sendto(packet, (socket.gethostbyname(f_hostname), f_port))

   # Printing the details of the END packet
   print("{} Packet".format("END"))
   print("send time:\t{}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]))
   print("requester addr:\t{}:{}".format(src_ip_address, src_port))
   print("Sequence num:\t{}".format(seq_no))
   print("payload:\n")
   print("Loss Rate:\t{}\n".format(retransmissions * 100 / (retransmissions + transmissions)))