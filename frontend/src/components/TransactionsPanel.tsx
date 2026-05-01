import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, ArrowUpDown, Loader2, AlertCircle } from "lucide-react";
import { api, TransactionLine } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type SortKey = "ordinal" | "posted_date" | "description" | "amount" | "balance_after" | "category";
type SortDir = "asc" | "desc";

const fmtUSD = (n: number) =>
  n.toLocaleString(undefined, { style: "currency", currency: "USD" });

const CATEGORY_LABELS: Record<string, string> = {
  groceries: "Groceries", dining: "Dining", delivery: "Delivery",
  subscriptions: "Subscriptions", utilities: "Utilities", gas: "Gas",
  transport: "Transport", shopping: "Shopping", loans: "Loans",
  credit_card_payments: "CC Payments", bnpl: "BNPL",
  peer_transfers: "Peer", internal_transfers: "Internal",
  atm_cash: "Cash", fees: "Fees", income: "Income",
  healthcare: "Health", entertainment: "Entertainment", other: "Other",
};

function categoryLabel(c: string | null): string {
  return c ? (CATEGORY_LABELS[c] ?? c) : "Other";
}

export function TransactionsPanel({ documentId }: { documentId: number }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["transactions", documentId],
    queryFn: () => api.getTransactions(documentId),
  });

  const [filter, setFilter] = useState("");
  const [direction, setDirection] = useState<"all" | "debit" | "credit">("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [sortKey, setSortKey] = useState<SortKey>("ordinal");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  // Distinct categories present in this doc, ordered by debit total desc
  const categoryOptions = useMemo<{ value: string; label: string; count: number }[]>(() => {
    if (!data) return [];
    const totals: Record<string, { count: number; debit: number }> = {};
    for (const r of data.lines) {
      const c = r.category ?? "other";
      if (!totals[c]) totals[c] = { count: 0, debit: 0 };
      totals[c].count += 1;
      if (r.direction === "debit") totals[c].debit += r.amount;
    }
    return Object.entries(totals)
      .sort(([, a], [, b]) => b.debit - a.debit)
      .map(([c, v]) => ({ value: c, label: categoryLabel(c), count: v.count }));
  }, [data]);

  const filtered = useMemo<TransactionLine[]>(() => {
    if (!data) return [];
    let rows = data.lines;
    if (direction !== "all") rows = rows.filter((r) => r.direction === direction);
    if (categoryFilter !== "all") rows = rows.filter((r) => (r.category ?? "other") === categoryFilter);
    if (filter.trim()) {
      const q = filter.toLowerCase();
      rows = rows.filter(
        (r) =>
          r.description.toLowerCase().includes(q) ||
          (r.posted_date ?? "").includes(q) ||
          r.amount.toString().includes(q) ||
          categoryLabel(r.category).toLowerCase().includes(q),
      );
    }
    rows = [...rows].sort((a, b) => {
      const av = (a as any)[sortKey];
      const bv = (b as any)[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "number") return sortDir === "asc" ? av - bv : bv - av;
      return sortDir === "asc"
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
    return rows;
  }, [data, filter, direction, categoryFilter, sortKey, sortDir]);

  const onSort = (k: SortKey) => {
    if (k === sortKey) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else { setSortKey(k); setSortDir(k === "amount" ? "desc" : "asc"); }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16 text-muted-foreground">
        <Loader2 className="animate-spin" />
      </div>
    );
  }
  if (error || !data) {
    return (
      <Card className="flex items-center gap-3 border-destructive/30 bg-destructive/5 p-4">
        <AlertCircle size={18} className="text-destructive" />
        <span className="text-sm">Could not load transactions.</span>
      </Card>
    );
  }
  if (data.lines.length === 0) {
    return (
      <Card className="p-8 text-center text-sm text-muted-foreground">
        No structured transactions parsed from this document.
        <div className="mt-2 text-xs">
          (Transaction extraction currently supports Capital One bank statements. More formats coming.)
        </div>
      </Card>
    );
  }

  const s = data.stats;

  return (
    <div className="space-y-4">
      {/* Stats summary */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Debits" value={fmtUSD(s.total_debits)} hint={`${s.count_debits} lines`} variant="warning" />
        <StatCard label="Credits" value={fmtUSD(s.total_credits)} hint={`${s.count_credits} lines`} variant="success" />
        <StatCard
          label="Net"
          value={fmtUSD(s.net)}
          hint={s.net >= 0 ? "money in" : "money out"}
          variant={s.net >= 0 ? "success" : "warning"}
        />
        <StatCard label="Largest debit" value={s.max_debit ? fmtUSD(s.max_debit.amount) : "—"} hint={s.max_debit?.description.slice(0, 40) ?? ""} />
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-2">
        <Input
          placeholder="Filter description, date, amount, or category…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="max-w-sm"
        />
        <div className="flex items-center gap-1 rounded-xl border bg-card p-1 text-xs">
          {(["all", "debit", "credit"] as const).map((d) => (
            <button
              key={d}
              onClick={() => setDirection(d)}
              className={cn(
                "rounded-lg px-3 py-1 transition",
                direction === d ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {d === "all" ? "All" : d === "debit" ? "Debits" : "Credits"}
            </button>
          ))}
        </div>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="h-8 rounded-xl border bg-card px-3 text-xs"
        >
          <option value="all">All categories ({data.lines.length})</option>
          {categoryOptions.map((c) => (
            <option key={c.value} value={c.value}>{c.label} ({c.count})</option>
          ))}
        </select>
        <div className="ml-auto text-xs text-muted-foreground">
          {filtered.length} of {data.lines.length}
        </div>
      </div>

      {/* Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto scrollbar-thin">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <Th onClick={() => onSort("posted_date")} active={sortKey === "posted_date"} dir={sortDir}>Date</Th>
                <Th onClick={() => onSort("description")} active={sortKey === "description"} dir={sortDir}>Description</Th>
                <Th onClick={() => onSort("category")} active={sortKey === "category"} dir={sortDir}>Category</Th>
                <th className="px-3 py-2 text-left font-medium">Type</th>
                <Th onClick={() => onSort("amount")} active={sortKey === "amount"} dir={sortDir} className="text-right">Amount</Th>
                <Th onClick={() => onSort("balance_after")} active={sortKey === "balance_after"} dir={sortDir} className="text-right">Balance</Th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map((r) => (
                <tr key={r.id} className="hover:bg-accent/30">
                  <td className="whitespace-nowrap px-3 py-2 text-muted-foreground">{r.posted_date ?? "—"}</td>
                  <td className="px-3 py-2">{r.description}</td>
                  <td className="px-3 py-2">
                    <Badge variant="secondary" className="font-normal">
                      {categoryLabel(r.category)}
                    </Badge>
                  </td>
                  <td className="px-3 py-2">
                    <Badge variant={r.direction === "debit" ? "warning" : "success"}>
                      {r.direction}
                    </Badge>
                  </td>
                  <td
                    className={cn(
                      "whitespace-nowrap px-3 py-2 text-right font-medium tabular-nums",
                      r.direction === "debit" ? "text-amber-600 dark:text-amber-400" : "text-emerald-600 dark:text-emerald-400",
                    )}
                  >
                    {r.direction === "debit" ? "−" : "+"}{fmtUSD(r.amount)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-muted-foreground">
                    {r.balance_after != null ? fmtUSD(r.balance_after) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function StatCard({
  label, value, hint, variant,
}: { label: string; value: string; hint?: string; variant?: "success" | "warning" }) {
  return (
    <Card className="p-4">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div
        className={cn(
          "mt-1 text-lg font-semibold tabular-nums",
          variant === "warning" && "text-amber-600 dark:text-amber-400",
          variant === "success" && "text-emerald-600 dark:text-emerald-400",
        )}
      >
        {value}
      </div>
      {hint && <div className="mt-1 truncate text-xs text-muted-foreground">{hint}</div>}
    </Card>
  );
}

function Th({
  children, onClick, active, dir, className,
}: {
  children: React.ReactNode;
  onClick: () => void;
  active: boolean;
  dir: SortDir;
  className?: string;
}) {
  const Icon = active ? (dir === "asc" ? ArrowUp : ArrowDown) : ArrowUpDown;
  return (
    <th
      onClick={onClick}
      className={cn(
        "cursor-pointer select-none px-3 py-2 text-left font-medium hover:text-foreground",
        active && "text-foreground",
        className,
      )}
    >
      <span className="inline-flex items-center gap-1">
        {children}
        <Icon size={11} />
      </span>
    </th>
  );
}
