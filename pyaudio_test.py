import pyaudio
import numpy as np
from matplotlib import pyplot as plt
from matplotlib import animation
from threading import Thread, Lock
from matplotlib.colors import hsv_to_rgb
import socket
from time import sleep
import tkinter as tk
import sys


buffer_size = 512
sample_rate = 16000
led_n = 50
# bass_gain = 0.5
# mid_gain = 2.0
# treble_gain = 10.0
# overall_gain = 0.15
# gamma = 3.0
fade_rate = 0.003


win = tk.Tk()
win.title('Reactive Light Settings')
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
levels = []
wave = np.zeros(buffer_size)
amp = np.zeros(buffer_size)
bass = 0
mid = 0
treble = 0
hsv_values = np.ones((led_n, 3))
hsv_values[:, 0] = np.linspace(0, 1, led_n)
rgb_values = np.zeros((led_n, 3))

scat = plt.scatter(np.arange(led_n) * 3 / 50, np.zeros(led_n), c=np.zeros((led_n, 3)))
levels_line = plt.plot([0, 1, 2, 3], [0, 0, 0, 0])[0]
hsv_line = plt.plot(np.linspace(0, 3, led_n), hsv_values[:, 0])[0]
plt.ylim(-0.1, 1.1)


def audio_worker():
    global wave, amp, bass, mid, treble, levels, run
    while run:
        wave = np.fromstring(stream.read(buffer_size), np.float32)
        amp = np.abs(np.fft.fft(wave)) * overall_gain_.get() / 100
        bass = np.average(amp[freq < bass_mid_freq])
        mid = np.average(amp[(freq < mid_treble_freq) * (freq > bass_mid_freq)])
        treble = np.average(amp[(freq > mid_treble_freq)])
        # print(bass.shape, mid.shape, treble.shape)
        levels.append((bass, mid, treble))
    stream.close()


def udp_worker():
    global rgb_values, hsv_values, run
    while run:
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

        data = np.zeros(512, dtype=np.uint8)
        data[:led_n * 3] = (rgb_values.flatten() * 255).astype(np.uint8)
        packet = b'Art-Net\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + data.tobytes()

        s.sendto(packet, ('192.168.0.34', 6454))
        sleep(1/20)


def animate(i):
    current_levels = np.array([bass * bass_gain_.get() / 10, mid * mid_gain_.get() / 10,
                               treble * treble_gain_.get() / 10, bass * bass_gain_.get() / 10])
    scat.set_color(rgb_values)
    levels_line.set_ydata(current_levels)
    hsv_line.set_ydata(hsv_values[:, 0])
    return levels_line, scat


def stop():
    global run, win
    win.destroy()
    win.quit()
    run = False


audio_thread = Thread(target=audio_worker)
audio_thread.start()

udp_thread = Thread(target=udp_worker)
udp_thread.start()

# ani = animation.FuncAnimation(plt.gcf(), animate)
# plt.show()

row = tk.Frame(win)
row.pack(fill=tk.X, expand=True)
tk.Label(row, text='Overall Brightness').pack(side=tk.LEFT)
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
win.protocol("WM_DELETE_WINDOW", stop)
win.mainloop()

# while True:
#     try:
#         sleep(10)
#     except KeyboardInterrupt:
#         run = False
