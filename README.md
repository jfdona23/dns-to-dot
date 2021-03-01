# DNS2DoT

## Translates DNS queries into DNS-over-TLS queries

1. [About](#about)
1. [Implementation](#implementation)
1. [Choices](#choices)
1. [Security Concerns](#security-concerns)
1. [Improvements](#improvements)
1. [Usage](#usage)

### About
This project is intended for learning purposes and is not production-ready. \
The idea was build a code that intercepts any local DNS query and rewrites it into a DNS-over-TLS compatible query.

### Implementation
The core of this code is the _socket_ library which listens on an IP and port using the UDP protocol. \
Then, when a DNS query is sent, it gets decoded using the _dnspython_ library and then enconded into a new query and submitted to a DoT provider using the _dnspython_ library again. \
Finally, the response is sent back to the client using the same UDP socket as the begining. \

As an idea this could be used inside a Kubernetes cluster as a sidecar container to make sure every container inside the pod is reaching a proper DNS-over-TLS provider. Of course there are better solutions out there, but again this is meant for learning purposes.

### Choices
* __Socket__: Since I don't know how queries will be submitted I've opted for _socket_ library and test my code using _dig_.
* __Dnspython__: Is a well known DNS toolkit and well documented.
* __Logging__: Is more powerfull that a simple _print_ function and is easy to implement. Also I've more control on the messages shown.
* __Multiprocessing__: Easy way to implement multiprocessing with python.
* __Pydantic__: _(Discarded)_ I usually choose this one to map dictionary structures as objects and improve code readibility and type validation, but in this case the structure is quite simple and it only adds a lot of complexity into the main code.

### Security Concerns
* Despite the final query is made over TLS, there is a chance to get a DNS poisoning attack between the client and the DNS proxy itself. A proper solution to avoid this could be the client performing the DNS-over-TLS query itself.
* Any data sent through UDP/53 to the proxy could make it crash since it doesn't perform any kind of DNS query validation. (tested with netcat)
* If someone with bad intentions gets access to the code, he/she could edit response parameters before reaching the client. An example of that is the query ID inside the header which I manipulate in order to not being detected as an attacker.

### Improvements
* Make the proxy able to detect if the DNS query is genuine or not.
* Make the proxy able to handle more than one request at the same time.
* Make the proxy able to handle both protocols at the same time. (__Done!__)
* With a better understanding of the DNS protocol, I think it's absolutely possible to write this proxy using only sockets (i.e no dns library).

### Usage
You can run the code and alter its behavior by passing a set of environmental variables:

| Variable        | Default    |
|-----------------|------------|
| LOGLEVEL        | info       |
| LISTEN_IP       | 0.0.0.0    |
| LISTEN_PORT     | 53         |
| PROTO           | udp        |
| BUFFER_SIZE     | 512        |
| DNS_PROVIDER    | cloudfare1 |
| MULTIPROCESSING | True       |

Notes:
- Protocols could be _tcp_ or _udp_. When multiprocessing this has no effect.
- Any value in Multiprocessing beyond "False", "No" or "0" (zero) will evaluate to True. (Case insensitive)
- Other providers could be _cloudfare2_, _google1_ and _google2_. Please see _dot_providers.py_.

#### Local
```bash
cd src
sudo python3 dns2dot.py
# or passing variables
sudo LOGLEVEL=debug MULTIPROCESSING=False python3 dns2dot.py                                                                                loki@wonderland
2021-02-27T17:09:54-0300 - DEBUG : Protocol UDP selected, creating socket...
2021-02-27T17:09:54-0300 - DEBUG : Listening on 127.0.0.1:53
2021-02-27T17:09:54-0300 - DEBUG : Buffer Size is 512
2021-02-27T17:09:54-0300 - DEBUG : DNS-over-TLS provider is cloudfare1
2021-02-27T17:09:54-0300 - INFO : Initializing DNS to DoT proxy...

2021-02-27T17:09:59-0300 - INFO : Received query from 127.0.0.1:58408
2021-02-27T17:09:59-0300 - DEBUG : DNS Answer: [<DNS ole.com.ar. IN A RRset: [<104.18.170.219>, <104.18.169.219>]>]
2021-02-27T17:09:59-0300 - DEBUG : Sending response back to 127.0.0.1:58408

```
Or importing it into your existing code:
```python
# Example with multiprocessing support
from dns2dot import start_proxy
start_proxy()
```
```python
# Example without multiprocessing support
from dns2dot import DNSProxy
my_proxy = DNSProxy()
my_proxy.run_proxy()
```
Remember you can configure certain parameters by sending environmental variables or by the constructor method from the DNSProxy class.

#### Docker
```bash
docker build -f Dockerfile -t <your_user>/<your_img_name> .
docker run --rm -p 53:53/udp <your_user>/<your_img_name>
# or passing variables
docker run --rm -p 53:53/udp -p 53:53/tcp --env LOGLEVEL=debug --env MULTIPROCESSING=True <your_user>/<your_img_name>
2021-02-27T20:18:12+0000 - DEBUG : Protocol UDP selected, creating socket...
2021-02-27T20:18:12+0000 - DEBUG : Listening on 0.0.0.0:53
2021-02-27T20:18:12+0000 - DEBUG : Buffer Size is 512
2021-02-27T20:18:12+0000 - DEBUG : DNS-over-TLS provider is cloudfare1
2021-02-27T20:18:12+0000 - DEBUG : Protocol TCP selected, creating socket...
2021-02-27T20:18:12+0000 - DEBUG : Listening on 0.0.0.0:53
2021-02-27T20:18:12+0000 - DEBUG : Buffer Size is 512
2021-02-27T20:18:12+0000 - DEBUG : DNS-over-TLS provider is cloudfare1
2021-02-27T20:18:12+0000 - INFO : Initializing DNS to DoT proxy...
2021-02-27T20:18:12+0000 - INFO : Initializing DNS to DoT proxy...

2021-02-27T20:18:15+0000 - INFO : Received query from 172.17.0.1:38324
2021-02-27T20:18:15+0000 - DEBUG : DNS Answer: [<DNS ole.com.ar. IN A RRset: [<104.18.169.219>, <104.18.170.219>]>]
2021-02-27T20:18:15+0000 - DEBUG : Sending response back to 172.17.0.1:38324
2021-02-27T20:18:17+0000 - INFO : Received query from 172.17.0.1:33882
2021-02-27T20:18:17+0000 - DEBUG : DNS Answer: [<DNS ole.com.ar. IN A RRset: [<104.18.170.219>, <104.18.169.219>]>]
2021-02-27T20:18:17+0000 - DEBUG : Sending response back to 172.17.0.1:33882
```
If you prefer run it from my repo:
```bash
docker run --rm -p 53:53/udp jfdona23/dns2dot
# or passing variables
docker run --rm -p 53:53/udp --env LOGLEVEL=debug --env MULTIPROCESSING=False --env PROTO=udp jfdona23/dns2dot
```
