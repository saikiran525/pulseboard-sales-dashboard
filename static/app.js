let trendChart; let categoryChart;
const palette = ['#1e5949', '#e88d55', '#9fc4cb', '#f5c761', '#9eafa3', '#d48b79'];
const money = value => '$' + Number(value).toLocaleString(undefined, {maximumFractionDigits: 0});

async function loadDashboard(file) {
  const body = new FormData();
  if (file) body.append('file', file);
  const response = await fetch('/api/analyze', {method: 'POST', body});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Could not analyze this file.');
  renderDashboard(data);
}

function renderDashboard(data) {
  const s = data.summary;
  document.querySelector('#datasetName').textContent = data.source;
  document.querySelector('#rowCount').textContent = `${data.rows.toLocaleString()} rows analyzed`;
  document.querySelector('#metricGrid').innerHTML = [
    ['Total revenue', money(s.revenue), `${s.best_month} was your strongest month`, ''],
    ['Units sold', s.units.toLocaleString(), `${s.orders.toLocaleString()} transactions`, ''],
    ['Average order value', money(s.avg_order), 'Revenue per transaction', ''],
    ['Monthly growth', `${s.growth > 0 ? '+' : ''}${s.growth}%`, s.growth >= 0 ? 'Latest period is gaining pace' : 'Latest period needs attention', s.growth >= 0 ? 'positive' : 'warning']
  ].map(([label, value, foot, state]) => `<div class="metric"><div class="metric-label">${label}</div><div class="metric-value">${value}</div><div class="metric-foot ${state}">${foot}</div></div>`).join('');

  if (trendChart) trendChart.destroy();
  trendChart = new Chart(document.querySelector('#trendChart'), {type:'line', data:{labels:data.monthly.map(x=>x.month), datasets:[{data:data.monthly.map(x=>x.revenue), borderColor:'#e88d55', backgroundColor:'rgba(232,141,85,.12)', fill:true, tension:.35, pointRadius:3, pointBackgroundColor:'#fff', pointBorderWidth:2}]}, options:{responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}}, scales:{y:{border:{display:false},grid:{color:'#edf0ed'},ticks:{callback:v=>money(v),font:{size:10},color:'#87918b'}},x:{border:{display:false},grid:{display:false},ticks:{font:{size:10},color:'#87918b'}}}}});

  if (categoryChart) categoryChart.destroy();
  categoryChart = new Chart(document.querySelector('#categoryChart'), {type:'doughnut', data:{labels:data.categories.map(x=>x.category), datasets:[{data:data.categories.map(x=>x.revenue), backgroundColor:palette, borderWidth:3, borderColor:'#fff'}]}, options:{responsive:true, maintainAspectRatio:false, cutout:'70%', plugins:{legend:{display:false}}}});
  document.querySelector('#categoryLegend').innerHTML = data.categories.map((x,i)=>`<div><span><i style="background:${palette[i%palette.length]}"></i>${x.category}</span><strong>${money(x.revenue)}</strong></div>`).join('');
  document.querySelector('#productsBody').innerHTML = data.products.map(x=>`<tr><td>${x.product}</td><td>${x.category}</td><td>${money(x.revenue)}</td><td><span class="share-bar"><b style="width:${Math.min(x.share,100)}%"></b></span>${x.share}%</td></tr>`).join('');
  document.querySelector('#suggestions').innerHTML = data.suggestions.map(x=>`<div class="suggestion ${x.type}"><div class="suggestion-icon">${x.type === 'warning' ? '!' : '✦'}</div><div><div class="suggestion-title">${x.title}</div><div class="suggestion-body">${x.body}</div></div></div>`).join('');
}

document.querySelector('#fileInput').addEventListener('change', event => { if (event.target.files[0]) loadDashboard(event.target.files[0]).catch(showError); });
document.querySelector('#resetButton').addEventListener('click', () => loadDashboard().catch(showError));
function showError(error) { const box = document.querySelector('#errorBox'); box.textContent = error.message; box.hidden = false; }
loadDashboard().catch(showError);
