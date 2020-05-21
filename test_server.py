from SmartSocket import connections

SERVER_ADDRESS = (
    connections.getLocalIP(),
    7871
)

SERVER = connections.SERVER(SERVER_ADDRESS)
SYSTEM = connections.ServerClientSystem(SERVER)
print("Server:",SYSTEM.server)
print(f"Hosting on: {SERVER_ADDRESS[0]}:{SERVER_ADDRESS[1]}")

server_running = True

while server_running:

    new_clients, new_messages, disconnected = SYSTEM.main()

    for new_client in new_clients:
        conn, addr = new_client
        print(f"New connection from address {addr[0]}:{addr[1]}")

    for msg in new_messages:
        if msg.is_dict:
            print(f"New dict message {str(msg.data)}")

            SYSTEM.send_to_clients( msg.data )
        else:
            print(f"New message: is_dict:{msg.is_dict}, is_pickled:{msg.is_pickled}")

    for client in disconnected:
        print(f"Client disconnected {client[1][0]}:{client[1][1]}")