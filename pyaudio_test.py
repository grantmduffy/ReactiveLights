import pyaudio
import numpy as np
from matplotlib import pyplot as plt

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

while True:
    wave = np.fromstring(stream.read(buffer_size), np.float32)
    amp = np.abs(np.fft.fft(wave))
    bass = np.average(amp[freq < bass_mid_freq])
    mid = np.average(amp[(freq < mid_treble_freq) * (freq > bass_mid_freq)])
    treble = np.average(amp[(freq > mid_treble_freq)])

    plt.subplot(311)
    plt.gca().clear()
    plt.title('Audio Wave')
    plt.ylabel('Value')
    plt.ylabel('Samples')
    plt.plot(wave)
    plt.subplot(312)
    plt.gca().clear()
    plt.title('Frequencies')
    plt.xlabel('Magnitude')
    plt.ylabel('Frequency')
    plt.plot(np.log10(np.abs(freq)), amp)
    plt.subplot(313)
    plt.gca().clear()
    plt.title('Levels')
    plt.bar([0, 1, 2], [bass, mid, treble])
    plt.xticks([0, 1, 2], ['Bass', 'Mid Range', 'Treble'])
    plt.pause(0.01)
