import pyaudio
import numpy as np
from threading import Thread, Lock
from matplotlib.colors import hsv_to_rgb
import socket
from time import sleep
import tkinter as tk
import serial
from serial.tools import list_ports

buffer_size = 512
sample_rate = 16000
led_n = 50
fade_rate = 0.003

try:
    with open('target_ip.txt', 'r') as f:
        target_ip = f.read()
except FileNotFoundError:
    target_ip = '127.0.0.1'

win = tk.Tk()
win.title('Reactive Light Settings')
brightness_ = tk.DoubleVar()
brightness_.set(100)
overall_gain_ = tk.DoubleVar()
overall_gain_.set(15)
bass_gain_ = tk.DoubleVar()
bass_gain_.set(5)
mid_gain_ = tk.DoubleVar()
mid_gain_.set(20)
treble_gain_ = tk.DoubleVar()
treble_gain_.set(100)
gamma_ = tk.DoubleVar()
gamma_.set(3.0)
com_port_ = tk.StringVar()
com_port_.set('None')
port_options = {p.device for p in list_ports.comports()}
print(port_options)
ssid_ = tk.StringVar()
password_ = tk.StringVar()

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

pa = pyaudio.PyAudio()
stream = pa.open(
    format=pyaudio.paFloat32,
    channels=1,
    rate=sample_rate,
    frames_per_buffer=buffer_size,
    input=True,
    output=False
)

lock = Lock()

freq = np.abs(np.fft.fftfreq(buffer_size, d=1.0 / sample_rate))
bass_mid_freq = 250.0
mid_treble_freq = 4000.0
run = True
paused = False
levels = []
wave = np.zeros(buffer_size)
amp = np.zeros(buffer_size)
bass = 0
mid = 0
treble = 0
hsv_values = np.ones((led_n, 3))
hsv_values[:, 0] = np.linspace(0, 1, led_n)
rgb_values = np.zeros((led_n, 3))


def audio_worker():
    global wave, amp, bass, mid, treble, levels, run
    while run:
        while paused:
            sleep(0.5)
        wave = np.fromstring(stream.read(buffer_size), np.float32)
        amp = np.abs(np.fft.fft(wave)) * overall_gain_.get() / 100
        bass = np.average(amp[freq < bass_mid_freq])
        mid = np.average(amp[(freq < mid_treble_freq) * (freq > bass_mid_freq)])
        treble = np.average(amp[(freq > mid_treble_freq)])
        levels.append((bass, mid, treble))
    stream.close()


def udp_worker():
    global rgb_values, hsv_values, run
    while run:
        while paused:
            sleep(0.5)
        current_levels = np.array([bass * bass_gain_.get() / 10, mid * mid_gain_.get() / 10,
                                   treble * treble_gain_.get() / 10, bass * bass_gain_.get() / 10])
        lightness = np.interp(np.linspace(0, 3, led_n), [0, 1, 2, 3], current_levels)

        hsv_values[:, 0] += fade_rate
        hsv_values[:, 0][hsv_values[:, 0] > 1] -= 1

        rgb_values = hsv_to_rgb(hsv_values)
        rgb_values[lightness <= 0.5] *= (lightness[lightness <= 0.5] * 2).reshape((-1, 1))

        a = (lightness[lightness > 0.5] * 2 - 1).reshape((-1, 1))
        rgb_values[lightness > 0.5] = (1 - a) * rgb_values[lightness > 0.5] + a * np.ones((led_n, 3))[lightness > 0.5]
        rgb_values[rgb_values > 1.0] = 1.0
        rgb_values[rgb_values < 0.0] = 0.0
        rgb_values = rgb_values ** gamma_.get()
        rgb_values *= brightness_.get() / 100

        data = np.zeros(512, dtype=np.uint8)
        data[:led_n * 3] = (rgb_values.flatten() * 255).astype(np.uint8)
        packet = b'Art-Net\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + data.tobytes()

        s.sendto(packet, (target_ip, 6454))
        sleep(1/20)


