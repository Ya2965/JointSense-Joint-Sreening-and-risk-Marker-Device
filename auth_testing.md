# JointSense auth testing
1. `POST /api/auth/login` with `{"identifier":"doctor1@jointsense.local","password":"JointSense123!"}`.
2. Keep the returned bearer token and call `GET /api/auth/me` with `Authorization: Bearer <token>`.
3. Register a new username/email and confirm duplicate email is rejected.
4. Confirm patients and assessment endpoints reject requests without a token.