import "./styles.css";
import {
  Allocation,
  AppSettings,
  PreviewResult,
  SCOPE_LABELS,
  Scope,
  Summary,
  api,
  eur,
} from "./api";

type Page = "overview" | "new" | "detail" | "settings";

const app = document.querySelector<HTMLDivElement>("#app")!;
let page: Page = "overview";
let detailId: number | null = null;
let filterScope: Scope | "" = "";
let flash = "";

function el(html: string): string {
  return html.trim();
}

async function navigate(next: Page, id?: number) {
  page = next;
  detailId = id ?? null;
  await render();
}

function moneyCells(amounts?: Record<string, number> | null): string {
  if (!amounts) return "<td>—</td><td>—</td><td>—</td>";
  return `<td>${eur(amounts.EG ?? 0)}</td><td>${eur(amounts["1OG"] ?? 0)}</td><td>${eur(amounts["2OG"] ?? 0)}</td>`;
}

async function renderOverview() {
  const [summary, invoices] = await Promise.all([
    api.summary(),
    api.listInvoices(filterScope || undefined),
  ]);
  const s = summary as Summary;

  return el(`
    <section class="panel grid stats">
      <div class="stat"><strong>${eur(s.totals.EG || 0)}</strong><span>Summe EG</span></div>
      <div class="stat"><strong>${eur(s.totals["1OG"] || 0)}</strong><span>Summe 1. OG</span></div>
      <div class="stat"><strong>${eur(s.totals["2OG"] || 0)}</strong><span>Summe 2. OG</span></div>
      <div class="stat"><strong>${s.count}</strong><span>Rechnungen</span></div>
    </section>
    <section class="panel">
      <div class="form-grid" style="margin-bottom:1rem;align-items:end">
        <label>Scope filtern
          <select id="filter-scope">
            <option value="">Alle</option>
            <option value="fernwaerme">Fernwärme</option>
            <option value="wasser_abwasser">Wasser / Abwasser</option>
            <option value="strom">Strom</option>
          </select>
        </label>
        <div class="row-actions">
          <button class="btn primary" id="btn-new">Neue Rechnung</button>
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Datum</th><th>Scope</th><th>Periode</th><th>Betrag</th>
            <th>EG</th><th>1. OG</th><th>2. OG</th>
          </tr>
        </thead>
        <tbody>
          ${
            invoices.length === 0
              ? `<tr><td colspan="7" class="muted">Noch keine Rechnungen.</td></tr>`
              : invoices
                  .map(
                    (inv) => `
            <tr class="clickable" data-id="${inv.id}">
              <td>${inv.invoice_date}</td>
              <td><span class="badge">${SCOPE_LABELS[inv.scope]}</span></td>
              <td>${inv.period_start} – ${inv.period_end}</td>
              <td>${eur(inv.amount)}</td>
              ${moneyCells(inv.allocation?.amounts)}
            </tr>`
                  )
                  .join("")
          }
        </tbody>
      </table>
    </section>
  `);
}

function bindOverview() {
  const sel = document.querySelector<HTMLSelectElement>("#filter-scope");
  if (sel) {
    sel.value = filterScope;
    sel.addEventListener("change", async () => {
      filterScope = sel.value as Scope | "";
      await render();
    });
  }
  document.querySelector("#btn-new")?.addEventListener("click", () => navigate("new"));
  document.querySelectorAll<HTMLTableRowElement>("tr[data-id]").forEach((row) => {
    row.addEventListener("click", () => navigate("detail", Number(row.dataset.id)));
  });
}

