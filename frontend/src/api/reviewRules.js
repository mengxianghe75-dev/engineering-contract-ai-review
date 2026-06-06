import http from "./http";

export function fetchReviewRules() {
  return http.get("/review-rules");
}

export function createReviewRule(payload) {
  return http.post("/review-rules", payload);
}

export function updateReviewRule(ruleId, payload) {
  return http.patch(`/review-rules/${ruleId}`, payload);
}
