/* SastoukaStore PATCH 6.6.1 */
(function(){
  "use strict";

  const ICON="/static/icons/sastoukastore-icon.png?v=661";
  const SELECTORS=[
    ".brand-mark",
    ".brand-logo",
    ".p64-brand-mark",
    ".premium-brand .brand-logo",
    ".logo-mark",
    ".site-logo",
    "[class*='brand-mark']",
    "[class*='brand-logo']",
    "[class*='logo-mark']",
    "[class*='site-logo']"
  ];

  function apply(){
    const seen=new Set();

    SELECTORS.forEach(selector=>{
      document.querySelectorAll(selector).forEach(el=>{
        if(seen.has(el)) return;
        seen.add(el);

        if(el.querySelector("img")) return;

        const value=(el.textContent||"").trim();
        if(value && value!=="C") return;

        const img=document.createElement("img");
        img.className="sastoukastore-brand-icon";
        img.src=ICON;
        img.alt="SastoukaStore";
        img.decoding="async";
        img.loading="eager";

        el.textContent="";
        el.appendChild(img);
      });
    });

    // Logo déjà présent dans un header : lorsqu'il s'agit explicitement
    // de SastoukaStore, on utilise le nouveau fichier.
    document.querySelectorAll("header img").forEach(img=>{
      const meta=((img.alt||"")+" "+(img.title||"")+" "+(img.src||"")).toLowerCase();
      if(meta.includes("sastoukastore")){
        img.src=ICON;
        img.classList.add("sastoukastore-brand-icon");
      }
    });
  }

  if(document.readyState==="loading"){
    document.addEventListener("DOMContentLoaded",apply,{once:true});
  }else{
    apply();
  }
  window.addEventListener("pageshow",apply);
})();
