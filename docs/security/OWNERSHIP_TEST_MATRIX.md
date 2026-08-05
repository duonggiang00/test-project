# Ownership and Tenant-Isolation Test Matrix

This matrix is derived from the approved target policy and executable backend tests. `PASS` means current code enforces the case. `EXPECTED FAIL` is an executable strict `xfail`: the target assertion currently fails, an unexpected pass fails the suite, and implementation remains governed by SEC-001/002 approval.

| Resource/action | Anonymous | Student | Owner teacher | Non-owner teacher | Admin | Current evidence |
|---|---|---|---|---|---|---|
| Update exam | deny | deny | allow | deny | allow | `test_exam_update_authorization_matrix` PASS |
| Bulk-assign questions to exam | deny | deny | allow | deny | allow | Non-owner case EXPECTED FAIL: service omits exam ownership check |
| Read material detail | deny | deny | allow | deny | allow | Non-owner case EXPECTED FAIL: service omits uploader/admin filter |

Rules for extending this matrix:

- Cover backend enforcement; frontend hiding or redirects are not authorization evidence.
- Add success, anonymous, student, owner, non-owner, and admin cases whenever the resource has an ownership boundary.
- Do not change an authorization assertion merely to match insecure current behavior.
- A strict expected failure must name the approved implementation task that will remove it.
