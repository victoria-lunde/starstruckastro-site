/* Asteroid selection works even before the calculation API is configured. */
(()=>{
 const container=document.getElementById('point-options');
 if(!container||document.getElementById('select-all-asteroids'))return;
 const names=new Set(['Chiron','Pholus','Ceres','Pallas','Juno','Vesta','Hygiea','Astraea','Iris','Psyche','Amor','Union','Sappho','Aphrodite','Apollo','Fortuna','Fama','Karma','Nemesis','Eros','Medusa','Nessus','Dejanira','Apophis']);
 const controls=document.createElement('div');controls.style.cssText='display:flex;flex-wrap:wrap;gap:10px;margin:12px 0';
 function setAll(checked){container.querySelectorAll('input[name="points"]').forEach(input=>{if(names.has(input.value))input.checked=checked});container.dispatchEvent(new Event('change',{bubbles:true}));}
 for(const [id,label,checked] of [['select-all-asteroids','select all asteroids',true],['clear-all-asteroids','clear asteroids',false]]){const b=document.createElement('button');b.id=id;b.type='button';b.className='outline';b.textContent=label;b.onclick=()=>setAll(checked);controls.append(b)}
 container.before(controls);
})();
/* Embed after the app script once the HTTPS backend is provisioned.
   Set <meta name="chart-api-base" content="https://YOUR-ENGINE-HOST">.
   This never accepts an API secret. Birth details go only to that configured host. */