async function renderNew() {
  return el(`
    <section class="panel">
      <h2 style="margin-top:0;font-family:Fraunces,serif">Rechnung erfassen</h2>
      <form id="invoice-form" class="form-grid">
        <label>Scope
          <select name="scope" required>
            <option value="fernwaerme">Fernwärme</option>
            <option value="wasser_abwasser">Wasser / Abwasser</option>
            <option value="strom">Strom</option>
          </select>
        </label>
        <label>Rechnungsdatum
          <input type="date" name="invoice_date" required />
        </label>
        <label>Zeitraum von
          <input type="date" name="period_start" required />
        </label>
        <label>Zeitraum bis
          <input type="date" name="period_end" required />
        </label>
        <label>Gesamtbetrag (€)
          <input type="number" name="amount" step="0.01" min="0.01" required />
        </label>
        <label>Rechnungsnummer
          <input type="text" name="number" />
        </label>
        <label style="grid-column:1/-1">Notiz
          <textarea name="note"></textarea>
        </label>
        <label style="grid-column:1/-1">Datei (PDF/Bild)
          <input type="file" name="file" accept=".pdf,image/*" />
        </label>
        <label style="grid-column:1/-1">
          <span><input type="checkbox" name="allow_interpolation" /> Fehlende Stände linear interpolieren</span>
        </label>
      </form>
      <div id="preview-box"></div>
      <div class="row-actions">
        <button class="btn" id="btn-preview">Vorschau berechnen</button>
        <button class="btn primary" id="btn-save">Speichern</button>
        <button class="btn" id="btn-cancel">Abbrechen</button>
      </div>
    </section>
  `);
}

function showPreview(box: HTMLElement, result: PreviewResult) {
  if ("error" in result && result.error === "missing_readings") {
    box.innerHTML = `
      <div class="alert warn">
        <strong>${result.message}</strong>
        <div class="muted" style="margin-top:0.4rem">Fehlend: ${result.missing.join(", ")}</div>
        <p>Aktivieren Sie die Option „Fehlende Stände linear interpolieren“ und berechnen Sie erneut.</p>
      </div>`;
    return;
  }
  const a = result as Allocation;
  box.innerHTML = `
    <div class="alert ok">
      Aufteilung (${a.method}${a.interpolated ? ", interpoliert" : ""}):
      EG ${eur(a.amounts.EG)}, 1. OG ${eur(a.amounts["1OG"])}, 2. OG ${eur(a.amounts["2OG"])}
    </div>`;
}

function formPayload(form: HTMLFormElement, allowOverride?: boolean): FormData {
  const fd = new FormData(form);
  const allow = allowOverride ?? (form.querySelector<HTMLInputElement>('[name="allow_interpolation"]')?.checked || false);
  fd.set("allow_interpolation", allow ? "true" : "false");
  return fd;
}

function bindNew() {
  const form = document.querySelector<HTMLFormElement>("#invoice-form")!;
  const box = document.querySelector<HTMLElement>("#preview-box")!;
  document.querySelector("#btn-cancel")?.addEventListener("click", () => navigate("overview"));
  document.querySelector("#btn-preview")?.addEventListener("click", async () => {
    const fd = formPayload(form);
    try {
      const result = await api.preview({
        scope: String(fd.get("scope")) as Scope,
        period_start: String(fd.get("period_start")),
        period_end: String(fd.get("period_end")),
        amount: Number(fd.get("amount")),
        allow_interpolation: fd.get("allow_interpolation") === "true",
      });
      showPreview(box, result);
    } catch (e) {
      const err = e as Error & { detail?: unknown };
      box.innerHTML = `<div class="alert error">${JSON.stringify(err.detail ?? err.message)}</div>`;
    }
  });
  document.querySelector("#btn-save")?.addEventListener("click", async () => {
    const fd = formPayload(form);
    try {
      const inv = await api.createInvoice(fd);
      flash = "Rechnung gespeichert.";
      await navigate("detail", inv.id);
    } catch (e) {
      const err = e as Error & { status?: number; detail?: any };
      if (err.status === 409 && err.detail?.detail?.error === "missing_readings") {
        const d = err.detail.detail;
        box.innerHTML = `
          <div class="alert warn">
            <strong>${d.message}</strong>
            <div class="muted">Fehlend: ${(d.missing || []).join(", ")}</div>
          </div>`;
      } else {
        box.innerHTML = `<div class="alert error">${JSON.stringify(err.detail ?? err.message)}</div>`;
      }
    }
  });
}

