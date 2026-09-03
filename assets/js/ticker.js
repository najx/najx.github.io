(function () {
  var ticker = document.getElementById("ai-ticker");
  if (!ticker) return;

  // WIRED is one of the few mainstream AI feeds whose RSS allows
  // cross-origin requests (Access-Control-Allow-Origin), so it can be
  // fetched straight from the browser without a proxy.
  var FEED = "https://www.wired.com/feed/tag/ai/latest/rss";
  var MAX_ITEMS = 10;
  var SPEED = 55; // scroll speed, px per second

  function parseFeed(text) {
    var doc = new DOMParser().parseFromString(text, "text/xml");
    if (doc.querySelector("parsererror")) return [];
    var nodes = doc.querySelectorAll("item, entry");
    var items = [];
    for (var i = 0; i < nodes.length && items.length < MAX_ITEMS; i++) {
      var node = nodes[i];
      var titleEl = node.querySelector("title");
      var dateEl = node.querySelector("pubDate, updated, published");
      var title = titleEl ? titleEl.textContent.trim() : "";
      if (title) {
        items.push({
          title: title,
          date: dateEl ? new Date(dateEl.textContent) : null,
        });
      }
    }
    return items;
  }

  function formatDate(date) {
    if (!date || isNaN(date)) return "";
    return date
      .toLocaleDateString("en-GB", { day: "2-digit", month: "short" })
      .toLowerCase();
  }

  function buildGroup(items, isCopy) {
    var group = document.createElement("div");
    group.className = "ticker-group";
    if (isCopy) group.setAttribute("aria-hidden", "true");
    items.forEach(function (item) {
      var el = document.createElement("span");
      el.className = "ticker-item";
      var date = formatDate(item.date);
      if (date) {
        var dateEl = document.createElement("span");
        dateEl.className = "ticker-date";
        dateEl.textContent = date;
        el.appendChild(dateEl);
      }
      el.appendChild(document.createTextNode(item.title));
      group.appendChild(el);
    });
    return group;
  }

  function render(items) {
    var track = ticker.querySelector(".ticker-track");
    // The track holds the list twice (second copy aria-hidden) so the
    // -50% translate loops without a visible seam.
    track.appendChild(buildGroup(items, false));
    track.appendChild(buildGroup(items, true));
    ticker.hidden = false;
    var distance = track.scrollWidth / 2;
    track.style.animationDuration = Math.max(20, Math.round(distance / SPEED)) + "s";
  }

  // If the feed fails, the ticker simply stays hidden.
  fetch(FEED)
    .then(function (response) {
      if (!response.ok) throw new Error(response.status);
      return response.text();
    })
    .then(function (text) {
      var items = parseFeed(text);
      if (items.length) render(items);
    })
    .catch(function () {});
})();
