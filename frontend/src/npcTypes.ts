export type NpcPolicy = {
  definition_id: string;
  name: string;
  stock: string;
  capacity: number;
  reorder_point: number;
  order_quantity: number;
  target_stock: number;
  minimum_lot_size: number;
  order_step: number;
  production_enabled: boolean;
  buy_enabled: boolean;
  sell_enabled: boolean;
  revision: number;
  status: string;
  price_units: string;
  recipe: Record<string, number> | null;
  minimum_lot_quote: {
    base_price_units: string;
    fixed_margin_units: string;
    total_price_units: string;
  };
};
export type NpcEconomyState = {
  id: string;
  name: string;
  account_id: string;
  enabled: boolean;
  production_enabled: boolean;
  purchase_enabled: boolean;
  sale_enabled: boolean;
  fixed_margin: number;
  factors: Record<string, number>;
  revision: number;
  market_revision: number;
  items: NpcPolicy[];
  stock_items: { definition_id: string; name: string; quantity: string }[];
  wallet: { total_weight_mg: string; coins: Record<string, string> };
  last_update: string;
  history: {
    id: number;
    kind: string;
    occurred_at: string;
    [key: string]: unknown;
  }[];
};
