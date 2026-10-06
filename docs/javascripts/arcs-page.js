const arcsPageScriptUrl = document.currentScript.src
let arcsSamplesModule
let arcsSamplesData
let arcsDatabasesModule
let arcsDatabasesData
const arcsLoadingTimers = new WeakMap()

const showArcsLoading = root => {
  const status = root.querySelector("[data-arcs-loading]")
  status.querySelector("span").textContent = status.dataset.loadingLabel
  status.querySelector("button").hidden = true
  delete status.dataset.error
  clearTimeout(arcsLoadingTimers.get(root))
  arcsLoadingTimers.set(root, setTimeout(() => {
    if (root.dataset.loading === "true") status.hidden = false
  }, 150))
}

const finishArcsLoading = root => {
  clearTimeout(arcsLoadingTimers.get(root))
  arcsLoadingTimers.delete(root)
  root.removeAttribute("aria-busy")
  root.querySelector("[data-arcs-loading]").hidden = true
}

const failArcsLoading = (root, message, retry) => {
  clearTimeout(arcsLoadingTimers.get(root))
  arcsLoadingTimers.delete(root)
  root.removeAttribute("aria-busy")
  const status = root.querySelector("[data-arcs-loading]")
  status.dataset.error = "true"
  status.querySelector("span").textContent = message
  const button = status.querySelector("button")
  button.hidden = false
  button.onclick = retry
  status.hidden = false
}

const loadArcsDatabases = (page, showLoading = false) => {
  const databases = page.querySelector("[data-arcs-databases]")
  if (!databases || databases.dataset.initialized === "true") return
  if (showLoading) showArcsLoading(databases)
  if (databases.dataset.loading === "true") return

  databases.dataset.loading = "true"
  databases.setAttribute("aria-busy", "true")
  arcsDatabasesModule ??= import(new URL("arcs-databases.js", arcsPageScriptUrl))
  arcsDatabasesData ??= fetch(new URL(databases.dataset.source, window.location.href)).then(response => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    return response.json()
  })
  Promise.all([arcsDatabasesModule, arcsDatabasesData])
    .then(([module, data]) => {
      module.initializeArcsDatabases(databases, data)
      finishArcsLoading(databases)
    })
    .catch(error => {
      arcsDatabasesModule = undefined
      arcsDatabasesData = undefined
      delete databases.dataset.loading
      failArcsLoading(
        databases,
        `Databases could not be loaded: ${error.message}`,
        () => loadArcsDatabases(page, true),
      )
    })
}

const loadArcsSamples = (page, showLoading = false) => {
  const samples = page.querySelector("[data-arcs-samples]")
  if (!samples || samples.dataset.initialized === "true") return
  if (showLoading) showArcsLoading(samples)
  if (samples.dataset.loading === "true") return

  samples.dataset.loading = "true"
  samples.setAttribute("aria-busy", "true")
  arcsSamplesModule ??= import(new URL("arcs-samples.js", arcsPageScriptUrl))
  arcsSamplesData ??= fetch(new URL(samples.dataset.source, window.location.href)).then(response => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    return response.json()
  })
  Promise.all([arcsSamplesModule, arcsSamplesData])
    .then(([module, tasks]) => {
      module.initializeArcsSamples(samples, tasks)
      finishArcsLoading(samples)
    })
    .catch(error => {
      arcsSamplesModule = undefined
      arcsSamplesData = undefined
      delete samples.dataset.loading
      failArcsLoading(
        samples,
        `Sample tasks could not be loaded: ${error.message}`,
        () => loadArcsSamples(page, true),
      )
    })
}

const updateArcsTabIndicator = (page, tab) => {
  const indicator = page.querySelector(".arcs-tabs__indicator")
  if (!indicator) return
  indicator.style.width = `${tab.offsetWidth}px`
  indicator.style.transform = `translateX(${tab.offsetLeft}px)`
  requestAnimationFrame(() => indicator.classList.add("is-ready"))
}

const selectArcsTab = (page, tab, updateHash = false) => {
  for (const candidate of page.querySelectorAll('[role="tab"]')) {
    const selected = candidate === tab
    candidate.setAttribute("aria-selected", selected ? "true" : "false")
    candidate.tabIndex = selected ? 0 : -1
  }

  for (const panel of page.querySelectorAll('[role="tabpanel"]')) {
    panel.hidden = panel.id !== tab.getAttribute("aria-controls")
  }

  const panel = tab.getAttribute("aria-controls")
  if (panel === "arcs-database") loadArcsDatabases(page, true)
  if (panel === "arcs-sample-tasks") loadArcsSamples(page, true)
  updateArcsTabIndicator(page, tab)
  if (updateHash) history.replaceState(null, "", `#${tab.getAttribute("aria-controls")}`)
}

