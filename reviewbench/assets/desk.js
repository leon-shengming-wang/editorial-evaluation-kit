'use strict';
const cases = JSON.parse(document.getElementById('case-data').textContent);
const fields = ['decision', 'evidence', 'reason', 'uncertainty'];
const format = 'reviewbench.private-draft.v1';
const empty = () => ({decision:'', evidence:'', reason:'', uncertainty:''});
let reviews = Object.create(null), current = 0, dirty = false;
const byId = Object.fromEntries(cases.map(c => [c.id, c]));
const element = id => document.getElementById(id);
function problems(c, r) {
  const issues = [];
  if (!['A','B','tie','abstain'].includes(r.decision)) issues.push('Choose a decision.');
  if (!r.reason.trim()) issues.push('Explain your decision.');
  const quote = r.evidence.trim();
  if (!quote) issues.push('Add an exact evidence quote.');
  else if (![c.source,c.responses.A,c.responses.B].some(t => t.includes(quote))) issues.push('Evidence must match a passage in the supplied source or a response.');
  return issues;
}
function draft(c) { return reviews[c.id] || empty(); }
function refresh() {
  const complete = cases.filter(c => reviews[c.id] && problems(c, reviews[c.id]).length === 0).length;
  element('progress').textContent = `${complete} / ${cases.length} complete`;
  const r = draft(cases[current]);
  const issues = problems(cases[current], r);
  element('validation').textContent = issues.length ? issues.join(' ') : 'Required fields complete. Your judgment has not been graded.';
  element('validation').classList.toggle('error', issues.length > 0 && Object.values(r).some(Boolean));
}
function show(index) {
  current = index;
  const c = cases[current], r = draft(c);
  element('case-select').value = String(index);
  element('case-title').textContent = `${c.id} / ${c.category}`;
  element('prompt').textContent = c.prompt;
  element('source').textContent = c.source;
  element('response-a').textContent = c.responses.A;
  element('response-b').textContent = c.responses.B;
  element('fingerprint').textContent = c.fingerprint;
  fields.forEach(k => { element(k).value = r[k]; });
  element('previous').disabled = index === 0;
  element('next').disabled = index === cases.length - 1;
  refresh();
}
function changed() {
  const r = empty(); fields.forEach(k => { r[k] = element(k).value; });
  reviews[cases[current].id] = r; dirty = true; refresh();
}
function notice(text, error=false) { element('notice').textContent = text; element('notice').classList.toggle('error', error); }
function exportObject() {
  return {format, scope:'Private practice on synthetic AI-assisted exercises. Not verified human-performance evidence.',
    reviews:cases.filter(c => reviews[c.id]).map(c => ({case_id:c.id, fingerprint:c.fingerprint, ...reviews[c.id]}))};
}
function validateImport(data) {
  if (!data || Array.isArray(data) || data.format !== format || !Array.isArray(data.reviews)) throw Error('Not a ReviewBench draft.');
  if (data.reviews.length > cases.length) throw Error('Too many records.');
  const incoming = Object.create(null);
  for (const row of data.reviews) {
    if (!row || Array.isArray(row) || typeof row !== 'object') throw Error('Invalid review record.');
    if (Object.keys(row).sort().join('|') !== ['case_id','fingerprint',...fields].sort().join('|')) throw Error('Unexpected or missing review fields.');
    const c = byId[row.case_id];
    if (!c || row.fingerprint !== c.fingerprint) throw Error('A case is unknown or its source has changed.');
    if (Object.hasOwn ? Object.hasOwn(incoming,c.id) : Object.prototype.hasOwnProperty.call(incoming,c.id)) throw Error('Duplicate case in draft.');
    if (fields.some(k => typeof row[k] !== 'string' || row[k].length > 12000)) throw Error('Invalid or oversized review text.');
    if (!['','A','B','tie','abstain'].includes(row.decision)) throw Error('Invalid decision.');
    incoming[c.id] = Object.fromEntries(fields.map(k => [k,row[k]]));
  }
  return incoming;
}
cases.forEach((c, i) => { const option = document.createElement('option'); option.value=String(i); option.textContent=`${c.id} · ${c.category}`; element('case-select').append(option); });
fields.forEach(k => element(k).addEventListener('input', changed));
element('case-select').addEventListener('change', () => show(Number(element('case-select').value)));
element('previous').addEventListener('click', () => { if(current > 0) show(current-1); });
element('next').addEventListener('click', () => { if(current < cases.length-1) show(current+1); });
element('download').addEventListener('click', () => {
  if (!Object.keys(reviews).length) { notice('No draft text to download yet.'); return; }
  const url = URL.createObjectURL(new Blob([JSON.stringify(exportObject(),null,2)+'\n'],{type:'application/json'}));
  const link=document.createElement('a'); link.href=url; link.download='reviewbench-private-draft.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
  notice('Download requested. Verify the JSON is in Downloads before closing; incomplete reviews are included.');
  // A click is not proof a download completed. Keep the unload warning active.
});
element('import').addEventListener('change', async () => {
  const file=element('import').files[0]; if(!file) return;
  try {
    if(file.size > 1000000) throw Error('Draft is larger than 1 MB.');
    const incoming=validateImport(JSON.parse(await file.text()));
    if(Object.keys(reviews).length && !window.confirm('Replace the current in-tab draft? Download it first if you want to keep it.')) { notice('Import cancelled; current draft kept.'); return; }
    reviews=incoming; dirty=true; show(current); notice('Draft restored. Nothing was uploaded.');
  } catch(error) { notice('Could not restore: '+error.message, true); }
  finally { element('import').value=''; }
});
window.addEventListener('beforeunload', event => { if(dirty) { event.preventDefault(); event.returnValue=''; } });
show(0);
