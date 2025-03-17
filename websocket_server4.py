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
USE_DUMMY_MODE = False  # โหมดจำลอง

async def serial_reader():
    global USE_DUMMY_MODE
    ser = None
    reconnect_delay = 2  # เริ่มต้นรอ 2 วินาที

    while True:
        if not USE_DUMMY_MODE:
            try:
                # ลองเปิด Serial Port
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0)
                print(f"✅ Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")
                
                # ส่งคำสั่ง M1000 O-1 P5 Q10000 หลังจากเชื่อมต่อสำเร็จ
                await asyncio.sleep(1)  # รอให้ระบบเสถียร
                if ser.is_open:
                    ser.write(b'M1000 O-1 P5 Q10000\n')

            except serial.SerialException:
                print(f"⚠️ No Serial Device on {SERIAL_PORT}, switching to Dummy Mode...")
                USE_DUMMY_MODE = True
        buffer = ""
        while True:
            try:
                if USE_DUMMY_MODE:
                    await asyncio.sleep(1)
                    data = "DUMMY_DATA\n"
                else:
                    loop = asyncio.get_event_loop()
                    data = await loop.run_in_executor(None, ser.read, 128)

                if data:
                    if isinstance(data, bytes):  # ตรวจสอบให้มั่นใจว่าเป็น bytes ก่อนทำการ decode
                        buffer += data.decode('utf-8', errors='ignore')

                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()

                        if clients and line:
                            await asyncio.gather(*(client.send(line) for client in clients))
                        print(line)

            except serial.SerialException:
                print("🔌 Serial Disconnected, retrying...")
                USE_DUMMY_MODE = True
                if ser and ser.is_open:
                    ser.close()  # ปิด Serial Port ที่เปิดอยู่
                    print(f"ser is close")
                break  # ออกจากลูปการอ่านข้อมูลแล้วไปเชื่อมต่อใหม่
            except Exception as e:
                print(f"⚠️ Error: {e}")

        # พยายามเปิด Serial Port ใหม่หลังจากหลุด
        while USE_DUMMY_MODE:
            try:
                print(f"🔄 Trying to reconnect to Serial Port... (Waiting {reconnect_delay}s)")
                await asyncio.sleep(reconnect_delay)
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0)
                USE_DUMMY_MODE = False
                reconnect_delay = 2  # Reset ค่า delay เมื่อเชื่อมต่อได้
                print(f"✅ Reconnected to {SERIAL_PORT} at {BAUD_RATE} baud.")

                # ส่งคำสั่ง M1000 O-1 P5 Q10000 หลังจากเชื่อมต่อใหม่
                await asyncio.sleep(1)
                if ser.is_open:
                    print(f"ser is open")
                    ser.write(b'M1000 O-1 P5 Q10000\n')
            except serial.SerialException:
                reconnect_delay = min(reconnect_delay * 2, 30)  # เพิ่ม delay แบบ exponential สูงสุด 30 วินาที

async def websocket_handler(websocket, path):
    clients.add(websocket)
    print("New WebSocket client connected.")

    try:
        async for _ in websocket:
            pass
    finally:
        clients.remove(websocket)
        print("WebSocket client disconnected.")

async def main():
    await asyncio.gather(
        serial_reader(),
        websockets.serve(websocket_handler, WS_HOST, WS_PORT)
    )

asyncio.run(main())
