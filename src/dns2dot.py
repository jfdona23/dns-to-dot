"""
Translates DNS queries into DNS-over-TLS queries
"""
import logging
import os
import socket
import sys

from multiprocessing import Process

import dns.message
import dns.query

from dot_providers import providers


# ----------------------------------------------------------------------------------------------- #
# Logging Config
# ----------------------------------------------------------------------------------------------- #
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(
    logging.Formatter(
        "%(asctime)s - %(levelname)s : %(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z"
    )
)
logger = logging.getLogger()
logger.addHandler(handler)
LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
logger.setLevel(LOGLEVEL)


# ----------------------------------------------------------------------------------------------- #
# Main Code
# ----------------------------------------------------------------------------------------------- #
class DNSProxy:  # pylint: disable=too-many-instance-attributes
    """ DNSProxy """

    def __init__(
        self,
        dns_listen_address=os.environ.get("LISTEN_IP", "127.0.0.1"),
        dns_listen_port=os.environ.get("LISTEN_PORT", 53),
        buffer_size=os.environ.get("BUFFER_SIZE", 512),
        dns_tls_provider=os.environ.get("DNS_PROVIDER", "cloudfare1"),
        proto=os.environ.get("PROTO", "udp"),
    ):  # pylint: disable=too-many-arguments
        """Init the class

        Args:
            - dns_listen_address (str): IP address to listen to queries
            - dns_listen_port (str): Port to listen to queries
            - buffer_size (int): Size for the UDP buffer. Lower values could truncate the data,
                while greater ones don't make sense for UDP (use TCP instead)
            - dns_tls_provider (str): Provider for the the DNS-over-TLS query.
                Possible values are determined by "providers" dict inside dot_providers.py
        """

        self.addr = str()
        self.dns_listen_address = dns_listen_address
        self.dns_listen_port = int(dns_listen_port)
        self.buffer_size = int(buffer_size)
        self.dns_tls_provider = dns_tls_provider
        self.proto = proto

        if self.proto == "udp":
            logger.debug("Protocol UDP selected, creating socket...")
            self.is_tcp = False
            self.socket_udp_init()
        elif self.proto == "tcp":
            logger.debug("Protocol TCP selected, creating socket...")
            self.is_tcp = True
            self.socket_tcp_init()
        else:
            logger.critical("Protocol %s is unknown. Please use UDP or TCP", self.proto)
            sys.exit(1)

    def socket_tcp_init(self):
        """Create the socket using TCP"""

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Needed to reuse a connection avoiding the TIME_WAIT. Please be careful with this.
            self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.client_socket.bind((self.dns_listen_address, self.dns_listen_port))
            self.client_socket.listen()
        except OSError as ex:
            logger.critical(ex)
            sys.exit(1)
        logger.debug(
            "Listening on %s:%s", self.dns_listen_address, self.dns_listen_port
        )
        logger.debug("Buffer Size is %s", self.buffer_size)
        logger.debug("DNS-over-TLS provider is %s", self.dns_tls_provider)

    def socket_udp_init(self):
        """Create the socket using UDP"""

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.client_socket.bind((self.dns_listen_address, self.dns_listen_port))
        except OSError as ex:
            logger.critical(ex)
            sys.exit(1)
        logger.debug(
            "Listening on %s:%s", self.dns_listen_address, self.dns_listen_port
        )
        logger.debug("Buffer Size is %s", self.buffer_size)
        logger.debug("DNS-over-TLS provider is %s", self.dns_tls_provider)

    def run_proxy(self):
        """ Main Loop """

        logger.info("Initializing DNS to DoT proxy...")
        while True:
            if self.is_tcp:
                connection, self.addr = self.client_socket.accept()
                data, _ = connection.recvfrom(self.buffer_size)
            else:
                data, self.addr = self.client_socket.recvfrom(self.buffer_size)
            logger.info("Received query from %s:%s", self.addr[0], self.addr[1])
            received_query = self.parse_query(data)
            if not received_query:
                continue
            built_query = self.build_tls_query(received_query)
            response = self.submit_tls_query(built_query)

            # Send the response back to the client
            logger.debug("Sending response back to %s:%s", self.addr[0], self.addr[1])
            if self.is_tcp:
                data_to_send = response.to_wire()
                data_size = bytes.fromhex(hex(len(data_to_send))[2:].zfill(4))
                connection.sendall(data_size + data_to_send)
                # connection.close()
            else:
                self.client_socket.sendto(response.to_wire(), self.addr)

    def parse_query(self, data):
        """Parse a raw DNS query

        Args:
            - data (byte): The raw query to parse.

        Returns:
            dns.message.QueryMessage: Object containing a parsed DNS query
        """

        if self.is_tcp:
            data = data[2:]
        dns_received_query = dns.message.from_wire(data)

        return dns_received_query

    def build_tls_query(self, dns_received_query):
        """Builds a DNS-over-TLS query

        Args:
            dns_received_query (dns.message.QueryMessage): Object containing a parsed DNS query

        Returns:
            dict: Dictionary containing parameters for the query
        """

        parameters = {}
        # Header data
        parameters.update({"query_id": int(dns_received_query.id)})
        # Response data
        response = dns_received_query.question.pop()
        domain_name = str(response.name)
        record_type = int(response.rdtype)
        query_class = int(response.rdclass)
        # Build the TLS query
        parameters.update(
            {
                "query": dns.message.make_query(
                    domain_name,
                    rdtype=record_type,
                    rdclass=query_class,
                )
            }
        )
        # Choose a DNS-over-TLS provider
        parameters.update(
            {"dns_provider_ip": providers[self.dns_tls_provider].get("ip")}
        )
        parameters.update(
            {"dns_provider_port": providers[self.dns_tls_provider].get("port")}
        )

        return parameters

    def submit_tls_query(self, parameters):  # pylint: disable=no-self-use
        """Submits a DNS-over-TLS query

        Args:
            parameters (dict): Dictionary containing parameters for the query such as:
                - query (str): query object created from dns.message.make_query() method
                - dns_provider_ip (str): IP address for the DNS-over-TLS provider
                - dns_provider_port (int): Port for the DNS-over-TLS provider.

        Returns:
            dns.message.QueryMessage: An object containing the response to the query
        """

        # Submit the query
        dns_tls_query = dns.query.tls(
            parameters["query"],
            parameters["dns_provider_ip"],
            port=parameters["dns_provider_port"],
        )
        # Overwrite the response ID
        dns_tls_query.id = parameters["query_id"]
        logger.debug("DNS Answer: %s", dns_tls_query.answer)
        return dns_tls_query


if __name__ == "__main__":

    if os.environ.get("PROTO") == "multi":
        app1 = DNSProxy(proto="udp")
        f1 = app1.run_proxy
        p1 = Process(target=f1)
        p1.start()

        app2 = DNSProxy(proto="tcp")
        f2 = app2.run_proxy
        p2 = Process(target=f2)
        p2.start()
    else:
        app = DNSProxy()
        app.run_proxy()