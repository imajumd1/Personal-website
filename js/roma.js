// Roma — flight agent page. The chat and the form post to the same backend and
// render the same result block; nothing about the recommendation is computed here.

const ROMA_API = {
  search: "/api/roma/search",
  chat: "/api/roma/chat",
  airports: "/api/roma/airports",
  airlines: "/api/roma/airlines",
};

const ROMA_AVATAR = "images/roma/roma-avatar.svg";

const ERROR_FIELDS = {
  origin: { input: "roma-origin", error: "roma-origin-error" },
  destination: { input: "roma-destination", error: "roma-destination-error" },
  depart_date: { input: "roma-depart", error: "roma-depart-error" },
  return_date: { input: "roma-return", error: "roma-return-error" },
  passengers: { input: "roma-passengers", error: "roma-passengers-error" },
};

let romaConversationId = null;

document.addEventListener("DOMContentLoaded", () => {
  greet();
  loadAirlines();
  attachTypeahead("roma-origin", "roma-origin-list");
  attachTypeahead("roma-destination", "roma-destination-list");

  const chatForm = document.getElementById("roma-chat-form");
  chatForm.addEventListener("submit", event => {
    event.preventDefault();
    const input = document.getElementById("roma-message");
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    sendChat(text);
  });

  document.querySelectorAll(".roma-example").forEach(button => {
    button.addEventListener("click", () => sendChat(button.dataset.example));
  });

  const airline = document.getElementById("roma-airline");
  airline.addEventListener("change", () => {
    const other = document.getElementById("roma-airline-other-field");
    const isOther = airline.value === "OTHER";
    other.hidden = !isOther;
    if (isOther) document.getElementById("roma-airline-other").focus();
  });

  const form = document.getElementById("roma-form");
  form.addEventListener("submit", event => {
    event.preventDefault();
    runFormSearch();
  });
  form.addEventListener("reset", () => {
    clearErrors();
    document.getElementById("roma-airline-other-field").hidden = true;
    document.getElementById("roma-form-status").textContent = "";
  });
});

/* ---------------- chat ---------------- */

function greet() {
  addTurn(
    "roma",
    "Roma here. Tell me where you are going and roughly when — “two of us to Tokyo in early March” " +
      "is enough to start. I will ask for anything I still need."
  );
}

async function sendChat(message) {
  addTurn("user", message);
  const pending = addTurn("roma", "Roma is searching…", { pending: true });
  setChatBusy(true);

  try {
    const response = await fetch(ROMA_API.chat, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, conversation_id: romaConversationId }),
    });
    const data = await response.json();
    pending.remove();

    if (!response.ok || !data.ok) {
      addTurn("roma", data.error || "Roma could not answer that just now.");
      return;
    }

    romaConversationId = data.conversation_id || romaConversationId;
    addTurn("roma", data.reply);

    if (data.search) {
      renderResults(data.search);
      syncFormFromQuery(data.search.query);
    }
  } catch (error) {
    pending.remove();
    addTurn("roma", "Roma could not reach the server. Check that it is still running and try again.");
  } finally {
    setChatBusy(false);
  }
}

function setChatBusy(busy) {
  const button = document.getElementById("roma-send");
  const input = document.getElementById("roma-message");
  button.disabled = busy;
  button.textContent = busy ? "Searching…" : "Send";
  if (!busy) input.focus();
}

function addTurn(role, text, options = {}) {
  const log = document.getElementById("roma-log");
  const turn = document.createElement("div");
  turn.className = `roma-turn roma-turn-${role}` + (options.pending ? " roma-turn-pending" : "");

  if (role === "roma") {
    const avatar = document.createElement("img");
    avatar.className = "roma-avatar";
    avatar.src = ROMA_AVATAR;
    avatar.alt = "Roma";
    avatar.width = 34;
    avatar.height = 34;
    turn.appendChild(avatar);
  }

  const bubble = document.createElement("div");
  bubble.className = "roma-bubble";

  const speaker = document.createElement("span");
  speaker.className = "roma-speaker";
  speaker.textContent = role === "roma" ? "Roma" : "You";
  bubble.appendChild(speaker);

  String(text)
    .split("\n")
    .filter(line => line.trim())
    .forEach(line => {
      const paragraph = document.createElement("p");
      paragraph.textContent = line;
      bubble.appendChild(paragraph);
    });

  turn.appendChild(bubble);
  log.appendChild(turn);
  log.scrollTop = log.scrollHeight;
  return turn;
}

