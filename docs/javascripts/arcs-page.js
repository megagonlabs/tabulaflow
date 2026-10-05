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
