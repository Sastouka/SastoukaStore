/* SASTOUKASTORE ADMIN DIGITAL V2 */
(function(){
"use strict";
function norm(v){return String(v||"").replace(/\s+/g," ").trim()}
function hide(el){if(el){el.setAttribute("data-ssk-hidden-digital","1");el.style.setProperty("display","none","important")}}
function replaceTree(root){
  const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  const a=[];
  while(w.nextNode()){
    const p=w.currentNode.parentElement;
    if(p && p.closest("script,style,noscript")) continue;
    a.push(w.currentNode);
  }
  a.forEach(n=>{
    n.nodeValue=n.nodeValue
      .replace(/Dernières\s+commandes/gi,"Derniers achats")
      .replace(/Dernieres\s+commandes/gi,"Derniers achats")
      .replace(/Statuts\s+des\s+commandes/gi,"Statuts des achats")
      .replace(/Rechercher\s+une\s+commande/gi,"Rechercher un achat")
      .replace(/N°\s*commande/gi,"N° achat")
      .replace(/Commandes\s+numériques/gi,"Achats numériques")
      .replace(/Commande\s+numérique/gi,"Achat numérique")
      .replace(/Commandes/gi,"Achats")
      .replace(/Commande/gi,"Achat");
  });
}
function clean(){
  replaceTree(document.body);
  document.querySelectorAll("a[href]").forEach(a=>{
    const h=a.getAttribute("href")||"";
    if(h.includes("/admin/commandes")||h.includes("/admin/commande/"))
      a.textContent=norm(a.textContent).replace(/Commandes/gi,"Achats").replace(/Commande/gi,"Achat");
    if(h.includes("/admin/ventes")) a.textContent="Achats LIVE";
    if(h.includes("/admin/produit/")&&h.includes("/stock")) hide(a);
  });

  document.querySelectorAll('input[name="stock"],select[name="stock"],textarea[name="stock"]').forEach(x=>{
    const l=x.closest("label");
    hide(l||x);
  });
  document.querySelectorAll('input[name="delivery_status"],select[name="delivery_status"],textarea[name="delivery_status"]').forEach(x=>{
    const l=x.closest("label");
    hide(l||x.closest("form")||x);
  });

  document.querySelectorAll(".price-stock span").forEach(x=>{
    if(/\bstock\b/i.test(norm(x.textContent))) hide(x);
  });

  document.querySelectorAll(".metrics article,.stat-card").forEach(x=>{
    const t=norm(x.textContent).toLowerCase();
    if(t.includes("stock")||t.includes("rupture")) hide(x);
  });

  document.querySelectorAll('form[action*="/statut"],a[href*="/statut"]').forEach(hide);

  document.querySelectorAll("th,td,span,small,p,label").forEach(x=>{
    if(x.children.length) return;
    const t=norm(x.textContent);
    if(/^stock\s*:?\s*$/i.test(t)||/^ruptures?$/i.test(t)||/^livraison$/i.test(t))
      hide(x);
  });

  document.querySelectorAll("a").forEach(a=>{
    if(/retour aux commandes/i.test(norm(a.textContent)))
      a.textContent="← Retour aux achats";
  });

  document.title=(document.title||"")
    .replace(/Ventes LIVE/gi,"Achats LIVE")
    .replace(/Commandes/gi,"Achats")
    .replace(/Commande/gi,"Achat");
}
if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",clean,{once:true});
else clean();
window.addEventListener("pageshow",clean);
})();