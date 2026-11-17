/* Load after the existing app script, before engine-client.js.
   One device-local profile; no account sync or Human Design calculation implied. */
(()=>{
 const chartKey='ss-calculated-chart',inputKey='ss-birth-input';
 let chart=null,birthInput=null;
 const read=key=>{try{return JSON.parse(localStorage.getItem(key)||'null')}catch{return null}};
 function publish(){window.dispatchEvent(new CustomEvent('starstruck:profile-updated',{detail:window.StarstruckBirthProfile.get()}))}
 function sync(){
  const selects=document.querySelectorAll('#strategy-placements select');
  const houses=[1,2,4,5,6,7,8,9,10,11,12];
  houses.forEach((house,i)=>{if(selects[i])selects[i].value=chart?.cusps?.[house-1]?.sign||''});
  ['Mars','Venus','Jupiter','Saturn'].forEach((name,i)=>{if(selects[11+i])selects[11+i].value=chart?.bodies?.[name]?.sign||''});
  selects.forEach(s=>{s.disabled=true;s.dispatchEvent(new Event('change'))});
  const wrap=document.getElementById('strategy-placements');
  if(wrap){const details=wrap.closest('details');if(details)details.hidden=true}
  for(const id of ['dashboard','insights','movement','human-design']){
   const page=document.getElementById(id);if(!page)continue;
   let status=page.querySelector('[data-birth-profile-status]');
   if(!status){status=document.createElement('p');status.dataset.birthProfileStatus='';status.className='notice';page.prepend(status)}
   status.textContent=id==='human-design'?(birthInput?'Your saved birth details are ready for Human Design. Personal design results are pending the Human Design engine.':'Add birth details once in My birth chart to reuse them here.'):(chart?'Using your saved birth chart'+(chart.unknown_time?' · birth time unknown; house guidance unavailable.':'.'):'Create your birth chart once to personalize this space.');
  }
  publish();
 }
 window.StarstruckBirthProfile=Object.freeze({
  get:()=>JSON.parse(JSON.stringify({chart,birthInput,humanDesignStatus:birthInput?'pending-engine':'needs-birth-details'})),
  getHumanDesignInput:()=>birthInput?JSON.parse(JSON.stringify(birthInput)):null
 });
 window.addEventListener('starstruck:chart-calculated',e=>{
  chart=e.detail.chart;birthInput=e.detail.birthInput;
  try{localStorage.setItem(chartKey,JSON.stringify(chart));localStorage.setItem(inputKey,JSON.stringify(birthInput))}catch{}
  sync();
 });
 window.addEventListener('starstruck:chart-cleared',()=>{
  chart=null;birthInput=null;
  try{localStorage.removeItem(chartKey);localStorage.removeItem(inputKey)}catch{}
  sync();
 });
 document.getElementById('delete-data')?.addEventListener('click',()=>window.dispatchEvent(new Event('starstruck:chart-cleared')));
 window.addEventListener('storage',e=>{if([chartKey,inputKey,null].includes(e.key)){chart=read(chartKey);birthInput=read(inputKey);sync()}});
 chart=read(chartKey);birthInput=read(inputKey);sync();
})();
