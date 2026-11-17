const selectCodeSample = (showcase, tab) => {
  for (const candidate of showcase.querySelectorAll('[role="tab"]')) {
    const selected = candidate === tab
    candidate.setAttribute("aria-selected", selected ? "true" : "false")
    candidate.tabIndex = selected ? 0 : -1
  }

  for (const panel of showcase.querySelectorAll(".code-showcase__panel")) {
    panel.hidden = panel.id !== tab.getAttribute("aria-controls")
  }
}

const initializeCodeShowcase = showcase => {
  const tabs = [...showcase.querySelectorAll('[role="tab"]')]

  for (const tab of tabs) {
    tab.addEventListener("click", () => selectCodeSample(showcase, tab))
    tab.addEventListener("keydown", event => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return

      event.preventDefault()
      const current = tabs.indexOf(tab)
      const next = event.key === "Home"
        ? tabs[0]
        : event.key === "End"
          ? tabs.at(-1)
          : tabs[(current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length]
      selectCodeSample(showcase, next)
      next.focus()
    })
  }
}

document$.subscribe(() => {
  document.querySelectorAll(".code-showcase").forEach(initializeCodeShowcase)
})
