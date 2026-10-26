"""Lightweight Strudel exporter; no transcription models are loaded here."""
import json
from pathlib import Path

ROOT = Path.cwd()  # Only legacy research helpers use this; public APIs take paths.


def note_name(midi):
    return ['c','cs','d','ds','e','f','fs','g','gs','a','as','b'][midi % 12] + str(midi//12-1)


def format_events(events):
    rows = []
    for i in range(0, len(events), 4):
        rows.append('  ' + ', '.join(json.dumps(row, separators=(',', ':')) for row in events[i:i+4]))
    return '[\n' + ',\n'.join(rows) + '\n]'


def strudel_source(track, data):
    text = f'''// {track['title']} — {track.get('collection', 'slopwave')}
// Source: {track['youtube']}
// Machine-transcribed synth draft; listening review is still needed.
// Pitch registers are grouped heuristically, NOT separated instrument stems.
// Percussion is inferred from spectral onsets. Original samples are not used.
// Paste this ENTIRE file into https://strudel.cc and press Play.

const BPM = {data['bpm']:.6f};
const BEATS = {data['beats']:.8f}; // one detected repeating passage
setcpm(BPM / 4);

// Mix controls: set a part to 0 to mute it.
const mix = {{ low: 0.26, middle: 0.13, high: 0.22, drums: 0.16 }};

// Events: [start beat, duration in beats, note name/MIDI, relative level].
// Unequal spacing preserves the detected timing instead of forcing a grid.
// Schedule only the current bar so fast phrases do not lose note attacks.
const phrase = events => {{
  const ticks = 100000;
  const bars = Array.from({{ length: Math.ceil(BEATS / 4) }}, () => []);
  const widths = bars.map((_, bar) => Math.round(Math.min(4, BEATS - bar * 4) * ticks));
  for (const [at, len, pitch, level] of events) {{
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
  }}
  const patterns = bars.map(events => events.length ? stack(...events) : silence);
  return BEATS % 4 === 0
    ? cat(...patterns)
    : timecat(...patterns.map((pattern, bar) => [widths[bar], pattern])).slow(BEATS / 4);
}};

'''
    for name, events in data['parts'].items():
        text += f'const {name} = {format_events(events)};\n\n'
    text += '''stack(
  phrase(low).s("triangle").lpf(850).attack(0.004).release(0.04).mul(gain(mix.low)),
  phrase(middle).s("triangle").lpf(2400).attack(0.006).release(0.07).mul(gain(mix.middle)),
  phrase(high).s("triangle").lpf(5000).attack(0.003).release(0.05).mul(gain(mix.high)),
  phrase(kick).s("sine").freq(65).penv(18).pdecay(0.045)
    .decay(0.12).sustain(0).mul(gain(mix.drums)),
  phrase(snare).s("white").hpf(900).lpf(5500)
    .decay(0.085).sustain(0).mul(gain(mix.drums * 0.45)),
  phrase(hat).s("white").hpf(6500)
    .decay(0.025).sustain(0).mul(gain(mix.drums * 0.20))
)
'''
    if data.get('mode') in ('full-song-stems', 'full-song-arrangement'):
        # timecat stacks every bar, which becomes costly on long partial-bar
        # recordings. Index into cat first, then crop only the trailing silence.
        text = text.replace('''  return BEATS % 4 === 0
    ? cat(...patterns)
    : timecat(...patterns.map((pattern, bar) => [widths[bar], pattern])).slow(BEATS / 4);''',
'''  if (BEATS % 4 === 0) return cat(...patterns);
  const padded = patterns.map((pattern, bar) => widths[bar] === 4 * ticks
    ? pattern : pattern.compress(0, widths[bar] / (4 * ticks)));
  return cat(...padded).fast(padded.length)
    .zoom(0, BEATS / (4 * padded.length)).slow(BEATS / 4);''')
        text = text.replace('// one detected repeating passage', '// full recording; repeats from the beginning')
        text = text.replace('// Pitch registers are grouped heuristically, NOT separated instrument stems.',
                            '// Voices: low = separated bass, middle = backing instruments, high = vocal melody.')
        text = text.replace('// Percussion is inferred from spectral onsets. Original samples are not used.',
                            '// Percussion follows the separated drum stem. Original samples and lyrics are not used.')
    if 'mix' in data:
        # Strudel's string-to-pattern transpiler rewrites quoted object keys.
        # Emit these fixed, known identifiers as JavaScript property names.
        mix = '{ ' + ', '.join(f"{name}: {data['mix'][name]}"
                              for name in ('low', 'middle', 'high', 'drums')) + ' }'
        text = text.replace('{ low: 0.26, middle: 0.13, high: 0.22, drums: 0.16 }', mix)
    if 'voices' in data:
        defaults = {
            'low': '.s("triangle").lpf(850).attack(0.004).release(0.04)',
            'middle': '.s("triangle").lpf(2400).attack(0.006).release(0.07)',
            'high': '.s("triangle").lpf(5000).attack(0.003).release(0.05)',
            'kick': '.s("sine").freq(65).penv(18).pdecay(0.045)\n    .decay(0.12).sustain(0)',
            'snare': '.s("white").hpf(900).lpf(5500)\n    .decay(0.085).sustain(0)',
            'hat': '.s("white").hpf(6500)\n    .decay(0.025).sustain(0)',
        }
        for part, settings in data['voices'].items():
            if (settings['sound'] not in ('sine', 'triangle', 'sawtooth', 'gm_piano', 'gm_string_ensemble_1',
                                         'gm_banjo', 'gm_acoustic_bass', 'gm_acoustic_guitar_steel', 'gm_woodblock')
                    and settings['sound'] not in data.get('sample_buffers', {})):
                raise ValueError('Unsupported synth')
            chain = f'.s("{settings["sound"]}")'
            chain += ''.join(f'.{key}({settings[key]})'
                             for key in ('n', 'hpf', 'lpf', 'bpf', 'bpq', 'noise', 'vib', 'vibmod', 'attack', 'decay', 'sustain', 'release', 'pan', 'room') if key in settings)
            text = text.replace(f'phrase({part}){defaults[part]}', f'phrase({part}){chain}')
    if 'drum_mix' in data:
        text = text.replace('mix.drums * 0.45', f'mix.drums * {data["drum_mix"]["snare"]}')
        text = text.replace('mix.drums * 0.20', f'mix.drums * {data["drum_mix"]["hat"]}')
    if 'soundfonts' in data:
        # A note at beat zero exposes a rounded-down loop boundary as an extra
        # onset at the end of queryArc. Retain full precision for derived scores.
        text = text.replace(f'const BEATS = {data["beats"]:.8f};', f'const BEATS = {data["beats"]!r};')
        pitches = {}
        for part, voice in data['voices'].items():
            preset = data['soundfonts'][voice['sound']]
            if voice['n'] != preset['n']:
                raise ValueError('Soundfont preload preset must match the voice variant')
            pitches.setdefault(preset['preset'], set()).update(row[2] for row in data['parts'][part])
        # Load every used pitch before starting: first-use network/decode latency
        # must not delay a note halfway through playback.
        from .refinement import midi_pitch
        loaders = []
        for preset, names in pitches.items():
            notes = sorted(midi_pitch(name) for name in names)
            loaders.append(f'  ...{json.dumps(notes)}.map(note => getFontBufferSource("{preset}", {{note}}, getAudioContext()))')
        preload = ('// Load the piano and strings before the first note (internet required).\n'
                   '// mini-off: preset identifiers are plain JavaScript strings.\n'
                   'const preload = [\n'+',\n'.join(loaders)+'\n];\n'
                   'await Promise.all(preload);\n// mini-on\n\n')
        text = text.replace('const BPM = ', preload+'const BPM = ', 1)
        text = text.replace('// Machine-transcribed synth draft; listening review is still needed.',
                            '// Piano-and-strings interpretation of reviewed notes; listening review pending.')
        text = text.replace('// Voices: low = separated bass, middle = backing instruments, high = vocal melody.',
                            '// Voices: low = supporting piano, middle = sustained strings, high = piano melody.')
        text = text.replace('// Percussion follows the separated drum stem. Original samples and lyrics are not used.',
                            '// Instrument samples use Strudel soundfonts. Original recording and lyrics are not used.')
        if data.get('arrangement', {}).get('profile', '').startswith('bluegrass'):
            text = text.replace('Load the piano and strings', 'Load the banjo, acoustic bass and guitar')
            if 'gm_woodblock' in data['soundfonts']:
                text = text.replace('Load the banjo, acoustic bass and guitar',
                                    'Load the banjo, acoustic bass, guitar and woodblock')
            text = text.replace('Piano-and-strings interpretation of reviewed notes', 'Bluegrass interpretation of source-inferred notes')
            text = text.replace('low = supporting piano, middle = sustained strings, high = piano melody',
                                'low = acoustic bass, middle = offbeat guitar, high = banjo melody and gap rolls')
            text = text.replace('// Unequal spacing preserves the detected timing instead of forcing a grid.',
                                '// Melody keeps source timing; composed bass, guitar and rolls follow the measured pulse.')
            if data['arrangement']['profile'] in ('bluegrass-riff-v2', 'bluegrass-drive-v3', 'bluegrass-continuity-v4', 'bluegrass-performance-v5'):
                text = text.replace('banjo melody and gap rolls', 'banjo melody and instrumental riff')
                text = text.replace('composed bass, guitar and rolls follow the measured pulse',
                                    'instrumental riff follows source attacks; quiet backing follows the measured pulse')
                if data['arrangement']['profile'] in ('bluegrass-drive-v3', 'bluegrass-continuity-v4', 'bluegrass-performance-v5'):
                    text = text.replace('middle = offbeat guitar', 'middle = rhythmic guitar')
                    text = text.replace('quiet backing follows the measured pulse', 'guitar and bass emphasize source accents')
                if data['arrangement']['profile'] == 'bluegrass-performance-v5':
                    text = text.replace('Melody keeps source timing', 'Reviewed banjo interpretation keeps retained note timing')
    if 'sample_buffers' in data:
        # Decode before Play scheduling begins, rather than losing first hits to
        # lazy sample loading. Register short, unpitched one-shots explicitly.
        preload = '''// Preload acoustic percussion (VCSL, CC0; internet required).
// mini-off: sample names and URLs are literal JavaScript strings.
const loadSampleBuffer = async uri => {
  const response = await fetch(uri);
  if (!response.ok) throw new Error(`Sample load failed: ${response.status}`);
  return getAudioContext().decodeAudioData(await response.arrayBuffer());
};
const sampleDefinitions = SAMPLE_DEFINITIONS;
const samplePreload = Object.entries(sampleDefinitions).map(async ([name, definition]) => {
  const buffer = await loadSampleBuffer(definition.url);
  registerSound(name, (time, value, onended) => {
    const ctx = getAudioContext();
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    const envelope = ctx.createGain();
    const end = time + Math.min(buffer.duration, definition.seconds);
    envelope.gain.setValueAtTime(1, time);
    envelope.gain.setValueAtTime(1, Math.max(time, end - .015));
    envelope.gain.linearRampToValueAtTime(0, end);
    source.connect(envelope);
    // Strudel owns the output envelope's downstream connections.
    source.onended = () => { source.disconnect(); onended(); };
    source.start(time);
    source.stop(end);
    return { node: envelope, stop: () => {}, nodes: { source: [source] } };
  }, { type: 'sample', prebake: true });
});
await Promise.all(samplePreload);
// mini-on

'''.replace('SAMPLE_DEFINITIONS', json.dumps(data['sample_buffers'], indent=2))
        text = text.replace('const BPM = ', preload+'const BPM = ', 1)
        text = text.replace(f'const BEATS = {data["beats"]:.8f};', f'const BEATS = {data["beats"]!r};')
    if data.get('arrangement', {}).get('profile') == 'kazoo-rock-v1':
        text = text.replace('Machine-transcribed synth draft; listening review is still needed.',
                            'Kazoo-like synth cover; listening review is still needed.')
        text = text.replace('low = separated bass, middle = backing instruments, high = vocal melody',
                            'low = bass, middle = supporting harmony, high = synthesized kazoo melody')
        text = text.replace('Original samples and lyrics are not used.',
                            'Drums use VCSL acoustic samples; original recording and lyrics are not used.')
    return text