async function renderDetail() {
  const inv = await api.getInvoice(detailId!);
  const a = inv.allocation;
  const details = a?.details || {};
  return el(`
    <section class="panel">
      <h2 style="margin-top:0;font-family:Fraunces,serif">${SCOPE_LABELS[inv.scope]} · ${eur(inv.amount)}</h2>
      <p class="muted">${inv.invoice_date} · Periode ${inv.period_start} – ${inv.period_end}
        ${inv.number ? ` · Nr. ${inv.number}` : ""}</p>
      ${inv.note ? `<p>${inv.note}</p>` : ""}
      <div class="detail-amounts" style="margin:1rem 0">
        <div class="stat panel" style="margin:0"><strong>${eur(a?.amounts.EG ?? 0)}</strong><span>EG</span></div>
        <div class="stat panel" style="margin:0"><strong>${eur(a?.amounts["1OG"] ?? 0)}</strong><span>1. OG</span></div>
        <div class="stat panel" style="margin:0"><strong>${eur(a?.amounts["2OG"] ?? 0)}</strong><span>2. OG</span></div>
      </div>
      ${
        a?.method === "verbrauch" && inv.scope === "fernwaerme"
          ? `<div class="muted">Heizung: ${eur(Number(details.kosten_hz || 0))} · Warmwasser-Erzeugung: ${eur(Number(details.kosten_ww || 0))}</div>`
          : ""
      }
      ${a?.interpolated ? `<div class="alert warn">Mindestens ein Zählerstand wurde interpoliert.</div>` : ""}
      ${inv.file_path ? `<p><a href="api/invoices/${inv.id}/file" target="_blank">Datei öffnen</a></p>` : ""}
      <details style="margin-top:1rem">
        <summary>Rohdaten Allocation</summary>
        <pre style="overflow:auto">${JSON.stringify(a, null, 2)}</pre>
      </details>
      <div class="row-actions">
        <button class="btn" id="btn-back">Zurück</button>
        <button class="btn" id="btn-delete" style="color:var(--danger)">Löschen</button>
      </div>
    </section>
  `);
}

function bindDetail(invId: number) {
  document.querySelector("#btn-back")?.addEventListener("click", () => navigate("overview"));
  document.querySelector("#btn-delete")?.addEventListener("click", async () => {
    if (!confirm("Rechnung wirklich löschen?")) return;
    await api.deleteInvoice(invId);
    flash = "Rechnung gelöscht.";
    await navigate("overview");
  });
}

const ENTITY_FIELDS: { key: keyof AppSettings["entities"]; label: string }[] = [
  { key: "wmz_eg", label: "WMZ EG" },
  { key: "wmz_1og", label: "WMZ 1. OG" },
  { key: "wmz_2og", label: "WMZ 2. OG" },
  { key: "wmz_gesamt", label: "WMZ Gesamt" },
  { key: "ww_eg", label: "WW EG" },
  { key: "ww_1og", label: "WW 1. OG" },
  { key: "ww_2og", label: "WW 2. OG" },
  { key: "ww_gesamt", label: "WW Gesamt" },
  { key: "wasser_eg", label: "Wasser EG" },
  { key: "wasser_1og", label: "Wasser 1. OG" },
  { key: "wasser_2og", label: "Wasser 2. OG" },
  { key: "strom_eg", label: "Strom EG" },
  { key: "strom_1og", label: "Strom 1. OG" },
  { key: "strom_2og", label: "Strom 2. OG" },
  { key: "strom_gesamt", label: "Strom Gesamt (optional)" },
];

async function renderSettings() {
  const s = await api.getSettings();
  const scopes: Scope[] = ["fernwaerme", "wasser_abwasser", "strom"];
  return el(`
    <section class="panel scope-settings">
      <h2 style="margin:0;font-family:Fraunces,serif">Einstellungen</h2>
      ${scopes
        .map((scope) => {
          const cfg = s.scopes[scope] || { method: "fix_prozent", percent: { EG: 50, "1OG": 25, "2OG": 25 } };
          return `
          <div class="scope-block panel" style="margin:0" data-scope="${scope}">
            <h3>${SCOPE_LABELS[scope]}</h3>
            <div class="form-grid">
              <label>Methode
                <select class="method">
                  <option value="verbrauch" ${cfg.method === "verbrauch" ? "selected" : ""}>Verbrauchsbasiert</option>
                  <option value="fix_prozent" ${cfg.method === "fix_prozent" ? "selected" : ""}>Fixe Prozente</option>
                </select>
              </label>
              <label>EG %
                <input type="number" class="pct-eg" step="0.01" value="${cfg.percent.EG}" />
              </label>
              <label>1. OG %
                <input type="number" class="pct-1og" step="0.01" value="${cfg.percent["1OG"]}" />
              </label>
              <label>2. OG %
                <input type="number" class="pct-2og" step="0.01" value="${cfg.percent["2OG"]}" />
              </label>
            </div>
          </div>`;
        })
        .join("")}
      <div class="panel" style="margin:0">
        <h3 style="margin-top:0;font-family:Fraunces,serif">Fernwärme-Optionen</h3>
        <label>
          <span><input type="checkbox" id="ww-residual" ${s.ww_1og_residual ? "checked" : ""} />
          WW 1. OG als Rest (Gesamt − EG − 2. OG), wie in der Excel</span>
        </label>
      </div>
      <div class="panel" style="margin:0">
        <h3 style="margin-top:0;font-family:Fraunces,serif">Entity-Mapping (Home Assistant)</h3>
        <p class="muted">Sensor- oder Helfer-Entity-IDs, z. B. <code>sensor.wmz_eg</code> oder <code>input_number.ww_eg</code>.</p>
        <div class="entity-grid">
          ${ENTITY_FIELDS.map(
            (f) => `
            <label>${f.label}
              <input type="text" data-entity="${f.key}" value="${s.entities[f.key] || ""}" placeholder="sensor...." />
            </label>`
          ).join("")}
        </div>
      </div>
      <div id="settings-msg"></div>
      <div class="row-actions">
        <button class="btn primary" id="btn-save-settings">Speichern</button>
      </div>
    </section>
  `);
}

