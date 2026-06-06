import http from "./http";

export function fetchReviewLogs(params) {
  return http.get("/review-logs", { params });
}
