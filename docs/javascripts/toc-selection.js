let selectedTocHash

const selectTocTarget = hash => {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      if (location.hash !== hash) return

      for (const link of document.querySelectorAll(".md-sidebar--secondary .md-nav__link")) {
        link.classList.toggle("md-nav__link--active", link.hash === hash)
      }
    })
  })
}

document.addEventListener("click", event => {
  if (!(event.target instanceof Element)) return

  const link = event.target.closest(".md-sidebar--secondary .md-nav__link")
  if (!(link instanceof HTMLAnchorElement)) return

  selectedTocHash = link.hash
  selectTocTarget(selectedTocHash)
}, true)

document$.subscribe(() => {
  if (!selectedTocHash) return
  if (location.hash === selectedTocHash) {
    selectTocTarget(selectedTocHash)
  } else {
    selectedTocHash = undefined
  }
})
