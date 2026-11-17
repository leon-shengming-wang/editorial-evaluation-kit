'use strict';
const data = JSON.parse(document.getElementById('data').textContent),
    audio = document.getElementById('audio'),
    edits = {},
    decisions = {};
let dirty = false;
const el = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
};
const seek = t => {
    audio.currentTime = Math.max(0, Math.min(data.duration, t));
};
[
    [data.duration.toFixed(1) + 's', 'recording'],
    [data.segments.length, 'segments'],
    [data.flags.length, 'review candidates']
].forEach(([n, label]) => {
    const box = el('div');
    box.append(el('strong', n), el('span', label));
    document.getElementById('summary').append(box);
});
document.getElementById('model').textContent = [data.engine, data.engine_version, data.model, data.language, 'CPU int8'].join(' / ');
const timed = [];
data.segments.forEach((s, i) => {
    const row = el('article', undefined, 'segment'),
        button = el('button', s.start.toFixed(2) + '–' + s.end.toFixed(2) + 's');
    button.onclick = () => seek(s.start);
    row.append(button);
    const words = el('p');
    if (!s.words.length) words.textContent = s.text;
    s.words.forEach(w => {
        const n = el('button', w.word, 'word');
        n.title = w.start.toFixed(2) + '–' + w.end.toFixed(2) + 's';
        n.onclick = () => seek(w.start);
        words.append(n);
        timed.push([n, w]);
    });
    row.append(words);
    const detail = el('details');
    detail.append(el('summary', 'Review / propose a correction'));
    const label = el('label', 'Corrected transcript (original retained)');
    label.htmlFor = 'edit-' + i;
    const edit = el('textarea');
    edit.id = 'edit-' + i;
    edit.value = s.text;
    edit.oninput = () => {
        edits[i] = edit.value;
        dirty = true;
    };
    detail.append(label, edit);
    row.append(detail);
    document.getElementById('transcript').append(row);
});
if (!data.segments.length) document.getElementById('transcript').append(el('p', 'No speech was transcribed. Listen; this is not proof of silence.'));
data.flags.forEach((f, i) => {
    const box = el('div', undefined, 'flag');
    box.append(el('span', f.kind, 'badge'), el('p', f.evidence));
    const btn = el('button', 'Listen ' + f.start.toFixed(2) + '–' + f.end.toFixed(2) + 's');
    btn.onclick = () => seek(f.start - .5);
    const label = el('label', ' Review decision '),
        select = el('select');
    select.setAttribute('aria-label', 'Decision for flag ' + (i + 1));
    ['unreviewed', 'confirmed', 'dismissed', 'uncertain'].forEach(v => {
        const o = el('option', v);
        o.value = v;
        select.append(o);
    });
    const notes = el('textarea');
    notes.placeholder = 'Evidence or rationale';
    notes.setAttribute('aria-label', 'Rationale for flag ' + (i + 1));
    const capture = () => {
        decisions[i] = {
            state: select.value,
            note: notes.value
        };
        dirty = true;
    };
    select.onchange = capture;
    notes.oninput = capture;
    label.append(select);
    box.append(btn, label, notes);
    document.getElementById('flags').append(box);
});
if (!data.flags.length) document.getElementById('flags').append(el('p', 'No heuristic flags. Listen for errors the rules cannot detect.'));
const reference = document.getElementById('reference');
if (data.reference_comparison) {
    reference.append(el('p', data.reference_comparison.note));
    data.reference_comparison.differences.forEach(d => {
        const box = el('div', undefined, 'flag');
        box.append(el('strong', d.operation), el('p', 'Expected: ' + (d.reference || '(none)')), el('p', 'Recognized: ' + (d.recognized || '(none)')));
        reference.append(box);
    });
    if (!data.reference_comparison.differences.length) reference.append(el('p', 'Normalized text matches the supplied reference. Timing and delivery still require review.'));
} else reference.append(el('p', 'No expected script supplied. Content omissions cannot be established from transcription alone.'));
const {
    segments,
    flags,
    speech_spans,
    reference_comparison,
    ...meta
} = data;
document.getElementById('provenance').textContent = JSON.stringify(meta, null, 2);

function sync() {
    document.getElementById('clock').textContent = audio.currentTime.toFixed(2) + 's';
    timed.forEach(([n, w]) => n.classList.toggle('active', audio.currentTime >= w.start && audio.currentTime < w.end));
}
['timeupdate', 'seeked', 'pause', 'ended'].forEach(e => audio.addEventListener(e, sync));
document.getElementById('speed').onchange = e => {
    audio.playbackRate = Number(e.target.value);
};
audio.addEventListener('error', () => {
    document.getElementById('status').textContent = 'Browser could not decode embedded audio. Try current Chrome, Firefox or Safari.';
});
document.getElementById('export').onclick = () => {
    const payload = {
        ...data,
        review: {
            exported_at: new Date().toISOString(),
            edits,
            decisions,
            note: 'Human-entered corrections and decisions, not model-certified results.'
        }
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
            type: 'application/json'
        }),
        url = URL.createObjectURL(blob),
        a = el('a');
    a.href = url;
    a.download = 'speech-qa-review.json';
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
    document.getElementById('status').textContent = 'Download requested. Verify the file is saved before closing.';
};
window.addEventListener('beforeunload', e => {
    if (dirty) {
        e.preventDefault();
        e.returnValue = '';
    }
});

// Animation frames keep short word highlights responsive; timing still comes only from audio.
let animationFrame = null;
function animatePlayhead() {
    sync();
    if (!audio.paused && !audio.ended) animationFrame = requestAnimationFrame(animatePlayhead);
    else animationFrame = null;
}
audio.addEventListener('play', () => {
    if (animationFrame === null) animationFrame = requestAnimationFrame(animatePlayhead);
});
