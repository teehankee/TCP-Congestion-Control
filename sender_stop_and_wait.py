import socket
import time

# total packet size
PACKET_SIZE = 1024
# bytes reserved for sequence id
SEQ_ID_SIZE = 4
# bytes available for message
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE

# read data
with open("file.mp3", "rb") as f:
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

        # Initialize variables
        total_bytes_sent = 0
        start_time = time.time()
        total_delay = 0
        num_packets = 0

        # wait for acknowledgement
        while True:
            try:
                # record send time
                send_time = time.time()

                # send message out and receive acknoledgement
                udp_socket.sendto(message, ("localhost", 5001))
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)

                # record receive time of acknoledgement
                ack_time = time.time()
                delay = ack_time - send_time

                # update variables
                total_bytes_sent += len(message)
                total_delay += delay
                num_packets += 1

                # extract ack id
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder="big")

                # ack id == sequence id, move on
                if ack_id == seq_id:
                    break

            except socket.timeout:
                # no ack, resend message
                udp_socket.sendto(message, ("localhost", 5001))

                # move sequence id forward

            if seq_id + MESSAGE_SIZE >= len(data):
                seq_id = len(data)
                # Send an empty message with the correct sequence id
                empty_message = int.to_bytes(
                    seq_id, SEQ_ID_SIZE, signed=True, byteorder="big"
                )
                udp_socket.sendto(empty_message, ("localhost", 5001))

                # Wait for acknowledgement and fin message

                while True:
                    try:
                        ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                        ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder="big")

                        # If ack id == sequence id and fin message received, move on
                        if ack_id == seq_id + 3 and ack[SEQ_ID_SIZE:] == b"fin":
                            # Send a message with body '==FINACK==' to let receiver know to exit
                            message = (
                                int.to_bytes(
                                    seq_id, SEQ_ID_SIZE, signed=True, byteorder="big"
                                )
                                + b"==FINACK=="
                            )
                            udp_socket.sendto(message, ("localhost", 5001))
                            break

                    except socket.timeout:
                        print("timeout, resending empty message")
                        print(ack_id, ack[SEQ_ID_SIZE:], seq_id, len(data))
                        udp_socket.sendto(empty_message, ("localhost", 5001))

                break

            else:
                seq_id += MESSAGE_SIZE

end_time = time.time()
total_time = end_time - start_time
throughput = total_bytes_sent / total_time
average_packet_delay = total_delay / num_packets
performance_metric = throughput / average_packet_delay

# Print the results
print(f"{throughput:.2f},{average_packet_delay:.2f},{performance_metric:.2f}")
