export type Appearance = {
  sexo_visual: string;
  skin_tone: string;
  hair_style_id: string;
  hair_color: string;
  appearance_head: string;
  appearance_torso: string;
  appearance_legs: string;
  appearance_feet: string;
};
export type SavedAppearance = Appearance & { revision: number };
export type AppearanceCatalog = {
  version: number;
  options: Record<
    keyof Appearance,
    { id: string; label: string; color?: string }[]
  >;
  default: Appearance;
  barber_fee_units: string;
  barber_fee_mg: string;
};
export const fields: (keyof Appearance)[] = [
  "sexo_visual",
  "skin_tone",
  "hair_style_id",
  "hair_color",
  "appearance_head",
  "appearance_torso",
  "appearance_legs",
  "appearance_feet",
];
export const labels: Record<keyof Appearance, string> = {
  sexo_visual: "Sexo visual",
  skin_tone: "Tom de pele",
  hair_style_id: "Modelo de cabelo",
  hair_color: "Cor de cabelo",
  appearance_head: "Cabeça",
  appearance_torso: "Peito",
  appearance_legs: "Pernas",
  appearance_feet: "Pés",
};
