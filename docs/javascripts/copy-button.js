const copyResetTimers = new WeakMap()

const resetCopyButton = button => {
  button.classList.remove("md-code__button--active", "md-code__button--failed")
  button.setAttribute("aria-label", "Copy to clipboard")
  button.title = "Copy to clipboard"
  copyResetTimers.delete(button)
}

const setCopyButtonState = (button, copied) => {
  const resetTimer = copyResetTimers.get(button)
  if (resetTimer) clearTimeout(resetTimer)

  button.classList.toggle("md-code__button--active", copied)
  button.classList.toggle("md-code__button--failed", !copied)
  button.setAttribute("aria-label", copied ? "Copied" : "Copy failed")
  button.title = copied ? "Copied" : "Copy failed"
  copyResetTimers.set(button, setTimeout(() => resetCopyButton(button), 1200))
}

const writeClipboardText = async text => {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }

  const textarea = document.createElement("textarea")
  textarea.value = text
  textarea.style.position = "fixed"
  textarea.style.opacity = "0"
  document.body.append(textarea)
  textarea.select()
  const copied = document.execCommand("copy")
  textarea.remove()
  if (!copied) throw new Error("Unable to copy code")
}

const copyCode = async button => {
  const selector = button.dataset.clipboardTarget
  const code = selector ? document.querySelector(selector) : undefined
  if (!(code instanceof HTMLElement)) {
    setCopyButtonState(button, false)
    return
  }

  try {
    await writeClipboardText(code.innerText.trimEnd())
    setCopyButtonState(button, true)
  } catch {
    setCopyButtonState(button, false)
  }
}

document.addEventListener("click", event => {
  if (!(event.target instanceof Element)) return

  const button = event.target.closest(".md-code__button[data-md-type='copy']")
  if (!(button instanceof HTMLButtonElement)) return

  event.preventDefault()
  event.stopImmediatePropagation()
  void copyCode(button)
}, true)
