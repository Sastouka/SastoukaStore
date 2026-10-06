let deferredPrompt=null;
const installBtn=document.getElementById("installBtn");
window.addEventListener("beforeinstallprompt",(event)=>{event.preventDefault();deferredPrompt=event;if(installBtn)installBtn.hidden=false});
if(installBtn){installBtn.addEventListener("click",async()=>{if(!deferredPrompt)return;deferredPrompt.prompt();await deferredPrompt.userChoice;deferredPrompt=null;installBtn.hidden=true})}
window.addEventListener("appinstalled",()=>{if(installBtn)installBtn.hidden=true});
if("serviceWorker" in navigator){window.addEventListener("load",()=>{navigator.serviceWorker.register("/static/sw.js").catch(console.error)})}
document.querySelectorAll(".product-footer button").forEach((button)=>{button.addEventListener("click",()=>{const badge=document.getElementById("cartBadge");if(badge)badge.textContent=Number(badge.textContent||0)+1})});
