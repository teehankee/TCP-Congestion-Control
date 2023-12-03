import socket
from datetime import datetime

# total packet size
PACKET_SIZE = 1024
# bytes reserved for sequence id
SEQ_ID_SIZE = 4
# bytes available for message
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE

# read data
with open("send.txt", "rb") as f:
    data = f.read()

# create a udp socket
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
    # bind the socket to a OS port
    udp_socket.bind(("localhost", 5000))
    udp_socket.settimeout(1)

    # start sending data from 0th sequence
    seq_id = 0
    while seq_id < len(data):
        # construct message
        # sequence id of length SEQ_ID_SIZE + message of remaining PACKET_SIZE - SEQ_ID_SIZE bytes
        message = (
            int.to_bytes(seq_id, SEQ_ID_SIZE, signed=True, byteorder="big")
            + data[seq_id : seq_id + MESSAGE_SIZE]
        )

        # wait for acknowledgement
        while True:
            try:
                # send message out
                udp_socket.sendto(message, ("localhost", 5001))

                # wait for ack
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)

                # extract ack id
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder="big")

                # ack id == sequence id, move on
                if ack_id == seq_id:
                    break

            except socket.timeout:
                # no ack, resend message
                udp_socket.sendto(message, ("localhost", 5001))

            # move sequence id forward
            seq_id += MESSAGE_SIZE
            print(ack_id, ack[SEQ_ID_SIZE:], seq_id)
            if seq_id >= len(data):
                seq_id = len(data)
                # Send an empty message with the correct sequence id
                empty_message = int.to_bytes(
                    seq_id, SEQ_ID_SIZE, signed=True, byteorder="big"
                )
                udp_socket.sendto(empty_message, ("localhost", 5001))
                print("sent empty message", seq_id)

                # Wait for acknowledgement and fin message
                while True:
                    try:
                        ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                        ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder="big")

                        # If ack id == sequence id and fin message received, move on
                        if ack_id == seq_id + 3 and ack[SEQ_ID_SIZE:] == b"fin":
                            print("ack id == seq id + 4")
                            # Send a message with body '==FINACK==' to let receiver know to exit
                            fin_ack_message = b"==FINACK=="
                            udp_socket.sendto(fin_ack_message, ("localhost", 5001))
                            break

                    except socket.timeout:
                        print("timeout, resending empty message")
                        print(ack_id, ack[SEQ_ID_SIZE:], seq_id, len(data))
                        udp_socket.sendto(empty_message, ("localhost", 5001))