import type { AuthenticatedUser, LoginRequest, LoginResponse } from "../../lib/api-contracts";
import { requestJson } from "../../lib/http";

export function loginOperator(payload: LoginRequest): Promise<LoginResponse> {
  return requestJson<LoginResponse>({
    method: "POST",
    path: "/v1/auth/login",
    body: payload,
  });
}

export function getCurrentOperator(): Promise<AuthenticatedUser> {
  return requestJson<AuthenticatedUser>({
    path: "/v1/auth/me?surface=POS",
  });
}
