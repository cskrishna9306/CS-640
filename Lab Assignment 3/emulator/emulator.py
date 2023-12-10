import sys, getopt
import socket
import struct
from datetime import datetime
import ipaddress
import select
import pickle

def readTopology(file_name):
    topology = {}
    with open(file_name) as f:
        for line in f:
            links = line.strip().split(" ")
            topology[(links[0].split(",")[0], int(links[0].split(",")[1]))] = [(ip_addr, int(port)) for ip_addr, port in (link.split(",") for link in links[1:])]
    
    return topology

def createRoutes():
    pass

def forwardPacket():
    pass

def buildForwardTable(start_vertex, topology):

    confirmed = {start_vertex: {"Cost": 0, "NextHop": None}}
    tentative = {neighbor: {"Cost": 1, "NextHop": neighbor} for neighbor in topology[start_vertex]}

    next = start_vertex

    while tentative:
        # Traversing each neighbor
        for neighbor in topology[next]:
            # Calculating the current cost to neighbor
            cost = confirmed[next]["Cost"] + 1
            if neighbor not in confirmed.keys() and neighbor not in tentative.keys():
                tentative[neighbor] = {"Cost": cost, "NextHop": neighbor if confirmed[next]["NextHop"] is None else confirmed[next]["NextHop"]}
            elif neighbor in tentative.keys():
                if cost < tentative[neighbor]["Cost"]:
                    tentative[neighbor] = {"Cost": cost, "NextHop": neighbor if confirmed[next]["NextHop"] is None else confirmed[next]["NextHop"]}
                    
        # Picking the lowest cost node from the tentative list
        next = min(tentative, key=lambda k: tentative[k]["Cost"])
        # Transferring the lowest cost node from tentative to confirmed
        confirmed[next] = tentative.pop(next)

    # Returning the forwarding table as a dictionary
    return {destination: confirmed[destination]["NextHop"] for destination in confirmed}

# Get the command line arguments
opts, _ = getopt.getopt(sys.argv[1:],"p:f:")
opts = dict(opts)

port, file_name = int(opts['-p']), opts['-f']

if not 2049 < port < 65536:
    print("Error: Port number not between the range 2049 and 65536")
    exit(1)

# Binding the socket at the specified port number
socket_object = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket_object.bind((socket.gethostbyname(socket.gethostname()), port))

# Set the socket to non-blocking mode
socket_object.setblocking(0)

# Reading the topology within the specified file
topology = readTopology(file_name)

# Static Forwarding Table (Destination, Next Hop)
forwarding_table = buildForwardTable((socket.gethostbyname(socket.gethostname()), port), topology)
# forwarding_table = buildForwardTable(("1.0.0.0", 1), topology)
print("Initial forwarding table:")
print(forwarding_table)
# Latest timestamps from neighbors
neighbors = {neighbor: 0 for neighbor in topology[(socket.gethostbyname(socket.gethostname()), port)]}

# TODO: Implement data structure for largest sequence numbers from each nodes
largest_seq_no = {}

seq_no = 1      # Initializing sequence number
TTL = 10        # Initializing TTL
LSP_INTERVAL = 4000 # Initializing defined interval for linkStateMessage
HM_INTERVAL = 500   # Initializing interval for helloMessage
last_LSP = 0
last_HM = 0

# helloMessage = struct.pack("!BIHIHIcII", TTL, int(ipaddress.ip_address(socket.gethostbyname(socket.gethostname()))), port, int(ipaddress.ip_address(src_ip_address)), src_port, 9, bytes("H", "utf-8"), 0, 0)
# TODO: LinkStateMessage contains a list of all directly connected neighbors to this emulator
LSM_body = str(list(neighbors.keys()))

