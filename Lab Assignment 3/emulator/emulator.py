import sys, getopt
import queue
import socket
import struct
from datetime import datetime
import random
import ipaddress
import select
import logging

# Get the command line arguments
opts, _ = getopt.getopt(sys.argv[1:],"p:q:f:l:")
opts = dict(opts)

port, queue_size, file_name, log = int(opts['-p']), int(opts['-q']), opts['-f'], opts['-l']

if not 2049 < port < 65536:
    print("Error: Port number not between the range 2049 and 65536")
    exit(1)

# Initializing the priority queues
priority_queues = [queue.Queue(maxsize = queue_size) for i in range(3)]

# Opening log file
logging.basicConfig(filename=log, level=logging.ERROR, encoding='utf-8', filemode='w', format='%(message)s')

# Binding the socket at the specified port number
socket_object = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket_object.bind((socket.gethostbyname(socket.gethostname()), port))

# Set the socket to non-blocking mode
socket_object.setblocking(0)

# Static Forwarding Table
forwarding_table = dict()

# Constructing the forwarding table
with open(file_name) as f:
    for line in f:
       file = line.strip().split(" ")
       if (socket.gethostbyname(file[0]), int(file[1])) == (socket.gethostbyname(socket.gethostname()), port):
           forwarding_table[(socket.gethostbyname(file[2]), int(file[3]))] = {"next_hop": (file[4], int(file[5])), "delay": int(file[6]), "loss_prob": int(file[7])}

delay_in_progress = False
forwarding_packet = None
recv_time = 0

# Receving and Forwarding packets
while True:
    ready_to_read, _, _ = select.select([socket_object], [], [], 0)
    
    if ready_to_read:
        full_packet, _ = socket_object.recvfrom(1024)
        # Unpacking the contents of the packet header
        packet_header = struct.unpack("!BIHIHIcII", full_packet[:26])
    
        priority = packet_header[0]
        
        src_ip_address = str(ipaddress.ip_address(int(packet_header[1])))
        src_port = packet_header[2]
        
        dest_ip_address = str(ipaddress.ip_address(int(packet_header[3])))
        dest_port = packet_header[4]
        
        payload_size = packet_header[5] - 9
        packet_type = packet_header[6].decode()

        # Logging packet loss: No match in forwarding table
        if (dest_ip_address, dest_port) not in forwarding_table:
            logging.error(f"{datetime.now().strftime('%m/%d/%Y %H:%M:%S.%f')[:-3]} - ERROR - Destination address not found in forwarding table \n\tSource: {socket.gethostbyaddr(src_ip_address)[0]}:{src_port} \n\tDestination: {socket.gethostbyaddr(dest_ip_address)[0]}:{dest_port} \n\tPriority: {priority} \n\tPayload Size: {payload_size} \n")
            continue

        if priority_queues[priority - 1].full():
            if packet_type != "E":  # Logging packet loss: Queue is full
                logging.error(f"{datetime.now().strftime('%m/%d/%Y %H:%M:%S.%f')[:-3]} - ERROR - Priority queue is full \n\tSource: {socket.gethostbyaddr(src_ip_address)[0]}:{src_port} \n\tDestination: {socket.gethostbyaddr(dest_ip_address)[0]}:{dest_port} \n\tPriority: {priority} \n\tPayload Size: {payload_size} \n")
            else:   # Forwarding END packets directly if the queue is full
                socket_object.sendto(full_packet, forwarding_table[(dest_ip_address, dest_port)]["next_hop"])
        else:   # Placing the packets in their respective priority queues
            priority_queues[priority - 1].put(full_packet)
            
    # Pulling a packet from the priority queues if no packet is being delayed
    if not delay_in_progress:
        forwarding_packet = None
        recv_time = 0
        for i in range(3):  # Choosing the highest priority packet to forward
            if not priority_queues[i].empty():
                forwarding_packet = priority_queues[i].get()
                recv_time = datetime.now().timestamp()

                # Unpacking the header of the forwarding packet
                forwarding_packet_header = struct.unpack("!BIHIHIcII", forwarding_packet[:26])
                
                forwarding_priority = forwarding_packet_header[0]
                
                forwarding_src_ip_address = str(ipaddress.ip_address(int(forwarding_packet_header[1])))
                forwarding_src_port = forwarding_packet_header[2]
                
                forwarding_dest_ip_address = str(ipaddress.ip_address(int(forwarding_packet_header[3])))
                forwarding_dest_port = forwarding_packet_header[4]
                
                forwarding_payload_size = forwarding_packet_header[5] - 9
                forwarding_packet_type = forwarding_packet_header[6].decode()
                
                delay_in_progress = True
                break
    
    # Continue if the priority queues are empty
    if not forwarding_packet:
        delay_in_progress = False
        continue

    # Delaying the packet
    if (datetime.now().timestamp() - recv_time) * 1000 < forwarding_table[(forwarding_dest_ip_address, forwarding_dest_port)]["delay"]:
        delay_in_progress = True
        continue

    # No Delay: Packet will be either dropped or sent
    delay_in_progress = False
    
    # Skipping the loss probability calculation if the packet is an END packet
    if forwarding_packet_type != "E":
        # Performing the loss probability calculation
        if random.randint(1, 100) <= forwarding_table[(forwarding_dest_ip_address, forwarding_dest_port)]["loss_prob"]:
            logging.error(f"{datetime.now().strftime('%m/%d/%Y %H:%M:%S.%f')[:-3]} - ERROR - Random loss probability \n\tSource: {socket.gethostbyaddr(forwarding_src_ip_address)[0]}:{forwarding_src_port} \n\tDestination: {socket.gethostbyaddr(forwarding_dest_ip_address)[0]}:{forwarding_dest_port} \n\tPriority: {forwarding_priority} \n\tPayload Size: {forwarding_payload_size} \n")
            continue

    # Sending the packet
    socket_object.sendto(forwarding_packet, forwarding_table[(forwarding_dest_ip_address, forwarding_dest_port)]["next_hop"])

    