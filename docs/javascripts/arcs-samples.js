class ArcsSampleBrowser {
  constructor(root) {
    this.root = root
    this.browser = root.querySelector("[data-sample-browser]")
    this.status = root.querySelector("[data-sample-status]")
    this.question = root.querySelector("[data-task-question]")
    this.position = root.querySelector("[data-task-position]")
    this.database = root.querySelector("[data-task-database]")
    this.controls = root.querySelector("[data-ambiguity-controls]")
    this.sql = root.querySelector("[data-task-sql]")
    this.results = root.querySelector("[data-task-results]")
    this.resultsCount = root.querySelector("[data-results-count]")
    this.previous = root.querySelector("[data-task-previous]")
    this.next = root.querySelector("[data-task-next]")
    this.tasks = []
    this.taskIndex = 0
    this.selections = new Map()
    this.operators = new Map()
    this.parameters = new Map()
  }

  async initialize() {
    try {
      const source = new URL(this.root.dataset.source, window.location.href)
      const response = await fetch(source)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const tasks = await response.json()
      if (!Array.isArray(tasks) || tasks.length === 0) throw new Error("No sample tasks found")
      if (!this.root.isConnected) return

      this.tasks = tasks
      this.previous.addEventListener("click", () => this.move(-1))
      this.next.addEventListener("click", () => this.move(1))
      this.status.hidden = true
      this.browser.hidden = false
      this.renderTask()
    } catch (error) {
      this.status.textContent = `Sample tasks could not be loaded: ${error.message}`
      this.status.classList.add("arcs-samples__status--error")
    }
  }

  move(offset) {
    const nextIndex = this.taskIndex + offset
    if (nextIndex < 0 || nextIndex >= this.tasks.length) return
    this.taskIndex = nextIndex
    this.renderTask()
  }

  renderTask() {
    this.task = this.tasks[this.taskIndex]
    this.selections.clear()
    this.operators.clear()
    this.parameters.clear()

    for (const point of this.task.gold_ambiguity_points) {
      if (point.type === "finite") {
        this.selections.set(point.id, point.intended_interpretation_idx)
      } else if (point.type === "infinite") {
        this.operators.set(point.parameter_name, point.intended_parameter_operator)
        this.parameters.set(point.parameter_name, point.intended_parameter_value)
      }
    }

    this.position.textContent = `${this.taskIndex + 1} of ${this.tasks.length}`
    this.database.textContent = `Database: ${this.task.db}`
    this.previous.disabled = this.taskIndex === 0
    this.next.disabled = this.taskIndex === this.tasks.length - 1
    this.renderQuestion()
    this.renderControls()
    this.updateOutput()
  }

  phraseGroups() {
    const groups = new Map()
    let color = 0
    for (const point of this.task.gold_ambiguity_points) {
      const key = point.phrase.toLowerCase()
      if (!groups.has(key)) {
        groups.set(key, { phrase: point.phrase, ids: [], color: (color % 3) + 1 })
        color += 1
      }
      groups.get(key).ids.push(point.id)
    }
    return groups
  }

  renderQuestion() {
    const groups = [...this.phraseGroups().values()]
    const questionLower = this.task.question.toLowerCase()
    const matches = groups
      .map(group => ({ ...group, index: questionLower.indexOf(group.phrase.toLowerCase()) }))
      .filter(group => group.index >= 0)
      .sort((left, right) => left.index - right.index || right.phrase.length - left.phrase.length)

    const fragment = document.createDocumentFragment()
    fragment.append('"')
    let cursor = 0
    for (const match of matches) {
      if (match.index < cursor) continue
      fragment.append(this.task.question.slice(cursor, match.index))
      const phrase = document.createElement("span")
      phrase.className = `arcs-ambig-phrase arcs-color-${match.color}`
      phrase.dataset.ambigIds = match.ids.join(",")
      phrase.textContent = this.task.question.slice(match.index, match.index + match.phrase.length)
      phrase.addEventListener("mouseenter", () => this.highlightControls(match.ids, true))
      phrase.addEventListener("mouseleave", () => this.highlightControls(match.ids, false))
      fragment.append(phrase)
      cursor = match.index + match.phrase.length
    }
    fragment.append(this.task.question.slice(cursor), '"')
    this.question.replaceChildren(fragment)
  }

  highlightControls(ids, highlighted) {
    for (const id of ids) {
      const control = this.controls.querySelector(`[data-ambig-id="${CSS.escape(id)}"]`)
      control?.classList.toggle("is-highlighted", highlighted)
    }
  }

  renderControls() {
    this.controls.replaceChildren()
    const groups = this.phraseGroups()
    for (const point of this.task.gold_ambiguity_points) {
      const color = groups.get(point.phrase.toLowerCase()).color
      const control = document.createElement("div")
      control.className = `arcs-ambiguity-control arcs-color-${color}`
      control.dataset.ambigId = point.id
      control.setAttribute("role", "group")
      control.setAttribute("aria-label", `${point.id}: ${point.phrase}`)

      const heading = document.createElement("div")
      heading.className = "arcs-ambiguity-heading"
      const id = document.createElement("span")
      id.className = "arcs-ambig-id"
      id.textContent = point.id
      const phrase = document.createElement("span")
      phrase.textContent = `"${point.phrase}"`
      heading.append(id, phrase)
      control.append(heading)

      if (point.type === "finite") this.renderFiniteControl(control, point)
      if (point.type === "infinite") this.renderInfiniteControl(control, point)
      this.controls.append(control)
    }
  }

  renderFiniteControl(control, point) {
    const options = document.createElement("div")
    options.className = "arcs-ambiguity-options"
    for (const [index, interpretation] of point.interpretations.entries()) {
      const label = document.createElement("label")
      label.className = "arcs-ambiguity-option"
      const radio = document.createElement("input")
      radio.type = "radio"
      radio.name = `arcs-${this.task.qid}-${point.id}`
      radio.value = index
      radio.checked = this.selections.get(point.id) === index
      radio.addEventListener("change", () => {
        this.selections.set(point.id, index)
        this.pulsePhrase(point.id)
        this.updateOutput()
      })
      const text = document.createElement("span")
      text.textContent = interpretation
      label.append(radio, text)
      options.append(label)
    }
    control.append(options)
  }

  renderInfiniteControl(control, point) {
    const content = document.createElement("div")
    content.className = "arcs-infinite-control"
    const operators = document.createElement("div")
    operators.className = "arcs-operator-options"
    for (const operator of point.parameter_sample_operators) {
      const label = document.createElement("label")
      label.className = "arcs-operator-option"
      const radio = document.createElement("input")
      radio.type = "radio"
      radio.name = `arcs-operator-${this.task.qid}-${point.id}`
      radio.value = operator
      radio.checked = this.operators.get(point.parameter_name) === operator
      radio.addEventListener("change", () => {
        this.operators.set(point.parameter_name, operator)
        this.updateOutput()
      })
      const text = document.createElement("span")
      text.textContent = operator
      label.append(radio, text)
      operators.append(label)
    }

    const samples = point.parameter_sample_values || [point.intended_parameter_value]
    const intended = Number(point.intended_parameter_value)
    const minimum = this.task.qid === "004" ? 9990 : Math.floor(Math.min(...samples) * 0.5)
    const maximum = this.task.qid === "004" ? 10000 : Math.ceil(Math.max(...samples) * 1.5)
    const sliderRow = document.createElement("div")
    sliderRow.className = "arcs-value-slider"
    const slider = document.createElement("input")
    slider.type = "range"
    slider.min = minimum
    slider.max = maximum
    slider.step = point.parameter_dtype === "int" ? 1 : (maximum - minimum) / 100
    slider.value = intended
    const value = document.createElement("output")
    value.textContent = intended
    slider.addEventListener("input", () => {
      const selected = Number(slider.value)
      value.textContent = selected
      this.parameters.set(point.parameter_name, selected)
      this.updateOutput()
    })
    sliderRow.append(slider, value)
    content.append(operators, sliderRow)
    control.append(content)
  }

  pulsePhrase(pointId) {
    for (const phrase of this.question.querySelectorAll("[data-ambig-ids]")) {
      if (!phrase.dataset.ambigIds.split(",").includes(pointId)) continue
      phrase.classList.remove("is-active")
      requestAnimationFrame(() => phrase.classList.add("is-active"))
      window.setTimeout(() => phrase.classList.remove("is-active"), 900)
    }
  }

  queryId() {
    const parts = ["GQRY"]
    const points = this.task.gold_ambiguity_points
      .filter(point => point.type === "finite")
      .sort((left, right) => left.id.localeCompare(right.id))
    for (const point of points) parts.push(`${point.id}.${this.selections.get(point.id)}`)
    return parts.join("-")
  }

  updateOutput() {
    const query = this.task.gold_queries.find(candidate => candidate.id === this.queryId())
    if (!query) {
      this.sql.textContent = "-- No query is available for this interpretation."
      this.renderMessage("No execution results are available for this interpretation.")
      return
    }

    let sql = query.query
    for (const point of this.task.gold_ambiguity_points.filter(candidate => candidate.type === "infinite")) {
      const name = point.parameter_name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
      const operator = this.operators.get(point.parameter_name)
      const value = this.parameters.get(point.parameter_name)
      sql = sql.replace(new RegExp(`([<>=!]+)\\s*(:${name})`, "g"), `${operator} $2`)
      sql = sql.replace(new RegExp(`:${name}\\b`, "g"), String(value))
    }
    this.sql.textContent = sql
    this.renderResults(query.exec_result)
  }

  filteredRows(rows) {
    if (this.task.qid !== "004") return rows
    const threshold = this.parameters.get("account_balance_threshold")
    const operator = this.operators.get("account_balance_threshold")
    return rows.filter(row => {
      if (typeof row.c_acctbal !== "number") return true
      return operator === ">=" ? row.c_acctbal >= threshold : row.c_acctbal > threshold
    })
  }

  renderResults(execResult) {
    if (!execResult || execResult.error) {
      this.renderMessage(execResult?.error ? `Error: ${execResult.error}` : "No execution result is available.", true)
      return
    }

    const rows = this.filteredRows(execResult.df?.data || [])
    if (rows.length === 0) {
      this.renderMessage("Query returned no results.")
      return
    }

    const columns = Object.keys(rows[0])
    const table = document.createElement("table")
    const head = document.createElement("thead")
    const headRow = document.createElement("tr")
    for (const column of columns) {
      const cell = document.createElement("th")
      cell.scope = "col"
      cell.textContent = column
      headRow.append(cell)
    }
    head.append(headRow)

    const body = document.createElement("tbody")
    for (const row of rows.slice(0, 10)) {
      const tableRow = document.createElement("tr")
      for (const column of columns) {
        const cell = document.createElement("td")
        cell.textContent = this.formatValue(row[column])
        tableRow.append(cell)
      }
      body.append(tableRow)
    }
    table.append(head, body)
    this.results.replaceChildren(table)
    const shown = Math.min(10, rows.length)
    this.resultsCount.textContent = rows.length > shown || execResult.df_is_truncated
      ? `Showing ${shown} of ${execResult.df_is_truncated ? "many" : rows.length} rows`
      : `${rows.length} row${rows.length === 1 ? "" : "s"}`
  }

  formatValue(value) {
    if (value === null || value === undefined) return ""
    if (typeof value !== "number") return String(value)
    return Number.isInteger(value)
      ? value.toLocaleString()
      : value.toLocaleString(undefined, { maximumFractionDigits: 2 })
  }

  renderMessage(message, error = false) {
    const paragraph = document.createElement("p")
    paragraph.className = error ? "arcs-results__error" : "arcs-results__empty"
    paragraph.textContent = message
    this.results.replaceChildren(paragraph)
    this.resultsCount.textContent = ""
  }
}

document$.subscribe(() => {
  const samples = document.querySelector("[data-arcs-samples]")
  if (samples && samples.dataset.initialized !== "true") {
    samples.dataset.initialized = "true"
    new ArcsSampleBrowser(samples).initialize()
  }
})
