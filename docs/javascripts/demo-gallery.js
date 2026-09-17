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

  if (updateHash) history.replaceState(null, "", `#${tab.id}`)
}

const balancedDemoTabRows = (widths, available, gap) => {
  let rowCount = 1
  let used = 0

  for (const width of widths) {
    if (width > available) return null
    const next = used ? used + gap + width : width
    if (used && next > available + 0.5) {
      rowCount++
      used = width
    } else {
      used = next
    }
  }

  if (rowCount === 1) return null

  const costs = Array.from({ length: rowCount + 1 }, () => Array(widths.length + 1).fill(Infinity))
  const breaks = Array.from({ length: rowCount + 1 }, () => Array(widths.length + 1).fill(-1))
  costs[0][0] = 0

  for (let row = 1; row <= rowCount; row++) {
    for (let end = row; end <= widths.length; end++) {
      used = 0
      for (let start = end - 1; start >= row - 1; start--) {
        used = widths[start] + (used ? gap + used : 0)
        if (used > available + 0.5) break
        const remainder = available - used
        const cost = costs[row - 1][start] + remainder * remainder
        if (cost < costs[row][end]) {
          costs[row][end] = cost
          breaks[row][end] = start
        }
      }
    }
  }

  const rows = []
  let end = widths.length
  for (let row = rowCount; row > 0; row--) {
    const start = breaks[row][end]
    if (start < 0) return null
    rows.unshift([start, end])
    end = start
  }
  return rows
}

const layoutDemoTabs = tabs => {
  const items = [...tabs.querySelectorAll('[role="tab"]')]
  for (const item of items) item.style.removeProperty("flex")
  tabs.classList.remove("demo-gallery__tabs--full-width")
  if (items.length < 2) return

  const style = getComputedStyle(tabs)
  let available = tabs.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight)
  const gap = parseFloat(style.columnGap) || 0
  const widths = items.map(item => item.getBoundingClientRect().width)
  let rows = balancedDemoTabRows(widths, available, gap)
  if (!rows) return

  tabs.classList.add("demo-gallery__tabs--full-width")
  available = tabs.clientWidth
  rows = balancedDemoTabRows(widths, available, gap) || [[0, items.length]]

  for (const [start, end] of rows) {
    const count = end - start
    const usedWidth = widths.slice(start, end).reduce((sum, width) => sum + width, 0)
    const extra = (available - usedWidth - gap * (count - 1)) / count
    for (let index = start; index < end; index++) {
      items[index].style.flex = `0 0 ${widths[index] + extra}px`
    }
  }
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

  const tab = tabs.find(candidate => `#${candidate.id}` === location.hash)
  if (tab) selectDemo(gallery, tab)
  requestAnimationFrame(() => layoutDemoTabs(gallery.querySelector(".demo-gallery__tabs")))
}

window.addEventListener("hashchange", () => {
  const tab = document.getElementById(location.hash.slice(1))
  const gallery = tab?.closest(".demo-gallery")
  if (gallery && tab.getAttribute("role") === "tab") selectDemo(gallery, tab)
})

window.addEventListener("resize", () => {
  requestAnimationFrame(() => {
    for (const tabs of document.querySelectorAll(".demo-gallery__tabs")) layoutDemoTabs(tabs)
  })
})

document$.subscribe(() => {
  const gallery = document.querySelector(".demo-gallery")
  if (gallery) initializeDemoGallery(gallery)
})
