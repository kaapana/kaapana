## Decisions in data.rego

- `^/portal-api/.*` GET is granted to every authenticated user. portal-api has
  no request-level authorization of its own, so this grant is the only gate:
  any authenticated user can read the ingress-derived menu (entries from
  `kaapana.ai/ui.*` annotations across all namespaces), including entries their
  roles cannot open. Accepted trade-off — only menu metadata leaks, the targets
  themselves stay gated.

## Install
```bash
curl -L -o opa https://openpolicyagent.org/downloads/v1.18.2/opa_linux_amd64_static
```

Keep the version in step with the `open-policy-agent` service image and the
`opa-build` step in the auth-backend image.


## Test that policies build

run
`opa build --v0-compatible files`

## Run testcases

`opa test --v0-compatible -b files`

`--v0-compatible` is required: the policies are written in rego v0 syntax, which
opa 1.x rejects by default. The platform runs opa with the same flag. This is
what CI's `opa_policy_tests` job runs.
