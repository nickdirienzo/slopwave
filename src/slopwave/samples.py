"""Freeze declared one-shot assets into a portable, hashed score snapshot."""
import base64
from copy import deepcopy
import hashlib
import math
from pathlib import Path
import re
from urllib.parse import urlparse
from urllib.request import urlopen

MAX_SAMPLE_BYTES = 16 * 1024 * 1024


def snapshot_samples(score, directory):
    if score.get('soundfonts'):
        raise ValueError('Session rendering needs explicit sample_buffers; network soundfont presets '
                         'are supported by REPL/module exports, not the offline renderer')
    result = deepcopy(score)
    for name, definition in result.get('sample_buffers', {}).items():
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name):
            raise ValueError('Sample names must be plain identifiers')
        seconds = definition.get('seconds')
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds <= 0:
            raise ValueError(f'{name}: sample seconds must be positive and finite')
        uri = definition['url']
        if uri.startswith('data:'):
            header, encoded = uri.split(',', 1)
            if not re.fullmatch(r'data:audio/[\w.+-]+;base64', header):
                raise ValueError('Samples must be base64 audio data URLs')
            if len(encoded) > (MAX_SAMPLE_BYTES + 2) // 3 * 4:
                raise ValueError('Sample exceeds 16 MiB')
            payload = base64.b64decode(encoded, validate=True)
            mime = header[5:-7]
        elif urlparse(uri).scheme:
            if urlparse(uri).scheme != 'https':
                raise ValueError('Remote sample URLs must use HTTPS')
            with urlopen(uri, timeout=30) as response:
                if urlparse(response.url).scheme != 'https':
                    raise ValueError('Sample redirects must stay on HTTPS')
                payload = response.read(MAX_SAMPLE_BYTES + 1)
                mime = response.headers.get_content_type()
        else:
            path = Path(directory) / uri
            if path.stat().st_size > MAX_SAMPLE_BYTES:
                raise ValueError('Sample exceeds 16 MiB')
            payload = path.read_bytes()
            mime = 'audio/wav' if payload.startswith(b'RIFF') else 'audio/mpeg'
        if not payload or len(payload) > MAX_SAMPLE_BYTES:
            raise ValueError('Sample must contain 1 byte to 16 MiB')
        sha = hashlib.sha256(payload).hexdigest()
        if definition.get('sha256') and definition['sha256'] != sha:
            raise ValueError(f'{name}: sample SHA-256 mismatch')
        definition.setdefault('origin', uri if not uri.startswith('data:') else 'embedded')
        definition['sha256'] = sha
        definition['url'] = f'data:{mime if mime.startswith("audio/") else "audio/wav"};base64,' + base64.b64encode(payload).decode()
    return result
