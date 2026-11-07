const colors=['#2878f0','#8b5cf6','#0d9488','#e8793e','#64748b','#6366f1'];
const titleCase=value=>value?value.charAt(0).toUpperCase()+value.slice(1):'Unknown';
const money=(value,currency='USD')=>value===null||value===undefined?'—':new Intl.NumberFormat('en-US',{style:'currency',currency,maximumFractionDigits:0}).format(Number(value));
const date=value=>value?new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',year:'numeric'}).format(new Date(value)):'No deadline';

export function mapSupplier(s,index=0){
  return {...s,initials:s.name.split(' ').map(n=>n[0]).slice(0,2).join('').toUpperCase(),contact:s.contact_name,risk:titleCase(s.risk_level),score:s.reliability_score??'—',commitments:s.active_commitments??0,spend:'—',lastContact:date(s.updated_at),status:titleCase(s.status),color:colors[index%colors.length]};
}
export function supplierPayload(form){return {name:form.name,category:form.category||'',contact_name:form.contact||form.contact_name||'',email:form.email||'',phone:form.phone||'',location:form.location||'',status:(form.status||'active').toLowerCase()}}
export function mapCommitment(c,suppliers){
  const supplier=suppliers.find(s=>s.id===c.supplier_id);
  const displayStatus=c.verified_at?'Verified':c.status==='breached'?'Breached':c.status==='fulfilled'?'Fulfilled':c.status==='overdue'?'Overdue':'Pending';
  return {...c,originalId:c.id,id:`VC-${String(c.id).padStart(4,'0')}`,supplier:supplier?.name||`Supplier #${c.supplier_id}`,item:c.title,amount:money(c.current_value,c.currency),delivery:date(c.deadline),status:displayStatus,confidence:null,source:'Record',updated:date(c.updated_at),previous:money(c.previous_value,c.currency),current:money(c.current_value,c.currency),savings:c.savings};
}
export function mapInteraction(i,suppliers){return {...i,type:titleCase(i.interaction_type),supplier:suppliers.find(s=>s.id===i.supplier_id)?.name||`Supplier #${i.supplier_id}`,person:i.author_id?`User #${i.author_id}`:'System',date:date(i.occurred_at),summary:i.content,commitments:0}}