(()=>{
 const base=document.querySelector('meta[name="chart-api-base"]')?.content.replace(/\/$/,'');
 if(!base)return;
 if(!base.startsWith('https://')&&!base.startsWith('http://localhost:'))return;
 const form=document.getElementById('birth-form'),city=form?.querySelector('[name="location"]');
 if(!form||!city)return;
 let selected=null,controller=null,timer=null,sequence=0,chartSequence=0,chartController=null;
 const list=document.createElement('div');list.id='city-suggestions';list.setAttribute('role','listbox');
 city.setAttribute('role','combobox');city.setAttribute('aria-controls',list.id);city.setAttribute('aria-expanded','false');city.autocomplete='off';city.after(list);
 const message=document.createElement('p');message.setAttribute('role','status');message.className='subtle';list.after(message);
 const credit=document.createElement('p');credit.className='subtle';credit.textContent='Place search: Geoapify | © OpenStreetMap contributors';message.after(credit);
 const occurrence=document.createElement('label');occurrence.textContent='If clocks repeated this birth time';
 const fold=document.createElement('select');[['','Not sure / not applicable'],['0','First occurrence'],['1','Second occurrence']].forEach(([value,label])=>{const o=document.createElement('option');o.value=value;o.textContent=label;fold.append(o)});occurrence.append(fold);credit.after(occurrence);
 city.addEventListener('input',()=>{selected=null;clearTimeout(timer);controller?.abort();sequence++;const current=sequence,q=city.value.trim();list.replaceChildren();city.setAttribute('aria-expanded','false');if(q.length<3){message.textContent='Type at least three letters, then select a city.';return}timer=setTimeout(async()=>{controller=new AbortController();message.textContent='Searching cities…';try{const r=await fetch(base+'/api/locations?q='+encodeURIComponent(q),{signal:controller.signal});const data=await r.json();if(current!==sequence)return;if(!r.ok)throw Error(data.error||'City lookup failed.');list.replaceChildren();(data.results||[]).forEach(place=>{const b=document.createElement('button');b.type='button';b.className='outline';b.setAttribute('role','option');b.style.cssText='display:block;width:100%;margin-top:7px;text-align:left';b.textContent=place.label;b.onclick=()=>{selected=place;city.value=place.label;list.replaceChildren();city.setAttribute('aria-expanded','false');message.textContent='Selected '+place.label+' · '+place.timezone};list.append(b)});city.setAttribute('aria-expanded',String(!!list.children.length));message.textContent=list.children.length?'Select the correct city, region, and country.':'No cities found. Try a nearby city or an alternate spelling.'}catch(e){if(e.name!=='AbortError'&&current===sequence)message.textContent=e.message}},350)});
 city.addEventListener('keydown',e=>{if(e.key==='ArrowDown'){e.preventDefault();list.querySelector('button')?.focus()}if(e.key==='Escape'){list.replaceChildren();city.setAttribute('aria-expanded','false')}});
 const button=document.createElement('button');button.type='button';button.className='primary';button.style.marginTop='20px';button.textContent='Calculate my chart';form.append(button);
 const results=document.createElement('div');results.setAttribute('aria-live','polite');form.append(results);
 function invalidate(){chartSequence++;chartController?.abort();button.disabled=false;results.replaceChildren();try{localStorage.removeItem('ss-calculated-chart')}catch{};window.dispatchEvent(new CustomEvent('starstruck:chart-cleared'));}
 form.addEventListener('input',invalidate);form.addEventListener('change',invalidate);
 form.addEventListener('submit',e=>{e.preventDefault();e.stopImmediatePropagation();button.click()},true);
 button.onclick=async()=>{if(!form.reportValidity())return;if(!selected){message.textContent='Select a city suggestion before calculating.';city.focus();return}const requestId=++chartSequence;chartController=new AbortController();const requestController=chartController;const timeout=setTimeout(()=>requestController.abort(),20000);button.disabled=true;message.textContent='Calculating your chart…';results.replaceChildren();const f=new FormData(form),unknown=document.getElementById('unknown').checked,payload={date:f.get('date'),time:unknown?null:f.get('time'),latitude:selected.latitude,longitude:selected.longitude,timezone:selected.timezone,tradition:f.get('tradition'),unknown_time:unknown,house_system:'W',points:f.getAll('points')};if(fold.value!=='')payload.fold=Number(fold.value);
 try{const response=await fetch(base+'/api/chart',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:requestController.signal});const chart=await response.json();if(requestId!==chartSequence)return;if(!response.ok)throw Error(chart.error||'Chart calculation failed.');
 const h=document.createElement('h2');h.style.marginTop='25px';h.textContent='Your calculated placements';results.append(h);
 const meta=document.createElement('p');meta.textContent=chart.engine+' · '+chart.zodiac+' · '+(chart.house_system||'No houses — time unknown');results.append(meta);
 const table=document.createElement('table');table.style.cssText='width:100%;border-collapse:collapse;text-align:left';const head=document.createElement('tr');['Body / point','Placement','House'].forEach(t=>{const c=document.createElement('th');c.textContent=t;head.append(c)});table.append(head);
 const rows={...chart.bodies};if(chart.angles){rows.Rising=chart.angles.rising;rows.Midheaven=chart.angles.midheaven}
 const meanings={Sun:'Identity, vitality, and creative expression.',Moon:'Emotional needs, habits, and your sense of comfort.',Mercury:'Communication, learning, and how you process information.',Venus:'Affection, values, pleasure, and connection.',Mars:'Drive, initiative, and how you approach action.',Jupiter:'Growth, learning, and the search for meaning.',Saturn:'Boundaries, responsibility, and long-term commitments.',Uranus:'Independence, change, and experimentation.',Neptune:'Imagination, ideals, and sensitivity.',Pluto:'Transformation, intensity, and power.',Rising:'The zodiac degree rising on the eastern horizon at birth.',Midheaven:'The meridian angle associated in astrology with public life and vocation.',Chiron:'A symbolic lens on vulnerability, learning, and care.',Algol:'A fixed star, separate from the asteroid catalog. A placement does not predict harm.'};
 const detail=document.createElement('section');detail.className='card';detail.tabIndex=-1;detail.setAttribute('aria-label','Placement preview');detail.style.marginTop='18px';
 const hint=document.createElement('p');hint.textContent='Tap a placement to explore it.';detail.append(hint);
 function preview(name,p){detail.replaceChildren();const h=document.createElement('h3');h.textContent=name+' in '+p.sign;detail.append(h);const lines=[p.degree.toFixed(2)+'° '+p.sign+' · '+(p.house?'house '+p.house:chart.unknown_time?'house unavailable — birth time unknown':'angle'),meanings[name]||'An optional astrological point. Its interpretation depends on the wider chart and tradition.'];if(typeof p.retrograde==='boolean')lines.push(p.retrograde?'Retrograde: apparent backward motion from Earth at birth.':'Direct: apparent forward motion from Earth at birth.');lines.push('Astrological meanings are symbolic reflection prompts.');for(const text of lines){const line=document.createElement('p');line.textContent=text;detail.append(line)}detail.focus({preventScroll:true});}
 Object.entries(rows).forEach(([name,p])=>{const row=document.createElement('tr');const cell=document.createElement('td');cell.style.padding='9px 4px';const b=document.createElement('button');b.type='button';b.className='outline';b.textContent=name;b.setAttribute('aria-label','Explore '+name+' in '+p.sign);b.onclick=()=>preview(name,p);cell.append(b);row.append(cell);[`${p.sign} ${p.degree.toFixed(2)}°${p.retrograde?' Rx':''}`,p.house||'—'].forEach(t=>{const c=document.createElement('td');c.style.padding='9px 4px';c.textContent=t;row.append(c)});table.append(row)});results.append(table,detail);
 [...(chart.warnings||[]),...(chart.unavailable||[]).map(x=>x.name+': '+x.reason)].forEach(text=>{const p=document.createElement('p');p.className='notice';p.textContent=text;results.append(p)});
 if(chart.moon_day_range){const p=document.createElement('p');p.textContent='Moon across your birth day: '+chart.moon_day_range.map(x=>x.sign+' '+x.degree.toFixed(2)+'°').join(' → ');results.append(p)}
 if(chart.aspects?.length){const h=document.createElement('h3');h.textContent='Major aspects';results.append(h);chart.aspects.forEach(a=>{const p=document.createElement('p');p.textContent=a.a+' '+a.aspect+' '+a.b+' · orb '+a.orb.toFixed(2)+'°';results.append(p)})}
 // Feed verified placements into existing reflection controls; no fabricated houses.
 const selects=document.querySelectorAll('#strategy-placements select'),houseMap={0:1,1:2,2:4,3:5,4:6,5:7,6:8,7:9,8:10,9:11,10:12};
 Object.entries(houseMap).forEach(([index,house])=>{const sign=chart.cusps?.[house-1]?.sign;if(selects[index]){selects[index].value=sign||'';selects[index].dispatchEvent(new Event('change'))}});
 ['Mars','Venus','Jupiter','Saturn'].forEach((name,i)=>{if(selects[11+i]){selects[11+i].value=chart.bodies[name]?.sign||'';selects[11+i].dispatchEvent(new Event('change'))}});
 message.textContent='Chart calculated. Guidance controls now use these placements.';
 window.dispatchEvent(new CustomEvent('starstruck:chart-calculated',{detail:{chart,birthInput:payload}}));
 try{localStorage.setItem('ss-calculated-chart',JSON.stringify(chart))}catch{message.textContent+=' Browser storage is unavailable.'}
 }catch(e){if(requestId===chartSequence)message.textContent=e.name==='AbortError'?'Chart request stopped. Please try again.':e.message}finally{clearTimeout(timeout);if(requestId===chartSequence)button.disabled=false}};
 document.getElementById('delete-data')?.addEventListener('click',()=>{selected=null;invalidate();message.textContent='Birth data and calculated chart cleared.'});
})();
