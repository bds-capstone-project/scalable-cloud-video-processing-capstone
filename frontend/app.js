'use strict';
// Configure this after deploying an API with these endpoints:
// POST /upload-url {filename, contentType} -> {uploadUrl, jobId}
// GET /job-status?jobId=... -> {status:'waiting'|'processing'|'completed'|'failed', downloadUrl?}
// Backend must generate unique S3 input keys and corresponding output keys.
const API_BASE_URL = 'https://vrx84yd7uj.execute-api.us-east-1.amazonaws.com';
const MAX_PARALLEL_UPLOADS = 3;
const form = document.querySelector('#upload-form');
const input = document.querySelector('#video');
const dropZone = document.querySelector('#drop-zone');
const submit = document.querySelector('#submit');
const summary = document.querySelector('#selection-summary');
const list = document.querySelector('#video-list');
const count = document.querySelector('#file-count');
const notice = document.querySelector('#notice');
const clearButton = document.querySelector('#clear-list');
const entries = [];
let nextId = 0;
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const sizeLabel = bytes => bytes >= 1048576 ? `${(bytes / 1048576).toFixed(1)} MB` : `${(bytes / 1024).toFixed(1)} KB`;

function addFiles(files) {
  const valid = Array.from(files).filter(file => file.name.toLowerCase().endsWith('.mp4') && (!file.type || file.type === 'video/mp4'));
  const rejected = files.length - valid.length;
  for (const file of valid) entries.push({ id: ++nextId, file, status: 'Ready', detail: '', phase: 'ready', downloadUrl: '' });
  if (rejected) notice.textContent = `${rejected} unsupported file(s) skipped. MP4 files only.`;
  else notice.textContent = '';
  render();
}
function render() {
  list.replaceChildren();
  count.textContent = String(entries.length);
  const ready = entries.filter(item => item.phase === 'ready').length;
  summary.textContent = ready ? `${ready} video${ready === 1 ? '' : 's'} ready to upload` : 'No new files selected';
  submit.disabled = !ready;
  submit.textContent = ready === 1 ? 'Upload video' : 'Upload videos';
  clearButton.hidden = !entries.some(item => ['completed', 'failed'].includes(item.phase));
  if (!entries.length) {
    const empty = document.createElement('p'); empty.className = 'empty-state';
    empty.textContent = 'Selected videos will appear here.'; list.append(empty); return;
  }
  for (const item of entries) {
    const row = document.createElement('div'); row.className = 'video-row';
    const fileCell = document.createElement('div');
    const name = document.createElement('div'); name.className = 'file-name'; name.textContent = item.file.name; name.title = item.file.name;
    const detail = document.createElement('div'); detail.className = 'file-detail'; detail.textContent = item.detail;
    fileCell.append(name, detail);
    const size = document.createElement('span'); size.className = 'file-size'; size.textContent = sizeLabel(item.file.size);
    const state = document.createElement('span'); state.className = `status ${item.phase}`; state.textContent = item.status;
    const action = document.createElement('div');
    if (item.downloadUrl) {
      const a = document.createElement('a'); a.className = 'row-action'; a.textContent = 'Download';
      a.href = item.downloadUrl; a.target = '_blank'; a.rel = 'noopener noreferrer'; action.append(a);
    } else if (item.phase === 'failed') {
      const retry = document.createElement('button'); retry.type = 'button'; retry.className = 'text-button'; retry.textContent = 'Retry';
      retry.addEventListener('click', () => { item.phase = 'ready'; item.status = 'Ready'; item.detail = ''; render(); }); action.append(retry);
    }
    row.append(fileCell, size, state, action); list.append(row);
  }
}
input.addEventListener('change', () => { addFiles(input.files); input.value = ''; });
['dragenter', 'dragover'].forEach(type => dropZone.addEventListener(type, e => { e.preventDefault(); dropZone.classList.add('drag-over'); }));
['dragleave', 'drop'].forEach(type => dropZone.addEventListener(type, e => { e.preventDefault(); dropZone.classList.remove('drag-over'); }));
dropZone.addEventListener('drop', e => { addFiles(e.dataTransfer?.files || []); });
// Prevent a drop outside the target from navigating away from the page.
window.addEventListener('dragover', e => e.preventDefault());
window.addEventListener('drop', e => e.preventDefault());
clearButton.addEventListener('click', () => { for (let i = entries.length - 1; i >= 0; i--) if (['completed', 'failed'].includes(entries[i].phase)) entries.splice(i, 1); render(); });
async function requestJson(path, options) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) throw new Error(`API returned HTTP ${response.status}`);
  return response.json();
}
function update(item, phase, status, detail = '') { item.phase = phase; item.status = status; item.detail = detail; render(); }
async function uploadAndTrack(item) {
  try {
    update(item, 'uploading', 'Preparing upload');
    const upload = await requestJson('/upload-url', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ filename: item.file.name }) });
    const uploadUrl = upload.upload_url;
    const jobId = upload.job_id;
    const uploadContentType = upload.content_type || 'video/mp4';
    if (!uploadUrl || !jobId) throw new Error('Upload API response is incomplete');
    update(item, 'uploading', 'Uploading');
    const uploadResponse = await fetch(uploadUrl, { method: 'PUT', headers: { 'Content-Type': uploadContentType }, body: item.file });
    if (!uploadResponse.ok) throw new Error(`S3 upload returned HTTP ${uploadResponse.status}`);
    update(item, 'processing', 'Queued');
    for (let attempt = 0; attempt < 180; attempt++) {
      const result = await requestJson(`/status/${encodeURIComponent(jobId)}`);
      if (result.status === 'completed') {
        const download = await requestJson(`/download-url/${encodeURIComponent(jobId)}`);
        item.downloadUrl = download.download_url;
        if (!item.downloadUrl) throw new Error('Download URL missing');
        update(item, 'completed', 'Completed'); return;
      }
      if (result.status === 'failed') throw new Error('Processing failed');
      update(item, 'processing', result.status === 'processing' ? 'Processing' : 'Queued');
      await sleep(5000);
    }
    throw new Error('Status check timed out. Check S3 output or try again.');
  } catch (error) { update(item, 'failed', 'Failed', error.message); }
}
form.addEventListener('submit', async e => {
  e.preventDefault();
  const pending = entries.filter(item => item.phase === 'ready');
  if (!pending.length) return;
  if (!API_BASE_URL) {
    notice.textContent = 'Frontend preview only. AWS upload API has not been connected yet; no files were uploaded.';
    return;
  }
  notice.textContent = '';
  // Upload a limited number concurrently; each file gets its own job/status.
  let cursor = 0;
  const workers = Array.from({ length: Math.min(MAX_PARALLEL_UPLOADS, pending.length) }, async () => {
    while (cursor < pending.length) await uploadAndTrack(pending[cursor++]);
  });
  await Promise.all(workers);
});
render();
