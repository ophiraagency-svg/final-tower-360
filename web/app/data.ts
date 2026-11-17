// All availability and prices are sample data for the concept.
export const ORBIT = { n: 144, mask: "/orbit/id", keys: 8 };
export const FLOORS = 33;

export type Unit = {
  id: string; floor: number; no: number; type: "1BR" | "2BR" | "3BR";
  sqft: number; side: "Sea" | "City"; price: number; status: "Available" | "Reserved" | "Sold";
};

// 12 residences per floor: 6 face the Gulf and the Downtown skyline, 6 face the city.
const PLAN: { type: Unit["type"]; sqft: number; side: Unit["side"] }[] = [
  { type: "3BR", sqft: 1780, side: "Sea" }, { type: "2BR", sqft: 1290, side: "Sea" },
  { type: "1BR", sqft: 811, side: "Sea" }, { type: "1BR", sqft: 811, side: "Sea" },
  { type: "2BR", sqft: 1290, side: "Sea" }, { type: "3BR", sqft: 1780, side: "Sea" },
  { type: "2BR", sqft: 1210, side: "City" }, { type: "1BR", sqft: 790, side: "City" },
  { type: "1BR", sqft: 790, side: "City" }, { type: "1BR", sqft: 790, side: "City" },
  { type: "1BR", sqft: 790, side: "City" }, { type: "2BR", sqft: 1210, side: "City" },
];

function rnd(seed: number) {
  const x = Math.sin(seed * 9301 + 49297) * 233280;
  return x - Math.floor(x);
}

export function unitsOn(floor: number): Unit[] {
  return PLAN.map((p, i) => {
    const r = rnd(floor * 31 + i);
    const status: Unit["status"] = r < 0.42 ? "Sold" : r < 0.55 ? "Reserved" : "Available";
    const base = p.type === "1BR" ? 2.17e6 : p.type === "2BR" ? 3.35e6 : 4.9e6;
    const price = Math.round((base * (1 + floor * 0.012) * (p.side === "Sea" ? 1.12 : 1)) / 1e4) * 1e4;
    return { id: `${floor}${String(i + 1).padStart(2, "0")}`, floor, no: i + 1, ...p, price, status };
  });
}

export const aed = (n: number) => "AED " + (n / 1e6).toFixed(2) + "M";

// 360 tour: node positions in metres inside the unit (x along the glass, y into the room)
export const NODES = {
  living: { x: 3.6, y: 3.35, label: "Living room", src: "/pano/pano_living.jpg", night: "/pano/pano_living_night.jpg", photo: "/stills/s_living.jpg" },
  kitchen: { x: 3.3, y: 5.55, label: "Kitchen & dining", src: "/pano/pano_kitchen.jpg", night: "/pano/pano_kitchen_night.jpg", photo: "/stills/s_kitchen.jpg" },
  bedroom: { x: 9.0, y: 2.2, label: "Principal bedroom", src: "/pano/pano_bedroom.jpg", night: "/pano/pano_bedroom_night.jpg", photo: "/stills/s_bedroom.jpg" },
  balcony: { x: 6.6, y: -1.1, label: "Terrace", src: "/pano/pano_balcony.jpg", night: "/pano/pano_balcony_night.jpg", photo: "/stills/s_balcony.jpg" },
} as const;
export type NodeId = keyof typeof NODES;
export const LINKS: Record<NodeId, NodeId[]> = {
  living: ["kitchen", "balcony", "bedroom"],
  kitchen: ["living", "bedroom"],
  bedroom: ["living", "kitchen"],
  balcony: ["living"],
};

export const STILLS = [
  { src: "/stills/s_living.jpg", label: "Living room" },
  { src: "/stills/s_view.jpg", label: "The view" },
  { src: "/stills/s_kitchen.jpg", label: "Kitchen" },
  { src: "/stills/s_bedroom.jpg", label: "Principal bedroom" },
  { src: "/stills/s_balcony.jpg", label: "Terrace" },
];


export function unitById(id: string): Unit | null {
  const m = /^(\d{1,2})(\d{2})$/.exec(id);
  if (!m) return null;
  const f = +m[1], n = +m[2];
  return f >= 1 && f <= FLOORS && n >= 1 && n <= 12 ? unitsOn(f)[n - 1] : null;
}

// Sample 60/40 plan: 60% during construction, 40% on handover. A developer would supply the approved terms.
export const PLAN_NAME = "60 / 40 · sample plan";
const STEPS = [
  { label: "Booking", when: "On reservation", pct: 20 },
  { label: "Instalment 1", when: "Jun 2027", pct: 10 },
  { label: "Instalment 2", when: "Dec 2027", pct: 10 },
  { label: "Instalment 3", when: "Jun 2028", pct: 10 },
  { label: "Instalment 4", when: "Dec 2028", pct: 10 },
  { label: "Handover", when: "Q2 2029", pct: 40 },
];
export const ANCHOR = "Assumes a reservation in Nov 2026; instalment dates are construction estimates.";
export const THROUGH = "Through Dec 2027";
export const DATA_VERSION = "sample-2026-11";
export const DLD = 0.04, ADMIN = 5250; // DLD registration 4% + sample Oqood / admin fee

export function payments(u: Unit) {
  const steps = STEPS.map((s) => ({ ...s, amount: Math.round((u.price * s.pct) / 100) }));
  const dld = Math.round(u.price * DLD);
  const now = steps[0].amount + dld + ADMIN;
  // everything dated up to the end of 2027, assuming a reservation in Nov 2026
  const firstYear = now + steps[1].amount + steps[2].amount;
  return { steps, dld, admin: ADMIN, now, firstYear, handover: steps[steps.length - 1].amount };
}

export const aedFull = (n: number) => "AED " + Math.round(n).toLocaleString("en");

// Broker directory: ?ref= is only trusted when it is listed here. Numbers come from the developer, never from the URL.
// shortcut: hard-coded sample directory, move to the developer's sheet/CRM when there is a real client.
export type Broker = { name: string; agency: string; wa: string };
export const BROKERS: Record<string, Broker> = {
  sara: { name: "Sara Haddad", agency: "Sample Realty (demo)", wa: "" },
};
// Project sales desk used when no broker is known. Empty = not configured in this concept.
export const PROJECT_ADVISOR: Broker = { name: "", agency: "The Final Tower sales desk", wa: "" };
