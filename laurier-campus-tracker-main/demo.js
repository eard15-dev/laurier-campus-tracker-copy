// Frontend-only sample API. No requests are sent to a server.
// Remove this script from index.html when connecting the real backend.
(() => {
  const spaces = [
    {id:'library-study',building:'Library',name:'Study area (demo)',category:'Study',description:'Illustrative study space. Verify the location before release.'},
    {id:'campus-common',building:'Campus common spaces',name:'Common lounge (demo)',category:'Common',description:'Illustrative common space for the UI demonstration.'},
    {id:'athletic-exercise',building:'Athletic Complex',name:'Exercise area (demo)',category:'Fitness',description:'Illustrative exercise space. Ratings are student estimates.'}
  ].sort((a,b)=>a.building.localeCompare(b.building));
  // In-memory reports intentionally reset on page reload.
  const reports=[];
  function status(id,now) {
    const result={};
    for(const field of ['noise','busyness']) {
      const eligible=reports.filter(r=>r.space_id===id && r[field]!=null && now-r.created_at<3600 && r.created_at<=now).reverse();
      if(!eligible.length){result[field]={value:null,count:0,updated_at:null,limited:false};continue;}
      const counts=new Map();
      for(const r of eligible)counts.set(r[field],(counts.get(r[field])||0)+1);
      const max=Math.max(...counts.values());
      result[field]={value:eligible.find(r=>counts.get(r[field])===max)[field],count:eligible.length,updated_at:eligible[0].created_at,limited:eligible.length===1};
    }
    return result;
  }
  window.CAMPUS_DEMO={async request(path,options={}) {
    const now=Date.now()/1000;
    if(path==='/api/reports' && options.method==='POST') {
      const p=JSON.parse(options.body);
      if(!spaces.some(s=>s.id===p.space_id))throw new Error('Choose a configured space.');
      if(p.noise==null && p.busyness==null)throw new Error('Choose noise, busyness, or both.');
      if(p.noise!=null && !['Quiet','Moderate','Loud'].includes(p.noise))throw new Error('Choose a valid noise level.');
      if(p.busyness!=null && (!Number.isInteger(p.busyness)||p.busyness<1||p.busyness>5))throw new Error('Choose a busyness level from 1 to 5.');
      reports.push({...p,created_at:now});
      return {message:'Demo report saved for this preview session.',report_id:reports.length};
    }
    if(path==='/api/spaces')return {spaces:spaces.map(s=>({...s,status:status(s.id,now)})),as_of:now};
    const id=decodeURIComponent(path.replace('/api/spaces/',''));
    const space=spaces.find(s=>s.id===id);
    if(!space)throw new Error('Space not found.');
    return {space:{...space,status:status(id,now)},as_of:now};
  }};
})();
