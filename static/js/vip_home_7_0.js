/* SastoukaStore — HOME VIP 7.0 */
(function(){
  "use strict";
  const KEY="sastoukastore_cart_v1";

  function read(){
    try{
      const value=JSON.parse(localStorage.getItem(KEY)||"[]");
      return Array.isArray(value)?value:[];
    }catch(_){return [];}
  }

  function updateCount(){
    const badge=document.getElementById("cartCount");
    if(badge) badge.textContent=String(read().length);
  }

  document.querySelectorAll(".vip-add-cart").forEach(function(btn){
    btn.addEventListener("click",function(){
      const cart=read();
      const id=String(btn.dataset.id||"");
      if(!id) return;

      if(!cart.some(function(item){return String(item.id)===id;})){
        cart.push({
          id:Number(btn.dataset.id),
          name:btn.dataset.name||"",
          price:Number(btn.dataset.price||0),
          currency:btn.dataset.currency||"FCFA",
          image:btn.dataset.image||"",
          product_type:"digital_pdf",
          quantity:1
        });
        localStorage.setItem(KEY,JSON.stringify(cart));
      }

      const original=btn.textContent;
      btn.textContent="Ajouté ✓";
      btn.disabled=true;
      updateCount();

      window.setTimeout(function(){
        btn.textContent=original;
        btn.disabled=false;
      },1100);
    });
  });

  updateCount();
})();
