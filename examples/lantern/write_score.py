"""Author the Lantern fixture from explicit notes, not from a recording or model.

CC0-1.0. This is a small composition fixture, not a music-generation algorithm.
"""
from pathlib import Path
from slopwave.score import digest, promote, save

parts = {p: [] for p in ('low','middle','high','kick','snare','hat')}
# Eight bars in D dorian. Deliberate rests, repeated attacks, and a bar-crossing hold.
melody = [
 (0,.75,'d4'),(1,.5,'a4'),(1.75,.25,'g4'),(2,1.5,'e4'),(3.5,1,'f4'),
 (5,.5,'e4'),(5.75,.75,'d4'),(7,.5,'a3'),
 (8,.5,'c4'),(8.75,.5,'e4'),(9.5,1,'g4'),(11,.5,'e4'),
 (12,1.5,'b3'),(14,.5,'d4'),(14.75,.75,'e4'),
 (16,.75,'d4'),(17,.5,'a4'),(17.75,.25,'b4'),(18,1.5,'g4'),(19.5,1,'e4'),
 (21,.5,'f4'),(21.75,.75,'e4'),(23,.5,'c4'),
 (24,.5,'b3'),(24.75,.5,'d4'),(25.5,1,'g4'),(27,.5,'e4'),
 (28,1,'a3'),(29.5,2,'d4')]
parts['high'] = [[at,length,note,.48 if i%3 else .58] for i,(at,length,note) in enumerate(melody)]
for bar,(bass,dyad) in enumerate([
 ('d2',('f3','a3')),('d2',('e3','a3')),('c2',('e3','g3')),('g2',('b3','d4')),
 ('d2',('f3','a3')),('f2',('a3','c4')),('g2',('b3','d4')),('d2',('f3','a3'))]):
 at=bar*4
 parts['low'] += [[at,1.6,bass,.55],[at+2.5,.8,bass,.38]]
 for n in dyad: parts['middle'].append([at+.5,2.5,n,.21])
source_hash = digest(parts)
score = promote(dict(bpm=112,beats=32,source_audio_sha256=source_hash,parts=parts),
                title='Lantern',source_id='original:lantern-v1',source_kind='authored',stage='reviewed')
score['provenance'].update(license='CC0-1.0',authorship='New explicit note study authored for this repository with agent assistance; no reference recording.',
                         hash_basis='Canonical parts JSON, not audio bytes')
score['status']='Authored fixture; no source-transcription accuracy claim; listening evaluation pending'
save(Path(__file__).with_name('score.json'),score)
