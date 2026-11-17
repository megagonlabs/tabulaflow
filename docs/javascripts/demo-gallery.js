let activeDemoGallery = null

const demoButtonForHash = gallery => {
  const anchor = document.getElementById(location.hash.slice(1))
  if (!anchor?.classList.contains("demo-gallery__anchor")) return null

  const button = document.getElementById(anchor.dataset.tabId)
  return button?.closest(".demo-gallery") === gallery ? button : null
}

const closeDemo = gallery => {
  const dialog = gallery.querySelector(".demo-gallery__dialog")
  if (dialog.open) dialog.close()
}

const openDemo = async (gallery, button, { autoplay = false, updateHistory = false } = {}) => {
  if (activeDemoGallery && activeDemoGallery !== gallery) closeDemo(activeDemoGallery)
  activeDemoGallery = gallery
  gallery.demoButton = button

  const dialog = gallery.querySelector(".demo-gallery__dialog")
  const video = dialog.querySelector("video")
  const anchorId = button.dataset.anchorId

  video.setAttribute("aria-label", button.dataset.title)
  video.pause()
  video.src = button.dataset.videoSrc
  video.poster = button.dataset.poster
  video.load()

  if (!dialog.open) {
    gallery.previousOverflow = document.documentElement.style.overflow
    document.documentElement.style.overflow = "hidden"
    dialog.showModal()
  }

  if (updateHistory && location.hash !== `#${anchorId}`) {
    history.pushState({ ...history.state, demoGallery: anchorId }, "", `#${anchorId}`)
  }

  if (autoplay) {
    try {
      await video.play()
    } catch (error) {
      if (!["AbortError", "NotAllowedError"].includes(error.name)) throw error
    }
  }
}

const dismissDemo = gallery => {
  const button = gallery.demoButton
  const anchorId = button?.dataset.anchorId

  if (anchorId && location.hash === `#${anchorId}` && history.state?.demoGallery === anchorId) {
    history.back()
    return
  }

  if (anchorId && location.hash === `#${anchorId}`) {
    const state = { ...history.state }
    delete state.demoGallery
    history.replaceState(state, "", "#demo-gallery")
  }
  closeDemo(gallery)
}

const syncDemoWithHash = gallery => {
  const button = demoButtonForHash(gallery)
  if (button) openDemo(gallery, button)
  else closeDemo(gallery)
}

const initializeDemoGallery = gallery => {
  const dialog = gallery.querySelector(".demo-gallery__dialog")
  const video = dialog.querySelector("video")

  for (const button of gallery.querySelectorAll(".demo-gallery__choice")) {
    button.addEventListener("click", () => openDemo(gallery, button, { autoplay: true, updateHistory: true }))
  }

  dialog.querySelector(".demo-gallery__dialog-close").addEventListener("click", () => dismissDemo(gallery))
  dialog.addEventListener("cancel", event => {
    event.preventDefault()
    dismissDemo(gallery)
  })
  dialog.addEventListener("click", event => {
    if (event.target === dialog) dismissDemo(gallery)
  })
  dialog.addEventListener("close", () => {
    if (dialog.open) return
    video.pause()
    video.removeAttribute("src")
    video.removeAttribute("poster")
    video.load()

    if (activeDemoGallery === gallery) {
      activeDemoGallery = null
      document.documentElement.style.overflow = gallery.previousOverflow || ""
      if (gallery.demoButton?.isConnected) gallery.demoButton.focus()
    }
  })

  syncDemoWithHash(gallery)
}

location$.subscribe(() => {
  const gallery = document.querySelector(".demo-gallery")
  if (gallery) syncDemoWithHash(gallery)
})

document$.subscribe(() => {
  if (activeDemoGallery) closeDemo(activeDemoGallery)
  const gallery = document.querySelector(".demo-gallery")
  if (gallery) initializeDemoGallery(gallery)
})
