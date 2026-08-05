(() => {
  const modal = document.querySelector("#login-benefits-modal");
  if (!modal) return;
  const message = modal.querySelector("[data-login-modal-message]");
  const defaultMessage = message.textContent;
  let opener = null;

  const openModal = (trigger, contextualMessage) => {
    opener = trigger;
    message.textContent = contextualMessage || trigger.dataset.benefitMessage || defaultMessage;
    if (!modal.open) modal.showModal();
    modal.querySelector("[data-login-modal-close]")?.focus();
  };
  const closeModal = () => {
    if (modal.open) modal.close();
  };
  modal.addEventListener("close", () => opener?.focus());
  modal.querySelector("[data-login-modal-close]")?.addEventListener("click", closeModal);
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeModal();
  });

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-login-modal-open]");
    if (!trigger) return;
    event.preventDefault();
    openModal(trigger);
  });

  document.querySelectorAll("[data-guest-term-add]").forEach((trigger) => {
    trigger.addEventListener("click", (event) => {
      const input = trigger.closest(".guest-term-preview")?.querySelector("[data-guest-term-input]");
      const term = input?.value.trim().replace(/\s+/g, " ") || "";
      if (term.length < 3) {
        event.preventDefault();
        input?.setCustomValidity("Introdu minimum 3 caractere.");
        input?.reportValidity();
        input?.addEventListener("input", () => input.setCustomValidity(""), {once: true});
        return;
      }
      event.preventDefault();
      openModal(trigger, `Creează un cont gratuit pentru a urmări „${term}” și pentru a vedea știrile relevante într-un singur flux.`);
    });
  });

  document.querySelectorAll("[data-guest-topic-options]").forEach((container) => {
    container.querySelectorAll("[data-guest-topic]").forEach((checkbox) => {
      checkbox.addEventListener("change", () => {
        const selected = [...container.querySelectorAll("[data-guest-topic]:checked")];
        if (selected.length > 1) {
          checkbox.checked = false;
          openModal(checkbox, "Creează un cont gratuit pentru a urmări mai multe subiecte și pentru a păstra fluxul personalizat.");
          return;
        }
        checkbox.form?.submit();
      });
    });
  });

  document.querySelectorAll(".guest-filter-section").forEach((section) => {
    const indicator = section.querySelector("[data-guest-group-indicator]");
    const options = [...section.querySelectorAll(".preference-group-options input[type='checkbox']")];
    const sync = () => {
      if (indicator) indicator.checked = options.some((option) => option.checked);
    };
    indicator?.addEventListener("click", (event) => {
      event.stopPropagation();
    });
    indicator?.addEventListener("change", () => {
      const topicOptions = section.querySelector("[data-guest-topic-options]");
      options.forEach((option, index) => {
        option.checked = indicator.checked && (!topicOptions || index === 0);
      });
    });
    section.querySelector("[data-guest-locked-indicator]")?.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      section.querySelector("[data-login-modal-open]")?.click();
    });
    options.forEach((option) => option.addEventListener("change", sync));
    sync();
  });
})();
