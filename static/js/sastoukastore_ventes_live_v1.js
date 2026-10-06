/* SastoukaStore — Ventes LIVE V1 */
(function(){
  "use strict";
  const CFG=window.SASTOUKASTORE_SALES_LIVE||{};
  const API=CFG.api||"/api/admin/ventes";
  const POLL_MS=5000;
  let latestSaleId=Number(CFG.initialLatestId||0), loading=false;

  const form=document.getElementById("salesFilterForm");
  const list=document.getElementById("salesList");
  const liveState=document.getElementById("liveState");
  const liveClock=document.getElementById("liveClock");
  const dot=document.getElementById("refreshDot");
  const toast=document.getElementById("newSaleToast");
  const toastText=document.getElementById("newSaleToastText");

  function esc(v){return String(v??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}
  function money(v){return Number(v||0).toLocaleString("fr-FR",{minimumFractionDigits:2,maximumFractionDigits:2})}
  function query(){const p=new URLSearchParams(new FormData(form));for(const [k,v] of [...p])if(!String(v||"").trim())p.delete(k);return p}

  function card(sale,isNew){
    const items=Array.isArray(sale.items)?sale.items:[];
    const covers=items.slice(0,4).map(i=>`<a class="ssk-cover-link" href="${esc(i.cover_url)}" target="_blank" rel="noopener"><img src="${esc(i.cover_url)}" alt="Page de garde — ${esc(i.product_name)}" loading="lazy"></a>`).join("");
    const cover=`<div class="ssk-cover-stack">${covers||'<div class="ssk-cover-empty">PDF</div>'}${items.length>4?`<span class="ssk-more-covers">+${items.length-4}</span>`:""}</div>`;
    const books=items.map(i=>`<div class="ssk-book-line"><div><b>${esc(i.product_name)}</b><small>${Number(i.quantity||1)>1?"×"+Number(i.quantity)+" · ":""}Support PDF numérique${i.variant?" · "+esc(i.variant):""}</small></div><strong>${money(i.subtotal)} FCFA</strong></div>`).join("")||'<div class="ssk-book-line muted">Aucun détail de livre enregistré.</div>';
    return `<article class="ssk-sale-card${isNew?" is-new":""}" data-sale-id="${Number(sale.id||0)}"><div class="ssk-sale-cover-column">${cover}</div><div class="ssk-sale-main"><div class="ssk-sale-top"><div><span class="ssk-sale-id">VENTE #${Number(sale.id||0)}</span><h3>${esc(sale.customer_name||"Client")}</h3><p>${esc(sale.customer_phone||"Téléphone non renseigné")} · ${esc(sale.created_at||"")}</p></div><div class="ssk-sale-price"><strong>${money(sale.total)}</strong><span>FCFA</span></div></div><div class="ssk-books">${books}</div><div class="ssk-sale-footer"><span class="ssk-paid">✓ PAYÉ</span><span>Mode : ${esc(sale.payment_method||"paypal")}</span><a href="/admin/commande/${Number(sale.id||0)}">Ouvrir la vente →</a></div></div></article>`;
  }

  function render(data,markNew){
    const sales=Array.isArray(data.sales)?data.sales:[];
    document.getElementById("salesCount").textContent=String(data.sales_count||0);
    document.getElementById("revenue").textContent=money(data.revenue);
    document.getElementById("booksCount").textContent=String(data.books_count||0);
    document.getElementById("customers").textContent=String(data.customers||0);
    document.getElementById("resultLabel").textContent=String(data.sales_count||0)+" vente(s)";
    list.innerHTML=sales.length?sales.map(s=>card(s,markNew&&Number(s.id||0)>latestSaleId)).join(""):'<div class="ssk-empty"><span>✦</span><h3>Aucune vente sur cette période</h3><p>Les nouvelles ventes payées apparaîtront automatiquement ici.</p></div>';
    const ids=sales.map(s=>Number(s.id||0)).filter(Boolean);
    if(ids.length)latestSaleId=Math.max(latestSaleId,Math.max(...ids));
    liveClock.textContent="Dernière actualisation : "+new Date().toLocaleTimeString("fr-FR");
  }

  function toastNew(data){
    const s=(data.sales||[])[0]; if(!s)return;
    toastText.textContent="#"+s.id+" · "+(s.customer_name||"Client")+" · "+money(s.total)+" FCFA";
    toast.hidden=false; clearTimeout(toastNew.t);
    toastNew.t=setTimeout(()=>toast.hidden=true,5000);
  }

  async function refresh(manual){
    if(loading)return; loading=true; dot.classList.add("busy"); liveState.textContent="Actualisation…";
    try{
      const r=await fetch(API+(query().toString()?"?"+query().toString():""),{cache:"no-store",credentials:"same-origin",headers:{Accept:"application/json"}});
      if(!r.ok){liveState.textContent=r.status===401||r.status===403?"Session administrateur expirée.":"Flux indisponible temporairement.";return}
      const data=await r.json(), serverLatest=Number(data.latest_sale_id||0), hasNew=serverLatest>latestSaleId;
      render(data,hasNew); if(hasNew&&!manual)toastNew(data);
      liveState.textContent="Flux actif · actualisation automatique toutes les 5 s";
    }catch(e){liveState.textContent="Connexion en attente…"}finally{loading=false;dot.classList.remove("busy")}
  }

  function localDate(offset){
    const d=new Date(); d.setDate(d.getDate()+offset);
    return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0");
  }

  document.querySelectorAll("[data-preset]").forEach(btn=>btn.addEventListener("click",()=>{
    const p=btn.dataset.preset, a=form.querySelector("[name=date_debut]"), b=form.querySelector("[name=date_fin]");
    if(p==="today"){a.value=localDate(0);b.value=localDate(0)}
    else if(p==="7d"){a.value=localDate(-6);b.value=localDate(0)}
    else if(p==="30d"){a.value=localDate(-29);b.value=localDate(0)}
    else{a.value="";b.value=""}
    form.submit();
  }));

  refresh(true);
  setInterval(()=>refresh(false),POLL_MS);
})();
