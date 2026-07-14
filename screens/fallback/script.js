(() => {
  const data = window.__fallbackData;
  document.getElementById('fallback-cause').textContent = data.cause || 'Something went wrong';
  document.getElementById('fallback-description').innerHTML = data.description || 'No details available.';

  document.getElementById('fallback-btn').addEventListener('click', () => {
    navigateTo(data.returnTo || 'home');
  });
})();
