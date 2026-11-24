(() => {
  const saved = localStorage.getItem('theme')
  const theme = saved === 'light' || saved === 'dark' ? saved : 'dark'
  document.documentElement.dataset.theme = theme
})()