def setup_wifi(ssid, psk, port='COM13'):
    with serial.Serial('COM13', 115200) as ser:

        def readlines():
            while not ser.in_waiting:
                pass
            out = b''
            while ser.in_waiting:
                out += ser.read()
            # print(str(out).replace('\\r\\n', '\\r\\n\n'))
            return out

        # Stop run()
        ser.write(b'\x03\r\n')
        print(readlines(), end='')

        # Imports
        ser.write(b'import network\r\nfrom machine import Pin\r\nfrom time import sleep\r\n')
        print(readlines().decode(), end='')

        # Definitions
        ser.write(f'ssid = "{ssid}"\r\npassword = "{psk}"\r\n'.encode())
        ser.write(b'sta_if = network.WLAN(network.STA_IF)\r\nled = Pin(2, Pin.OUT)\r\n')
        print(readlines().decode(), end='')

        # Connect WiFi
        ser.write(b'sta_if.active(False)\r\nsta_if.active(True)\r\nsta_if.connect(ssid, password)\r\n')
        print(readlines().decode(), end='')

        # Wait until connected
        ser.write(b'while not sta_if.isconnected():\r\nled.off()\r\nsleep(0.1)\r\nled.on()\r\nsleep(0.1)\r\n\x08\r\n')
        print(readlines().decode(), end='')
        ser.write(b'led.off()\r\nprint("Connected.")\r\n')
        print(readlines().decode(), end='')

        # Get IP Address
        sleep(1)
        print('Getting IP')
        ser.write(b'sta_if.ifconfig()\r\n')
        res = readlines()
        print(res.decode())
        ip = res.split(b'\r\n')[-2][1:-1].split(b', ')[0][1:-1].decode()
        print(ip)

        # Start run()
        ser.write(b'run()\r\n')

        return ip


def update_wifi():
    global paused, target_ip

    paused = True
    for i in range(20):
        devices = [x.device for x in list_ports.comports()]
        if devices:
            print(devices)
            break
        sleep(0.1)

    port = com_port_.get()
    ssid = ssid_.get()
    psk = password_.get()

    sleep(1)
    target_ip = setup_wifi(ssid, psk, port)
    with open('target_ip.txt', 'w') as f:
        f.write(target_ip)
    paused = False


def stop():
    global run, win
    win.destroy()
    win.quit()
    run = False


audio_thread = Thread(target=audio_worker)
audio_thread.start()

udp_thread = Thread(target=udp_worker)
udp_thread.start()

row = tk.Frame(win)
row.pack(fill=tk.X, expand=True)
tk.Label(row, text='Overall Brightness').pack(side=tk.LEFT)
tk.Scale(row, variable=brightness_, from_=0, to=100, length=500, orient=tk.HORIZONTAL).pack(side=tk.RIGHT)
row = tk.Frame(win)
row.pack(fill=tk.X, expand=True)
tk.Label(row, text='Microphone Sensitivity').pack(side=tk.LEFT)
tk.Scale(row, variable=overall_gain_, from_=0, to=100, length=500, orient=tk.HORIZONTAL).pack(side=tk.RIGHT)
row = tk.Frame(win)
row.pack(fill=tk.X, expand=True)
tk.Label(row, text='Bass Level').pack(side=tk.LEFT)
tk.Scale(row, variable=bass_gain_, from_=0, to=100, length=500, orient=tk.HORIZONTAL).pack(side=tk.RIGHT)
row = tk.Frame(win)
row.pack(fill=tk.X, expand=True)
tk.Label(row, text='Mid Level').pack(side=tk.LEFT)
tk.Scale(row, variable=mid_gain_, from_=0, to=100, length=500, orient=tk.HORIZONTAL).pack(side=tk.RIGHT)
row = tk.Frame(win)
row.pack(fill=tk.X, expand=True)
tk.Label(row, text='Treble Level').pack(side=tk.LEFT)
tk.Scale(row, variable=treble_gain_, from_=0, to=100, length=500, orient=tk.HORIZONTAL).pack(side=tk.RIGHT)
row = tk.Frame(win)
row.pack(fill=tk.X, expand=True)
tk.Label(row, text='Gamma Correction').pack(side=tk.LEFT)
tk.Scale(row, variable=gamma_, from_=0.0, to=5.0, resolution=0.1, length=500, orient=tk.HORIZONTAL).pack(side=tk.RIGHT)

row = tk.Frame(win)
row.pack(fill=tk.X, expand=True)
tk.Label(row, text='COM Port').pack(side=tk.LEFT)
tk.OptionMenu(row, com_port_, com_port_.get(), *port_options).pack(side=tk.LEFT)
tk.Label(row, text='WiFI SSID').pack(side=tk.LEFT)
tk.Entry(row, textvariable=ssid_).pack(side=tk.LEFT)
tk.Label(row, text='WiFI Password').pack(side=tk.LEFT)
tk.Entry(row, textvariable=password_).pack(side=tk.LEFT)
tk.Button(row, text='Update', command=update_wifi).pack(side=tk.LEFT)

win.protocol("WM_DELETE_WINDOW", stop)
win.mainloop()