/* ---------------- form ---------------- */

async function loadAirlines() {
  const select = document.getElementById("roma-airline");
  try {
    const response = await fetch(ROMA_API.airlines);
    const data = await response.json();
    if (!data.ok) return;
    data.airlines.forEach(airline => {
      const option = document.createElement("option");
      option.value = airline.code;
      option.textContent = airline.name;
      select.appendChild(option);
    });
  } catch (error) {
    /* the field still works as "Any airline" */
  }
}

function readForm() {
  return {
    origin: codeFrom(document.getElementById("roma-origin").value),
    destination: codeFrom(document.getElementById("roma-destination").value),
    depart_date: document.getElementById("roma-depart").value,
    return_date: document.getElementById("roma-return").value || null,
    passengers: Number(document.getElementById("roma-passengers").value || 1),
    cabin: document.getElementById("roma-cabin").value,
    airline: document.getElementById("roma-airline").value || null,
    airline_other: document.getElementById("roma-airline-other").value || "",
  };
}

function validateLocally(values) {
  const errors = {};
  const today = new Date().toISOString().slice(0, 10);

  if (!values.origin) errors.origin = "Where are you leaving from?";
  if (!values.destination) errors.destination = "Where are you going?";
  if (
    values.origin &&
    values.destination &&
    values.origin.toLowerCase() === values.destination.toLowerCase()
  ) {
    errors.destination = "Origin and destination are the same airport.";
  }

  if (!values.depart_date) errors.depart_date = "Pick a departure date.";
  else if (values.depart_date < today) errors.depart_date = "That date is in the past.";

  if (values.return_date) {
    if (values.return_date < today) errors.return_date = "That date is in the past.";
    else if (values.depart_date && values.return_date < values.depart_date) {
      errors.return_date = "Return is before departure.";
    }
  }

  if (!Number.isInteger(values.passengers) || values.passengers < 1 || values.passengers > 9) {
    errors.passengers = "Between 1 and 9 passengers.";
  }
  return errors;
}

