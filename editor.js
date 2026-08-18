(() => {
  const storageKey = "dividend-grid-local-stocks-v1";
  const $ = (selector) => document.querySelector(selector);
  const normalizeNumber = (value) => value === "" ? null : Number(value);
  function draw() {
    const stocks = window.dividendGrid.getBaseStocks();
    $("#editor-list").innerHTML = stocks.map((stock, index) => `<div class="editor-row"><span><b>${stock.name}</b> <small>${stock.code}.${stock.exchange} · ${stock.category}</small></span><button class="delete-stock" data-index="${index}" type="button">删除</button></div>`).join("");
    document.querySelectorAll(".delete-stock").forEach((button) => button.addEventListener("click", () => {
      const next = window.dividendGrid.getBaseStocks(); next.splice(Number(button.dataset.index), 1); save(next); draw();
    }));
  }
  function save(stocks) { localStorage.setItem(storageKey, JSON.stringify(stocks)); window.dividendGrid.setBaseStocks(stocks); }
  function download() { const blob = new Blob([JSON.stringify(window.dividendGrid.getBaseStocks(), null, 2)], { type: "application/json" }); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "stocks.json"; link.click(); URL.revokeObjectURL(link.href); }
  function init() {
    $("#manage-stocks").addEventListener("click", () => { draw(); $("#editor-modal").showModal(); });
    $("#close-editor").addEventListener("click", () => $("#editor-modal").close());
    $("#stock-form").addEventListener("submit", (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); const code = String(form.get("code")).padStart(6, "0"); const stocks = window.dividendGrid.getBaseStocks(); if (stocks.some((stock) => stock.code === code && stock.exchange === form.get("exchange"))) return alert("这只股票已存在。"); stocks.push({ code, exchange: form.get("exchange"), name: form.get("name").trim(), category: form.get("category").trim(), annual_dividend: normalizeNumber(form.get("annual_dividend")), dividend_note: "自动分红优先；人工值作为兜底", target_low: normalizeNumber(form.get("target_low")), target_high: normalizeNumber(form.get("target_high")), target_price: normalizeNumber(form.get("target_price")), grid_min: 4.0, grid_max: 7.0, grid_step: 0.1, notes: "", dividend_mode: "auto" }); save(stocks); event.currentTarget.reset(); draw(); });
    $("#export-stocks").addEventListener("click", download);
    $("#reset-stocks").addEventListener("click", () => { if (confirm("恢复仓库默认股票？当前浏览器内的新增和删除会丢失。")) { localStorage.removeItem(storageKey); window.dividendGrid.resetToRepository(); draw(); } });
  }
  window.addEventListener("dividend-grid-ready", init, { once: true });
})();
