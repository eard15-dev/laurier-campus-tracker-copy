const main = document.querySelector('main');
const labels = ['','Very quiet','Lightly occupied','Moderately busy','Busy','Very crowded'];
let routeVersion = 0;
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path, options={}) {
  if (window.CAMPUS_DEMO) return window.CAMPUS_DEMO.request(path, options);
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Could not load data. Please try again.');
  return data;
}
function field(status, name) {
  const s = status[name];
  const value = s.value === null ? 'No recent reports' : name === 'noise' ? s.value : `${s.value}/5 · ${labels[s.value]}`;
  return `<section class="panel"><div class="eyebrow">${name === 'noise' ? 'Noise' : 'Busyness'}</div><div class="value">${esc(value)}</div><p class="meta">${s.count} recent report${s.count === 1 ? '' : 's'}</p>${s.updated_at === null ? '' : `<p class="meta">Last update: ${esc(new Date(s.updated_at*1000).toLocaleString())}</p>`}${s.limited ? '<p class="notice">Limited data: one report.</p>' : ''}</section>`;
}
async function render({refresh=false, saved=false}={}) {
  const version = ++routeVersion;
  const parts = (location.hash || '#/').slice(2).split('/');
  if (!refresh) main.innerHTML = '<p role="status">Loading campus spaces…</p>';
  try {
    if (!parts[0]) {
      const {spaces} = await api('/api/spaces');
      if (version !== routeVersion) return;
      main.innerHTML = `<div class="eyebrow">Find your next spot</div><h1>A little less guesswork.</h1><p class="intro">Browse study, common and fitness spaces. Check recent student reports before deciding where to go.</p><p class="notice">Demo catalogue: locations require team verification. No live campus feed is connected.</p><div class="cards">${spaces.map(s=>`<article class="card"><div class="eyebrow">${esc(s.category)}</div><h2>${esc(s.name)}</h2><p class="meta">${esc(s.building)}</p><p>Noise: <strong>${esc(s.status.noise.value ?? 'No recent reports')}</strong></p><p>Busyness: <strong>${s.status.busyness.value === null ? 'No recent reports' : `${s.status.busyness.value}/5`}</strong></p><p class="meta">${esc(s.description)}</p><a class="button" href="#/space/${encodeURIComponent(s.id)}">View space</a></article>`).join('') || '<p>No spaces configured.</p>'}</div>`;
    } else if (parts[0] === 'space' && parts[1]) {
      const {space:s} = await api('/api/spaces/' + encodeURIComponent(decodeURIComponent(parts[1])));
      if (version !== routeVersion) return;
      if (parts[2] === 'report') {
        main.innerHTML = `<a href="#/space/${encodeURIComponent(s.id)}">← Back to space</a><h1>Share a quick update</h1><p>${esc(s.building)} · ${esc(s.name)}</p><p class="intro">Choose noise, busyness, or both. These are your estimates of the space right now.</p><form class="panel" id="report"><fieldset><legend>Noise level (optional)</legend><div class="options">${['Quiet','Moderate','Loud'].map(n=>`<label class="choice"><input type="radio" name="noise" value="${n}">${n}</label>`).join('')}</div></fieldset><fieldset><legend>Busyness (optional)</legend><div class="options">${labels.slice(1).map((n,i)=>`<label class="choice"><input type="radio" name="busyness" value="${i+1}">${i+1} · ${n}</label>`).join('')}</div></fieldset><div id="feedback" role="alert"></div><div class="actions"><button type="submit">Submit report</button><button type="reset" class="secondary">Clear choices</button><a class="button secondary" href="#/space/${encodeURIComponent(s.id)}">Cancel</a></div></form>`;
        document.querySelector('#report').addEventListener('submit', async event => {
          event.preventDefault();
          const form = event.target, values = new FormData(form), button = form.querySelector('[type=submit]');
          button.disabled = true;
          try {
            await api('/api/reports', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({space_id:s.id,noise:values.get('noise'),busyness:values.has('busyness') ? Number(values.get('busyness')) : null})});
            history.replaceState(null, '', '#/space/' + encodeURIComponent(s.id));
            await render({saved:true});
          } catch (error) {
            const feedback = document.querySelector('#feedback');
            if (feedback && form.isConnected) {feedback.className='error'; feedback.textContent = error.message || 'Connection failed. Your choices are preserved; please try again.';}
          } finally {button.disabled=false;}
        });
      } else {
        main.innerHTML = `<a href="#/">← All spaces</a><h1>${esc(s.name)}</h1><p class="intro">${esc(s.building)} · ${esc(s.description)}</p>${saved ? '<p class="success" role="status">Your report was saved.</p>' : ''}<div class="status-grid">${field(s.status,'noise')}${field(s.status,'busyness')}</div><p class="meta">Reports expire at 60 minutes. Each field uses the most common recent rating; ties use the newest contribution. This view refreshes every 30 seconds.</p><div class="actions"><a class="button" href="#/space/${encodeURIComponent(s.id)}/report">Submit a report</a><button class="secondary" id="refresh">Refresh status</button></div>`;
        document.querySelector('#refresh').onclick = () => render({refresh:true});
      }
    } else {main.innerHTML='<h1>Page not found</h1><a href="#/">Browse spaces</a>';}
    if (!refresh) main.focus();
  } catch(error) {
    if (version !== routeVersion) return;
    if (refresh) {
      let alert = document.querySelector('#refresh-error');
      if (!alert) {alert=document.createElement('p');alert.id='refresh-error';alert.className='error';alert.setAttribute('role','alert');main.prepend(alert);}
      alert.textContent='Refresh failed. Displayed reports may be stale. Try Refresh status again.';
    } else {main.innerHTML=`<h1>Could not load this view</h1><p class="error" role="alert">${esc(error.message)}</p><a href="#/">Back to spaces</a>`;}
  }
}
window.addEventListener('hashchange', () => render());
setInterval(() => {if (!document.hidden && !location.hash.endsWith('/report')) render({refresh:true});},30000);
render();
