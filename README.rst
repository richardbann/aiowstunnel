aiowstunnel
===========

Persistent and reliable TCP tunneling based on ``asyncio``.

Concepts
--------

To illustrate the two differenc modes Client can operate in, we give a detailed
example of two conceptually different setups.

Local Port Forwarding: the ``CONNECT`` mode
...........................................

Let's suppose you have an application server listening on host
``srv:6789``, you have two servers ``host1`` and ``host2`` and a client
workstation ``cli``. Let's suppose we have the following setup:

``cli`` ---> ``host1`` ---> ``host2`` ---> ``srv``

The arrow ``a`` ---> ``b`` indicates that ``a`` can connect to ``b``, but
``b`` can not connect to ``a``.

In this case you start a tunnel server on ``host2`` that listens on port 9000.

.. code-block:: python

  Server('0.0.0.0', 9000)

You also strart a tunnel client
on ``host1`` in ``CONNECT`` mode with the following parameters

.. code-block:: python

  Client(
      aiowstunnel.CONNECT,  # you need connect mode here
      'host2', 9000,        # the tunnel server is listening on port 9000
      '0.0.0.0', 5678,      # the listening host/port
      'srv', 6789,          # the connectiong host/port
  )

In this case, the parameters mean the following:

``server_mode``
  This was set to ``aiowstunnel.CONNECT``, which means the client wants
  the server to use the ``connect_host``, ``connect_port`` settings when
  a new connection is received by the client and connect to the given
  host-port.

``tunnel_host``, ``tunnel_port``
  It tells the Client where the tunnel server is listening. The client will
  connect to this server and tries to keep the connection open.

``listen_host``, ``listen_port``
  The ``server_mode`` parameter is ``CONNECT``, so the server is going to
  use the ``connect_host`` and ``connect_port`` parameters and the client
  will listen on this host/port. In this example the client is running
  on ``host1`` and it will start a new server on ``0.0.0.0:5678``.
  The program running on ``cli`` can connect to this server as if it was
  the application server

``connect_host``, ``connect_port``
  As described earlier in ``CONNECT`` mode the server will use these to
  connect when a connection comes to the client.
  The client tells the server to connect to ``srv:6789`` -- the application
  server.

Remote Port Forwarding: the ``LISTEN`` mode
...........................................

What if the firewall is configured in this way:

``cli`` ---> ``host1`` <--- ``host2`` ---> ``srv``

In this case the tunnel server will be started on ``host1``, the
client on ``host2``. The server needs to **listen** ``0.0.0.0:5678`` while
the client **connects** to the application server.

.. code-block:: python

  Server('0.0.0.0', 9000)

.. code-block:: python

  Client(
      aiowstunnel.LISTEN,   # you need the server to listen
      'host1', 9000,        # the tunnel server is listening on port 9000
      '0.0.0.0', 5678,      # the server listens here
      'srv', 6789,          # the client connects here
  )

Strarting the Server and the Client
-----------------------------------

Here is the code to properly start the server in the above example

.. code-block:: python

  import asyncio
  import signal
  import logging

  from aiowstunnel.server import Server


  logging.basicConfig(level=logging.INFO)


  async def serve(stop):
      srv = Server('0.0.0.0', 9000)
      srv.start()
      await stop
      await srv.close()


  loop = asyncio.get_event_loop()

  # install signal handler
  stop = asyncio.Future()
  loop.add_signal_handler(signal.SIGINT, stop.set_result, None)

  loop.run_until_complete(serve(stop))

Starting the client is very similar

.. code-block:: python

  import asyncio
  import logging
  import signal

  from aiowstunnel.client import Client
  import aiowstunnel


  logging.basicConfig(level=logging.INFO)


  async def provide_tunnel(stop):
      cli = Client(
          aiowstunnel.LISTEN,   # you need the server to listen
          'host1', 9000,        # the tunnel server is listening on port 9000
          '0.0.0.0', 5678,      # the server listens here
          'srv', 6789,          # the client connects here
      )
      cli.start()
      await stop
      await cli.close()


  loop = asyncio.get_event_loop()

  # install signal handler
  stop = asyncio.Future()
  loop.add_signal_handler(signal.SIGINT, stop.set_result, None)

  loop.run_until_complete(provide_tunnel(stop))

Using SSL/TLS
-------------
TODO
