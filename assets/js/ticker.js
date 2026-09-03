(function () {
  var ticker = document.getElementById("ai-ticker");
  if (!ticker) return;

  // Feeds are tried in order; all of them must allow cross-origin requests
  // (Access-Control-Allow-Origin), which is why the list is hand-picked.
  var FEEDS = [
    "https://www.wired.com/feed/tag/ai/latest/rss",
    "https://simonwillison.net/atom/everything/",
  ];
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
      var linkEl = node.querySelector("link");
      var dateEl = node.querySelector("pubDate, updated, published");
      var title = titleEl ? titleEl.textContent.trim() : "";
      var link = linkEl
        ? (linkEl.getAttribute("href") || linkEl.textContent).trim()
        : "";
      if (title && link) {
        items.push({
          title: title,
          link: link,
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
      var link = document.createElement("a");
      link.className = "ticker-item";
      link.href = item.link;
      link.target = "_blank";
      link.rel = "noopener";
      if (isCopy) link.tabIndex = -1;
      var date = formatDate(item.date);
      if (date) {
        var dateEl = document.createElement("span");
        dateEl.className = "ticker-date";
        dateEl.textContent = date;
        link.appendChild(dateEl);
      }
      link.appendChild(document.createTextNode(item.title));
      group.appendChild(link);
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

  function load(index) {
    // Every feed failed: the ticker simply stays hidden.
    if (index >= FEEDS.length) return;
    fetch(FEEDS[index])
      .then(function (response) {
        if (!response.ok) throw new Error(response.status);
        return response.text();
      })
      .then(function (text) {
        var items = parseFeed(text);
        if (!items.length) throw new Error("empty feed");
        render(items);
      })
      .catch(function () {
        load(index + 1);
      });
  }

  load(0);
})();
