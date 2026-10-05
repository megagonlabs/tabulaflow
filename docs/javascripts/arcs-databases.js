class ArcsDatabaseBrowser {
  constructor(root, databases) {
    this.root = root
    this.browser = root.querySelector("[data-database-browser]")
    this.status = root.querySelector("[data-database-status]")
    this.name = root.querySelector("[data-database-name]")
    this.position = root.querySelector("[data-database-position]")
    this.schema = root.querySelector("[data-database-schema]")
    this.previous = root.querySelector("[data-database-previous]")
    this.next = root.querySelector("[data-database-next]")
    this.databases = databases
    this.databaseIndex = 0
  }

  initialize() {
    this.previous.addEventListener("click", () => this.move(-1))
    this.next.addEventListener("click", () => this.move(1))
    this.status.hidden = true
    this.browser.hidden = false
    this.render()
  }

  move(offset) {
    const nextIndex = this.databaseIndex + offset
    if (nextIndex < 0 || nextIndex >= this.databases.length) return
    this.databaseIndex = nextIndex
    this.render()
  }

  render() {
    const database = this.databases[this.databaseIndex]
    this.name.textContent = database.name
    this.position.textContent = `${this.databaseIndex + 1} of ${this.databases.length}`
    this.previous.disabled = this.databaseIndex === 0
    this.next.disabled = this.databaseIndex === this.databases.length - 1
    this.schema.replaceChildren(...database.tables.map(table => this.renderTable(table)))
  }

  renderTable(table) {
    const card = document.createElement("section")
    card.className = "arcs-schema-card"

    const header = document.createElement("header")
    header.className = "arcs-schema-card__header"
    const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg")
    icon.setAttribute("viewBox", "0 0 24 24")
    icon.setAttribute("aria-hidden", "true")
    const box = document.createElementNS("http://www.w3.org/2000/svg", "rect")
    box.setAttribute("x", "3")
    box.setAttribute("y", "3")
    box.setAttribute("width", "18")
    box.setAttribute("height", "18")
    box.setAttribute("rx", "2")
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line")
    line.setAttribute("x1", "3")
    line.setAttribute("y1", "9")
    line.setAttribute("x2", "21")
    line.setAttribute("y2", "9")
    icon.append(box, line)

    const name = document.createElement("code")
    name.textContent = table.name
    const rows = document.createElement("span")
    rows.textContent = `${table.rows} rows`
    header.append(icon, name, rows)

    const schema = document.createElement("table")
    schema.className = "arcs-schema-table"
    schema.setAttribute("aria-label", `${table.name} schema`)
    const body = document.createElement("tbody")
    for (const column of table.columns) {
      const row = document.createElement("tr")
      const columnName = document.createElement("td")
      columnName.textContent = column.name
      const details = document.createElement("td")
      if (column.primary) details.append(this.badge("PK", "arcs-schema-key--primary"))
      if (column.foreign) details.append(this.badge(`FK → ${column.foreign}`, "arcs-schema-key--foreign"))
      const type = document.createElement("span")
      type.textContent = column.type
      details.append(type)
      row.append(columnName, details)
      body.append(row)
    }
    schema.append(body)
    card.append(header, schema)
    return card
  }

  badge(label, modifier) {
    const badge = document.createElement("span")
    badge.className = `arcs-schema-key ${modifier}`
    badge.textContent = label
    return badge
  }
}

export const initializeArcsDatabases = (root, databases) => {
  if (root.dataset.initialized === "true") return
  if (!Array.isArray(databases) || databases.length === 0) throw new Error("No databases found")
  root.dataset.initialized = "true"
  delete root.dataset.loading
  new ArcsDatabaseBrowser(root, databases).initialize()
}
