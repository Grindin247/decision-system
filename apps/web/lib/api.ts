export type Family = {
  id: number;
  name: string;
  created_at: string;
};

export type FamilyMember = {
  id: number;
  family_id: number;
  email: string;
  display_name: string;
  role: "admin" | "editor" | "viewer";
};

export type Goal = {
  id: number;
  family_id: number;
  name: string;
  description: string;
  weight: number;
  action_types: string[];
  active: boolean;
};

export type Decision = {
  id: number;
  family_id: number;
  created_by_member_id: number;
  owner_member_id: number | null;
  title: string;
  description: string;
  cost: number | null;
  urgency: number | null;
  target_date: string | null;
  tags: string[];
  status: string;
  notes: string;
  version: number;
  created_at: string;
  score_summary: {
    weighted_total_1_to_5: number;
    weighted_total_0_to_100: number;
    goal_scores: Array<{
      goal_id: number;
      goal_name: string;
      goal_weight: number;
      score_1_to_5: number;
      rationale: string;
      computed_by: string;
      version: number;
    }>;
  } | null;
};

export type DecisionScoreResult = {
  decision_id: number;
  weighted_total_1_to_5: number;
  weighted_total_0_to_100: number;
  threshold_1_to_5: number;
  routed_to: string;
  status: string;
  queue_item_id: number | null;
};

export type RoadmapItem = {
  id: number;
  decision_id: number;
  bucket: string;
  start_date: string | null;
  end_date: string | null;
  status: string;
  dependencies: number[];
};

export type MemberBudgetSummary = {
  member_id: number;
  display_name: string;
  role: "admin" | "editor" | "viewer";
  allowance: number;
  used: number;
  remaining: number;
};

export type BudgetSummary = {
  family_id: number;
  threshold_1_to_5: number;
  period_days: number;
  default_allowance: number;
  period_start_date: string;
  period_end_date: string;
  members: MemberBudgetSummary[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `request failed (${response.status})`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  listFamilies: () => request<{ items: Family[] }>("/families"),
  createFamily: (payload: { name: string }) => request<Family>("/families", { method: "POST", body: JSON.stringify(payload) }),
  updateFamily: (familyId: number, payload: { name: string }) =>
    request<Family>(`/families/${familyId}`, { method: "PATCH", body: JSON.stringify(payload) }),

  listFamilyMembers: (familyId: number) => request<{ items: FamilyMember[] }>(`/families/${familyId}/members`),
  createFamilyMember: (familyId: number, payload: { email: string; display_name: string; role: string }) =>
    request<FamilyMember>(`/families/${familyId}/members`, { method: "POST", body: JSON.stringify(payload) }),
  updateFamilyMember: (familyId: number, memberId: number, payload: { display_name?: string; role?: string }) =>
    request<FamilyMember>(`/families/${familyId}/members/${memberId}`, { method: "PATCH", body: JSON.stringify(payload) }),

  listGoals: (familyId: number) => request<{ items: Goal[] }>(`/goals?family_id=${familyId}`),
  createGoal: (payload: {
    family_id: number;
    name: string;
    description: string;
    weight: number;
    action_types: string[];
    active: boolean;
  }) => request<Goal>("/goals", { method: "POST", body: JSON.stringify(payload) }),
  updateGoal: (
    goalId: number,
    payload: Partial<{ name: string; description: string; weight: number; action_types: string[]; active: boolean }>,
  ) => request<Goal>(`/goals/${goalId}`, { method: "PATCH", body: JSON.stringify(payload) }),

  listDecisions: (familyId: number, includeScores = true) =>
    request<{ items: Decision[] }>(`/decisions?family_id=${familyId}&include_scores=${includeScores}`),
  createDecision: (payload: {
    family_id: number;
    created_by_member_id: number;
    owner_member_id?: number | null;
    title: string;
    description: string;
    cost?: number | null;
    urgency?: number | null;
    target_date?: string | null;
    tags?: string[];
    notes?: string;
  }) => request<Decision>("/decisions", { method: "POST", body: JSON.stringify(payload) }),
  updateDecision: (
    decisionId: number,
    payload: Partial<{
      owner_member_id: number | null;
      title: string;
      description: string;
      cost: number | null;
      urgency: number | null;
      target_date: string | null;
      tags: string[];
      notes: string;
    }>,
  ) => request<Decision>(`/decisions/${decisionId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  scoreDecision: (
    decisionId: number,
    payload: {
      goal_scores: Array<{ goal_id: number; score_1_to_5: number; rationale: string }>;
      threshold_1_to_5: number;
      computed_by?: "human" | "ai";
    },
  ) => request<DecisionScoreResult>(`/decisions/${decisionId}/score`, { method: "POST", body: JSON.stringify(payload) }),

  listRoadmap: (familyId: number) => request<{ items: RoadmapItem[] }>(`/roadmap?family_id=${familyId}`),
  createRoadmapItem: (payload: {
    decision_id: number;
    bucket: string;
    start_date?: string | null;
    end_date?: string | null;
    status: string;
    dependencies: number[];
    use_discretionary_budget?: boolean;
  }) => request<RoadmapItem>("/roadmap", { method: "POST", body: JSON.stringify(payload) }),
  updateRoadmapItem: (roadmapId: number, payload: Partial<{ bucket: string; start_date: string | null; end_date: string | null; status: string; dependencies: number[] }>) =>
    request<RoadmapItem>(`/roadmap/${roadmapId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteRoadmapItem: (roadmapId: number) => request<void>(`/roadmap/${roadmapId}`, { method: "DELETE" }),

  getBudgetSummary: (familyId: number) => request<BudgetSummary>(`/budgets/families/${familyId}`),
  updateBudgetPolicy: (
    familyId: number,
    payload: {
      threshold_1_to_5: number;
      period_days: number;
      default_allowance: number;
      member_allowances: Array<{ member_id: number; allowance: number }>;
    },
  ) => request<BudgetSummary>(`/budgets/families/${familyId}/policy`, { method: "PUT", body: JSON.stringify(payload) }),
  resetBudgetPeriod: (familyId: number) => request<BudgetSummary>(`/budgets/families/${familyId}/period/reset`, { method: "POST" }),
};