async function runFormSearch() {
  const values = readForm();
  const status = document.getElementById("roma-form-status");
  clearErrors();

  const errors = validateLocally(values);
  if (Object.keys(errors).length) {
    showErrors(errors);
    status.textContent = "Fix the highlighted fields and search again.";
    return;
  }

  const button = document.getElementById("roma-search-btn");
  button.disabled = true;
  status.textContent = "Roma is searching…";

  try {
    const response = await fetch(ROMA_API.search, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
    const data = await response.json();

    if (!response.ok || !data.ok) {
      showErrors(data.field_errors || {});
      status.textContent = data.error || "That search did not work.";
      return;
    }

    status.textContent = "";
    renderResults(data);
    document.getElementById("roma-results").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    status.textContent = "Roma could not reach the server.";
  } finally {
    button.disabled = false;
  }
}

function clearErrors() {
  Object.values(ERROR_FIELDS).forEach(({ input, error }) => {
    document.getElementById(error).textContent = "";
    document.getElementById(input).removeAttribute("aria-invalid");
  });
}

function showErrors(errors) {
  let first = null;
  Object.entries(errors).forEach(([field, message]) => {
    const target = ERROR_FIELDS[field];
    if (!target) return;
    document.getElementById(target.error).textContent = message;
    const input = document.getElementById(target.input);
    input.setAttribute("aria-invalid", "true");
    if (!first) first = input;
  });
  if (first) first.focus();
}

function syncFormFromQuery(query) {
  if (!query) return;
  document.getElementById("roma-origin").value = query.origin;
  document.getElementById("roma-destination").value = query.destination;
  document.getElementById("roma-depart").value = query.depart_date;
  document.getElementById("roma-return").value = query.return_date || "";
  document.getElementById("roma-passengers").value = query.passengers;
  document.getElementById("roma-cabin").value = query.cabin;
}

/* ---------------- results ---------------- */

function renderResults(payload) {
  const section = document.getElementById("roma-results");
  section.hidden = false;

  renderVerdict(payload);
  renderSources(payload.deep_links || []);
  renderOffers(payload.results || [], payload.data || {});
  renderProvenance(payload);
}

function renderVerdict(payload) {
  const rec = payload.recommendation || {};
  const history = payload.history || {};
  const container = document.getElementById("roma-verdict");
  container.innerHTML = "";

  container.appendChild(element("span", "eyebrow", "Recommendation"));
  container.appendChild(element("h3", "roma-verdict-title", rec.verdict_label || "No verdict"));

  const chips = element("div", "roma-chips");
  chips.appendChild(element("span", "roma-chip", `Confidence: ${rec.confidence || "unknown"}`));
  chips.appendChild(element("span", "roma-chip roma-chip-mono", `rule_fired: ${rec.rule_fired || "none"}`));
  if (payload.data && payload.data.simulated) {
    chips.appendChild(element("span", "roma-chip roma-chip-sim", "Simulated data"));
  }
  container.appendChild(chips);

  const reasons = element("ul", "roma-reasons");
  (rec.reasoning || []).forEach(line => reasons.appendChild(element("li", "", line)));
  container.appendChild(reasons);

  const facts = document.createElement("dl");
  facts.className = "roma-facts";
  addFact(facts, "Cheapest", rec.price_per_person != null
    ? `${money(rec.price_per_person)} per person` +
      (rec.passengers > 1 ? ` · ${money(rec.best_price)} total` : "")
    : "No priced option");
  addFact(facts, "At stake", `${money(rec.dollars_at_stake)} — ${rec.dollars_basis || ""}`);
  addFact(facts, "Revisit by", `${rec.revisit_by} — ${rec.revisit_reason || ""}`);
  addFact(
    facts,
    "Price history",
    history.percentile_available
      ? `${history.observation_days} observation days · median ${money(history.median)}` +
        (rec.percentile != null ? ` · this fare at the ${rec.percentile}th percentile` : "")
      : `${history.observation_days || 0} observation day(s) recorded — too few for a percentile`
  );
  container.appendChild(facts);

  if ((rec.confidence_notes || []).length) {
    container.appendChild(
      element("p", "roma-caps", `Confidence capped at low: ${rec.confidence_notes.join(" ")}`)
    );
  }
  if (rec.explanation) {
    const explanation = element("div", "roma-explanation");
    explanation.appendChild(element("span", "roma-explanation-label", "In plain words"));
    String(rec.explanation)
      .split("\n")
      .filter(line => line.trim())
      .forEach(line => explanation.appendChild(element("p", "", line)));
    container.appendChild(explanation);
  }
}

function renderSources(links) {
  const row = document.getElementById("roma-source-links");
  row.innerHTML = "";
  links.forEach(link => {
    const anchor = document.createElement("a");
    anchor.className = "btn btn-ghost btn-small";
    anchor.href = link.url;
    anchor.target = "_blank";
    anchor.rel = "noopener";
    anchor.textContent = link.label;
    row.appendChild(anchor);
  });
}

function renderOffers(offers, meta) {
  const container = document.getElementById("roma-offers");
  container.innerHTML = "";
  container.appendChild(element("span", "eyebrow", `Results (${offers.length})`));

  if (!offers.length) {
    container.appendChild(element("p", "roma-hint", "No priced itineraries came back for that search."));
    return;
  }

  const list = document.createElement("ul");
  list.className = "roma-offer-list";

  offers.forEach((offer, index) => {
    const item = document.createElement("li");
    item.className = "roma-offer" + (index === 0 ? " roma-offer-best" : "");

    const main = element("div", "roma-offer-main");
    main.appendChild(element("span", "roma-offer-airline", offer.airline_name));
    main.appendChild(
      element(
        "span",
        "roma-offer-meta",
        `${offer.stops_label} · ${offer.duration_label} · ${offer.depart_time} → ${offer.arrive_time}`
      )
    );
    main.appendChild(
      element(
        "span",
        "roma-offer-source",
        `${offer.source} · retrieved ${offer.retrieved_at}`
      )
    );
    item.appendChild(main);

    const side = element("div", "roma-offer-side");
    side.appendChild(element("span", "roma-offer-price", money(offer.price_total)));
    side.appendChild(element("span", "roma-offer-currency", offer.currency));
    if (offer.simulated) side.appendChild(element("span", "roma-badge", "Simulated"));
    item.appendChild(side);

    list.appendChild(item);
  });

  container.appendChild(list);
  if (meta.simulated) {
    container.appendChild(
      element("p", "roma-hint", "Every price above is generated locally for demonstration.")
    );
  }
}

function renderProvenance(payload) {
  const data = payload.data || {};
  const parts = [
    `Sources: ${(data.sources_used || []).join(", ") || "none"}`,
    `Retrieved: ${data.retrieved_at || "unknown"}`,
    data.simulated ? "Simulated: yes" : "Simulated: no",
  ];
  const notes = (data.notes || []).join(" ");
  document.getElementById("roma-provenance").textContent = parts.join(" · ") + (notes ? ` · ${notes}` : "");
}

/* ---------------- typeahead ---------------- */

function attachTypeahead(inputId, listId) {
  const input = document.getElementById(inputId);
  const list = document.getElementById(listId);
  let options = [];
  let active = -1;
  let timer = null;

  input.addEventListener("input", () => {
    clearTimeout(timer);
    const value = input.value.trim();
    if (value.length < 2) return close();
    timer = setTimeout(() => load(value), 140);
  });

  input.addEventListener("keydown", event => {
    if (list.hidden) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      move(1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      move(-1);
    } else if (event.key === "Enter" && active >= 0) {
      event.preventDefault();
      choose(options[active]);
    } else if (event.key === "Escape") {
      close();
    }
  });

  input.addEventListener("blur", () => setTimeout(close, 150));

  list.addEventListener("mousedown", event => {
    const item = event.target.closest("li[data-index]");
    if (!item) return;
    event.preventDefault();
    choose(options[Number(item.dataset.index)]);
  });

  async function load(value) {
    try {
      const response = await fetch(`${ROMA_API.airports}?q=${encodeURIComponent(value)}`);
      const data = await response.json();
      options = data.ok ? data.airports : [];
      active = -1;
      render();
    } catch (error) {
      close();
    }
  }

  function render() {
    list.innerHTML = "";
    if (!options.length) return close();
    options.forEach((airport, index) => {
      const item = document.createElement("li");
      item.id = `${listId}-option-${index}`;
      item.dataset.index = String(index);
      item.setAttribute("role", "option");
      item.setAttribute("aria-selected", index === active ? "true" : "false");
      item.className = "roma-suggest-item" + (index === active ? " is-active" : "");
      item.appendChild(element("span", "roma-suggest-city", `${airport.city} (${airport.code})`));
      item.appendChild(element("span", "roma-suggest-name", airport.name));
      list.appendChild(item);
    });
    list.hidden = false;
    input.setAttribute("aria-expanded", "true");
  }

  function move(step) {
    if (!options.length) return;
    active = (active + step + options.length) % options.length;
    render();
    input.setAttribute("aria-activedescendant", `${listId}-option-${active}`);
  }

  function choose(airport) {
    if (!airport) return;
    input.value = `${airport.city} (${airport.code})`;
    close();
  }

  function close() {
    list.hidden = true;
    list.innerHTML = "";
    options = [];
    active = -1;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
  }
}

/* ---------------- helpers ---------------- */

function codeFrom(value) {
  const text = String(value || "").trim();
  const parenthesised = text.match(/\(([A-Za-z]{3})\)/);
  if (parenthesised) return parenthesised[1].toUpperCase();
  if (/^[A-Za-z]{3}$/.test(text)) return text.toUpperCase();
  return text;
}

function money(value) {
  if (value === null || value === undefined) return "n/a";
  return `$${Number(value).toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

function addFact(list, term, description) {
  list.appendChild(element("dt", "", term));
  list.appendChild(element("dd", "", description));
}
