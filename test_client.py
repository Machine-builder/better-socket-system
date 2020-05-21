from SmartSocket import connections

CLIENT = connections.SCS_CLIENT()

ip = input("Enter IP >>> ") or connections.getLocalIP()
port = int( input("Enter Port >>> ") or 7871 )

print(f"Connecting to {ip}:{port}")
CLIENT.connect( (ip, port), )
print("Connected")

while 1:
    something = input("Enter something\n>> ")
    if something is not None:
        m = {
            'message': something
        }
        CLIENT.hsend_o( m )
    
    messages, connected = CLIENT.get_new_messages()

    if not connected:
        print("Connection closed by server!")
        break
    
    for message in messages:
        print(f"Message from server: {message.data}")