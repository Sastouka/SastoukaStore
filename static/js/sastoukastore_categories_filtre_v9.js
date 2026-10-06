/* ============================================================
   SASTOUKASTORE — FILTRE CATÉGORIES V9
   Compatible avec la recherche catalogue existante.
   ============================================================ */
(function(){
  "use strict";

  function normalize(value){
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g,"")
      .toLowerCase()
      .replace(/\s+/g," ")
      .trim();
  }

  const cards = Array.from(document.querySelectorAll(
    ".vip-product-card, .premium-product, .product-card, .digital-card"
  ));

  const categories = Array.from(document.querySelectorAll(
    ".vip-category-card[data-category-id]"
  ));

  if(!categories.length || !cards.length) return;

  let activeCategory = "";

  /* Ajoute l'identifiant de catégorie à chaque carte produit.
     Le patch HTML écrit cet attribut depuis p.category_id. */

  cards.forEach(function(card){
    card.dataset.sskCategoryId = String(
      card.getAttribute("data-category-id") || ""
    ).trim();
  });

  function getSearchInput(){
    return document.getElementById("sskCatalogSearch");
  }

  function getSearchResult(){
    return document.getElementById("sskCatalogSearchResult");
  }

  function getGrid(){
    return document.querySelector(".vip-product-grid") ||
           document.querySelector(".product-grid") ||
           document.querySelector(".products-grid");
  }

  function getOrCreateState(){
    let state = document.getElementById("sskCategoryFilterState");
    if(state) return state;

    const catalogue = document.getElementById("catalogue");
    if(!catalogue) return null;

    const heading = catalogue.querySelector(".vip-catalogue-heading");
    state = document.createElement("div");
    state.id = "sskCategoryFilterState";
    state.className = "ssk-category-filter-state";
    state.innerHTML =
      '<span>Catégorie :</span><strong></strong>';

    if(heading){
      heading.insertAdjacentElement("afterend", state);
    }else{
      catalogue.insertBefore(state, catalogue.firstChild);
    }
    return state;
  }

  function getQuery(){
    const input = getSearchInput();
    return input ? normalize(input.value) : "";
  }

  function update(){
    const query = getQuery();
    let visible = 0;

    cards.forEach(function(card){
      if(!card.dataset.sskSearchText){
        card.dataset.sskSearchText = normalize(card.textContent);
      }

      const textMatch = !query ||
        card.dataset.sskSearchText.includes(query);

      const categoryId = String(
        card.dataset.sskCategoryId || ""
      ).trim();

      const categoryMatch = !activeCategory ||
        categoryId === activeCategory;

      const show = textMatch && categoryMatch;
      card.hidden = !show;

      if(show) visible++;
    });

    /* Message catégorie active */
    const state = getOrCreateState();
    if(state){
      const strong = state.querySelector("strong");
      const activeButton = categories.find(function(btn){
        return String(btn.dataset.categoryId) === activeCategory;
      });

      if(activeCategory && activeButton){
        const name = activeButton.dataset.categoryName ||
          activeButton.textContent.trim();

        if(strong) strong.textContent = name;
        state.classList.add("is-visible");
      }else{
        state.classList.remove("is-visible");
      }
    }

    /* Harmonise le compteur de recherche avec le filtre catégorie. */
    const result = getSearchResult();
    if(result){
      if(activeCategory && query){
        result.textContent =
          visible + " support(s) trouvé(s) dans cette catégorie pour « " +
          (getSearchInput()?.value.trim() || "") + " »";
      }else if(activeCategory){
        result.textContent =
          visible + " support(s) disponible(s) dans cette catégorie";
      }else if(!query){
        result.textContent =
          cards.length + " support(s) disponible(s)";
      }
    }

    /* Message aucun résultat */
    const grid = getGrid();
    if(grid){
      let empty = document.getElementById("sskCategoryNoResult");

      if(visible === 0){
        if(!empty){
          empty = document.createElement("div");
          empty.id = "sskCategoryNoResult";
          empty.className = "ssk-search-no-result";
          empty.innerHTML =
            '<span class="icon">⌕</span>' +
            '<strong>Aucun livre dans cette sélection</strong>' +
            '<p>Choisissez une autre catégorie ou effacez la recherche.</p>';
          grid.appendChild(empty);
        }
        empty.hidden = false;
      }else if(empty){
        empty.hidden = true;
      }
    }
  }

  function setActive(button){
    categories.forEach(function(btn){
      btn.classList.toggle("ssk-category-active", btn === button);
      btn.setAttribute(
        "aria-pressed",
        btn === button ? "true" : "false"
      );
    });

    const all = document.getElementById("sskCategoryAll");
    if(all){
      all.classList.remove("ssk-category-active");
      all.setAttribute("aria-pressed","false");
    }

    activeCategory = String(
      button.dataset.categoryId || ""
    ).trim();

    update();

    const catalogue = document.getElementById("catalogue");
    if(catalogue){
      catalogue.scrollIntoView({
        behavior:"smooth",
        block:"start"
      });
    }
  }

  categories.forEach(function(button){
    button.addEventListener("click", function(event){
      event.preventDefault();
      event.stopPropagation();
      setActive(this);
    });

    button.setAttribute("role","button");
    button.setAttribute("aria-pressed","false");
  });

  /* Tous les supports */
  let all = document.getElementById("sskCategoryAll");

  if(!all){
    all = document.createElement("button");
    all.type = "button";
    all.id = "sskCategoryAll";
    all.className = "ssk-category-all ssk-category-active";
    all.setAttribute("aria-pressed","true");
    all.innerHTML = "Tous les supports";
    const section = document.querySelector(".vip-categories .vip-container");
    if(section){
      const grid = section.querySelector(".vip-category-grid");
      if(grid){
        grid.insertAdjacentElement("afterend", all);
      }else{
        section.appendChild(all);
      }
    }
  }

  all.addEventListener("click", function(){
    activeCategory = "";

    categories.forEach(function(btn){
      btn.classList.remove("ssk-category-active");
      btn.setAttribute("aria-pressed","false");
    });

    this.classList.add("ssk-category-active");
    this.setAttribute("aria-pressed","true");

    update();

    const catalogue = document.getElementById("catalogue");
    if(catalogue){
      catalogue.scrollIntoView({
        behavior:"smooth",
        block:"start"
      });
    }
  });

  /* Permet à la recherche existante de déclencher aussi notre filtre.
     On observe les changements du champ sans remplacer son script. */
  const input = getSearchInput();
  if(input){
    input.addEventListener("input", function(){
      window.setTimeout(update,0);
    });
  }

  /* Premier état */
  update();

})();
