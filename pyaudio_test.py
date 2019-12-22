import pyaudio
import numpy as np
from matplotlib import pyplot as plt
from matplotlib import animation
from threading import Thread

buffer_size = 512
sample_rate = 16000

pa = pyaudio.PyAudio()
stream = pa.open(
    format=pyaudio.paFloat32,
    channels=1,
    rate=sample_rate,
    frames_per_buffer=buffer_size,
    input=True,
    output=False
)

freq = np.abs(np.fft.fftfreq(buffer_size, d=1.0 / sample_rate))
bass_mid_freq = 250.0
mid_treble_freq = 4000.0
run = True
levels = []
wave = np.zeros(buffer_size)
amp = np.zeros(buffer_size)
bass = np.zeros(buffer_size)
mid = np.zeros(buffer_size)
treble = np.zeros(buffer_size)

fft_line = plt.plot(freq, amp)[0]
plt.ylim(0, 10)



def audio_worker():
    global wave, amp, bass, mid, treble, levels
    while run:
        wave = np.fromstring(stream.read(buffer_size), np.float32)
        amp = np.abs(np.fft.fft(wave))
        bass = np.average(amp[freq < bass_mid_freq])
        mid = np.average(amp[(freq < mid_treble_freq) * (freq > bass_mid_freq)])
        treble = np.average(amp[(freq > mid_treble_freq)])
        levels.append((bass, mid, treble))


def animate(i):
    fft_line.set_ydata(amp)
    return fft_line,


audio_thread = Thread(target=audio_worker)
audio_thread.start()
ani = animation.FuncAnimation(plt.gcf(), animate, blit=True)
plt.show()
