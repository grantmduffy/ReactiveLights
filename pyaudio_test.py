import pyaudio
import numpy as np
from matplotlib import pyplot as plt
from matplotlib import animation
from threading import Thread, Lock
from matplotlib.colors import hsv_to_rgb

buffer_size = 512
sample_rate = 16000
led_n = 50
bass_gain = 6.0
mid_gain = 2.0
treble_gain = 10.0

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
bass = np.zeros(buffer_size)
mid = np.zeros(buffer_size)
treble = np.zeros(buffer_size)
hsv_values = np.ones((led_n, 3))
hsv_values[:, 0] = np.linspace(0, 1, led_n)

scat = plt.scatter(np.arange(led_n) * 3 / 50, np.zeros(led_n), c=np.zeros((led_n, 3)))
levels_line = plt.plot([0, 1, 2, 3], [0, 0, 0, 0])[0]
plt.ylim(-0.1, 1)

# ax1 = plt.subplot(211)
# fft_line = plt.plot(freq, amp)[0]
# plt.ylim(0, 10)
# ax2 = plt.subplot(212)
# bass_line = plt.plot([], label='Bass')[0]
# mid_line = plt.plot([], label='Mid Range')[0]
# treble_line = plt.plot([], label='Treble')[0]
# plt.legend()


def audio_worker():
    global wave, amp, bass, mid, treble, levels
    while run:
        wave = np.fromstring(stream.read(buffer_size), np.float32)
        amp = np.abs(np.fft.fft(wave))
        bass = np.average(amp[freq < bass_mid_freq])
        mid = np.average(amp[(freq < mid_treble_freq) * (freq > bass_mid_freq)])
        treble = np.average(amp[(freq > mid_treble_freq)])
        levels.append((bass, mid, treble))
    stream.close()


def animate(i):

    current_levels = [bass * bass_gain, mid * mid_gain, treble * treble_gain, bass * bass_gain]
    lightness = np.interp(np.linspace(0, 3, led_n), [0, 1, 2, 3], current_levels)
    # scat.set_color(np.ones((led_n, 3)) * lightness)
    rgb_values = hsv_to_rgb(hsv_values)
    rgb_values[lightness <= 0.5] *= (lightness[lightness <= 0.5] * 2).reshape((-1, 1))
    # rgb_values[lightness > 0.5] *= (1 - lightness[lightness > 0.5] * 2).reshape((-1, 1)) \
    #                                + np.ones((led_n, 3))[lightness > 0.5]

    a = (lightness[lightness > 0.5] * 2 - 1).reshape((-1, 1))
    print(a.shape, rgb_values[lightness > 0.5].shape)
    rgb_values[lightness > 0.5] = (1 - a) * rgb_values[lightness > 0.5] + a * np.ones((led_n, 3))[lightness > 0.5]
    rgb_values[rgb_values > 1.0] = 1.0
    rgb_values[rgb_values < 0.0] = 0.0
    print(np.max(rgb_values), np.min(rgb_values))
    scat.set_color(rgb_values)
    levels_line.set_ydata(current_levels)
    return levels_line, scat

    # bass_arr, mid_arr, treble_arr = np.array(levels).T
    # frames = np.arange(len(bass_arr))
    # fft_line.set_ydata(amp)
    # bass_line.set_data(frames, bass_arr)
    # mid_line.set_data(frames, mid_arr)
    # treble_line.set_data(frames, treble_arr)
    # ax2.set_xlim(0, len(bass_arr))
    # ax2.set_ylim(0, np.max([bass_arr, mid_arr, treble_arr]))
    # return fft_line,


audio_thread = Thread(target=audio_worker)
audio_thread.start()

ani = animation.FuncAnimation(plt.gcf(), animate)
plt.show()

run = False
