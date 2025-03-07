import serial
import asyncio
import websockets

# Serial port configuration
SERIAL_PORT = 'COM6'
BAUD_RATE = 115200

# WebSocket server configuration
WS_HOST = 'localhost'
WS_PORT = 2567

# Global variable to track WebSocket clients
clients = set()

async def serial_reader():
    try:
        # Open the serial port
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0)  # Non-blocking mode
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")
        
        loop = asyncio.get_event_loop()
        buffer = ""  # Buffer to store incomplete lines

        # Continuously read lines from the serial port
        while True:
            data = await loop.run_in_executor(None, ser.read, 128)  # Asynchronously read up to 128 bytes
            if data:  # If data is received
                buffer += data.decode('utf-8', errors='ignore')  # Decode and append to the buffer
                
                while '\n' in buffer:  # Process complete lines
                    line, buffer = buffer.split('\n', 1)  # Extract a single line
                    line = line.strip()

                    if clients and line:  # If there are connected clients and the line is not empty
                        # Send the line to each connected WebSocket client
                        await asyncio.gather(*(client.send(line) for client in clients))
                        print(line)  # Print the sent data for verification
                    else:
                        print(line)

    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")

    except KeyboardInterrupt:
        print("Stopped by user.")

    finally:
        if ser.is_open:
            ser.close()
            print("Serial port closed.")

async def websocket_handler(websocket, path):
    # Add new client to the set
    clients.add(websocket)
    print("New WebSocket client connected.")

    try:
        # Keep the connection open to the client
        async for _ in websocket:
            pass
    finally:
        # Remove client on disconnect
        clients.remove(websocket)
        print("WebSocket client disconnected.")

async def main():
    # Start WebSocket server
    await asyncio.gather(
        serial_reader(),
        websockets.serve(websocket_handler, WS_HOST, WS_PORT)
    )

# Run the main function
asyncio.run(main())
