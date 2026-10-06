/* SastoukaStore - Catalogue Search V1 */
(function(){
  "use strict";

  const input = document.getElementById("sskCatalogSearch");
  const form = document.getElementById("sskCatalogSearchForm");
  const clear = document.getElementById("sskCatalogSearchClear");
  const result = document.getElementById("sskCatalogSearchResult");
  if(!input || !form || !result) return;

  function getCards(){
    return Array.from(document.querySelectorAll(
      ".vip-product-card, .premium-product, .product-card, .digital-card"
    ));
  }

  function normalize(value){
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g,"")
      .toLowerCase()
      .replace(/\s+/g," ")
      .trim();
  }

  function update(){
    const query = normalize(input.value);
    const cards = getCards();
    let visible = 0;

    cards.forEach(function(card){
      if(!card.dataset.sskSearchText){
        card.dataset.sskSearchText = normalize(card.textContent);
      }
      const matches = !query || card.dataset.sskSearchText.includes(query);
      card.hidden = !matches;
      card.classList.toggle("ssk-search-match", !!query && matches);
      if(matches) visible++;
    });

    clear.hidden = !input.value;

    if(!input.value.trim()){
      result.textContent = cards.length + " support(s) disponible(s)";
    }else if(visible === 0){
      result.textContent = "Aucun support trouvé";
    }else{
      result.textContent = visible + " support(s) trouvé(s) pour « " +
        input.value.trim() + " »";
    }

    const grid = document.querySelector(".vip-product-grid") ||
                 document.querySelector(".product-grid") ||
                 document.querySelector(".products-grid");
    if(!grid) return;

    let empty = document.getElementById("sskCatalogSearchEmpty");
    if(visible === 0 && cards.length > 0){
      if(!empty){
        empty = document.createElement("div");
        empty.id = "sskCatalogSearchEmpty";
        empty.className = "ssk-search-no-result";
        empty.innerHTML =
          '<span class="icon">&#9906;</span>' +
          '<strong>Aucun livre ne correspond à votre recherche</strong>' +
          '<p>Essayez un autre titre, une autre matière ou un autre niveau.</p>';
        grid.appendChild(empty);
      }
      empty.hidden = false;
    }else if(empty){
      empty.hidden = true;
    }
  }

  form.addEventListener("submit", function(event){
    event.preventDefault();
    input.focus();
    update();
  });

  input.addEventListener("input", update);

  clear.addEventListener("click", function(){
    input.value = "";
    update();
    input.focus();
  });

  document.addEventListener("keydown", function(event){
    const tag = document.activeElement && document.activeElement.tagName;
    const typing = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
    if(event.key === "/" && !typing){
      event.preventDefault();
      input.focus();
    }
    if(event.key === "Escape" && document.activeElement === input && input.value){
      input.value = "";
      update();
    }
  });

  update();
})();
