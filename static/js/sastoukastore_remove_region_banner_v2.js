(function(){
  "use strict";

  var FRAGMENTS = [
    "SUPPORTS SCOLAIRES NUMERIQUES",
    "TOGO",
    "AFRIQUE FRANCOPHONE",
    "DIASPORA"
  ];

  function norm(s){
    return String(s || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g,"")
      .toUpperCase()
      .replace(/\s+/g," ")
      .trim();
  }

  function isTarget(text){
    var t = norm(text);
    var hits = 0;

    FRAGMENTS.forEach(function(f){
      if(t.indexOf(f) !== -1) hits++;
    });

    /*
     * On cible la bande si elle contient au minimum deux marqueurs
     * régionaux, ou le titre complet.
     */
    return hits >= 2 ||
      t.indexOf("SUPPORTS SCOLAIRES NUMERIQUES") !== -1 &&
      (t.indexOf("TOGO") !== -1 ||
       t.indexOf("AFRIQUE FRANCOPHONE") !== -1 ||
       t.indexOf("DIASPORA") !== -1);
  }

  function removeElement(el){
    if(!el || el.nodeType !== 1) return;

    var cls = String(el.className || "").toLowerCase();

    /*
     * Les anciens strips connus sont supprimés sans attendre le texte.
     */
    if(
      /\bssk7-strip\b/.test(cls) ||
      /\bssk-client-strip\b/.test(cls) ||
      /\bssk6-strip\b/.test(cls)
    ){
      el.remove();
      return;
    }

    var txt = norm(el.textContent || "");
    if(!txt) return;

    if(isTarget(txt)){
      /*
       * Le plus petit conteneur affichable portant le texte cible est
       * supprimé. On évite de supprimer body/main.
       */
      if(
        el.tagName !== "BODY" &&
        el.tagName !== "HTML" &&
        el.tagName !== "MAIN"
      ){
        el.remove();
      }
    }
  }

  function scan(root){
    if(!root) return;

    if(root.nodeType === 1) removeElement(root);

    var all = root.querySelectorAll
      ? root.querySelectorAll("body *")
      : [];

    for(var i=0;i<all.length;i++){
      removeElement(all[i]);
    }
  }

  function start(){
    scan(document);

    /*
     * Certains anciens scripts injectent le bandeau après DOMContentLoaded.
     */
    var observer = new MutationObserver(function(mutations){
      mutations.forEach(function(m){
        for(var i=0;i<m.addedNodes.length;i++){
          var node = m.addedNodes[i];
          if(node && node.nodeType === 1){
            removeElement(node);
            scan(node);
          }
        }
      });
    });

    if(document.documentElement){
      observer.observe(document.documentElement,{
        childList:true,
        subtree:true
      });
    }

    /*
     * Double passage différé pour les injections lentes.
     */
    window.setTimeout(function(){ scan(document); }, 50);
    window.setTimeout(function(){ scan(document); }, 500);
    window.setTimeout(function(){ scan(document); }, 1500);
  }

  if(document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded", start);
  }else{
    start();
  }

})();
