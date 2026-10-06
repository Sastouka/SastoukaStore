/* SastoukaStore — ACCÈS ADMIN DISCRET : 7 CLICS SUR LE LOGO */
(function () {
  "use strict";

  var REQUIRED_CLICKS = 7;
  var WINDOW_MS = 5000;
  var clicks = 0;
  var timer = null;
  var activeElement = null;

  function reset() {
    clicks = 0;

    if (timer) {
      clearTimeout(timer);
      timer = null;
    }

    activeElement = null;
  }

  function findLogoTarget(target) {
    if (!target || !target.closest) return null;

    /*
      On cible uniquement le logo / bloc de marque de l'en-tête.
      Aucun compteur, contour, cadenas ou message n'est injecté.
    */
    var el = target.closest(
      ".vip-brand,.premium-brand,.p64-brand,.brand"
    );

    if (el) return el;

    var img = target.closest("img.sastoukastore-header-logo");
    if (img) return img;

    return null;
  }

  function openAdmin(ev) {
    reset();

    if (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      ev.stopImmediatePropagation();
    }

    window.location.href = "/admin/login?next=/admin/dashboard";
  }

  function handleClick(ev) {
    var logo = findLogoTarget(ev.target);
    if (!logo) return;

    /*
      Le logo reste visuellement parfaitement normal.
      Le clic normal sur le logo est neutralisé afin de compter la séquence.
    */
    ev.preventDefault();
    ev.stopPropagation();

    if (activeElement && activeElement !== logo) {
      reset();
    }

    activeElement = logo;

    clicks += 1;

    if (clicks === 1) {
      timer = window.setTimeout(reset, WINDOW_MS);
    } else if (timer) {
      clearTimeout(timer);
      timer = window.setTimeout(reset, WINDOW_MS);
    }

    if (clicks >= REQUIRED_CLICKS) {
      openAdmin(ev);
    }
  }

  function removeOldVisibleAccess() {
    var ids = [
      "sastoukastoreAdminAccess22",
      "sastoukastoreAdminTrigger"
    ];

    ids.forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.remove();
    });

    document.querySelectorAll(
      ".sastoukastore-admin-access-22," +
      ".sastoukastore-admin-trigger," +
      ".sastoukastore-admin-logo-indicator"
    ).forEach(function (el) {
      el.remove();
    });

    /*
      Supprime également les styles/éléments issus des anciennes versions.
    */
    var oldStyle = document.getElementById("sastoukastoreAdmin7ClicksStyle");
    if (oldStyle) oldStyle.remove();
    var oldStyle22 = document.getElementById("sastoukastoreAdminAccess22Style");
    if (oldStyle22) oldStyle22.remove();
  }

  function init() {
    removeOldVisibleAccess();

    /*
      Capture phase pour fonctionner même si le header est recréé
      dynamiquement par un autre script.
    */
    document.addEventListener("click", handleClick, true);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
