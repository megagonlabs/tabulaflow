const selectArcsTab = (page, tab, updateHash = false) => {
  for (const candidate of page.querySelectorAll('[role="tab"]')) {
    const selected = candidate === tab
    candidate.setAttribute("aria-selected", selected ? "true" : "false")
    candidate.tabIndex = selected ? 0 : -1
  }

  for (const panel of page.querySelectorAll('[role="tabpanel"]')) {
    panel.hidden = panel.id !== tab.getAttribute("aria-controls")
  }

  if (updateHash) history.replaceState(null, "", `#${tab.getAttribute("aria-controls")}`)
}

const tabForArcsHash = page => {
  const hash = location.hash.slice(1)
  const targetPanel = document.getElementById(hash)?.closest('[role="tabpanel"]')
  const panelId = targetPanel?.id || hash
  return [...page.querySelectorAll('[role="tab"]')]
    .find(tab => tab.getAttribute("aria-controls") === panelId)
}

const initializeArcsPage = marker => {
  if (marker.dataset.initialized === "true") return
  marker.dataset.initialized = "true"

  const page = marker.closest(".md-content__inner")
  const tabs = [...page.querySelectorAll('[role="tab"]')]
  for (const tab of tabs) {
    tab.addEventListener("click", () => selectArcsTab(page, tab, true))
    tab.addEventListener("keydown", event => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return

      event.preventDefault()
      const current = tabs.indexOf(tab)
      const next = event.key === "Home"
        ? tabs[0]
        : event.key === "End"
          ? tabs.at(-1)
          : tabs[(current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length]
      selectArcsTab(page, next, true)
      next.focus()
    })
  }

  const hashTab = tabForArcsHash(page)
  if (hashTab) selectArcsTab(page, hashTab)
}

window.addEventListener("hashchange", () => {
  const marker = document.querySelector("[data-arcs-page]")
  if (!marker) return

  const page = marker.closest(".md-content__inner")
  const tab = tabForArcsHash(page)
  if (tab) selectArcsTab(page, tab)
})

document$.subscribe(() => {
  const root = document.querySelector("[data-arcs-page]")
  if (root) initializeArcsPage(root)
})
