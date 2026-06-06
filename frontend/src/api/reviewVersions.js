import http from "./http";

export function fetchReviewVersions(contractId) {
  return http.get(`/contracts/${contractId}/versions`);
}

export function fetchReviewVersionDetail(contractId, versionId) {
  return http.get(`/contracts/${contractId}/versions/${versionId}`);
}

export function compareReviewVersions(contractId, baseVersionId, targetVersionId) {
  return http.get(`/contracts/${contractId}/versions/compare/result`, {
    params: {
      base_version_id: baseVersionId,
      target_version_id: targetVersionId,
    },
  });
}
