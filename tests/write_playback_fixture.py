"""Small original fixture covering pitched and noise-based percussion starts."""
from pathlib import Path
from slopwave.score import promote, save, digest
from slopwave.cli import arrange, mix, export

parts=dict(low=[[0,1,48,.4]],middle=[],high=[[0,.5,'c4',.4],[1.5,.5,'d4',.4]],
           kick=[[0,.12,36,.4],[2,.12,36,.4]],snare=[[1,.12,36,.4]],
           hat=[[at,.12,36,.3] for at in (.5,1.5,2.5,3.5)])
score=promote(dict(bpm=120,beats=4,source_audio_sha256=digest(parts),parts=parts),
              title='Playback check',source_id='original:playback-test',source_kind='authored',stage='reviewed')
mixed=mix(arrange(score,'synth'))
output=Path('build/playback-fixture'); output.mkdir(parents=True,exist_ok=True)
save(output/'score.json',mixed)
(output/'score.strudel.js').write_text(export(mixed))
# Negative control for manual diagnostics: the expected score still has this hit.
mixed['parts']['hat'].pop()
(output/'missing-hit.strudel.js').write_text(export(mixed))
