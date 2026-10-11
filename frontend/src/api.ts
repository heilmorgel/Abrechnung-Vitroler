export type Scope = "fernwaerme" | "wasser_abwasser" | "strom";
export type Method = "verbrauch" | "fix_prozent";

export interface PercentShares {
  EG: number;
  "1OG": number;
  "2OG": number;
}

export interface ScopeSettings {
  method: Method;
  percent: PercentShares;
}

export interface EntityMapping {
  wmz_eg: string;
  wmz_1og: string;
  wmz_2og: string;
  wmz_gesamt: string;
  ww_eg: string;
  ww_1og: string;
  ww_2og: string;
  ww_gesamt: string;
  wasser_eg: string;
  wasser_1og: string;
  wasser_2og: string;
  strom_eg: string;
  strom_1og: string;
  strom_2og: string;
  strom_gesamt: string;
}

export interface AppSettings {
  scopes: Record<string, ScopeSettings>;
  entities: EntityMapping;
  ww_1og_residual: boolean;
}

export interface Invoice {
  id: number;
  scope: Scope;
  number: string;
  invoice_date: string;
  period_start: string;
  period_end: string;
  amount: number;
  note: string;
  file_path: string | null;
  status: string;
  created_at: string;
  allocation: Allocation | null;
}

export interface Allocation {
  method: Method;
  scope: Scope;
  amount: number;
  amounts: Record<string, number>;
  shares: Record<string, number>;
  details: Record<string, unknown>;
  readings: unknown[];
  interpolated: boolean;
}

export interface Summary {
  totals: Record<string, number>;
  by_scope: Record<string, Record<string, number>>;
  count: number;
}

export type PreviewResult =
  | Allocation
  | { error: string; message: string; missing: string[]; can_interpolate: boolean };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // Relative paths work under HA Ingress subpaths and local root.
  const res = await fetch(path.replace(/^\//, ""), init);
  if (!res.ok) {
    let detail: unknown = await res.text();
    try {
      detail = JSON.parse(detail as string);
    } catch {
      /* keep text */
    }
    const err = new Error("API-Fehler") as Error & { status: number; detail: unknown };
    err.status = res.status;
    err.detail = detail;
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("api/health"),
  getSettings: () => request<AppSettings>("api/settings"),
  saveSettings: (body: AppSettings) =>
    request<AppSettings>("api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  listInvoices: (scope?: Scope) =>
    request<Invoice[]>(scope ? `api/invoices?scope=${scope}` : "api/invoices"),
  getInvoice: (id: number) => request<Invoice>(`api/invoices/${id}`),
  deleteInvoice: (id: number) =>
    request<{ ok: boolean }>(`api/invoices/${id}`, { method: "DELETE" }),
  summary: () => request<Summary>("api/summary"),
  preview: (body: {
    scope: Scope;
    period_start: string;
    period_end: string;
    amount: number;
    allow_interpolation: boolean;
  }) =>
    request<PreviewResult>("api/allocate/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  createInvoice: (form: FormData) =>
    request<Invoice>("api/invoices", { method: "POST", body: form }),
};

export const SCOPE_LABELS: Record<Scope, string> = {
  fernwaerme: "Fernwärme",
  wasser_abwasser: "Wasser / Abwasser",
  strom: "Strom",
};

export function eur(n: number): string {
  return new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(n);
}
