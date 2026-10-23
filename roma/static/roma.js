/* Roma's own front end. Vanilla ES2019, no build step, no dependencies.
   It renders what the API returns and never computes a fare or a verdict of
   its own — if a number appears on screen, the engine produced it. */

(function () {
  "use strict";

  var meta = null;
  var sessionId = null;

  /* ------------------------------ helpers ------------------------------- */
  function $(id) { return document.getElementById(id); }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) { node.className = className; }
    if (text !== undefined && text !== null) { node.textContent = String(text); }
    return node;
  }

  function clear(node) { while (node.firstChild) { node.removeChild(node.firstChild); } }

  function money(amount, currency) {
    try {
      return new Intl.NumberFormat(undefined, {
        style: "currency", currency: currency, maximumFractionDigits: 0
      }).format(amount);
    } catch (err) {
      return currency + " " + Math.round(amount).toLocaleString();
    }
  }

  function duration(minutes) {
    if (!minutes) { return "\u2014"; }
    var h = Math.floor(minutes / 60);
    var m = minutes % 60;
    return h + "h " + (m < 10 ? "0" : "") + m + "m";
  }

  function stopsText(stops) {
    if (stops === 0) { return "Nonstop"; }
    return stops === 1 ? "1 stop" : stops + " stops";
  }

  function postJSON(url, payload) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(function (response) {
      if (!response.ok && response.status >= 500) {
        throw new Error("Roma's server returned " + response.status);
      }
      return response.json();
    });
  }

  /* -------------------------------- meta -------------------------------- */
  function loadMeta() {
    return fetch("/api/meta").then(function (r) { return r.json(); }).then(function (payload) {
      meta = payload;
      $("disclosure-product").textContent = payload.disclosure.product;

      var airline = $("airline");
      payload.airlines.forEach(function (item) {
        var option = el("option", null, item.name + " (" + item.code + ")");
        option.value = item.code;
        airline.appendChild(option);
      });
      var other = el("option", null, "Other \u2014 name it yourself");
      other.value = payload.airline_other;
      airline.appendChild(other);

      var cabin = $("cabin");
      payload.cabins.forEach(function (item) {
        var option = el("option", null, item.label);
        option.value = item.id;
        cabin.appendChild(option);
      });

      $("depart_date").min = payload.today;
      $("return_date").min = payload.today;

      var language = payload.language.mode === "llm"
        ? "phrasing via " + payload.language.model + ", numbers always computed in code"
        : "deterministic phrasing, no language model configured";
      $("footer-config").textContent =
        "Roma runs on the Python standard library. Fare source: " +
        (payload.providers[0] && payload.providers[0].name) + ". Language: " + language +
        ". Price history: SQLite, local to this machine.";

      greet();
    });
  }

  /* -------------------------------- tabs -------------------------------- */
  function setupTabs() {
    var tabs = [$("tab-chat"), $("tab-form")];

    function select(index, focus) {
      tabs.forEach(function (tab, i) {
        var chosen = i === index;
        tab.setAttribute("aria-selected", chosen ? "true" : "false");
        tab.tabIndex = chosen ? 0 : -1;
        $(tab.getAttribute("aria-controls")).hidden = !chosen;
      });
      if (focus) { tabs[index].focus(); }
    }

    tabs.forEach(function (tab, index) {
      tab.addEventListener("click", function () { select(index, false); });
      tab.addEventListener("keydown", function (event) {
        if (event.key === "ArrowRight" || event.key === "ArrowDown") {
          event.preventDefault();
          select((index + 1) % tabs.length, true);
        } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
          event.preventDefault();
          select((index - 1 + tabs.length) % tabs.length, true);
        } else if (event.key === "Home") {
          event.preventDefault();
          select(0, true);
        } else if (event.key === "End") {
          event.preventDefault();
          select(tabs.length - 1, true);
        }
      });
    });
  }

  /* ------------------------------ combobox ------------------------------ */
  function setupCombobox(inputId, listId) {
    var input = $(inputId);
    var list = $(listId);
    var results = [];
    var active = -1;
    var timer = null;

    function close() {
      list.hidden = true;
      clear(list);
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
      active = -1;
      results = [];
    }

    function highlight(index) {
      var items = list.querySelectorAll("li");
      for (var i = 0; i < items.length; i += 1) {
        items[i].setAttribute("aria-selected", i === index ? "true" : "false");
      }
      active = index;
      if (index >= 0 && items[index]) {
        input.setAttribute("aria-activedescendant", items[index].id);
        items[index].scrollIntoView({ block: "nearest" });
      } else {
        input.removeAttribute("aria-activedescendant");
      }
    }

    function choose(index) {
      var airport = results[index];
      if (!airport) { return; }
      input.value = airport.city + " (" + airport.iata + ")";
      close();
      clearFieldError(inputId);
    }

    function render(items) {
      results = items;
      clear(list);
      if (!items.length) { close(); return; }
      items.forEach(function (airport, index) {
        var li = el("li");
        li.id = listId + "-option-" + index;
        li.setAttribute("role", "option");
        li.setAttribute("aria-selected", "false");
        li.appendChild(el("span", "combo-code", airport.iata));
        li.appendChild(el("span", null, airport.city));
        li.appendChild(el("span", "combo-where", " \u00b7 " + airport.name + ", " + airport.country));
        li.addEventListener("mousedown", function (event) {
          event.preventDefault();
          choose(index);
        });
        list.appendChild(li);
      });
      list.hidden = false;
      input.setAttribute("aria-expanded", "true");
      highlight(-1);
    }

    input.addEventListener("input", function () {
      var term = input.value.trim();
      window.clearTimeout(timer);
      if (term.length < 1) { close(); return; }
      timer = window.setTimeout(function () {
        fetch("/api/airports?q=" + encodeURIComponent(term))
          .then(function (r) { return r.json(); })
          .then(function (payload) {
            if (input.value.trim() !== term) { return; }
            render(payload.results || []);
          })
          .catch(function () { close(); });
      }, 130);
    });

    input.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        if (list.hidden) { input.dispatchEvent(new Event("input")); return; }
        highlight((active + 1) % results.length);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        if (!list.hidden) { highlight((active - 1 + results.length) % results.length); }
      } else if (event.key === "Enter") {
        if (!list.hidden && active >= 0) { event.preventDefault(); choose(active); }
      } else if (event.key === "Escape") {
        if (!list.hidden) { event.stopPropagation(); close(); }
      } else if (event.key === "Tab") {
        if (!list.hidden && active >= 0) { choose(active); }
      }
    });

    input.addEventListener("blur", function () { window.setTimeout(close, 120); });
  }

  /* ------------------------------ form state ---------------------------- */
  function clearFieldError(field) {
    var input = $(field);
    var error = $(field + "-error");
    if (input) { input.removeAttribute("aria-invalid"); }
    if (error) { error.hidden = true; error.textContent = ""; }
  }

  function clearAllErrors() {
    ["origin", "destination", "depart_date", "return_date"].forEach(clearFieldError);
    var summary = $("error-summary");
    summary.hidden = true;
    clear($("error-summary-list"));
  }

  function showErrors(errors) {
    clearAllErrors();
    var list = $("error-summary-list");
    errors.forEach(function (error) {
      var input = $(error.field);
      var target = $(error.field + "-error");
      if (input) { input.setAttribute("aria-invalid", "true"); }
      if (target) { target.textContent = error.message; target.hidden = false; }

      var li = el("li");
      if (input) {
        var link = el("a", null, error.message);
        link.href = "#" + error.field;
        link.addEventListener("click", function (event) {
          event.preventDefault();
          input.focus();
        });
        li.appendChild(link);
      } else {
        li.appendChild(el("span", null, error.message));
      }
      li.appendChild(el("span", "error-rule", "rule: " + error.rule));
      list.appendChild(li);
    });
    var summary = $("error-summary");
    summary.hidden = false;
    summary.focus();
  }

  function setupForm() {
    var form = $("search-form");
    var submit = $("search-submit");

    document.querySelectorAll('input[name="trip"]').forEach(function (radio) {
      radio.addEventListener("change", function () {
        var oneWay = radio.value === "oneway" && radio.checked;
        $("return-field").hidden = oneWay;
        if (oneWay) { $("return_date").value = ""; clearFieldError("return_date"); }
      });
    });

    $("airline").addEventListener("change", function () {
      var isOther = meta && $("airline").value === meta.airline_other;
      $("airline-other-field").hidden = !isOther;
      if (isOther) { $("airline_other").focus(); } else { $("airline_other").value = ""; }
    });

    ["origin", "destination", "depart_date", "return_date"].forEach(function (field) {
      var input = $(field);
      if (input) { input.addEventListener("input", function () { clearFieldError(field); }); }
    });

    form.addEventListener("reset", function () {
      window.setTimeout(function () {
        clearAllErrors();
        $("return-field").hidden = false;
        $("airline-other-field").hidden = true;
      }, 0);
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var oneWay = document.querySelector('input[name="trip"]:checked').value === "oneway";
      var payload = {
        origin: $("origin").value,
        destination: $("destination").value,
        depart_date: $("depart_date").value,
        return_date: oneWay ? null : $("return_date").value,
        one_way: oneWay,
        airline: $("airline").value,
        airline_other: $("airline_other").value,
        cabin: $("cabin").value,
        adults: $("adults").value,
        source: "form"
      };
      submit.disabled = true;
      submit.textContent = "Searching\u2026";
      $("answer").setAttribute("aria-busy", "true");

      postJSON("/api/search", payload).then(function (result) {
        if (result.ok) {
          clearAllErrors();
          renderResult(result);
        } else if (result.kind === "validation") {
          showErrors(result.errors || []);
          renderMessage("Roma did not run the search. Fix the highlighted fields and try again.");
        } else {
          renderMessage((result.errors && result.errors[0] && result.errors[0].message) ||
            result.error || "Roma could not answer that.");
        }
      }).catch(function (error) {
        renderMessage("Roma's server did not answer: " + error.message);
      }).then(function () {
        submit.disabled = false;
        submit.textContent = "Search fares";
        $("answer").setAttribute("aria-busy", "false");
      });
    });
  }

  /* -------------------------------- chat -------------------------------- */
  function addTurn(who, text, kind) {
    var transcript = $("transcript");
    var turn = el("div", "turn turn-" + who + (kind ? " turn-" + kind : ""));
    turn.appendChild(el("span", "turn-who", who === "user" ? "You" : "Roma"));
    turn.appendChild(el("p", "turn-text", text));
    transcript.appendChild(turn);
    transcript.scrollTop = transcript.scrollHeight;
    return turn;
  }

  function greet() {
    addTurn("roma",
      "Roma here. Give it a route and a date and it will price the trip and tell you " +
      "whether today looks worth taking. Every fare it quotes is simulated.");
  }

  function slotLine(slots) {
    var parts = [];
    if (slots.origin_label) { parts.push("from " + slots.origin_label); }
    if (slots.destination_label) { parts.push("to " + slots.destination_label); }
    if (slots.depart_date) { parts.push("out " + slots.depart_date); }
    if (slots.return_date) { parts.push("back " + slots.return_date); }
    if (slots.one_way && !slots.return_date) { parts.push("one way"); }
    if (slots.airline_label) { parts.push(slots.airline_label); }
    return parts.length ? "holding: " + parts.join(", ") : "";
  }

  function setupChat() {
    var form = $("chat-form");
    var input = $("chat-input");
    var send = $("chat-send");

    function say(message) {
      if (!message.trim()) { return; }
      addTurn("user", message);
      input.value = "";
      send.disabled = true;
      var pending = addTurn("roma", "thinking\u2026", "pending");

      postJSON("/api/chat", { session_id: sessionId, message: message }).then(function (payload) {
        sessionId = payload.session_id || sessionId;
        pending.parentNode.removeChild(pending);
        var turn = addTurn("roma", payload.reply, payload.state === "unparsed" ? "unparsed" : null);
        var line = slotLine(payload.slots || {});
        if (line && payload.state !== "result") { turn.appendChild(el("span", "slotline", line)); }
        if (payload.result && payload.result.ok) { renderResult(payload.result); }
      }).catch(function (error) {
        pending.parentNode.removeChild(pending);
        addTurn("roma", "Roma's server did not answer: " + error.message, "unparsed");
      }).then(function () {
        send.disabled = false;
        input.focus();
      });
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      say(input.value);
    });

    $("suggestions").addEventListener("click", function (event) {
      var button = event.target.closest("button[data-say]");
      if (button) { say(button.getAttribute("data-say")); }
    });
  }

  /* ------------------------------- render ------------------------------- */
  function renderMessage(text) {
    var body = $("answer-body");
    clear(body);
    body.appendChild(el("p", "empty", text));
  }

  function levelBadge(levelId, label) {
    var badge = el("span", "level-badge level-" + levelId, label);
    return badge;
  }

  function renderResult(result) {
    var body = $("answer-body");
    clear(body);

    var query = result.query;
    var heading = el("p", "result-query",
      query.origin_label + " to " + query.destination_label);
    body.appendChild(heading);

    var metaBits = [query.depart_date];
    metaBits.push(query.return_date ? "back " + query.return_date : "one way");
    if (query.trip_nights !== null && query.trip_nights !== undefined) {
      metaBits.push(query.trip_nights + " nights");
    }
    metaBits.push(query.cabin_label);
    metaBits.push(query.adults + (query.adults === 1 ? " traveller" : " travellers"));
    if (query.airline_label) { metaBits.push(query.airline_label); }
    metaBits.push("asked via " + query.source);
    body.appendChild(el("p", "result-meta", metaBits.join("  \u00b7  ")));

    /* Disclosure level 2: this result set. */
    var setNote = el("div", "disclosure-results");
    setNote.appendChild(el("strong", null, result.data_level.label + ". "));
    setNote.appendChild(document.createTextNode(
      result.disclosure.result_set + " " + result.data_level.detail));
    body.appendChild(setNote);

    body.appendChild(renderVerdict(result));
    body.appendChild(renderFares(result));
    body.appendChild(renderTrend(result));
    body.appendChild(renderLinks(result));
    body.appendChild(renderProvenance(result));
  }

  function renderVerdict(result) {
    var rec = result.recommendation;
    var block = el("section", "block");
    block.appendChild(el("h3", "block-title", "Buy or wait"));

    var card = el("div", "verdict verdict-" + rec.verdict);
    var head = el("div", "verdict-head");
    var word = { buy: "Buy", wait: "Wait", watch: "Watch" }[rec.verdict] || rec.verdict;
    head.appendChild(el("span", "verdict-word", word));
    head.appendChild(el("span", "verdict-headline", rec.headline));
    card.appendChild(head);

    var facts = el("ul", "verdict-facts");
    rec.facts.forEach(function (fact) { facts.appendChild(el("li", null, fact)); });
    card.appendChild(facts);

    var rule = el("p", "verdict-rule");
    rule.appendChild(document.createTextNode("rule_fired: "));
    rule.appendChild(el("code", null, rec.rule_fired));
    rule.appendChild(document.createTextNode(
      "  \u00b7  confidence: " + rec.confidence +
      "  \u00b7  " + rec.inputs.days_to_departure + " days to departure"));
    card.appendChild(rule);

    block.appendChild(card);
    return block;
  }

  function renderFares(result) {
    var block = el("section", "block");
    block.appendChild(el("h3", "block-title", "Fares"));

    var table = el("table", "fares");
    table.appendChild(el("caption", null,
      "Cheapest first. " + result.offers.length +
      " options. Every row is labelled with where its number came from."));

    var head = el("thead");
    var headRow = el("tr");
    ["Airline", "Price", "Stops", "Out", "Back", "Basis", "Source"].forEach(function (title, i) {
      var th = el("th", i === 1 ? "col-price" : (i >= 2 && i <= 4 ? "col-num" : null), title);
      th.scope = "col";
      headRow.appendChild(th);
    });
    head.appendChild(headRow);
    table.appendChild(head);

    var tbody = el("tbody");
    result.offers.forEach(function (offer, index) {
      var row = el("tr", index === 0 ? "fare-cheapest" : null);

      var airlineCell = el("td");
      airlineCell.appendChild(el("span", "fare-airline", offer.airline_name));
      if (offer.airline_code && offer.airline_code !== "\u2014") {
        airlineCell.appendChild(el("span", "fare-code", offer.airline_code));
      }
      (offer.notes || []).forEach(function (note) {
        airlineCell.appendChild(el("span", "fare-note", note));
      });
      row.appendChild(airlineCell);

      row.appendChild(el("td", "col-price", money(offer.price, offer.currency)));
      row.appendChild(el("td", "col-num", stopsText(offer.stops)));
      row.appendChild(el("td", "col-num", duration(offer.outbound_duration_minutes)));
      row.appendChild(el("td", "col-num",
        offer.return_duration_minutes ? duration(offer.return_duration_minutes) : "\u2014"));
      row.appendChild(el("td", null, offer.fare_basis));

      var sourceCell = el("td");
      var levelLabel = (meta && meta.data_levels || []).filter(function (level) {
        return level.id === offer.data_level;
      })[0];
      sourceCell.appendChild(levelBadge(offer.data_level, levelLabel ? levelLabel.short : offer.data_level));
      row.appendChild(sourceCell);

      tbody.appendChild(row);
    });
    table.appendChild(tbody);
    block.appendChild(table);
    return block;
  }

  function renderTrend(result) {
    var history = result.history;
    var block = el("section", "block");
    block.appendChild(el("h3", "block-title", "Price history for this exact query"));

    var card = el("div", "trend");
    var series = history.series || [];
    var currency = (result.cheapest && result.cheapest.currency) || "USD";

    if (series.length >= 2) {
      var width = 600;
      var height = 78;
      var pad = 4;
      var prices = series.map(function (point) { return point.price; });
      var low = Math.min.apply(null, prices);
      var high = Math.max.apply(null, prices);
      var span = high - low || 1;

      var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("class", "spark");
      svg.setAttribute("viewBox", "0 0 " + width + " " + height);
      svg.setAttribute("preserveAspectRatio", "none");
      svg.setAttribute("role", "img");
      svg.setAttribute("aria-label",
        series.length + " recorded price points ranging from " +
        money(low, currency) + " to " + money(high, currency));

      function x(i) { return pad + (i / (series.length - 1)) * (width - pad * 2); }
      function y(price) { return height - pad - ((price - low) / span) * (height - pad * 2); }

      var polyline = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
      polyline.setAttribute("class", "spark-line");
      polyline.setAttribute("vector-effect", "non-scaling-stroke");
      polyline.setAttribute("points", series.map(function (point, i) {
        return x(i) + "," + y(point.price);
      }).join(" "));
      svg.appendChild(polyline);

      series.forEach(function (point, i) {
        if (point.kind !== "observed") { return; }
        var dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        dot.setAttribute("class", "spark-observed");
        dot.setAttribute("cx", x(i));
        dot.setAttribute("cy", y(point.price));
        dot.setAttribute("r", 3);
        dot.setAttribute("vector-effect", "non-scaling-stroke");
        svg.appendChild(dot);
      });
      card.appendChild(svg);

      var legend = el("div", "spark-legend");
      legend.appendChild(el("span", null, "line: modelled trail"));
      legend.appendChild(el("span", null, "dots: prices Roma actually produced"));
      card.appendChild(legend);
    } else {
      card.appendChild(el("p", "trend-note", "Not enough points yet to draw a trend."));
    }

    var stats = el("div", "trend-stats");
    function stat(label, value) {
      var wrap = el("span");
      wrap.appendChild(document.createTextNode(label + " "));
      wrap.appendChild(el("b", null, value));
      stats.appendChild(wrap);
    }
    if (history.min !== null) { stat("low", money(history.min, currency)); }
    if (history.median !== null) { stat("median", money(history.median, currency)); }
    if (history.max !== null) { stat("high", money(history.max, currency)); }
    stat("points", history.points);
    stat("observed", history.observed_points);
    stat("modelled", history.modeled_points);
    stat("window", history.window_days + " days");
    card.appendChild(stats);
    card.appendChild(el("p", "trend-note", history.note));

    block.appendChild(card);
    return block;
  }

  function renderLinks(result) {
    var block = el("section", "block");
    block.appendChild(el("h3", "block-title", "See real prices"));
    var grid = el("div", "links");
    result.deeplinks.forEach(function (link) {
      var card = el("a", "link-card");
      card.href = link.url;
      card.target = "_blank";
      card.rel = "noopener noreferrer";
      card.appendChild(el("span", "link-site", link.site));
      card.appendChild(el("span", "link-note", "opens their own search"));
      grid.appendChild(card);
    });
    block.appendChild(grid);
    block.appendChild(el("p", "trend-note",
      "Roma does not scrape these sites and cannot book. It builds the search URL and hands you over."));
    return block;
  }

  function renderProvenance(result) {
    var block = el("div", "provenance");
    var attempted = (result.provider.attempted || []).map(function (item) {
      return item.provider + ":" + item.outcome + (item.reason ? " (" + item.reason + ")" : "");
    }).join(", ");
    block.appendChild(el("span", null, "fare provider: " + result.provider.used +
      (attempted ? "  \u00b7  chain: " + attempted : "")));
    block.appendChild(el("span", null, "phrasing: " + result.language.mode +
      (result.language.used_model ? " (model draft accepted)" : " (template)") +
      (result.language.reason ? "  \u00b7  " + result.language.reason : "")));
    block.appendChild(el("span", null, "generated at " + result.generated_at));
    return block;
  }

  /* -------------------------------- boot -------------------------------- */
  document.addEventListener("DOMContentLoaded", function () {
    setupTabs();
    setupCombobox("origin", "origin-listbox");
    setupCombobox("destination", "destination-listbox");
    setupForm();
    setupChat();
    loadMeta().catch(function (error) {
      $("disclosure-product").textContent =
        "Roma could not load its own configuration: " + error.message;
    });
  });
}());
