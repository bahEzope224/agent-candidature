// Content Script for JobAgent QuickSave

function extractJobInfo() {
  const url = window.location.href;
  let title = '';
  let company = '';
  let platform = '';

  if (url.includes('linkedin.com')) {
    platform = 'LinkedIn';
    // Plusieurs sélecteurs possibles selon la version de l'interface LinkedIn
    title = document.querySelector('.job-details-jobs-unified-top-card__job-title')?.innerText || 
            document.querySelector('.jobs-details-sidebar__job-details-title')?.innerText ||
            document.querySelector('h1.t-24')?.innerText;
            
    company = document.querySelector('.job-details-jobs-unified-top-card__company-name')?.innerText ||
              document.querySelector('.jobs-details-sidebar__company-name')?.innerText ||
              document.querySelector('.job-details-jobs-unified-top-card__primary-description')?.innerText?.split('·')[0];
  } else if (url.includes('welcometothejungle.com')) {
    platform = 'WTTJ';
    title = document.querySelector('h1')?.innerText;
    company = document.querySelector('header a[href*="/companies/"]')?.innerText || 
              document.querySelector('meta[property="og:description"]')?.content?.split('·')[0];
  } else {
    // Détection générique (Open Graph)
    platform = 'Autre';
    title = document.querySelector('meta[property="og:title"]')?.content || document.title;
    company = document.querySelector('meta[property="og:site_name"]')?.content || 'Inconnue';
  }

  return {
    title: title?.trim(),
    company: company?.trim(),
    url,
    platform
  };
}

// Escuchar mensajes de la popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "GET_JOB_INFO") {
    sendResponse(extractJobInfo());
  }
});
