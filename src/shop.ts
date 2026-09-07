export type ItemId = 'water_flask' | 'medkit' | 'scrap_coil';

export interface ItemDefinition {
  readonly id: ItemId;
  readonly name: string;
  readonly description: string;
  readonly buyPrice: number;
  readonly sellPrice: number;
  readonly icon: 'flask' | 'medkit' | 'coil';
}

export const ITEMS: Readonly<Record<ItemId, ItemDefinition>> = Object.freeze({
  water_flask: Object.freeze({ id: 'water_flask', name: 'Water Flask',
    description: 'A dented field flask with a fresh seal and clean water.', buyPrice: 4, sellPrice: 2, icon: 'flask' }),
  medkit: Object.freeze({ id: 'medkit', name: 'Medkit',
    description: 'A compact pack of sealed dressings and colony first-aid supplies.', buyPrice: 9, sellPrice: 4, icon: 'medkit' }),
  scrap_coil: Object.freeze({ id: 'scrap_coil', name: 'Scrap Coil',
    description: 'A worn induction coil. Someone at the market can still use the copper.', buyPrice: 2, sellPrice: 1, icon: 'coil' }),
});

const ITEM_IDS: readonly ItemId[] = ['water_flask', 'medkit', 'scrap_coil'];
export interface InventoryItem extends ItemDefinition { readonly quantity: number }
export interface ShopSnapshot {
  readonly credits: number;
  readonly items: readonly InventoryItem[];
  readonly purchases: number;
  readonly sales: number;
}
export interface TradeResult {
  readonly ok: boolean;
  readonly message: string;
  /** Unknown runtime input has no valid item identity. */
  readonly itemId: ItemId | null;
}

function validItem(id: unknown): id is ItemId {
  return typeof id === 'string' && Object.hasOwn(ITEMS, id);
}

function wholeAmount(value: number) {
  return Number.isSafeInteger(value) && value >= 0;
}

function creditsText(value: number) { return `${value} credit${value === 1 ? '' : 's'}`; }

/** One local session; every successful call transfers exactly one item. */
export class Shop {
  #credits = 25;
  readonly #inventory: Record<ItemId, number> = { water_flask: 0, medkit: 0, scrap_coil: 1 };
  #purchases = 0;
  #sales = 0;

  buy(id: ItemId): TradeResult { return this.trade(id, 'buy'); }
  sell(id: ItemId): TradeResult { return this.trade(id, 'sell'); }

  private trade(id: ItemId, operation: 'buy' | 'sell'): TradeResult {
    if (!validItem(id)) return { ok: false, message: 'That item is not available.', itemId: null };
    const item = ITEMS[id];
    const price = operation === 'buy' ? item.buyPrice : item.sellPrice;
    if (operation === 'buy' && this.#credits < price) {
      return { ok: false, message: `You need ${creditsText(price - this.#credits)} more for ${item.name}.`, itemId: id };
    }
    if (operation === 'sell' && this.#inventory[id] < 1) {
      return { ok: false, message: `You have no ${item.name} to sell.`, itemId: id };
    }
    const credits = this.#credits + (operation === 'buy' ? -price : price);
    const quantity = this.#inventory[id] + (operation === 'buy' ? 1 : -1);
    const count = (operation === 'buy' ? this.#purchases : this.#sales) + 1;
    if (![price, credits, quantity, count].every(wholeAmount)) {
      return { ok: false, message: 'This trade cannot be completed.', itemId: id };
    }
    // Validate the entire transfer before changing any balance or success counter.
    this.#credits = credits;
    this.#inventory[id] = quantity;
    if (operation === 'buy') this.#purchases = count;
    else this.#sales = count;
    return { ok: true, message: `${operation === 'buy' ? 'Bought' : 'Sold'} ${item.name} for ${creditsText(price)}.`, itemId: id };
  }

  get snapshot(): ShopSnapshot {
    return Object.freeze({
      credits: this.#credits,
      items: Object.freeze(ITEM_IDS.map((id) => Object.freeze({ ...ITEMS[id], quantity: this.#inventory[id] }))),
      purchases: this.#purchases,
      sales: this.#sales,
    });
  }
}