function bindSettings() {
  document.querySelector("#btn-save-settings")?.addEventListener("click", async () => {
    const scopes: Record<string, any> = {};
    document.querySelectorAll<HTMLElement>(".scope-block").forEach((block) => {
      const scope = block.dataset.scope!;
      scopes[scope] = {
        method: block.querySelector<HTMLSelectElement>(".method")!.value,
        percent: {
          EG: Number(block.querySelector<HTMLInputElement>(".pct-eg")!.value),
          "1OG": Number(block.querySelector<HTMLInputElement>(".pct-1og")!.value),
          "2OG": Number(block.querySelector<HTMLInputElement>(".pct-2og")!.value),
        },
      };
    });
    const entities: Record<string, string> = {};
    document.querySelectorAll<HTMLInputElement>("[data-entity]").forEach((input) => {
      entities[input.dataset.entity!] = input.value.trim();
    });
    const body: AppSettings = {
      scopes,
      entities: entities as unknown as AppSettings["entities"],
      ww_1og_residual: document.querySelector<HTMLInputElement>("#ww-residual")!.checked,
    };
    const msg = document.querySelector("#settings-msg")!;
    try {
      await api.saveSettings(body);
      msg.innerHTML = `<div class="alert ok">Einstellungen gespeichert.</div>`;
    } catch (e) {
      const err = e as Error & { detail?: unknown };
      msg.innerHTML = `<div class="alert error">${JSON.stringify(err.detail ?? err.message)}</div>`;
    }
  });
}

async function render() {
  const flashHtml = flash ? `<div class="alert ok">${flash}</div>` : "";
  flash = "";
  app.innerHTML = `
    <header class="app-header">
      <div>
        <h1>Abrechnung Vitroler</h1>
        <p>Kondominiums-Spesen · EG · 1. OG · 2. OG</p>
      </div>
      <nav>
        <button data-nav="overview" class="${page === "overview" || page === "detail" ? "active" : ""}">Übersicht</button>
        <button data-nav="new" class="${page === "new" ? "active" : ""}">Neue Rechnung</button>
        <button data-nav="settings" class="${page === "settings" ? "active" : ""}">Einstellungen</button>
      </nav>
    </header>
    ${flashHtml}
    <div id="content"><div class="panel muted">Laden…</div></div>
  `;
  app.querySelectorAll<HTMLButtonElement>("nav button").forEach((btn) => {
    btn.addEventListener("click", () => navigate(btn.dataset.nav as Page));
  });

  const content = app.querySelector("#content")!;
  try {
    if (page === "overview") {
      content.innerHTML = await renderOverview();
      bindOverview();
    } else if (page === "new") {
      content.innerHTML = await renderNew();
      bindNew();
    } else if (page === "detail" && detailId != null) {
      content.innerHTML = await renderDetail();
      bindDetail(detailId);
    } else if (page === "settings") {
      content.innerHTML = await renderSettings();
      bindSettings();
    }
  } catch (e) {
    const err = e as Error;
    content.innerHTML = `<div class="alert error">Fehler: ${err.message}</div>`;
  }
}

render();