# Receving and Forwarding packets
while True:
    ready_to_read, _, _ = select.select([socket_object], [], [], 0)
    print("TOPOLOGY:")
    print(topology)
    if ready_to_read:
        full_packet, neighbor_address = socket_object.recvfrom(1024)
        # Unpacking the contents of the packet header
        packet_header = struct.unpack("!BIHIHIcII", full_packet[:26])
        
        # TODO: Maybe use priority for TTL
        packet_TTL = packet_header[0]
        
        src_ip_address = str(ipaddress.ip_address(int(packet_header[1])))
        src_port = packet_header[2]
        
        dest_ip_address = str(ipaddress.ip_address(int(packet_header[3])))
        dest_port = packet_header[4]
        
        packet_type = packet_header[6].decode()
        packet_seq_no = packet_header[7]

        # Handle Hello Message
        if packet_type == "H":
            if neighbor_address not in neighbors:
                # Updating topology to reflect the addition of a new neighbor
                topology[(socket.gethostbyname(socket.gethostname()), port)].append(neighbor_address)
                # Updating the forwarding table
                forwarding_table = buildForwardTable((socket.gethostbyname(socket.gethostname()), port), topology)
                # Incrementing sequence number
                seq_no += 1
                # print("UPDATE:")
                # print(forwarding_table)
            
            # Updating the latest timestamp for the neighbor
            neighbors[neighbor_address] = datetime.now().timestamp()
            # Generating a new LinkStateMessage
            LSM_body = str(list(neighbors.keys()))
            continue
        
        # Handle Link State Message
        if packet_type == "L":
            if (src_ip_address, src_port) in largest_seq_no:
                # Check for an update
                if largest_seq_no[(src_ip_address, src_port)] < packet_seq_no:
                    # Updating route topology
                    topology[(src_ip_address, src_port)] = eval(full_packet[26:].decode())
                
                    # Updating the forwarding table
                    forwarding_table = buildForwardTable(((socket.gethostbyname(socket.gethostname()), port)), topology)
                    # print("UPDATE:")
                    # print(forwarding_table)
                    # Forwarding packets via reliable flooding
                    # forwardPacket(socket_object, full_packet, neighbors.keys().remove(neighbor_address))
                
                    for neighbor in neighbors.keys():
                        if neighbor is not neighbor_address:
                            newPacket = struct.pack("!BIHIHIcII", packet_TTL - 1, int(ipaddress.ip_address(src_ip_address)), src_port, int(ipaddress.ip_address(dest_ip_address)), dest_port, 0, bytes("L", "utf-8"), packet_seq_no, 0) + full_packet[26:]
                            socket_object.sendto(newPacket, neighbor)
            else:
                # Updating route topology
                    topology[(src_ip_address, src_port)] = eval(full_packet[26:].decode())
                
                    # Updating the forwarding table
                    forwarding_table = buildForwardTable(((socket.gethostbyname(socket.gethostname()), port)), topology)
                    # print("UPDATE:")
                    # print(forwarding_table)
                    # Forwarding packets via reliable flooding
                    # forwardPacket(socket_object, full_packet, neighbors.keys().remove(neighbor_address))
                
                    for neighbor in neighbors.keys():
                        if neighbor is not neighbor_address:
                            newPacket = struct.pack("!BIHIHIcII", packet_TTL - 1, int(ipaddress.ip_address(src_ip_address)), src_port, int(ipaddress.ip_address(dest_ip_address)), dest_port, 0, bytes("L", "utf-8"), packet_seq_no, 0) + full_packet[26:]
                            socket_object.sendto(newPacket, neighbor)
            
            # Updating the largest sequence number from this source node
            largest_seq_no[(src_ip_address, src_port)] = packet_seq_no
            continue

        # Handle Data, End, and Request packets
        if packet_type in ("D","E","R","A"):
            # Sending the packet to its next hop
            # TODO: Handle packet_TTL before sending
            socket_object.sendto(full_packet, forwarding_table[(dest_ip_address, dest_port)])
            continue
        
        # Handle Route Trace packets
        if packet_type == "T":
            if packet_TTL == 0:
                routeTrace = struct.pack("!BIHIHIcII", packet_TTL, int(ipaddress.ip_address(socket.gethostbyname(socket.gethostname()))), port, int(ipaddress.ip_address(dest_ip_address)), dest_port, 9, bytes("T", "utf-8"), 0, 0)
                socket_object.sendto(routeTrace, (src_ip_address, src_port))
            else:
                routeTrace = struct.pack("!BIHIHIcII", packet_TTL - 1, int(ipaddress.ip_address(socket.gethostbyname(src_ip_address))), src_port, int(ipaddress.ip_address(dest_ip_address)), dest_port, 9, bytes("T", "utf-8"), 0, 0)
                socket_object.sendto(routeTrace, forwarding_table[(dest_ip_address, dest_port)])
            continue

    # TODO: Step 3: Sending helloMessage to neighbors after certain interval
    if (datetime.now().timestamp() - last_HM) * 1000 > HM_INTERVAL:
        for neighbor in neighbors:
            # TODO: Sending hello message to every neighbor
            helloMessage = struct.pack("!BIHIHIcII", TTL, int(ipaddress.ip_address(socket.gethostbyname(socket.gethostname()))), port, int(ipaddress.ip_address(neighbor[0])), neighbor[1], 9, bytes("H", "utf-8"), 0, 0)
            socket_object.sendto(helloMessage, neighbor)
        last_HM = datetime.now().timestamp()

    # TODO: Step 4: Check for helloMessages from neighbors
    neighbors_rm = []
    for neighbor in neighbors:
        # TODO: Check for the timestamp and remove from topology
        if (datetime.now().timestamp() - neighbors[neighbor]) * 1000 > HM_INTERVAL:
            if neighbor in topology[(socket.gethostbyname(socket.gethostname()), port)]:
                topology[(socket.gethostbyname(socket.gethostname()), port)].remove(neighbor)
            neighbors_rm.append(neighbor)
            seq_no += 1
    
    # TODO: Rebuild forwarding table
    forwarding_table = buildForwardTable((socket.gethostbyname(socket.gethostname()), port), topology)
    for neighbor in neighbors_rm:
        del neighbors[neighbor]
        # largest_seq_no.pop(neighbor)
        
    # Sending new LinkStateMessage to all neighbors after certain interval
    LSM_body = str(list(neighbors.keys()))
    if (datetime.now().timestamp() - last_LSP) * 1000 > LSP_INTERVAL:
        for neighbor in neighbors:
            linkStateMessage = struct.pack("!BIHIHIcII", TTL, int(ipaddress.ip_address(socket.gethostbyname(socket.gethostname()))), port, int(ipaddress.ip_address(neighbor[0])), neighbor[1], 9 + len(LSM_body), bytes("L", "utf-8"), seq_no, len(LSM_body)) + LSM_body.encode()
            socket_object.sendto(linkStateMessage, neighbor)
        last_LSP = datetime.now().timestamp()