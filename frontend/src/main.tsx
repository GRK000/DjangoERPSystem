import React, { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Boxes,
  Building2,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  ClipboardCheck,
  ClipboardList,
  Clock3,
  Command,
  Cpu,
  Database,
  Eye,
  FileText,
  Filter,
  Gauge,
  Home,
  Layers3,
  LogIn,
  LogOut,
  Package,
  PackageCheck,
  Plus,
  RefreshCw,
  Search,
  Settings,
  Shield,
  Sparkles,
  Truck,
  UserPlus,
  Users,
  Warehouse,
  X,
  Zap,
} from "lucide-react";
import "./styles.css";

type AppUser = {
  isAuthenticated: boolean;
  username: string;
  isStaff: boolean;
};

type CommandItem = {
  type: string;
  label: string;
  href: string;
};

type FlashMessage = {
  tags: string;
  message: string;
};

type InitialData = {
  page: string;
  payload: Record<string, any>;
  csrfToken: string;
  user: AppUser;
  messages: FlashMessage[];
  commandItems: CommandItem[];
};

type Client = {
  id: number;
  codi_client: string;
  nom_comercial: string;
  cif: string;
  persona_contacte: string;
  telefon: string;
  email: string;
  adreca_entrega: string;
  poblacio: string;
  codi_postal: string;
  actiu: boolean;
};

type Category = {
  id: number;
  nom: string;
  descripcio: string;
  requereix_refrigeracio: boolean;
  temperatura_maxima: number;
};

type Warehouse = {
  id: number;
  nom: string;
  adreca: string;
  capacitat_maxima: number;
  te_cambra_frio: boolean;
  responsable: string;
};

type Product = {
  id: number;
  codi: string;
  nom: string;
  descripcio: string;
  categoria: Category;
  preu_unitari: number;
  unitat_mesura: string;
  iva: number;
  es_perible: boolean;
  imatge_url: string;
  actiu: boolean;
  stock_total?: number;
};

type AlbaraLine = {
  id: number;
  producte: Product | null;
  nom_producte: string;
  quantitat: number;
  preu_unitari: number;
  iva: number;
  descompte_percentatge: number;
  subtotal: number;
  observacions: string;
  stock_disponible?: number;
  ubicacio?: string;
  stock_baix?: boolean;
};

type Albara = {
  id: number;
  numero_albara: string;
  client: Client;
  empleat: { nom: string; codi_empleat: string; carrec: string } | null;
  magatzem: Warehouse | null;
  data_creacio: string;
  data_entrega_prevista: string;
  estat: string;
  estat_label: string;
  base_imposable: number;
  total_iva: number;
  total: number;
  observacions: string;
  signatura_client: string;
  pot_afegir_linies: boolean;
  linies?: AlbaraLine[];
};

type Stock = {
  id: number;
  producte: Product;
  magatzem: Warehouse;
  quantitat: number;
  data_ultima_entrada: string;
  ubicacio: string;
  stock_baix: boolean;
};

type SelectOption = {
  value: string | number;
  label: string;
};

const initialNode = document.getElementById("erp-initial-data");
const initialData: InitialData = initialNode?.textContent
  ? JSON.parse(initialNode.textContent)
  : {
      page: "home",
      payload: {},
      csrfToken: "",
      user: { isAuthenticated: false, username: "", isStaff: false },
      messages: [],
      commandItems: [],
    };

const statusMeta: Record<string, { label: string; tone: string }> = {
  PENDENT: { label: "Pendent", tone: "warning" },
  EN_PREPARACIO: { label: "En preparacio", tone: "info" },
  PREPARAT: { label: "Preparat", tone: "primary" },
  ENVIAT: { label: "Enviat", tone: "neutral" },
  ENTREGAT: { label: "Entregat", tone: "success" },
  CANCELAT: { label: "Cancel.lat", tone: "danger" },
};

function formatMoney(value: number | string | null | undefined) {
  const amount = Number(value || 0);
  return new Intl.NumberFormat("ca-ES", { style: "currency", currency: "EUR" }).format(amount);
}

function formatNumber(value: number | string | null | undefined) {
  return new Intl.NumberFormat("ca-ES").format(Number(value || 0));
}

function formatDate(value?: string | null, withTime = false) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("ca-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  }).format(new Date(value));
}

function initials(label: string) {
  return label
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
}

function getError(errors: Record<string, string[]> | undefined, field: string) {
  return errors?.[field]?.[0];
}

