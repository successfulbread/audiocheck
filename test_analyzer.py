"""Synthetic controls for basic detector behaviour, not real-world accuracy."""
import sys
import unittest
from pathlib import Path
import tempfile

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyzer import (
    SAMPLE_RATE, _click_candidates, _consolidate_broadcast,
    _consolidate_electrical, _consolidate_vinyl, _spectrum_window,
    _vinyl_window, _windows, analyze_path, _dropout_candidates, _pilot_variation_hz,
)

RATE = SAMPLE_RATE
RNG = np.random.default_rng(901)


def base_audio(seconds=38.0):
    n = int(RATE * seconds)
    t = np.arange(n) / RATE
    x = .002 * RNG.normal(size=n) + .028 * np.sin(2 * np.pi * 277 * t)
    return np.column_stack([x, x]).astype(np.float32)


def add_ticks(x, rpm):
    interval = 60 / rpm
    for moment in np.arange(.9, len(x)/RATE-0.5, interval):
        i = int(moment * RATE)
        x[i:i+6, :] += np.array([.22, -.14, .07, -.08, .03, 0], dtype=np.float32)[:, None]
    return x


def musical_drums(x, bpm=90):
    interval = 60 / bpm
    n = int(.075 * RATE)
    t = np.arange(n) / RATE
    sound = .15 * np.sin(2*np.pi*150*t) * np.exp(-t*50)
    for moment in np.arange(.5, len(x)/RATE-.2, interval):
        i = int(moment*RATE)
        x[i:i+n] += sound[:, None]
    return x


class AudiocheckChecks(unittest.TestCase):
    def test_window_spreading(self):
        for duration in (10, 30, 55, 100, 150, 300):
            samples = _windows(duration)
            self.assertTrue(1 <= len(samples) <= 4)
            self.assertTrue(sum(s for _, s in samples) <= 161)
            self.assertLessEqual(samples[-1][0]+samples[-1][1], duration+.001)
            if len(samples) > 1:
                self.assertGreaterEqual(samples[-1][0], duration / 2)

    def test_vinyl_45(self):
        data = add_ticks(base_audio(), 45)
        result = _vinyl_window(data)
        print('vinyl45', result)
        self.assertIsNotNone(result)
        self.assertEqual(result['rpm'], 45.0)

    def test_vinyl_33(self):
        data = add_ticks(base_audio(), 33.333333)
        result = _vinyl_window(data)
        print('vinyl33', result)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['rpm'], 33.333, places=2)

    def test_vinyl_78(self):
        data = add_ticks(base_audio(), 78)
        result = _vinyl_window(data)
        print('vinyl78', result)
        self.assertIsNotNone(result)
        self.assertEqual(result['rpm'], 78.0)

    def test_vinyl_noise_negative(self):
        data = base_audio()
        self.assertIsNone(_vinyl_window(data))

    def test_vinyl_drums_negative(self):
        data = musical_drums(base_audio())
        result = _vinyl_window(data)
        print('vinyl drums', result)
        self.assertIsNone(result)

    def test_mains_50_and_60(self):
        for base in (50, 60):
            data = base_audio(30)
            t = np.arange(len(data)) / RATE
            for harmonic, level in ((1,.006),(2,.003),(3,.002)):
                data += (level*np.sin(2*np.pi*base*harmonic*t)).astype('float32')[:,None]
            mains, air, cutoff = _spectrum_window(data, RATE)
            print('mains', base, mains)
            result = _consolidate_electrical([{'mains': mains}])
            self.assertIn(f'{base} Hz', result['result'])

    def test_single_60hz_is_not_mains_family(self):
        data = base_audio(30)
        t = np.arange(len(data)) / RATE
        data += (.01*np.sin(2*np.pi*60*t)).astype('float32')[:,None]
        mains, air, cutoff = _spectrum_window(data, RATE)
        result = _consolidate_electrical([{'mains': mains}])
        print('single 60', result)
        self.assertEqual(result['result'], 'Unclear')

    def test_noise_is_not_mains_or_broadcast(self):
        data = base_audio(30)
        mains, air, cutoff = _spectrum_window(data, RATE)
        self.assertEqual(_consolidate_electrical([{'mains': mains}])['result'], 'Unclear')
        self.assertEqual(_consolidate_broadcast([{'broadcast': air}])['result'], 'Unclear')

    def test_fm_tone(self):
        data = base_audio(30)
        t = np.arange(len(data)) / RATE
        data += (.006*np.sin(2*np.pi*19000*t)).astype('float32')[:,None]
        mains, air, cutoff = _spectrum_window(data, RATE)
        print('fm tone', air['FM stereo pilot'])
        result = _consolidate_broadcast([{'broadcast': air}])
        self.assertEqual(result['result'], 'FM stereo pilot')

    def test_tv_tone(self):
        data = base_audio(30)
        t = np.arange(len(data)) / RATE
        data += (.006*np.sin(2*np.pi*15625*t)).astype('float32')[:,None]
        mains, air, cutoff = _spectrum_window(data, RATE)
        result = _consolidate_broadcast([{'broadcast': air}])
        print('tv', result)
        self.assertEqual(result['result'], '625-line TV')

    def test_beta_dropout_candidate(self):
        data = base_audio(30)
        data[int(12*RATE):int(12.25*RATE), :] = 0
        self.assertGreaterEqual(_dropout_candidates(data), 1)

    def test_beta_pilot_variation(self):
        data = base_audio(30)
        t = np.arange(len(data)) / RATE
        data += (.006*np.sin(2*np.pi*19000*t)).astype('float32')[:,None]
        value = _pilot_variation_hz(data)
        self.assertIsNotNone(value)
        self.assertLess(value, 1.5)

    def test_short_sample_rate_disables_fm(self):
        data = base_audio(30)
        mains, air, cutoff = _spectrum_window(data, 22050)
        self.assertIsNone(air['FM stereo pilot'])

    def test_end_to_end_mono(self):
        with tempfile.TemporaryDirectory() as temp:
            wav = Path(temp) / 'short.wav'
            n = RATE * 12
            x = (.05*np.sin(2*np.pi*300*np.arange(n)/RATE))
            wavfile.write(wav, RATE, (x*32767).astype(np.int16))
            results, info = analyze_path(wav)
            self.assertEqual(results[-1][1]['result'], 'Mono')
            self.assertAlmostEqual(info['duration'], 12., places=1)


if __name__ == '__main__':
    unittest.main()