const tabForArcsHash = page => {
  const hash = location.hash.slice(1)
  const targetPanel = document.getElementById(hash)?.closest('[role="tabpanel"]')
  const panelId = targetPanel?.id || hash
  return [...page.querySelectorAll('[role="tab"]')]
    .find(tab => tab.getAttribute("aria-controls") === panelId)
}

const initializeArcsLeaderboard = root => {
  const table = root.querySelector("[data-arcs-leaderboard-table]")
  if (!table) return

  const headers = [...table.querySelectorAll("thead tr:first-child th")]
  const body = table.tBodies[0]
  const rows = [...body.rows]
  rows.forEach((row, index) => row.dataset.sourceOrder = index)

  let sortColumn = 5
  let sortDirection = "descending"

  const sort = (column, direction) => {
    sortColumn = column
    sortDirection = direction
    const multiplier = direction === "ascending" ? 1 : -1
    rows.sort((left, right) => {
      const leftValue = Number.parseFloat(left.cells[column].textContent)
      const rightValue = Number.parseFloat(right.cells[column].textContent)
      return multiplier * (leftValue - rightValue)
        || Number(left.dataset.sourceOrder) - Number(right.dataset.sourceOrder)
    })

    rows.forEach((row, index) => {
      body.append(row)
      const rank = row.cells[0]
      rank.textContent = index < 3 ? ["🥇", "🥈", "🥉"][index] : String(index + 1)
      rank.setAttribute("aria-label", `Rank ${index + 1}`)
      for (const cell of row.cells) cell.classList.remove("is-sorted")
      row.cells[column].classList.add("is-sorted")
    })

    headers.forEach((header, index) => {
      header.setAttribute("aria-sort", index === column ? direction : "none")
      header.classList.toggle("is-sorted", index === column)
    })
  }

  headers.forEach((header, index) => {
    if (index < 2) return
    header.classList.add("is-sortable")
    header.tabIndex = 0
    header.setAttribute("aria-sort", "none")
    header.addEventListener("click", () => {
      const direction = sortColumn === index && sortDirection === "descending"
        ? "ascending"
        : "descending"
      sort(index, direction)
    })
    header.addEventListener("keydown", event => {
      if (!["Enter", " "].includes(event.key)) return
      event.preventDefault()
      header.click()
    })
  })

  sort(sortColumn, sortDirection)
}

const initializeArcsPage = marker => {
  if (marker.dataset.initialized === "true") return
  marker.dataset.initialized = "true"

  const page = marker.closest(".md-content__inner")
  const tabs = [...page.querySelectorAll('[role="tab"]')]
  for (const tab of tabs) {
    const panel = tab.getAttribute("aria-controls")
    const prefetch = panel === "arcs-database"
      ? () => loadArcsDatabases(page)
      : panel === "arcs-sample-tasks"
        ? () => loadArcsSamples(page)
        : null
    if (prefetch) {
      let hoverTimer
      tab.addEventListener("pointerenter", event => {
        if (event.pointerType === "touch") return
        hoverTimer = setTimeout(prefetch, 75)
      })
      tab.addEventListener("pointerleave", () => clearTimeout(hoverTimer))
      tab.addEventListener("focus", prefetch, { once: true })
    }
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

  const activeTab = hashTab || tabs.find(tab => tab.getAttribute("aria-selected") === "true")
  if (activeTab?.getAttribute("aria-controls") === "arcs-database") loadArcsDatabases(page, true)
  if (activeTab) updateArcsTabIndicator(page, activeTab)

  const tabsContainer = page.querySelector(".arcs-tabs")
  new ResizeObserver(() => {
    const selectedTab = tabs.find(tab => tab.getAttribute("aria-selected") === "true")
    if (selectedTab) updateArcsTabIndicator(page, selectedTab)
  }).observe(tabsContainer)

  const leaderboard = page.querySelector("[data-arcs-leaderboard]")
  if (leaderboard) initializeArcsLeaderboard(leaderboard)
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
