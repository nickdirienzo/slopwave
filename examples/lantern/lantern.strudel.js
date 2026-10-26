// Lantern — slopwave
// Input score SHA-256: af3f2efce7284baaa49aece96a918ed17e56a475be336d7a161e12072e82b240
// Research arrangement; listening evaluation is separate from execution checks.
// Paste the entire file into https://strudel.cc to play.

const BPM = 112.000000;
const BEATS = 32.00000000; // full recording; repeats from the beginning
setcpm(BPM / 4);

// Mix controls: set a part to 0 to mute it.
const mix = { low: 0.24, middle: 0.08, high: 0.3, drums: 0.14 };

// Events: [start beat, duration in beats, note name/MIDI, relative level].
// Unequal spacing preserves the detected timing instead of forcing a grid.
// Schedule only the current bar so fast phrases do not lose note attacks.
const phrase = events => {
  const ticks = 100000;
  const bars = Array.from({ length: Math.ceil(BEATS / 4) }, () => []);
  const widths = bars.map((_, bar) => Math.round(Math.min(4, BEATS - bar * 4) * ticks));
  for (const [at, len, pitch, level] of events) {
    const bar = Math.floor(at / 4);
    const start = Math.round((at - bar * 4) * ticks);
    const duration = Math.round(Math.min(len, BEATS - at) * ticks);
    const span = Math.min(duration, widths[bar] - start);
    if (span <= 0) continue;
    bars[bar].push(timecat(...[
      [start, silence],
      [span, note(pitch).gain(level).legato(duration / span)],
      [widths[bar] - start - span, silence]
    ].filter(([length]) => length > 0)));
  }
  const patterns = bars.map(events => events.length ? stack(...events) : silence);
  if (BEATS % 4 === 0) return cat(...patterns);
  const padded = patterns.map((pattern, bar) => widths[bar] === 4 * ticks
    ? pattern : pattern.compress(0, widths[bar] / (4 * ticks)));
  return cat(...padded).fast(padded.length)
    .zoom(0, BEATS / (4 * padded.length)).slow(BEATS / 4);
};

const low = [
  [0,1.6,"d2",0.55], [2.5,0.8,"d2",0.38], [4,1.6,"d2",0.55], [6.5,0.8,"d2",0.38],
  [8,1.6,"c2",0.55], [10.5,0.8,"c2",0.38], [12,1.6,"g2",0.55], [14.5,0.8,"g2",0.38],
  [16,1.6,"d2",0.55], [18.5,0.8,"d2",0.38], [20,1.6,"f2",0.55], [22.5,0.8,"f2",0.38],
  [24,1.6,"g2",0.55], [26.5,0.8,"g2",0.38], [28,1.6,"d2",0.55], [30.5,0.8,"d2",0.38]
];

const middle = [
  [0.5,2.5,"a3",0.147], [0.5,2.5,"f3",0.147], [4.5,2.5,"a3",0.1615], [4.5,2.5,"e3",0.1615],
  [8.5,2.5,"e3",0.1615], [8.5,2.5,"g3",0.1615], [12.5,2.5,"b3",0.1615], [12.5,2.5,"d4",0.1615],
  [16.5,2.5,"a3",0.147], [16.5,2.5,"f3",0.147], [20.5,2.5,"a3",0.1615], [20.5,2.5,"c4",0.1615],
  [24.5,2.5,"b3",0.1615], [24.5,2.5,"d4",0.1615], [28.5,2.5,"a3",0.1615], [28.5,2.5,"f3",0.1615]
];

const high = [
  [0,0.75,"d4",0.562], [1,0.5,"a4",0.48], [1.75,0.25,"g4",0.48], [2,1.5,"e4",0.562],
  [3.5,1,"f4",0.48], [5,0.5,"e4",0.48], [5.75,0.75,"d4",0.562], [7,0.5,"a3",0.48],
  [8,0.5,"c4",0.48], [8.75,0.5,"e4",0.562], [9.5,1,"g4",0.48], [11,0.5,"e4",0.48],
  [12,1.5,"b3",0.562], [14,0.5,"d4",0.48], [14.75,0.75,"e4",0.48], [16,0.75,"d4",0.562],
  [17,0.5,"a4",0.48], [17.75,0.25,"b4",0.48], [18,1.5,"g4",0.562], [19.5,1,"e4",0.48],
  [21,0.5,"f4",0.48], [21.75,0.75,"e4",0.562], [23,0.5,"c4",0.48], [24,0.5,"b3",0.48],
  [24.75,0.5,"d4",0.562], [25.5,1,"g4",0.48], [27,0.5,"e4",0.48], [28,1,"a3",0.562],
  [29.5,2,"d4",0.48]
];

const kick = [

];

const snare = [

];

const hat = [

];

stack(
  phrase(low).s("sine").lpf(900).attack(0.005).release(0.05).mul(gain(mix.low)),
  phrase(middle).s("triangle").lpf(2400).attack(0.035).release(0.1).mul(gain(mix.middle)),
  phrase(high).s("triangle").lpf(4500).attack(0.006).release(0.08).mul(gain(mix.high)),
  phrase(kick).s("sine").freq(65).penv(18).pdecay(0.045)
    .decay(0.12).sustain(0).mul(gain(mix.drums)),
  phrase(snare).s("white").hpf(900).lpf(5500)
    .decay(0.085).sustain(0).mul(gain(mix.drums * 0.35)),
  phrase(hat).s("white").hpf(6500)
    .decay(0.025).sustain(0).mul(gain(mix.drums * 0.12))
)
