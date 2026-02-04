export interface FraisInscription {
  iuec: number;
  tutelle: number;
  total: number;
  echeance: string | null;
}

export interface FraisScolarite {
  tranche1: number;
  tranche2: number;
  tranche3: number | null;
  total: number;
  echeances: string[];
}

export interface FraisOptions {
  inscription: FraisInscription;
  scolarite: FraisScolarite;
  autres: Record<string, number | string>;
}

export interface FraisOptionsResponse {
  faculte: string;
  niveau: string;
  specialite: string;
  program_id: string;
  program_code: string;
  program_name: string;
  academic_year: string;
  frais: FraisOptions;
  total_estime: number;
}

export interface ProgramOption {
  faculte: string;
  niveaux: string[];
}

export interface SpecialiteOption {
  key: string;
  name: string;
  program_id: string;
  program_code: string;
}

export interface SpecialitesOptionsResponse {
  faculte: string;
  niveau: string;
  specialites: SpecialiteOption[];
}

export interface TrancheEcheance {
  type: "inscription" | "scolarite" | "autres";
  label: string;
  montant: number;
  echeance: string;
  due: boolean;
  payee: boolean;
  montant_restant?: number;
}

export interface EcheanceResponse {
  tranches: TrancheEcheance[];
  montant_du: number;
  prochaine_echeance: string | null;
  statut: string;
  jours_retard: number;
  total_paye: number;
}

export interface Moratoire {
  id: string;
  student: string;
  student_matricule: string;
  student_nom: string;
  montant_reporte: number;
  date_accord: string;
  date_fin: string;
  duree_jours: number;
  motif: string;
  accorde_par: string;
  accorde_par_email: string;
  statut: "Actif" | "Respecté" | "Dépassé";
  created_by_role: string;
  created_at: string;
  updated_at: string;
}

export interface Bourse {
  id: string;
  student: string;
  student_matricule: string;
  student_nom: string;
  type_bourse: "Merite" | "Besoin" | "Tutelle" | "Externe" | "Interne";
  montant: number;
  pourcentage: number | null;
  annee_academique: number;
  annee_academique_code: string;
  annee_academique_label: string;
  date_attribution: string;
  date_fin_validite: string | null;
  motif: string;
  accorde_par: string;
  accorde_par_email: string;
  statut: "Active" | "Suspendue" | "Terminee";
  conditions: Record<string, any>;
  created_by_role: string;
  created_at: string;
  updated_at: string;
}

export interface BoursesActivesResponse {
  student_id: string;
  matricule: string;
  bourses: Bourse[];
  total_bourses_actives: number;
}

export interface DemandeAdministrative {
  id: string;
  student: string;
  student_matricule: string;
  student_nom: string;
  type_demande: "Releve_notes" | "Certificat_scolarite" | "Attestation_reussite" | "Autre";
  motif: string;
  statut: "En attente" | "Approuvée" | "Rejetée";
  date_soumission: string;
  date_traitement: string | null;
  traite_par: string | null;
  traite_par_email: string | null;
  piece_jointe: string | null;
  commentaire: string;
  created_at: string;
  updated_at: string;
}

export interface BourseSummary {
  id: string;
  type_bourse: "Merite" | "Besoin" | "Tutelle" | "Externe" | "Interne";
  montant: number;
  pourcentage: number | null;
  date_attribution: string;
  date_fin_validite: string | null;
  statut: "Active" | "Suspendue" | "Terminee";
  motif: string;
  accorde_par_email: string;
}

export interface MoratoireSummary {
  id: string;
  montant_reporte: number;
  date_accord: string;
  date_fin: string;
  statut: "Actif" | "Respecté" | "Dépassé";
  motif: string;
  accorde_par_email: string;
  duree_jours: number;
}

export interface BoursesEtMoratoiresResponse {
  student_id: string;
  matricule: string;
  bourses: BourseSummary[];
  moratoires: MoratoireSummary[];
  total_bourses: number;
  total_moratoires: number;
}