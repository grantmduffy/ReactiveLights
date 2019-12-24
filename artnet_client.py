import socket, neopixel, machine
from time import sleep

n_led = 50
np = neopixel.NeoPixel(machine.Pin(4), 50)


def run():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind(('192.168.0.34', 6454))
        while True:
            data, addr = s.recvfrom(1024)
            header = data[:18]
            body = data[18:]
            # print(len(data), addr)
            if len(data) == 530:
                for i in range(n_led):
                    np[i] = (body[i * 3 + 1], body[i * 3], body[i * 3 + 2])
                np.write()
            sleep(0.01)
    except:
        s.close()
        raise