function Badge({ tone = "neutral", children }: { tone?: string; children: ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

function StatusBadge({ status }: { status: string }) {
  const meta = statusMeta[status] || { label: status, tone: "neutral" };
  return <Badge tone={meta.tone}>{meta.label}</Badge>;
}

function Sparkline({ values, tone = "cyan" }: { values: number[]; tone?: "cyan" | "violet" | "lime" | "amber" | "coral" }) {
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const span = Math.max(max - min, 1);
  const points = values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * 110;
      const y = 34 - ((value - min) / span) * 28;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg className={`sparkline sparkline-${tone}`} viewBox="0 0 110 38" aria-hidden="true">
      <polyline points={points} />
    </svg>
  );
}

function Panel({
  title,
  eyebrow,
  action,
  children,
  className = "",
}: {
  title?: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      {(title || eyebrow || action) && (
        <div className="panel-head">
          <div>
            {eyebrow && <p className="eyebrow">{eyebrow}</p>}
            {title && <h2>{title}</h2>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

function EmptyState({
  icon,
  title,
  text,
  action,
}: {
  icon: ReactNode;
  title: string;
  text: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-orbit">{icon}</div>
      <h3>{title}</h3>
      <p>{text}</p>
      {action}
    </div>
  );
}

function ActionLink({ href, children, variant = "primary" }: { href: string; children: ReactNode; variant?: "primary" | "ghost" | "danger" }) {
  return (
    <a className={`btn btn-${variant}`} href={href}>
      {children}
    </a>
  );
}

function SubmitButton({ children, variant = "primary" }: { children: ReactNode; variant?: "primary" | "danger" }) {
  return (
    <button className={`btn btn-${variant}`} type="submit">
      {children}
    </button>
  );
}

function Field({
  label,
  name,
  error,
  children,
}: {
  label: string;
  name: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <label className="field" htmlFor={name}>
      <span>{label}</span>
      {children}
      {error && <strong>{error}</strong>}
    </label>
  );
}

function TextInput({
  name,
  label,
  values,
  errors,
  type = "text",
  placeholder,
  required = true,
}: {
  name: string;
  label: string;
  values: Record<string, any>;
  errors?: Record<string, string[]>;
  type?: string;
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <Field label={label} name={name} error={getError(errors, name)}>
      <input id={name} name={name} type={type} defaultValue={values?.[name] ?? ""} placeholder={placeholder} required={required} />
    </Field>
  );
}

function SelectField({
  name,
  label,
  values,
  errors,
  options,
  placeholder = "Selecciona",
  required = true,
}: {
  name: string;
  label: string;
  values: Record<string, any>;
  errors?: Record<string, string[]>;
  options: SelectOption[];
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <Field label={label} name={name} error={getError(errors, name)}>
      <select id={name} name={name} defaultValue={values?.[name] ?? ""} required={required}>
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </Field>
  );
}

function Shell({ data }: { data: InitialData }) {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const pageTitle = pageTitles[data.page] || "Operacions";

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen(true);
      }
      if (event.key === "Escape") {
        setPaletteOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div className="app-shell">
      <Sidebar user={data.user} />
      <div className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Aurora Ops ERP</p>
            <h1>{pageTitle}</h1>
          </div>
          <div className="topbar-actions">
            <button className="command-trigger" type="button" onClick={() => setPaletteOpen(true)}>
              <Search size={16} />
              <span>Buscar entidad o modulo</span>
              <kbd>Ctrl K</kbd>
            </button>
            {data.user.isAuthenticated ? (
              <a className="user-chip" href="/logout/">
                <span>{initials(data.user.username)}</span>
                <strong>{data.user.username}</strong>
                <LogOut size={16} />
              </a>
            ) : (
              <a className="user-chip" href="/login/">
                <LogIn size={16} />
                <strong>Entrar</strong>
              </a>
            )}
          </div>
        </header>
        <Flash messages={data.messages} />
        <main className="page-stage">
          <PageRenderer data={data} />
        </main>
      </div>
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        items={data.commandItems}
      />
    </div>
  );
}

const pageTitles: Record<string, string> = {
  home: "Centro de mando",
  clients_list: "Clientes",
  client_detail: "Ficha de cliente",
  client_form: "Cliente",
  cataleg: "Catalogo inteligente",
  albarans_list: "Albaranes",
  albara_detail: "Detalle de albaran",
  albara_form: "Nuevo albaran",
  linia_form: "Linea de albaran",
  consulta_form: "Consulta publica",
  consulta_result: "Resultado de consulta",
  preparacio: "Preparacion",
  stock_list: "Stock",
  stock_reposicio: "Reposicion",
  estadistiques: "Estadisticas",
  auth_login: "Acceso",
  auth_register: "Registro",
};

function Sidebar({ user }: { user: AppUser }) {
  const nav = [
    { href: "/", label: "Mando", icon: Home, public: true },
    { href: "/clients/", label: "Clientes", icon: Users, public: true },
    { href: "/cataleg/", label: "Catalogo", icon: Package, public: true },
    { href: "/albarans/", label: "Albaranes", icon: FileText, public: false },
    { href: "/preparacio/", label: "Preparacion", icon: ClipboardCheck, public: false },
    { href: "/stock/", label: "Stock", icon: Boxes, public: false },
    { href: "/estadistiques/", label: "Analitica", icon: BarChart3, public: false },
    { href: "/consulta/", label: "Consulta", icon: Search, public: true },
  ];

  return (
    <aside className="sidebar">
      <a className="brand" href="/">
        <span className="brand-mark"><Cpu size={22} /></span>
        <span>
          <strong>Aurora Ops</strong>
          <small>ERP Distribuidora</small>
        </span>
      </a>
      <nav className="nav-stack">
        {nav
          .filter((item) => item.public || user.isAuthenticated)
          .map((item) => {
            const Icon = item.icon;
            return (
              <a key={item.href} href={item.href}>
                <Icon size={18} />
                <span>{item.label}</span>
              </a>
            );
          })}
      </nav>
      <div className="sidebar-card">
        <div className="pulse-dot" />
        <p>IA contextual</p>
        <strong>Priorizacion operativa activa</strong>
      </div>
      {user.isStaff && (
        <a className="admin-link" href="/admin/">
          <Settings size={16} />
          Admin Django
        </a>
      )}
    </aside>
  );
}

function CommandPalette({ open, onClose, items }: { open: boolean; onClose: () => void; items: CommandItem[] }) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const source = items.length ? items : [{ type: "Pantalla", label: "Dashboard operatiu", href: "/" }];
    if (!normalized) return source.slice(0, 10);
    return source
      .filter((item) => `${item.type} ${item.label}`.toLowerCase().includes(normalized))
      .slice(0, 10);
  }, [items, query]);

  if (!open) return null;

  return (
    <div className="palette-backdrop" role="presentation" onMouseDown={onClose}>
      <div className="palette" role="dialog" aria-modal="true" onMouseDown={(event) => event.stopPropagation()}>
        <div className="palette-search">
          <Command size={18} />
          <input autoFocus placeholder="Buscar clientes, albaranes, productos o modulos" value={query} onChange={(event) => setQuery(event.target.value)} />
          <button type="button" onClick={onClose} aria-label="Cerrar">
            <X size={18} />
          </button>
        </div>
        <div className="palette-results">
          {filtered.map((item) => (
            <a key={`${item.type}-${item.label}-${item.href}`} href={item.href}>
              <span>{item.type}</span>
              <strong>{item.label}</strong>
              <ChevronRight size={16} />
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

function Flash({ messages }: { messages: FlashMessage[] }) {
  if (!messages.length) return null;
  return (
    <div className="flash-stack">
      {messages.map((message, index) => (
        <div key={`${message.message}-${index}`} className={`flash flash-${message.tags || "info"}`}>
          <Shield size={16} />
          <span>{message.message}</span>
        </div>
      ))}
    </div>
  );
}

function PageRenderer({ data }: { data: InitialData }) {
  const page = data.page;
  const payload = data.payload || {};
  const props = { payload, csrfToken: data.csrfToken, user: data.user };
  switch (page) {
    case "clients_list":
      return <ClientsList {...props} />;
    case "client_detail":
      return <ClientDetail {...props} />;
    case "client_form":
      return <ClientFormPage {...props} />;
    case "cataleg":
      return <CatalogPage {...props} />;
    case "albarans_list":
      return <AlbaransList {...props} />;
    case "albara_detail":
      return <AlbaraDetail {...props} />;
    case "albara_form":
      return <AlbaraFormPage {...props} />;
    case "linia_form":
      return <LineFormPage {...props} />;
    case "consulta_form":
      return <ConsultaForm csrfToken={data.csrfToken} />;
    case "consulta_result":
      return <ConsultaResult {...props} />;
    case "preparacio":
      return <PreparacioPage {...props} />;
    case "stock_list":
      return <StockPage {...props} />;
    case "stock_reposicio":
      return <StockReposicioPage {...props} />;
    case "estadistiques":
      return <StatsPage {...props} />;
    case "auth_login":
      return <LoginPage {...props} />;
    case "auth_register":
      return <RegisterPage {...props} />;
    default:
      return <HomePage {...props} />;
  }
}

function KpiCard({
  label,
  value,
  icon,
  tone,
  hint,
  spark,
}: {
  label: string;
  value: ReactNode;
  icon: ReactNode;
  tone: "cyan" | "violet" | "lime" | "amber" | "coral";
  hint: string;
  spark: number[];
}) {
  return (
    <article className={`kpi-card kpi-${tone}`}>
      <div className="kpi-top">
        <span>{icon}</span>
        <Sparkline values={spark} tone={tone} />
      </div>
      <strong>{value}</strong>
      <p>{label}</p>
      <small>{hint}</small>
    </article>
  );
}

function HomePage({ payload, user }: { payload: Record<string, any>; csrfToken: string; user: AppUser }) {
  const stats = payload.stats || {};
  const recent = (payload.recent_albarans || []) as Albara[];
  const stockAlerts = (payload.stock_alerts || []) as Stock[];
  const statusCounts = payload.status_counts || {};
  const pending = Number(stats.albarans_pendents || 0);

  return (
    <div className="dashboard-grid">
      <section className="ops-hero">
        <div className="hero-copy">
          <p className="eyebrow">Centro de mando logistico</p>
          <h2>Operacion preparada para decidir, priorizar y ejecutar.</h2>
          <p>
            Vision consolidada de albaranes, stock critico y rendimiento comercial con senales
            de accion visibles desde el primer segundo.
          </p>
          <div className="hero-actions">
            {user.isAuthenticated ? (
              <>
                <ActionLink href="/albarans/nova/"><Plus size={16} /> Nuevo albaran</ActionLink>
                <ActionLink href="/preparacio/" variant="ghost"><ClipboardCheck size={16} /> Preparacion</ActionLink>
              </>
            ) : (
              <>
                <ActionLink href="/login/"><LogIn size={16} /> Entrar</ActionLink>
                <ActionLink href="/register/" variant="ghost"><UserPlus size={16} /> Crear cuenta</ActionLink>
              </>
            )}
          </div>
        </div>
        <div className="signal-tower">
          <div className="signal-ring" />
          <div className="signal-core">
            <Sparkles size={24} />
            <span>AI routing</span>
          </div>
        </div>
      </section>

      <KpiCard label="Clientes activos" value={formatNumber(stats.total_clients)} icon={<Users size={20} />} tone="cyan" hint="Cartera comercial disponible" spark={[8, 12, 11, 18, 22, 26, 29]} />
      <KpiCard label="Albaranes totales" value={formatNumber(stats.total_albarans)} icon={<FileText size={20} />} tone="violet" hint={`${pending} pendientes`} spark={[12, 15, 14, 21, 28, 24, 32]} />
      <KpiCard label="Productos activos" value={formatNumber(stats.total_productes)} icon={<Package size={20} />} tone="lime" hint="Catalogo operativo" spark={[32, 28, 31, 33, 36, 39, 41]} />
      <KpiCard label="Ventas entregadas" value={formatMoney(stats.vendes_entregades)} icon={<CircleDollarSign size={20} />} tone="amber" hint="Base de albaranes cerrados" spark={[10, 18, 15, 24, 27, 31, 36]} />

      <Panel title="Flujo de estados" eyebrow="Pipeline" className="span-2">
        <div className="status-board">
          {Object.entries(statusMeta).map(([status, meta]) => (
            <div key={status} className="status-cell">
              <Badge tone={meta.tone}>{meta.label}</Badge>
              <strong>{formatNumber(statusCounts[status] || 0)}</strong>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Albaranes recientes" eyebrow="Actividad" className="span-2" action={<ActionLink href="/albarans/" variant="ghost"><Eye size={16} /> Ver todos</ActionLink>}>
        {recent.length ? <AlbaraTable albarans={recent} compact /> : <EmptyState icon={<ClipboardList size={28} />} title="Sin albaranes recientes" text="Cuando se cree el primer documento, aparecera aqui con su estado y prioridad." action={<ActionLink href="/albarans/nova/"><Plus size={16} /> Crear albaran</ActionLink>} />}
      </Panel>

      <Panel title="Stock bajo" eyebrow="Riesgo operativo">
        {stockAlerts.length ? (
          <div className="alert-list">
            {stockAlerts.map((stock) => (
              <a key={stock.id} href="/stock/">
                <AlertTriangle size={18} />
                <span>
                  <strong>{stock.producte.nom}</strong>
                  <small>{stock.magatzem.nom} - {stock.ubicacio}</small>
                </span>
                <Badge tone="warning">{stock.quantitat} uds</Badge>
              </a>
            ))}
          </div>
        ) : (
          <EmptyState icon={<CheckCircle2 size={28} />} title="No hay reposicion urgente" text="El inventario critico esta despejado para este ciclo." />
        )}
      </Panel>
    </div>
  );
}

function ClientsList({ payload }: { payload: Record<string, any>; csrfToken: string; user: AppUser }) {
  const clients = (payload.clients || []) as Client[];
  return (
    <Panel
      title="Clientes activos"
      eyebrow={`${clients.length} cuentas operativas`}
      action={<ActionLink href="/clients/nova/"><Plus size={16} /> Nuevo cliente</ActionLink>}
    >
      {clients.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Codigo</th>
                <th>Cliente</th>
                <th>Contacto</th>
                <th>Poblacion</th>
                <th>Email</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {clients.map((client) => (
                <tr key={client.id}>
                  <td><Badge tone="neutral">{client.codi_client}</Badge></td>
                  <td><a className="link-strong" href={`/clients/${client.id}/`}>{client.nom_comercial}</a></td>
                  <td>{client.persona_contacte}</td>
                  <td>{client.poblacio}</td>
                  <td>{client.email}</td>
                  <td className="table-actions"><a href={`/clients/${client.id}/`}><ArrowRight size={16} /></a></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState icon={<Users size={28} />} title="Aun no hay clientes activos" text="Crea el primer cliente para comenzar a emitir albaranes." action={<ActionLink href="/clients/nova/"><Plus size={16} /> Crear cliente</ActionLink>} />
      )}
    </Panel>
  );
}

function ClientDetail({ payload }: { payload: Record<string, any>; csrfToken: string; user: AppUser }) {
  const client = payload.client as Client;
  const albarans = (payload.albarans || []) as Albara[];
  return (
    <div className="detail-grid">
      <Panel className="span-2">
        <div className="entity-head">
          <div className="avatar">{initials(client.nom_comercial)}</div>
          <div>
            <p className="eyebrow">{client.codi_client}</p>
            <h2>{client.nom_comercial}</h2>
            <p>{client.adreca_entrega}, {client.poblacio} {client.codi_postal}</p>
          </div>
          <ActionLink href={`/clients/${client.id}/editar/`} variant="ghost"><Settings size={16} /> Editar</ActionLink>
        </div>
      </Panel>
      <Panel title="Contacto" eyebrow="Ficha">
        <div className="metric-list">
          <span>Persona <strong>{client.persona_contacte}</strong></span>
          <span>Telefono <strong>{client.telefon}</strong></span>
          <span>Email <strong>{client.email}</strong></span>
          <span>CIF <strong>{client.cif}</strong></span>
        </div>
      </Panel>
      <Panel title="Ultimos albaranes" eyebrow="Actividad" className="span-2">
        {albarans.length ? <AlbaraTable albarans={albarans} compact /> : <EmptyState icon={<FileText size={28} />} title="Sin albaranes asociados" text="Este cliente todavia no tiene documentos recientes." />}
      </Panel>
    </div>
  );
}

function ClientFormPage({ payload, csrfToken }: { payload: Record<string, any>; csrfToken: string; user: AppUser }) {
  const client = payload.client as Client | null;
  const values = payload.values || {};
  const errors = payload.errors || {};
  return (
    <Panel title={client ? "Editar cliente" : "Nuevo cliente"} eyebrow="Maestro comercial">
      <form className="form-grid" method="post" action={client ? `/clients/${client.id}/editar/` : "/clients/nova/"}>
        <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
        <TextInput name="codi_client" label="Codigo" values={values} errors={errors} placeholder="CLI001" />
        <TextInput name="nom_comercial" label="Nombre comercial" values={values} errors={errors} />
        <TextInput name="cif" label="CIF" values={values} errors={errors} placeholder="B12345678" />
        <TextInput name="persona_contacte" label="Persona de contacto" values={values} errors={errors} />
        <TextInput name="telefon" label="Telefono" values={values} errors={errors} />
        <TextInput name="email" label="Email" values={values} errors={errors} type="email" />
        <TextInput name="adreca_entrega" label="Direccion de entrega" values={values} errors={errors} />
        <TextInput name="poblacio" label="Poblacion" values={values} errors={errors} />
        <TextInput name="codi_postal" label="Codigo postal" values={values} errors={errors} />
        <label className="toggle-field">
          <input type="checkbox" name="actiu" defaultChecked={values.actiu !== false} />
          <span>Cliente activo</span>
        </label>
        <div className="form-actions">
          <ActionLink href="/clients/" variant="ghost">Cancelar</ActionLink>
          <SubmitButton><CheckCircle2 size={16} /> Guardar</SubmitButton>
        </div>
      </form>
    </Panel>
  );
}

function CatalogPage({ payload }: { payload: Record<string, any>; csrfToken: string; user: AppUser }) {
  const categories = (payload.categories || []) as Category[];
  const products = (payload.productes || []) as Product[];
  const current = payload.categoria_actual as Category | null;
  return (
    <div className="catalog-layout">
      <Panel title="Categorias" eyebrow="Filtro">
        <div className="category-list">
          <a className={!current ? "active" : ""} href="/cataleg/">Todas</a>
          {categories.map((category) => (
            <a key={category.id} className={current?.id === category.id ? "active" : ""} href={`/cataleg/${encodeURIComponent(category.nom)}/`}>
              <Layers3 size={16} /> {category.nom}
            </a>
          ))}
        </div>
      </Panel>
      <Panel title={current ? current.nom : "Catalogo activo"} eyebrow={`${products.length} referencias`} className="span-2">
        {products.length ? (
          <div className="product-grid">
            {products.map((product) => (
              <article key={product.id} className="product-card">
                <div className="product-image">
                  {product.imatge_url ? <img src={product.imatge_url} alt="" /> : <Package size={30} />}
                </div>
                <div>
                  <Badge tone={product.es_perible ? "warning" : "neutral"}>{product.categoria.nom}</Badge>
                  <h3>{product.nom}</h3>
                  <p>{product.descripcio || `${product.unitat_mesura} - IVA ${Math.round(product.iva * 100)}%`}</p>
                </div>
                <div className="product-meta">
                  <strong>{formatMoney(product.preu_unitari)}</strong>
                  <span>{formatNumber(product.stock_total || 0)} uds</span>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState icon={<Package size={28} />} title="Catalogo sin referencias" text="No hay productos activos para este filtro." />
        )}
      </Panel>
    </div>
  );
}

function AlbaransList({ payload }: { payload: Record<string, any>; csrfToken: string; user: AppUser }) {
  const albarans = (payload.albarans || []) as Albara[];
  return (
    <Panel title="Albaranes" eyebrow={`${albarans.length} documentos`} action={<ActionLink href="/albarans/nova/"><Plus size={16} /> Nuevo albaran</ActionLink>}>
      {albarans.length ? <AlbaraTable albarans={albarans} /> : <EmptyState icon={<FileText size={28} />} title="No hay albaranes todavia" text="Crea un albaran para activar el flujo de preparacion y stock." action={<ActionLink href="/albarans/nova/"><Plus size={16} /> Crear albaran</ActionLink>} />}
    </Panel>
  );
}

function AlbaraTable({ albarans, compact = false }: { albarans: Albara[]; compact?: boolean }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Numero</th>
            <th>Cliente</th>
            {!compact && <th>Magatzem</th>}
            <th>Fecha</th>
            <th>Estado</th>
            <th className="right">Total</th>
          </tr>
        </thead>
        <tbody>
          {albarans.map((albara) => (
            <tr key={albara.id}>
              <td><a className="link-strong" href={`/albarans/${albara.id}/`}>#{albara.numero_albara}</a></td>
              <td><a href={`/clients/${albara.client.id}/`}>{albara.client.nom_comercial}</a></td>
              {!compact && <td>{albara.magatzem?.nom || "-"}</td>}
              <td>{formatDate(albara.data_creacio, true)}</td>
              <td><StatusBadge status={albara.estat} /></td>
              <td className="right"><strong>{formatMoney(albara.total)}</strong></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AlbaraDetail({ payload, csrfToken }: { payload: Record<string, any>; csrfToken: string; user: AppUser }) {
  const albara = payload.albara as Albara;
  const states = (payload.estats_possibles || []) as SelectOption[];
  const alerts = payload.alertes_stock || [];
  return (
    <div className="detail-grid">
      <Panel className="span-2">
        <div className="entity-head">
          <div className="avatar"><FileText size={24} /></div>
          <div>
            <p className="eyebrow">#{albara.numero_albara}</p>
            <h2>{albara.client.nom_comercial}</h2>
            <p>{albara.magatzem?.nom || "Sin magatzem"} - Entrega prevista {formatDate(albara.data_entrega_prevista)}</p>
          </div>
          <StatusBadge status={albara.estat} />
        </div>
      </Panel>
      <Panel title="Totales" eyebrow="Resumen">
        <div className="metric-list">
          <span>Base <strong>{formatMoney(albara.base_imposable)}</strong></span>
          <span>IVA <strong>{formatMoney(albara.total_iva)}</strong></span>
          <span>Total <strong>{formatMoney(albara.total)}</strong></span>
        </div>
      </Panel>
      <Panel title="Transiciones" eyebrow="Workflow">
        {states.length ? (
          <form className="inline-form" method="post" action={`/albarans/${albara.id}/estat/`}>
            <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
            <select name="nou_estat" defaultValue="">
              <option value="">Nuevo estado</option>
              {states.map((state) => <option key={state.value} value={state.value}>{state.label}</option>)}
            </select>
            <SubmitButton><RefreshCw size={16} /> Cambiar</SubmitButton>
          </form>
        ) : (
          <EmptyState icon={<CheckCircle2 size={28} />} title="Estado cerrado" text="No hay transiciones disponibles para este documento." />
        )}
      </Panel>
      <Panel title="Lineas" eyebrow={`${albara.linies?.length || 0} productos`} className="span-2" action={albara.pot_afegir_linies ? <ActionLink href={`/albarans/${albara.id}/afegir-linia/`}><Plus size={16} /> Anadir linea</ActionLink> : null}>
        {alerts.length > 0 && (
          <div className="notice notice-warning">
            <AlertTriangle size={18} /> Hay lineas con stock bajo. Revisa disponibilidad antes de preparar.
          </div>
        )}
        {albara.linies?.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Producto</th>
                  <th>Cantidad</th>
                  <th>Precio</th>
                  <th>Dto.</th>
                  <th className="right">Subtotal</th>
                </tr>
              </thead>
              <tbody>
                {albara.linies.map((line) => (
                  <tr key={line.id}>
                    <td>{line.nom_producte}</td>
                    <td>{line.quantitat}</td>
                    <td>{formatMoney(line.preu_unitari)}</td>
                    <td>{line.descompte_percentatge}%</td>
                    <td className="right"><strong>{formatMoney(line.subtotal)}</strong></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState icon={<PackageCheck size={28} />} title="Albaran sin lineas" text="Anade productos para calcular totales y activar alertas de stock." />
        )}
      </Panel>
    </div>
  );
}

function AlbaraFormPage({ payload, csrfToken }: { payload: Record<string, any>; csrfToken: string; user: AppUser }) {
  const values = payload.values || {};
  const errors = payload.errors || {};
  const options = payload.options || { clients: [], magatzems: [], estats: [] };
  return (
    <Panel title="Nuevo albaran" eyebrow="Documento logistico">
      <form className="form-grid" method="post" action="/albarans/nova/">
        <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
        <TextInput name="numero_albara" label="Numero de albaran" values={values} errors={errors} placeholder="ALB-2026-001" />
        <SelectField name="client" label="Cliente" values={values} errors={errors} options={options.clients} />
        <SelectField name="magatzem" label="Magatzem" values={values} errors={errors} options={options.magatzems} required={false} placeholder="Sin magatzem" />
        <TextInput name="data_entrega_prevista" label="Entrega prevista" values={values} errors={errors} type="date" />
        <SelectField name="estat" label="Estado inicial" values={values} errors={errors} options={options.estats} />
        <label className="field span-2" htmlFor="observacions">
          <span>Observaciones</span>
          <textarea id="observacions" name="observacions" defaultValue={values.observacions || ""} rows={4} />
          {getError(errors, "observacions") && <strong>{getError(errors, "observacions")}</strong>}
        </label>
        <div className="form-actions">
          <ActionLink href="/albarans/" variant="ghost">Cancelar</ActionLink>
          <SubmitButton><CheckCircle2 size={16} /> Crear</SubmitButton>
        </div>
      </form>
    </Panel>
  );
}

function LineFormPage({ payload, csrfToken }: { payload: Record<string, any>; csrfToken: string; user: AppUser }) {
  const albara = payload.albara as Albara;
  const products = (payload.productes || []) as Product[];
  const values = payload.values || {};
  const errors = payload.errors || {};
  const productOptions = products.map((product) => ({ value: product.id, label: `${product.codi} - ${product.nom}` }));

  function fillProduct(event: FormEvent<HTMLSelectElement>) {
    const product = products.find((item) => String(item.id) === event.currentTarget.value);
    const form = event.currentTarget.form;
    if (!product || !form) return;
    (form.elements.namedItem("nom_producte") as HTMLInputElement).value = product.nom;
    (form.elements.namedItem("preu_unitari") as HTMLInputElement).value = String(product.preu_unitari);
    (form.elements.namedItem("iva") as HTMLInputElement).value = String(product.iva);
  }

  return (
    <Panel title="Anadir linea" eyebrow={`Albaran ${albara.numero_albara}`}>
      <form className="form-grid" method="post" action={`/albarans/${albara.id}/afegir-linia/`}>
        <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
        <Field label="Producto del catalogo" name="producte" error={getError(errors, "producte")}>
          <select id="producte" name="producte" defaultValue={values.producte || ""} onChange={fillProduct}>
            <option value="">Linea manual</option>
            {productOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </Field>
        <TextInput name="nom_producte" label="Nombre producto" values={values} errors={errors} />
        <TextInput name="quantitat" label="Cantidad" values={values} errors={errors} type="number" />
        <TextInput name="preu_unitari" label="Precio unitario" values={values} errors={errors} type="number" />
        <TextInput name="iva" label="IVA decimal" values={values} errors={errors} type="number" required={false} />
        <TextInput name="descompte_percentatge" label="Descuento %" values={values} errors={errors} type="number" required={false} />
        <TextInput name="observacions" label="Observaciones" values={values} errors={errors} required={false} />
        <div className="form-actions">
          <ActionLink href={`/albarans/${albara.id}/`} variant="ghost">Cancelar</ActionLink>
          <SubmitButton><Plus size={16} /> Anadir</SubmitButton>
        </div>
      </form>
    </Panel>
  );
}

function ConsultaForm({ csrfToken }: { csrfToken: string }) {
  return (
    <Panel title="Consulta publica de albaran" eyebrow="Tracking">
      <form className="lookup-form" method="get" action="/consulta/resultat/">
        <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
        <Search size={20} />
        <input name="numero" placeholder="ALB-2026-001" required />
        <SubmitButton><Eye size={16} /> Consultar</SubmitButton>
      </form>
    </Panel>
  );
}

function ConsultaResult({ payload }: { payload: Record<string, any>; csrfToken: string; user: AppUser }) {
  if (payload.error) {
    return <EmptyState icon={<Search size={28} />} title={payload.error} text="Revisa el numero introducido o contacta con operaciones." action={<ActionLink href="/consulta/" variant="ghost">Nueva consulta</ActionLink>} />;
  }
  const albara = payload.albara as Albara;
  return (
    <Panel title={`Albaran ${albara.numero_albara}`} eyebrow="Estado publico">
      <div className="result-card">
        <StatusBadge status={albara.estat} />
        <h3>{albara.client.nom_comercial}</h3>
        <p>Entrega prevista {formatDate(albara.data_entrega_prevista)}</p>
        {payload.mostrar_detall ? <AlbaraTable albarans={[albara]} compact /> : <p className="muted">El detalle completo solo esta disponible para el cliente autenticado.</p>}
      </div>
    </Panel>
  );
}

function PreparacioPage({ payload, csrfToken }: { payload: Record<string, any>; csrfToken: string; user: AppUser }) {
  const albarans = (payload.albarans || []) as Albara[];
  const empleat = payload.empleat;
  return (
    <div className="prep-stack">
      <Panel title="Cola de preparacion" eyebrow={empleat ? `${empleat.nom} - ${empleat.magatzem_assignat?.nom || ""}` : "Empleado"}>
        {albarans.length ? (
          <div className="prep-list">
            {albarans.map((albara) => (
              <article key={albara.id} className="prep-card">
                <div className="prep-head">
                  <div>
                    <Badge tone="warning">{albara.numero_albara}</Badge>
                    <h3>{albara.client.nom_comercial}</h3>
                    <p>{albara.linies?.length || 0} lineas - {formatMoney(albara.total)}</p>
                  </div>
                  <StatusBadge status={albara.estat} />
                </div>
                <div className="line-chips">
                  {albara.linies?.map((line) => (
                    <span key={line.id} className={line.stock_baix ? "danger-chip" : ""}>
                      {line.nom_producte} - {line.quantitat} uds - {line.ubicacio || "N/A"}
                    </span>
                  ))}
                </div>
                <form method="post" action={`/preparacio/${albara.id}/`}>
                  <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
                  <SubmitButton><PackageCheck size={16} /> Marcar preparado</SubmitButton>
                </form>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState icon={<ClipboardCheck size={28} />} title="No hay albaranes pendientes" text="La cola de este magatzem esta limpia. Puedes revisar stock o volver al centro de mando." action={<ActionLink href="/stock/" variant="ghost"><Boxes size={16} /> Ver stock</ActionLink>} />
        )}
      </Panel>
    </div>
  );
}

function StockPage({ payload }: { payload: Record<string, any>; csrfToken: string; user: AppUser }) {
  const stocks = (payload.stocks || []) as Stock[];
  const magatzems = (payload.magatzems || []) as Warehouse[];
  const categories = (payload.categories || []) as Category[];
  return (
    <div className="stock-layout">
      <Panel title="Filtros" eyebrow="Inventario">
        <form className="filter-form" method="get" action="/stock/">
          <label>
            Magatzem
            <select name="magatzem" defaultValue={payload.magatzem_seleccionat || ""}>
              <option value="">Todos</option>
              {magatzems.map((warehouse) => <option key={warehouse.id} value={warehouse.id}>{warehouse.nom}</option>)}
            </select>
          </label>
          <label>
            Categoria
            <select name="categoria" defaultValue={payload.categoria_seleccionada || ""}>
              <option value="">Todas</option>
              {categories.map((category) => <option key={category.id} value={category.id}>{category.nom}</option>)}
            </select>
          </label>
          <SubmitButton><Filter size={16} /> Filtrar</SubmitButton>
          <ActionLink href="/stock/" variant="ghost">Limpiar</ActionLink>
        </form>
      </Panel>
      <Panel title="Inventario operativo" eyebrow={`${stocks.length} posiciones`} className="span-2" action={<ActionLink href="/stock/reposicio/"><Plus size={16} /> Reposicion</ActionLink>}>
        {stocks.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Codigo</th>
                  <th>Producto</th>
                  <th>Categoria</th>
                  <th>Magatzem</th>
                  <th>Ubicacion</th>
                  <th className="right">Cantidad</th>
                </tr>
              </thead>
              <tbody>
                {stocks.map((stock) => (
                  <tr key={stock.id} className={stock.stock_baix ? "risk-row" : ""}>
                    <td><Badge tone="neutral">{stock.producte.codi}</Badge></td>
                    <td>{stock.producte.nom}</td>
                    <td>{stock.producte.categoria.nom}</td>
                    <td>{stock.magatzem.nom}</td>
                    <td><Badge tone="neutral">{stock.ubicacio}</Badge></td>
                    <td className="right"><strong>{stock.quantitat}</strong></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState icon={<Warehouse size={28} />} title="No hay stock con estos filtros" text="Ajusta los filtros o registra una reposicion para alimentar inventario." action={<ActionLink href="/stock/reposicio/"><Plus size={16} /> Nueva reposicion</ActionLink>} />
        )}
      </Panel>
    </div>
  );
}

function StockReposicioPage({ payload, csrfToken }: { payload: Record<string, any>; csrfToken: string; user: AppUser }) {
  const values = payload.values || {};
  const errors = payload.errors || {};
  const productOptions = ((payload.productes || []) as Product[]).map((product) => ({ value: product.id, label: `${product.codi} - ${product.nom}` }));
  const warehouseOptions = ((payload.magatzems || []) as Warehouse[]).map((warehouse) => ({ value: warehouse.id, label: warehouse.nom }));
  return (
    <Panel title="Nueva reposicion" eyebrow="Entrada de stock">
      <form className="form-grid" method="post" action="/stock/reposicio/">
        <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
        <SelectField name="producte" label="Producto" values={values} errors={errors} options={productOptions} />
        <SelectField name="magatzem" label="Magatzem" values={values} errors={errors} options={warehouseOptions} />
        <TextInput name="quantitat" label="Cantidad" values={values} errors={errors} type="number" />
        <TextInput name="ubicacio" label="Ubicacion" values={values} errors={errors} placeholder="A-12" required={false} />
        <div className="form-actions">
          <ActionLink href="/stock/" variant="ghost">Cancelar</ActionLink>
          <SubmitButton><Database size={16} /> Registrar entrada</SubmitButton>
        </div>
      </form>
    </Panel>
  );
}

function StatsPage({ payload }: { payload: Record<string, any>; csrfToken: string; user: AppUser }) {
  const total = payload.total_vendes || {};
  const products = payload.productes_mes_venuts || [];
  const categories = payload.vendes_per_categoria || [];
  const clients = payload.ranquing_clients || [];
  const delivered = (payload.albarans_entregats || []) as Albara[];
  const maxCategory = Math.max(...categories.map((item: any) => Number(item.total_vendes || 0)), 1);

  return (
    <div className="dashboard-grid">
      <KpiCard label="Ventas entregadas" value={formatMoney(total.total)} icon={<CircleDollarSign size={20} />} tone="lime" hint="Albaranes entregados" spark={[12, 18, 21, 19, 26, 31, 38]} />
      <KpiCard label="Base imponible" value={formatMoney(total.total_base)} icon={<Gauge size={20} />} tone="cyan" hint="Sin IVA" spark={[8, 13, 17, 21, 23, 28, 35]} />
      <KpiCard label="IVA total" value={formatMoney(total.total_iva)} icon={<Activity size={20} />} tone="violet" hint="Carga fiscal acumulada" spark={[4, 8, 9, 12, 14, 16, 19]} />
      <Panel title="Productos mas vendidos" eyebrow="Top 10" className="span-2">
        {products.length ? (
          <div className="rank-list">
            {products.map((product: any, index: number) => (
              <div key={product.nom_producte}>
                <span>{index + 1}</span>
                <strong>{product.nom_producte}</strong>
                <small>{formatNumber(product.total_quantitat)} uds</small>
                <b>{formatMoney(product.total_vendes)}</b>
              </div>
            ))}
          </div>
        ) : <EmptyState icon={<BarChart3 size={28} />} title="Sin ventas cerradas" text="Los rankings apareceran al entregar albaranes." />}
      </Panel>
      <Panel title="Ventas por categoria" eyebrow="Mix comercial">
        {categories.length ? (
          <div className="bar-list">
            {categories.map((category: any) => (
              <div key={category.categoria}>
                <span>{category.categoria}</span>
                <strong>{formatMoney(category.total_vendes)}</strong>
                <i style={{ width: `${(Number(category.total_vendes || 0) / maxCategory) * 100}%` }} />
              </div>
            ))}
          </div>
        ) : <EmptyState icon={<Layers3 size={28} />} title="Sin categorias vendidas" text="Aun no hay informacion suficiente para comparar categorias." />}
      </Panel>
      <Panel title="Ranking clientes" eyebrow="Volumen de compra" className="span-2">
        {clients.length ? (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Cliente</th><th>Albaranes</th><th className="right">Total</th></tr></thead>
              <tbody>
                {clients.map((client: any) => (
                  <tr key={client.id}>
                    <td><a className="link-strong" href={`/clients/${client.id}/`}>{client.nom_comercial}</a></td>
                    <td>{client.num_albarans}</td>
                    <td className="right"><strong>{formatMoney(client.total_compres)}</strong></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <EmptyState icon={<Users size={28} />} title="Sin ranking de clientes" text="No hay compras entregadas para ordenar el rendimiento." />}
      </Panel>
      <Panel title="Albaranes entregados" eyebrow={`${delivered.length} cerrados`} className="span-2">
        {delivered.length ? <AlbaraTable albarans={delivered} compact /> : <EmptyState icon={<Truck size={28} />} title="Sin entregas cerradas" text="Cuando los albaranes lleguen a entregado, apareceran aqui." />}
      </Panel>
    </div>
  );
}

function LoginPage({ payload, csrfToken }: { payload: Record<string, any>; csrfToken: string; user: AppUser }) {
  const values = payload.values || {};
  const errors = payload.errors || {};
  const action = payload.next ? `/login/?next=${encodeURIComponent(payload.next)}` : "/login/";
  return (
    <AuthFrame title="Acceso operativo" text="Entra para activar albaranes, stock, preparacion y analitica.">
      <form className="auth-form" method="post" action={action}>
        <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
        <TextInput name="username" label="Usuario" values={values} errors={errors} />
        <TextInput name="password" label="Contraseña" values={{}} errors={errors} type="password" />
        <SubmitButton><LogIn size={16} /> Entrar</SubmitButton>
      </form>
      <a className="auth-link" href="/register/">Crear cuenta</a>
    </AuthFrame>
  );
}

function RegisterPage({ payload, csrfToken }: { payload: Record<string, any>; csrfToken: string; user: AppUser }) {
  const values = payload.values || {};
  const errors = payload.errors || {};
  return (
    <AuthFrame title="Alta de operador" text="Registra un usuario para acceder al sistema.">
      <form className="auth-form" method="post" action="/register/">
        <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
        <TextInput name="username" label="Usuario" values={values} errors={errors} />
        <TextInput name="password1" label="Contraseña" values={{}} errors={errors} type="password" />
        <TextInput name="password2" label="Confirmar contraseña" values={{}} errors={errors} type="password" />
        <SubmitButton><UserPlus size={16} /> Registrar</SubmitButton>
      </form>
      <a className="auth-link" href="/login/">Ya tengo cuenta</a>
    </AuthFrame>
  );
}

function AuthFrame({ title, text, children }: { title: string; text: string; children: ReactNode }) {
  return (
    <div className="auth-frame">
      <div className="auth-visual">
        <Zap size={26} />
        <h2>{title}</h2>
        <p>{text}</p>
      </div>
      <Panel>{children}</Panel>
    </div>
  );
}

createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <Shell data={initialData} />
  </React.StrictMode>
);
