const selectDemo = (gallery, tab, updateHash = false) => {
  const stage = gallery.querySelector(".demo-gallery__stage")
  const video = gallery.querySelector(".demo-gallery__video")
  const placeholder = gallery.querySelector(".media-placeholder")

  for (const candidate of gallery.querySelectorAll('[role="tab"]')) {
    const selected = candidate === tab
    candidate.setAttribute("aria-selected", selected ? "true" : "false")
    candidate.tabIndex = selected ? 0 : -1
  }

  stage.setAttribute("aria-labelledby", tab.id)
  placeholder.querySelector(".media-placeholder__type").textContent = tab.dataset.type
  placeholder.querySelector("strong").textContent = tab.dataset.title
  placeholder.querySelector(".media-placeholder__content > span:last-child").textContent = tab.dataset.description

  video.pause()
  video.removeAttribute("src")
  video.removeAttribute("poster")
  video.load()

  if (tab.dataset.videoSrc) {
    video.src = tab.dataset.videoSrc
    if (tab.dataset.poster) video.poster = tab.dataset.poster
    video.hidden = false
    placeholder.hidden = true
  } else {
    video.hidden = true
    placeholder.hidden = false
  }

  if (updateHash) history.replaceState(null, "", `#${tab.dataset.anchorId}`)
}

const tabForDemoHash = gallery => {
  const anchor = document.getElementById(location.hash.slice(1))
  if (!anchor?.classList.contains("demo-gallery__anchor")) return null

  const tab = document.getElementById(anchor.dataset.tabId)
  return tab?.closest(".demo-gallery") === gallery ? tab : null
}

const initializeDemoGallery = gallery => {
  const tabs = [...gallery.querySelectorAll('[role="tab"]')]

  for (const tab of tabs) {
    tab.addEventListener("click", () => selectDemo(gallery, tab, true))
    tab.addEventListener("keydown", event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return

      event.preventDefault()
      const current = tabs.indexOf(tab)
      const next = event.key === "Home"
        ? tabs[0]
        : event.key === "End"
          ? tabs.at(-1)
          : tabs[(current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length]
      selectDemo(gallery, next, true)
      next.focus()
    })
  }

  const tab = tabForDemoHash(gallery)
  if (tab) selectDemo(gallery, tab)
}

window.addEventListener("hashchange", () => {
  const anchor = document.getElementById(location.hash.slice(1))
  const gallery = anchor?.closest(".demo-gallery")
  const tab = gallery ? tabForDemoHash(gallery) : null
  if (tab) selectDemo(gallery, tab)
})

document$.subscribe(() => {
  const gallery = document.querySelector(".demo-gallery")
  if (gallery) initializeDemoGallery(gallery)
})
