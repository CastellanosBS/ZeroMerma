# Merenna opening profile

Status: prepared from the owner's answers for a **new real branch**. This document
does not create a branch, migrate a database or configure an existing demonstration
branch. The owner selected a new branch rather than reusing a seeded location.

## Commercial identity

| Field | Prepared value | Source |
| --- | --- | --- |
| Receipt commercial name | Merenna | Owner |
| Receipt business descriptor | Panadería y repostería | Selected under the owner's authorization |
| Address line | Plaza Distrito H, Boulevard Juan Navarrete 492K | Owner; capitalization normalized |
| City | Hermosillo | Owner |
| State | Sonora | Owner |
| Postal code | 83249 | Owner |
| Country | México | Owner |
| Branch timezone | America/Hermosillo | IANA identifier for the owner's location |

The commercial name is independent of the internal branch name. No legal entity
name, RFC, fiscal regime, telephone or email was supplied. Leave these unspecified;
do not use the commercial name as a legal identity. Receipts remain operational
documents and are not CFDI or evidence of BBVA authorization.

## Apply during controlled onboarding

1. Deploy the matching API, POS and Backoffice contracts and the migration chain
   through `20261019_0057_receipt_identity` in the intended environment.
2. Confirm the real environment and the intended Merenna brand. Seeded brand or
   branch names are not evidence that they are the real business configuration.
3. Create a new branch through the authorized Backoffice branch form. Assign a
   unique branch code and an explicit internal name during provisioning; neither
   a branch UUID nor a production workstation has been assigned by this document.
4. Enter the commercial fields and structured address above. Verify the timezone
   and saved branch detail. Do not overwrite `MAIN`, `NORTE` or `SUR` demo branches.
5. Bind the intended checkout workstation and users to the new branch, establish
   its catalog, prices and inventory, and configure the approved order commitment
   policy before accepting customer orders. Its duration remains an owner decision.
6. Before real sales, rehearse sale, order payment and return receipts. Verify the
   Merenna header, descriptor, address, folio, amounts and payment methods on the
   selected printer. Changing the branch profile must affect only new receipts;
   reprinting an issued receipt must preserve its original identity and address.

Commercial configuration is audited. Each new receipt freezes the branch profile
inside its economic transaction. Historical receipts without these optional fields
remain readable without being rewritten or borrowing the current branch identity.

## Opening dependencies

The intended opening has one branch and one checkout. Cash and separately charged
BBVA card payments are the approved initial workflow. Actual BBVA integration,
printer/drawer adapters and physical acceptance are still pending; a successful
software test does not validate the purchased equipment. Digital tickets are not
sent by the current implementation.

See [checkout and orders](pos-checkout-and-orders.md),
[local hardware](local-hardware.md) and the
[POS validation record](../implementation/pos-block-validation.md) for operational
steps, verified software evidence and the remaining boundaries.
