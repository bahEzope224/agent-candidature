// Content Script for JobAgent QuickSave

function extractJobInfo() {
  const url = window.location.href;
  let title = '';
  let company = '';
  let platform = '';

  if (url.includes('linkedin.com')) {
    platform = 'LinkedIn';
    title = document.querySelector('.job-details-jobs-unified-top-card__job-title')?.innerText || 
            document.querySelector('.jobs-details-sidebar__job-details-title')?.innerText;
    company = document.querySelector('.job-details-jobs-unified-top-card__company-name')?.innerText ||
              document.querySelector('.jobs-details-sidebar__company-name')?.innerText;
  } else if (url.includes('welcometothejungle.com')) {
    platform = 'WTTJ';
    title = document.querySelector('h1')?.innerText;
    company = document.querySelector('header a[href*="/companies/"]')?.innerText || 
              document.querySelector('meta[property="og:description"]')?.content?.split('·')[0];
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
