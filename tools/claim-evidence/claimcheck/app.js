'use strict';
const $ = id => document.getElementById(id);
const node = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
};
let report = null,
    stale = false,
    reviewDirty = false,
    sourceNumber = 0,
    inputRevision = 0;
const reviews = {};

function markStale() {
    inputRevision++;
    stale = true;
    if (report) {
        $('export').disabled = true;
        $('input-status').textContent = 'Inputs changed. Re-run analysis before exporting; existing results reflect the previous input.';
    }
}
async function request(path, payload) {
    const r = await fetch(path, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': document.querySelector('meta[name=csrf]').content
        },
        body: JSON.stringify(payload)
    });
    const d = await r.json();
    if (!r.ok) throw Error(d.error || 'Request failed');
    return d;
}

function sourceEditor(source = {}) {
    const box = node('div', undefined, 'source-editor'),
        id = ++sourceNumber;
    box.originalSource = source.original_source || ((source.retrieved_at || source.license) ? {
        title: source.title,
        url: source.url,
        license: source.license || null,
        retrieved_at: source.retrieved_at || null,
        last_modified_at: source.last_modified_at || null
    } : null);
    if (box.originalSource) box.originalSource = Object.freeze({
        ...box.originalSource
    });
    [
        ['title', 'Source title'],
        ['url', 'Original public HTTPS URL (not fetched)'],
        ['text', 'Source text or excerpt']
    ].forEach(([key, title]) => {
        const label = node('label', title),
            field = node(key === 'text' ? 'textarea' : 'input');
        field.id = 'source-' + id + '-' + key;
        field.dataset.key = key;
        field.value = source[key] || '';
        field.maxLength = key === 'text' ? 50000 : key === 'title' ? 300 : 2048;
        label.htmlFor = field.id;
        field.addEventListener('input', () => {
            box.sourceMetadata = {
                origin: 'User-edited source; retrieval attribution and dates cleared',
                retrieved_at: null,
                publication_date: null,
                last_modified_at: null,
                license: box.originalSource ? box.originalSource.license : null,
                original_source: box.originalSource
            };
            markStale();
        });
        box.append(label, field);
    });
    box.sourceMetadata = {
        origin: source.origin || 'User-supplied text; attribution not independently verified',
        retrieved_at: source.retrieved_at || null,
        publication_date: source.publication_date || null,
        license: source.license || null,
        last_modified_at: source.last_modified_at || null,
        original_source: box.originalSource
    };
    const remove = node('button', 'Remove source');
    remove.onclick = () => {
        box.remove();
        markStale();
    };
    box.append(remove);
    $('sources').append(box);
}

function readSources() {
    return [...$('sources').children].map(box => {
        const source = {
            ...box.sourceMetadata
        };
        box.querySelectorAll('[data-key]').forEach(f => source[f.dataset.key] = f.value);
        return source;
    });
}
$('add-source').onclick = () => {
    if ($('sources').children.length >= 12) {
        $('input-status').textContent = 'Maximum 12 source documents.';
        return;
    }
    sourceEditor();
    markStale();
};
$('response').addEventListener('input', markStale);
$('example').onclick = async () => {
    if (reviewDirty && !confirm('Replace inputs and discard unsaved review edits?')) return;
    try {
        const r = await fetch('/example');
        const demo = await r.json();
        $('response').value = demo.response;
        $('sources').replaceChildren();
        demo.sources.forEach(sourceEditor);
        markStale();
        $('input-status').textContent = 'Public-source demo loaded. Response deliberately contains errors and an opinion; it is not a measured model output.';
    } catch (e) {
        $('input-status').textContent = e.message;
    }
};
$('analyze').onclick = async () => {
    if (reviewDirty && !confirm('Re-running analysis discards unsaved review edits. Continue?')) return;
    $('analyze').disabled = true;
    $('export').disabled = true;
    const revision = inputRevision;
    $('input-status').textContent = 'Extracting exact claim spans and ranking local source passages…';
    try {
        const result = await request('/analyze', {
            response: $('response').value,
            sources: readSources()
        });
        if (revision !== inputRevision) {
            $('input-status').textContent = 'Inputs changed during analysis. Result discarded; re-run with the current inputs.';
            return;
        }
        report = result;
        stale = false;
        reviewDirty = false;
        Object.keys(reviews).forEach(k => delete reviews[k]);
        render();
        $('input-status').textContent = 'Local analysis complete. No external query was sent.';
        $('results').scrollIntoView({
            behavior: 'smooth'
        });
    } catch (e) {
        $('input-status').textContent = e.message;
    } finally {
        $('analyze').disabled = false;
    }
};

