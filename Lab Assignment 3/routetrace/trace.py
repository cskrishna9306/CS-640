import sys, getopt
import socket
import struct
import ipaddress

# Get the command line arguments
opts, _ = getopt.getopt(sys.argv[1:],"a:b:c:d:e:f:")
opts = dict(opts)

port, src_hostname, src_port, dest_hostname, dest_port, debug = int(opts['-a']), opts['-b'], int(opts['-c']), opts['-d'], int(opts['-e']), int(opts['-f'])

if not 2049 < port < 65536:
    print("Error: Port number not between the range 2049 and 65536")
    exit(1)

# Binding the socket at the specified port number
socket_object = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket_object.bind((socket.gethostbyname(socket.gethostname()), port))

# Initialize TTL
TTL = 0

while True:
    # Building the route trace packet
    #   a. TTL = 0
    #   b. (Source IP, Source Port) = (Route Trace IP, Route Trace Port)
    #   c. (Destination IP, Destination Port) = (Destination IP, Destination Port)
    #   d. Route trace packets have the packet type "T"
    routeTrace = struct.pack("!BIHIHIcII", TTL, int(ipaddress.ip_address(socket.gethostbyname(socket.gethostname()))), port, int(ipaddress.ip_address(dest_hostname)), dest_port, 9, bytes("T", "utf-8"), 0, 0)

    # Sending the route trace packet to the source node
    socket_object.sendto(routeTrace, (socket.gethostbyname(src_hostname), src_port))
    
    # Printing sent packet debug information
    if debug == 1:
        print("TTL:\t\t{}".format(TTL))
        print("Source Address:\t\t{}:{}".format(socket.gethostbyname(src_hostname), src_port))
        print("Destination Address:\t\t{}:{}".format(socket.gethostbyname(dest_hostname), dest_port))
    
    # Waiting for a response
    response_packet, response_address = socket_object.recvfrom(1024)
 
    # Unpacking the contents of the response packet header
    packet_header = struct.unpack("!BIHIHIcII", response_packet[:26])
        
    packet_TTL = packet_header[0]
    
    packet_src_ip_address = str(ipaddress.ip_address(int(packet_header[1])))
    packet_src_port = packet_header[2]

    packet_dest_ip_address = str(ipaddress.ip_address(int(packet_header[3])))
    packet_dest_port = packet_header[4]

    # Printing the responder's IP and port
    print("Responder's Address: {}:{}".format(response_address[0], response_address[1]))

    # Printing response packet debug information
    if debug == 1:
        print("TTL:\t\t{}".format(packet_TTL))
        print("Source Address:\t\t{}:{}".format(packet_src_ip_address, packet_src_port))
        print("Destination Address:\t\t{}:{}".format(packet_dest_ip_address, packet_dest_port))

    # Terminate if:
    #   a. Source IP (Route Trace packet) = Destination IP (command line), and
    #   b. Source Port (Route Trace packet) = Destination Port (command line)
    if (packet_src_ip_address, packet_src_port) == (socket.gethostbyname(dest_hostname), dest_port):
        break
    
    # Increment TTL
    TTL += 1
        