function link(url, text) {
    const a = node('a', text || url);
    a.href = url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    return a;
}

function render() {
    $('results').hidden = false;
    $('export').disabled = false;
    $('claims').replaceChildren();
    $('summary').replaceChildren();
    [
        [report.claims.length, 'passages inspected'],
        [report.claims.filter(c => c.scope === 'candidate').length, 'claim candidates'],
        [report.sources.length, 'source documents']
    ].forEach(([n, t]) => {
        const box = node('div');
        box.append(node('strong', n), node('span', t));
        $('summary').append(box);
    });
    if (report.coverage.skipped_long_passages || report.coverage.duplicate_source_count) $('summary').append(node('p', 'Coverage: ' + report.coverage.skipped_long_passages + ' overlong passages skipped; ' + report.coverage.duplicate_source_count + ' duplicate-text sources grouped with their aliases preserved.', 'notice'));
    report.claims.forEach(claim => {
        const card = node('article', undefined, 'claim'),
            head = node('div', undefined, 'claim-head');
        head.append(node('span', claim.id, 'tag'), node('span', claim.scope === 'candidate' ? 'Claim candidate' : 'Scope review needed', 'tag'));
        card.append(head, node('p', claim.text, 'claim-text'), node('small', 'Response character span ' + claim.start + '–' + claim.end + ' · ' + claim.reason));
        if (claim.compound) card.append(node('p', 'May contain multiple assertions. Judge each assertion, not just the sentence as a whole.', 'cue'));
        const grid = node('div', undefined, 'review-grid'),
            evidence = node('div'),
            form = node('div', undefined, 'adjudication');
        grid.append(evidence, form);
        card.append(grid);
        const review = {
            verdict: 'unreviewed',
            rationale: '',
            evidence_relations: {}
        };
        reviews[claim.id] = review;
        evidence.append(node('h3', 'Retrieved evidence'));
        if (!claim.evidence.length) evidence.append(node('p', 'No sufficient lexical match in the supplied corpus. This does not mean the claim is false. Add a relevant source or research further.', 'notice'));
        claim.evidence.forEach(p => {
            const source = report.sources.find(s => s.id === p.source_id),
                item = node('div', undefined, 'evidence');
            item.append(node('strong', source.title), node('blockquote', p.quote), link(source.url), node('p', 'Source text characters ' + p.start + '–' + p.end + ' · ' + source.origin, 'source-url'), node('small', 'Shared terms: ' + p.shared_terms.join(', ') + ' · relevance ' + p.lexical_relevance.toFixed(3) + ' (not truth probability)'));
            if (source.license) item.append(node('small', source.license));
            if (source.original_source && source.origin.startsWith('User-edited')) {
                item.append(node('p', 'Original source attribution (current excerpt may be edited):', 'source-url'), link(source.original_source.url, source.original_source.title));
            }
            if (source.last_modified_at) item.append(node('p', 'Source revision: ' + source.last_modified_at, 'source-url'));
            if (source.aliases.length) item.append(node('p', 'Same text also supplied at: ' + source.aliases.map(a => a.url).join(', '), 'source-url'));
            p.cues.forEach(cue => item.append(node('p', cue.detail, 'cue')));
            const label = node('label', 'How does this passage relate?'),
                select = node('select');
            select.setAttribute('aria-label', 'Evidence relation ' + claim.id + ' ' + p.id);
            [
                ['unassessed', 'Not assessed'],
                ['supports', 'Supports'],
                ['contradicts', 'Contradicts'],
                ['context', 'Context only'],
                ['irrelevant', 'Not relevant']
            ].forEach(([v, t]) => {
                const o = node('option', t);
                o.value = v;
                select.append(o);
            });
            select.onchange = () => {
                review.evidence_relations[p.id] = select.value;
                reviewDirty = true;
            };
            label.append(select);
            item.append(label);
            evidence.append(item);
        });
        form.append(node('h3', 'Your adjudication'), node('p', 'Nothing here has been automatically labeled true or false.', 'muted'));
        const verdictLabel = node('label', 'Review conclusion'),
            verdict = node('select');
        verdict.setAttribute('aria-label', 'Conclusion ' + claim.id);
        ['unreviewed', 'supported', 'contradicted', 'mixed', 'inconclusive', 'not-a-factual-claim'].forEach(v => {
            const o = node('option', v);
            o.value = v;
            verdict.append(o);
        });
        verdict.onchange = () => {
            review.verdict = verdict.value;
            reviewDirty = true;
        };
        verdictLabel.append(verdict);
        const rationaleLabel = node('label', 'Reason and remaining uncertainty'),
            rationale = node('textarea');
        rationale.setAttribute('aria-label', 'Rationale ' + claim.id);
        rationale.maxLength = 8000;
        rationale.oninput = () => {
            review.rationale = rationale.value;
            reviewDirty = true;
        };
        rationaleLabel.append(rationale);
        form.append(verdictLabel, rationaleLabel, node('small', 'Support/contradiction conclusions require an appropriate evidence relation and a rationale. Sources may not be current, independent or authoritative.'));
        const details = node('details');
        details.append(node('summary', 'Optional public-source discovery'));
        const info = node('p', 'This sends ONLY the query below to English Wikipedia/Wikimedia, not your full response. Inspect it for private information. Results are secondary-source summaries, not primary-source verification.'),
            query = node('input');
        query.value = claim.query;
        query.maxLength = 160;
        query.className = 'query';
        query.setAttribute('aria-label', 'Public query ' + claim.id);
        const consentLabel = node('label', undefined, 'check-label'),
            consent = node('input');
        consent.type = 'checkbox';
        consentLabel.append(consent, node('span', 'I approve sending this query to Wikimedia.'));
        const button = node('button', 'Search Wikimedia'),
            status = node('p', '', 'status'),
            found = node('div');
        button.onclick = async () => {
            if (!consent.checked) {
                status.textContent = 'Approve the displayed query before sending.';
                return;
            }
            button.disabled = true;
            status.textContent = 'Searching the approved public query…';
            try {
                const result = await request('/discover', {
                    query: query.value,
                    consent: true
                });
                status.textContent = 'Results for approved query: ' + result.query + '. ' + result.notice + ' ' + result.failures.join('; ');
                found.replaceChildren();
                result.sources.forEach(s => {
                    const item = node('div', undefined, 'evidence');
                    item.append(link(s.url, s.title), node('p', s.text), node('small', s.license));
                    const add = node('button', 'Add source to corpus');
                    add.onclick = () => {
                        if ($('sources').children.length >= 12) {
                            status.textContent = 'Source limit reached.';
                            return;
                        }
                        sourceEditor(s);
                        markStale();
                        add.disabled = true;
                        add.textContent = 'Added; re-run local analysis';
                    };
                    item.append(add);
                    found.append(item);
                });
                if (!result.sources.length) found.append(node('p', 'No readable source returned. No evidence was fabricated.'));
            } catch (e) {
                status.textContent = e.message;
            } finally {
                button.disabled = false;
            }
        };
        query.oninput = () => {
            consent.checked = false;
        };
        details.append(info, query, consentLabel, button, status, found);
        form.append(details);
        $('claims').append(card);
    });
}
$('export').onclick = () => {
    if (!report || stale) return;
    for (const [id, r] of Object.entries(reviews)) {
        const relations = Object.values(r.evidence_relations);
        if (r.verdict !== 'unreviewed' && !r.rationale.trim()) {
            alert(id + ': add a rationale before exporting a conclusion.');
            return;
        }
        if (['supported', 'mixed'].includes(r.verdict) && !relations.includes('supports')) {
            alert(id + ': identify supporting evidence first.');
            return;
        }
        if (['contradicted', 'mixed'].includes(r.verdict) && !relations.includes('contradicts')) {
            alert(id + ': identify contradicting evidence first.');
            return;
        }
    }
    const payload = {
        ...report,
        human_review: {
            exported_at: new Date().toISOString(),
            reviewer: 'not identified',
            claims: reviews,
            note: 'User-entered adjudications; no automatic accuracy certification.'
        }
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
            type: 'application/json'
        }),
        url = URL.createObjectURL(blob),
        a = node('a');
    a.href = url;
    a.download = 'claim-evidence-review.json';
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
    $('input-status').textContent = 'Export download requested. Verify it saved; source text is included, so share carefully.';
};
window.addEventListener('beforeunload', e => {
    if (reviewDirty) {
        e.preventDefault();
        e.returnValue = '';
    }
});
