# PLAN MAESTRO CANÓNICO DE FINALIZACIÓN DE ZEROMERMA
**Estado:** fuente de verdad de planificación para finalizar, validar, pilotear y llevar ZeroMerma a producción. No certifica que las tareas ya estén implementadas.  \n**Fecha de consolidación:** 2026-08-25 (America/Hermosillo).  \n**Fuentes normativas de evidencia:** `AUDITORIA_CODEX_ZERO_MERMA.md` (SHA-256 `9ef1fd2997cf7e0b478184ac30b5ff70abf09dd18772415df935b47a1ad5f54f`) y `AUDITORIA_ACTIVA_ZERO_MERMA.md` (SHA-256 `7f4377a8fa450b1c80af576f13096fe1802681dfbeb98e7364f76bb97615e438`).  \n**Documento expresamente no usado como fuente normativa:** el `PLAN_MAESTRO_ZERO_MERMA.md` previo. Se reemplaza por este documento.
## 0. Reglas de uso y jerarquía de verdad

1. El código vigente del repositorio, cuando Codex aporte evidencia reproducible, tiene prioridad sobre este plan y sobre las auditorías.
2. Las dos auditorías son el punto de partida mínimo; un hallazgo activo con HTTP/UI/DB/log tiene más fuerza que una inferencia estática, pero la ausencia de prueba dinámica no invalida un control ausente observado en código.
3. Cuando código, auditoría activa y auditoría estática se contradigan, la tarea debe detener la conclusión, documentar la contradicción y pedir la decisión/verificación correspondiente.
4. Este plan distingue: **hecho auditado**, **inferencia técnica**, **propuesta de ingeniería** y **decisión de negocio pendiente**.
5. Ninguna tarea se declara terminada por existencia de archivo, ruta, pantalla o migración. Se exige prueba y evidencia.
6. Sólo existe un plan maestro y un documento vigente de decisiones. Los resultados de Codex actualizan esos documentos; no crean roadmaps paralelos.
## 1. Resumen ejecutivo

ZeroMerma posee una base adecuada para evolucionar sin reescritura: monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI generado, precisión decimal, auditoría y outbox transaccionales. La auditoría activa demostró que una parte importante de ventas, pagos, pedidos, documentos y administración es real. También demostró defectos sistémicos: el POS no alimenta el inventario canónico; el pago de pedido no entra en caja/corte; el worker no procesa eventos; la trazabilidad de identidad/origen es incorrecta; y varias superficies administrativas son simuladas o incompletas.

El sistema no está terminado ni listo para producción. La ruta correcta no es reconstruirlo: es fijar una línea base reproducible, cerrar decisiones, aplicar autorización/scopes, garantizar idempotencia y concurrencia, unificar ledgers, completar verticales POS/Backoffice, volver operativo el worker, probar integralmente y construir una plataforma desplegable/recuperable. Este plan contiene **126 tareas secuenciales**. Cada tarea incluye los 23 campos requeridos y un prompt de Codex autocontenido.
## 2. Qué significa “ZeroMerma terminado”

**ZeroMerma terminado** significa que todo el alcance aprobado está implementado verticalmente —backend, persistencia, autorización, UI, contratos, pruebas y documentación— y que ninguna ruta productiva es un placeholder. Terminado no equivale todavía a listo para producción.

**ZeroMerma listo para producción** exige además seguridad validada, integridad de datos, artefactos inmutables, infraestructura, observabilidad, migraciones, backup/restore, rollback/DR, hardware, staging y runbooks.

**ZeroMerma listo para producción general** exige adicionalmente un piloto real estabilizado, reconciliación de dinero/inventario/eventos, soporte operativo y evidencia de que las cadencias representativas del negocio se ejecutaron sin bloqueos críticos.
### 2.1 Definition of Done global
1. El alcance productivo y la política de visibilidad están aprobados; ninguna función excluida aparenta estar disponible.
2. La arquitectura vigente se conserva: monolito modular, API como fuente de verdad, PostgreSQL, cliente OpenAPI generado y frontends separados.
3. Todos los casos de uso críticos validan reglas en backend y respetan usuario, sucursal, caja, estación y turno.
4. RBAC y scopes son deny-by-default y están probados con identidades limitadas y datos multi-sucursal.
5. Sesiones, contraseñas, configuración, secretos, CORS/CSP/headers y endpoints de desarrollo cumplen la política aprobada.
6. Cada comando económico/físico es atómico, idempotente, auditable y seguro ante concurrencia/retry.
7. Los ledgers financiero y físico son canónicos, inmutables por compensación y reconstruibles desde movimientos causales.
8. Ventas, pedidos, pagos, caja, devoluciones, transferencias, compras, producción, correcciones y merma reconcilian entre API, DB, POS, Backoffice y reportes.
9. Outbox y worker procesan al menos una vez con consumidores idempotentes; backlog, edad, errores y DLQ son observables y operables.
10. No existen placeholders, datos simulados, endpoints incompletos o pantallas desconectadas dentro del alcance aprobado.
11. OpenAPI, cliente TypeScript, migraciones, toolchain y artefactos son reproducibles desde un commit limpio y no generan diff.
12. Las pruebas unitarias, integración PostgreSQL, contract, E2E, seguridad, concurrencia, recuperación, rendimiento y hardware pasan en entornos aislados.
13. La aplicación tiene logs estructurados, métricas, traces, liveness/readiness, alertas accionables y SLOs aprobados.
14. API, worker y frontends se distribuyen como artefactos inmutables y se promueven sin rebuild entre staging y producción.
15. La infraestructura está codificada, protegida por TLS/red, usa secretos externos y aplica migraciones de forma controlada.
16. Backups/PITR se restauraron y reconciliaron; rollback/roll-forward/DR se ensayaron y cuentan con runbooks.
17. Instalación/actualización POS, impresora, cajón, terminal, conectividad y contingencia fueron probadas en hardware objetivo.
18. Documentación técnica, operativa, de privacidad/fiscalidad y capacitación coincide con el sistema desplegado.
19. Staging, UAT y piloto cubrieron todas las cadencias representativas, con reconciliación y sin defectos críticos/altos abiertos.
20. El release general está identificado por commit, schema, contrato y digests; operación, soporte y mantenimiento tienen owners explícitos.

## 3. Revisión crítica y consolidación de auditorías
La auditoría activa eleva algunos riesgos estáticos a defectos reproducidos y reduce otros: por ejemplo, el OpenAPI servido sí coincidió con el generado en el snapshot activo, y 29 de 32 rutas administrativas tenían integración real; esto no elimina el gate de drift ni convierte las tres superficies simuladas en completas. `/health` 200 con outbox inmóvil demuestra que liveness y readiness operacional deben separarse.

| Hallazgo estático | Evidencia activa | Decisión consolidada | Tareas |
|---|---|---|---|
| ZM-SEC-001 | ZMA-SEC-001 | Confirmado conceptualmente: el modelo RBAC no gobierna sistemáticamente los endpoints. | ZM-FIN-015–019, 095 |
| ZM-SEC-002 | ZMA-SEC-002 | Confirmado: scopes administrativos por sucursal no soportados. | ZM-FIN-020–022, 086, 095 |
| ZM-DATA-003 | ZMA-DATA-002 | Riesgo de carrera no explotado; requiere prueba PostgreSQL determinista. | ZM-FIN-036–037, 097 |
| ZM-DATA-004 | ZMA-DATA-001 / ZMA-WASTE-001 | Confirmado dinámicamente: POS no alimenta el ledger físico; compra admin sí. | ZM-FIN-048–055, 099 |
| ZM-REL-005 | ZMA-REL-001 | Control ausente; duplicación no explotada por seguridad. | ZM-FIN-028–035, 097 |
| ZM-ASYNC-006 | ZMA-ASYNC-001 | Confirmado dinámicamente: worker vivo, 34 eventos pendientes, cero intentos. | ZM-FIN-087–093 |
| ZM-SEC-007 | — | Configuración productiva fail-closed no demostrada. | ZM-FIN-026–027, 096, 107, 111 |
| ZM-SEC-008 | ZMA-SEC-003 | Confirmado por código: bearer persistente y aceptado por URL. | ZM-FIN-023–024, 026, 096 |
| ZM-SEC-009 | ZMA-ID-001 / ZMA-UI-001 | Ciclo de identidad incompleto; last_login no persistió en auditoría activa. | ZM-FIN-024–025, 096 |
| ZM-QA-010 | ZMA-QA-001 | Riesgo destructivo confirmado por inspección; no se ejecutó deliberadamente. | ZM-FIN-005 |
| ZM-QA-011 | — | Cobertura integrada insuficiente para permisos, idempotencia, concurrencia y E2E real. | ZM-FIN-094–101 |
| ZM-FUNC-012 | ZMA-FUNC-001 | CRUD de descuentos real, sin consumidor en venta/pedido. | ZM-FIN-071–072 |
| ZM-FUNC-013 | ZMA-BO-001 / ZMA-BO-002 | Dashboard/alertas/pagos operativos simulados y first-record roto en incidencias/equipos. | ZM-FIN-080–083, 091 |
| ZM-OPS-014 | — | No existe evidencia de despliegue, restore y observabilidad productivos. | ZM-FIN-106–126 |
| ZM-REL-015 / 018 | ZMA-REL-002 | Estado Git y toolchain no reproducibles; OpenAPI sí coincidió en el snapshot activo. | ZM-FIN-001, 004, 009, 014 |
| ZM-MAINT-016 | ZMA-UX-001 | Deuda de componentes grandes y feedback/localización inconsistente; refactor sólo tras caracterización. | ZM-FIN-067, 094 |
| ZM-OBS-017 | ZMA-AUD-001 / ZMA-ASYNC-001 | Auditabilidad de negocio superior a observabilidad técnica; contexto/origen incorrectos. | ZM-FIN-040, 084, 089, 109 |
| — | ZMA-FIN-001 | Pago de pedido omitido de caja/corte; diferencia artificial de 6.00. | ZM-FIN-042, 045, 098 |
| — | ZMA-PROD-001 / ZMA-CAT-001 | Producción cancelada y estado de insumo contradictorios. | ZM-FIN-054, 068–070 |
| — | ZMA-REP-001 | Venta mixta no clasificada como mixta. | ZM-FIN-045, 083, 098 |

### 3.1 Brechas imprescindibles no limitadas por la auditoría
- Requisitos fiscales/regulatorios, privacidad, retención y contenido/numeración de tickets según jurisdicción aprobada.
- Frontera real de pagos electrónicos, certificación de terminal, conciliación y reversas.
- Instalación y actualización de estaciones, impresora, cajón, drivers/bridge y matriz de hardware soportado.
- Política de conectividad/offline y recuperación de resultados después de timeout o desconexión.
- Artefactos productivos, IaC, TLS/red, CI/CD, secretos, backups/PITR, restore, rollback y disaster recovery.
- Observabilidad completa, SLOs, on-call, incident response, postmortems y soporte de sucursales.
- Pruebas de carga/capacidad, seguridad de cadena de suministro, SBOM, DAST y accesibilidad en dispositivos reales.
- UAT, capacitación, migración de datos, cutover, piloto, reconciliación diaria y expansión por oleadas.
- Catálogo de eventos, lineage, proyecciones analíticas y base gobernada para IA, sin modificar OLTP.

## 4. Arquitectura y decisiones que se preservan

- Monolito modular; no microservicios prematuros.
- FastAPI como frontera HTTP y backend como única autoridad de reglas críticas.
- PostgreSQL como sistema de registro; balances y reportes son proyecciones reconciliables.
- POS y Backoffice separados; UI consume contratos generados y nunca sustituye autorización backend.
- `Decimal`/`Numeric` para dinero y cantidades; reglas de redondeo explícitas.
- Auditoría y outbox dentro de la transacción de negocio; eventos entregados al menos una vez y consumidores idempotentes.
- Documentos/movimientos confirmados no se editan para “corregir”: se compensan con referencias causales.
- Aislamiento por sucursal, caja, usuario, estación y turno cuando corresponda.
- Refactors sólo incrementales, precedidos por caracterización y justificados por seguridad, consistencia o mantenibilidad necesaria.
## 5. Registro de decisiones del propietario

Este es el único Plan Maestro canónico versionado del repositorio. Conserva 126 tareas, ZM-FIN-001–ZM-FIN-126. DEC-01–DEC-20 están `APROBADA`; no quedan decisiones pendientes. Aprobar una DEC modifica criterios futuros, no marca implementación ni satisface gates.

Se registra `PLAN_MASTER_CANONICAL_IN_REPO=true`, `PLAN_MASTER_SINGLE=true`, `TASK_COUNT_126=true`, `TASK_IDS_001_126_COMPLETE=true`, `NO_TASK_MARKED_IMPLEMENTED_BY_SYNC=true` y `GATES_NOT_FAKE_COMPLETED=true`.

| ID | Decisión | Contenido canónico o todavía pendiente |
|---|---|---|
| DEC-01 | Línea base canónica | Qué cambios locales/no rastreados forman parte del producto y qué commit será la fuente de verdad. |
| DEC-02 | Alcance y visibilidad | Qué capacidades forman parte de la salida y cuáles deben ocultarse/retirarse hasta completarse. |
| DEC-03 | RBAC | Catálogo de capacidades, superadministrador, separación de funciones y quién administra roles. |
| DEC-04 | Scopes | Roles globales/scoped, múltiples sucursales y operaciones centralizadas permitidas. |
| DEC-05 | Sesión | Cookie segura, intercambio de un solo uso u otro mecanismo; duración, refresh, revocación y terminal compartida. |
| DEC-06 | Cierre | Qué comando gana ante venta/pago concurrente, si se permite cierre sin conteo y cómo se tratan pendientes. |
| DEC-07 | Idempotencia | Generador/scope/retención de claves y respuesta ante mismo key con payload distinto. |
| DEC-08 | Inventario | Momento de afectación de PRODUCT_DIRECT/CLASS_CAPTURE, reservas, UOM y política de stock negativo. |
| DEC-09 | Devolución y merma | Restock/cuarentena/waste/no-stock, SEND_TO_WASTE y reglas de reversa. |
| DEC-10 | Pedidos | Momento de reconocimiento financiero/físico, reserva, pago parcial, entrega y cancelación. |
| DEC-11 | Pago mixto | Definición métrica y conteo/conciliación por medio. |
| DEC-12 | Producción | Semántica de cancelación, consumo, output, merma, rendimiento y receta versionada. |
| DEC-13 | Pricing y descuentos | Vigencia, prioridad, acumulación, límites, redondeo y autorización de excepciones. |
| DEC-14 | Pagos externos | Proveedor/terminal, fallback manual, reversas, estados pendientes y responsabilidades. |
| DEC-15 | Hardware y offline | Matriz de dispositivos, bridge/local agent, alcance offline/reconnect y contingencia. |
| DEC-16 | Requisitos externos | Jurisdicción, ticket, privacidad, retención, exportación, comunicaciones y consentimiento. |
| DEC-17 | Continuidad — APROBADA | LOCAL_FIRST: backend/PostgreSQL local autoritativo por LAN; operación sin Internet pero no browser offline; segundo mini-PC standby controlado; RPO local cero/casi cero, RPO de sitio <=5m, RTO primario <=1h y RTO de sitio <=8h; cloud complementario. |
| DEC-18 | Métricas y alertas — APROBADA | Instrumentación amplia; catálogo KPI exhaustivo/versionado; dashboard selectivo; alerting conservador; Telegram crítico; outbox/fact layer; HOT/WARM/COLD; lakehouse/IA futuros no bloqueantes. Append-only transversal no se presume. |
| DEC-19 | Datos existentes — APROBADA | Volúmenes locales conocidos clasificados por el propietario como desarrollo/demo/test; ninguna fuente legacy externa actual; clean operational start; política híbrida/selectiva por dominio; opening state auditable; operaciones abiertas reconciliadas o migradas sólo con causalidad suficiente; Superadministrador inicial explícito y único `GLOBAL` inicial. |
| DEC-20 | Piloto y rollout — APROBADA | Sucursal Matriz como único sitio piloto inicial; duración híbrida con dos ciclos semanales completos y cobertura obligatoria; stop por impacto; autoridad dual para reanudación crítica y expansión; contingencia inicial stop-only; rollout de una sucursal por oleada; línea de release controlada; BBVA obligatorio en la aceptación final después de gates; fiscalidad derivada de DEC-16/ZM-FIN-007. |

## 6. Gates obligatorios
| Gate | Debe ser verdadero | Evidencia mínima |
|---|---|---|
| **G0 — Baseline Ready** | Existe commit canónico, toolchain reproducible, DB de pruebas aislada y fail-closed, migraciones rastreadas/validadas, alcance y decisiones P0 aprobados. La clasificación no productiva de los volúmenes conocidos no sustituye los controles de aislamiento. | SHA, estado Git limpio, logs fresh install/upgrade desde DB vacía y datasets representativos, pruebas allow/deny de guardia DB y documento único de decisiones. |
| **G1 — Development Complete** | Código, migraciones, contratos y configuración de todas las tareas de desarrollo del alcance están integrados; lint, typing, unitarias, integración y builds pasan; no hay cambios generados pendientes. | CI verde por commit, OpenAPI sin diff, lista de tareas cerradas y artefactos de pruebas. |
| **G2 — Feature Complete** | Todas las funciones aprobadas existen verticalmente en backend, persistencia, permisos, UI y pruebas; no hay placeholders ni rutas que aparenten capacidad inexistente. | Matriz ruta–capacidad–prueba, E2E POS/Backoffice y política de visibilidad. |
| **G3 — Data Integrity Ready** | Idempotencia, locks y transacciones están probados; ledgers financiero/físico reconcilian; opening state, migraciones, backfills y rebuilds preservan datos sin inventar historia. | Suites concurrentes, ecuaciones de caja, conteo físico/opening state firmado, mapping de IDs, reconciliación de inventario y dry runs idempotentes con rechazo de datos ambiguos. |
| **G4 — Security Ready** | RBAC/scopes deny-by-default, sesión/revocación, hardening, secrets, threat model y scans no tienen hallazgos críticos/altos abiertos sin aceptación explícita. | Matriz 401/403/2xx, pruebas cross-branch, scans/SBOM, evidencia de configuración fail-closed. |
| **G5 — QA Ready** | Suites unitarias, integración, E2E, recuperación, rendimiento y hardware/a11y cubren los riesgos aprobados; fórmulas KPI críticas, data quality, correlation/causation, opening state y rebuilds deterministas están probados; seeds/demo no contaminan una DB real y no hay flakiness no controlada ni defectos críticos/altos abiertos. | Resultados CI, pruebas de aislamiento DB, KPI/lineage/rebuild/opening state, rechazo de datos ambiguos, reportes no funcionales, artefactos Playwright y triage firmado. |
| **G6 — Staging Ready** | Staging equivalente a producción se aprovisiona desde cero y ejecuta el release candidate con migración, probes, worker, smoke y datos UAT explícitamente no productivos; ensaya clean start, opening state y reconciliación. | Manifiesto desplegado, digests, schema revision, clasificación del dataset, opening-state dry run, smoke, reconciliación y drift detection. |
| **G7 — Production Ready** | La topología LOCAL_FIRST, artefactos, red/TLS local, PostgreSQL autoritativo, standby controlado, observabilidad, secretos, backup off-site/restore, rollback/DR y runbooks están probados; clean operational start, master data aprobada y mecanismo de opening state están listos; la matriz fiscal de la entidad real está validada; dashboard de alertas y Telegram crítico se prueban con Internet, y perder Telegram no bloquea la tienda. | Restore/failover drills con RPO/RTO observado, operación local sin Internet, paquete de carga/opening state idempotente, Superadministrador inicial explícito, matriz `obligation -> module -> control -> evidence`, alert dashboard, prueba Telegram y cola pendiente/retry, release pipeline, SLO/runbooks y aprobación formal. |
| **G8 — Pilot Ready** | G7 Production Ready está aprobado; Sucursal Matriz es el único sitio inicial y acredita mini-PC principal/standby, LAN, energía, backup off-site, clean opening state, usuarios/scopes, capacitación observada, soporte, stop-only inicial, rollback y cutover; BBVA sólo se habilita después de todos sus gates y es obligatorio para la aceptación final integral; requisitos fiscales aplicables están satisfechos. | Site survey de Sucursal Matriz, evidencia firmada de master data, Superadministrador inicial, conteo/opening state, hardware y versiones, capacitación, runbooks, dual authority, tratamiento de operaciones abiertas, gate BBVA/PCI cuando corresponda, reconciliación inicial, smoke sin Internet, dashboards selectivos y acta go/no-go. |
| **G9 — General Production** | El piloto en Sucursal Matriz cubrió como mínimo dos ciclos semanales operativos completos y todas las cadencias obligatorias; no tiene defectos `CRITICAL`, blockers `HIGH` ni alertas `CRITICAL-A` sin resolver; reconcilia dinero/inventario/outbox/proyecciones; soporte y ownership operan el producto; rollout de una sucursal por oleada y línea de release controlada están aprobados. No exige lakehouse para v1. | Acta de estabilización, cobertura de ciclos, incidentes/postmortems, reconciliaciones longitudinales desde cutover, evidencia KPI válida, aprobaciones técnica/administrativa, release line y plan de rollout/handover por sucursal. |

### 6.1 Sincronización canónica DEC-17/DEC-18

DEC-17 y DEC-18 se aplican transversalmente a las tareas afectadas. La fuente del diccionario KPI es `docs/DECISIONES_ZERO_MERMA.md`; sus cientos de definiciones no se duplican en cada prompt. Toda tarea que produzca o consuma un KPI debe exigir definición/versión, fuente canónica, lineage, dimensiones/scopes, owner, validez, requisitos de calidad y pruebas.

Invariantes de implementación futura:

- `business mutation + canonical ledger/state + audit + outbox` comparten la misma transacción PostgreSQL cuando la operación genera un hecho relevante;
- delivery es at-least-once, consumidores son idempotentes, eventos sin procesar son recuperables y proyecciones reconstruibles;
- la instrumentación es amplia, el catálogo exhaustivo, el dashboard selectivo y el alerting conservador;
- backup operacional de DEC-17 no es archivo analítico HOT/WARM/COLD de DEC-18;
- PostgreSQL local sigue siendo autoridad operacional; la capa analítica es derivada y no muta OLTP;
- `occurred_at` es tiempo de negocio y `recorded_at` es persistencia/lineage;
- dinero usa Decimal/Numeric, nunca float; ausencia, stale, estimado o no reconciliado no se presentan como cero/actual/medido/válido.

| Tareas | Alineación obligatoria adicional |
|---|---|
| ZM-FIN-003, 007–009 | Registro DEC-17/18, privacidad/retención, matriz de hechos/eventos y contratos versionados. |
| ZM-FIN-015–022, 027 | Capabilities/scopes de dashboard, ACK, resolución, export y secreto Telegram. |
| ZM-FIN-028–040 | Idempotencia, contexto, correlation/causation y frontera atómica audit/outbox. |
| ZM-FIN-041–055 | Ledgers/fuentes canónicas y hechos granulares para KPI financieros, inventario, producción, merma y costos. |
| ZM-FIN-066, 068–086 | LOCAL_FIRST sin mutaciones offline de browser; hechos de dominio; dashboard selectivo, reporting y audit. |
| ZM-FIN-087–093 | Claim/lease, attempts/backoff/DLQ, métricas ASY, alertas A/B/C, Telegram y fact layer. |
| ZM-FIN-094–105 | Pruebas de fórmula/lineage/DQ/rebuild, privacidad, rendimiento y documentación. |
| ZM-FIN-106–116 | Artefactos/topología LOCAL_FIRST, standby, telemetría, backup/restore y gobierno de incidentes. |
| ZM-FIN-117–126 | Staging, gates, piloto y rollout con evidencia; futuros no bloqueantes. |

Dependencias arquitectónicas: contratos y ledgers preceden hechos analíticos confiables; outbox transaccional e identidad versionada preceden consumidores; worker durable precede proyecciones; data quality/reconciliación preceden KPI `VALID`; 2–4 semanas de datos reales preceden cualquier propuesta de sensibilidad intermedia; escala/evidencia preceden lakehouse. No se crea un ID nuevo para esas dependencias y ningún gate queda cumplido por documentarlas.

Se registra `NOT_G8_BLOCKER=true` y `NOT_G9_V1_BLOCKER=true` para lakehouse. También son futuros no bloqueantes WhatsApp, sensibilidad intermedia, forecast avanzado, ML/IA, anomalías no calibradas, warehouse externo, herramientas Big Data concretas y Living Lab no aprobado.

Se registra `LOCAL_FIRST_PLAN_PRESERVED=true`, `MANAGED_CLOUD_NOT_REINTRODUCED_AS_PILOT_PRIMARY=true`, `BACKUP_ANALYTICS_SEPARATED=true`, `LAKEHOUSE_NOT_PILOT_BLOCKER=true` y `LAKEHOUSE_NOT_PRODUCTION_V1_BLOCKER=true`.

### 6.2 Sincronización canónica DEC-19

DEC-19 se aplica transversalmente a toda tarea que cree, cargue, migre, backfillee, reconstruya, reconcilie, archive o corte datos. Esta sección añade requisitos obligatorios a los campos y prompts de las tareas existentes indicadas; no crea tareas, no cambia IDs, no declara implementación y no satisface gates.

#### Evidencia técnica frente a declaración del propietario

La inspección técnica read-only identificó `PG-ZM-CURRENT` (`zeromerma_zeromerma_postgres_data`) y `PG-ZM-LEGACY` (`zeromerma_pgdata`), pero no verificó filas ni revisiones de schema porque PostgreSQL estaba detenido. El propietario clasificó expresamente ambas fuentes como `DEVELOPMENT_DEMO_TEST` y confirmó `external_legacy_sources_to_migrate=NONE`.

Por tanto:

- `local_volumes_owner_classification=NON_PRODUCTION` es política aprobada por el propietario, no inferencia desde las filas;
- `production_operational_history_start=CLEAN`;
- seeds, fixtures, training y demo no son historia empresarial ni opening balance;
- `migration_policy=HYBRID_SELECTIVE_BY_DOMAIN` permanece disponible ante una fuente real futura;
- `full_historical_canonicalization_required=false`;
- una fuente real nueva obliga `STOP_MIGRATION_ASSUMPTION=true` y reclasificación antes de usarla o borrarla;
- `clean_start_policy_approved != migration_implemented`;
- `owner_classified_test_data != safe_test_database_controls_implemented`.

#### Invariantes de datos y cutover

- Dinero/caja/pagos se resuelven desde evidencia económica cerrada y reconciliable; conflictos no resueltos quedan en `MANUAL_RECONCILIATION`.
- Inventario inicial se deriva de conteo físico validado y causalidad fiable cuando exista; si falta historia se usa opening adjustment auditable, nunca movimiento ficticio.
- Catálogo, recetas y pricing iniciales provienen de configuración empresarial vigente explícitamente aprobada, no del seed.
- Identidad productiva proviene de cuentas activas validadas explícitamente.
- Todo opening state conserva cutover/occurred time, recorded time, scope, actor, reason, evidencia, audit, idempotencia y outbox cuando corresponda.
- Operaciones abiertas se cierran y reconcilian cuando sea viable; sólo se migran con identidad, causalidad, estado, importes/cantidades, scope y auditabilidad suficientes.
- `historical_event`, `backfilled_analytical_fact`, `migration_record` y `opening_adjustment` son categorías distintas.
- PII demo/test no se migra por defecto; todo cambio de identidad conserva mapping durable `source_id -> target_id`.
- El primer Superadministrador será `ZEROMERMA_OWNER`, con rol Superadministrador explícito y `GLOBAL`; será el único `GLOBAL` inicial. Ningún admin seed/legacy hereda Superadministrador ni `GLOBAL`.

#### Alineación adicional por tarea existente

| Tareas | Dependencia o criterio DEC-19 obligatorio |
|---|---|
| `ZM-FIN-003` | DEC-19 queda aprobada; la tarea continúa abierta exclusivamente por DEC-20. El registro documental no equivale a implementación. |
| `ZM-FIN-004` | Toolchain reproducible sin tratar datos demo como productivos ni depender de ellos para instalación productiva. |
| `ZM-FIN-005` | DB de test aislada y fail-closed; toda prueba destructiva debe abortar antes del primer SQL contra DB operacional, staging real o producción. |
| `ZM-FIN-006` | Validar cadena desde DB vacía y snapshots/datasets representativos; los dos volúmenes clasificados no productivos pueden probar compatibilidad, pero no imponen preservación de historia empresarial. |
| `ZM-FIN-015`–`022` | Materializar Superadministrador inicial explícito para `ZEROMERMA_OWNER`, único `GLOBAL` inicial; ningún rol/usuario seed o legacy recibe privilegio implícito; demás autoridades usan capabilities y scopes explícitos. |
| `ZM-FIN-041`–`046` | El ledger productivo inicia limpio; opening economic state es explícito; no se importan efectos financieros demo/test ni se inventa causalidad. |
| `ZM-FIN-047` | Mantener diagnóstico/backfill para fuentes reales futuras, staging y opening-state transformation; prohibir backfill demo/test, exigir idempotencia y reconciliación antes/después. |
| `ZM-FIN-048`–`054` | Ningún balance demo/test es autoridad; movimientos y relaciones nuevas deben poder explicar el opening state y preservar mapping/causalidad. |
| `ZM-FIN-055` | Conteo físico validado + opening state aprobado; rebuild sólo con historia causal fiable; diferencias ambiguas requieren reconciliación y nunca movimientos ficticios. |
| `ZM-FIN-071`–`072` | Precios/promociones productivos nacen de configuración empresarial aprobada; no migrar precios o commercial discounts demo como autoridad. |
| `ZM-FIN-087`–`092` | No procesar outbox/audit demo como historia productiva; apertura/cutover y operaciones abiertas deben preservar estado y reanudación sin duplicar efectos. |
| `ZM-FIN-093` | Distinguir evento histórico, fact analítico backfilled, migration record y opening adjustment; no fabricar eventos retrospectivos. |
| `ZM-FIN-098` | Probar clean start, opening state financiero, mappings, idempotencia, reconciliación, rechazo de datos ambiguos y futura fuente representativa; conservar suite aunque no exista legacy real actual. |
| `ZM-FIN-099` | Probar que seeds/demo no contaminan producción; opening inventory, mappings, replay/restart y rechazo de movimientos ambiguos; conservar suite para migración futura. |
| `ZM-FIN-108` | Orquestar migración y carga inicial una sola vez, con identidad del dataset, guardas de entorno, schema revision y reconciliación; no inferir producción por nombre de volumen. |
| `ZM-FIN-117` | Staging usa datos UAT clasificados, ensaya clean start/opening state y no presenta seeds como historia productiva. |
| `ZM-FIN-119` | UAT incluye opening state, Superadministrador inicial, operaciones abiertas, mappings, rechazo de ambigüedad y reconciliación completa. |
| `ZM-FIN-121` | Preparar master data aprobada, conteo físico, opening economic state, Superadministrador inicial y tratamiento firmado de operaciones abiertas; no migrar historia demo/test. |
| `ZM-FIN-122` | Cutover inicia historia productiva limpia; ejecuta cargas/opening state idempotentes, reconcilia excepciones y conserva rollback/runbook y evidencia firmada. |
| `ZM-FIN-123` | Reconciliación diaria parte del opening state aprobado, conserva causalidad/mappings y nunca normaliza discrepancias o datos demo como reales. |

Tareas con menciones generales a legacy, backfill, migration, opening balance, seed, fixtures, initial admin, production data load, cutover o reconciliation heredan los mismos invariantes aunque no se repitan en su prompt.

#### Gates y estado

DEC-19 modifica la evidencia futura de G0, G3, G5, G6, G7, G8 y G9 conforme a sus filas canónicas. Ninguno queda cumplido por esta sincronización documental.

Se registra `DEC19_PLAN_ALIGNMENT=true`, `DEC19_CLEAN_OPERATIONAL_START=true`, `DEC19_HYBRID_SELECTIVE_POLICY=true`, `DEC19_OPENING_STATE_AUDITABLE=true`, `DEC19_INITIAL_GLOBAL_SUPERADMIN_ONLY=true`, `NO_TASK_MARKED_IMPLEMENTED_BY_DEC19=true` y `GATES_NOT_FAKE_COMPLETED=true`.

### 6.3 Sincronización canónica DEC-20

DEC-20 cierra documentalmente las decisiones bloqueantes de ZM-FIN-003 y añade requisitos futuros a piloto, estabilización y rollout. No implementa tareas, no satisface gates y no inicia ZM-FIN-004.

Invariantes aprobados:

- `actual_pilot_site=Sucursal Matriz`, `pilot_branch_count=1`, `20-SITE-A`;
- Sucursal Matriz no se infiere del seed `MAIN` y debe tener identidad productiva explícita;
- `20-DUR-C`, mínimo `TWO_COMPLETE_WEEKLY_OPERATIONAL_CYCLES`, cobertura obligatoria y extensión automática por evidencia faltante;
- `20-STOP-B`, con stop por impacto y alert severity separada de defect severity;
- cualquier operador puede solicitar pausa; supervisor o Incident Commander pueden ejecutar stop; reanudación crítica y expansión requieren autoridad técnica y administrativa;
- `pilot_initial_outage_policy=STOP_ONLY` hasta validar formalmente la contingencia manual;
- `20-ROL-B`, inicialmente una sucursal por oleada, con pausa del rollout ante incidente material;
- `20-REL-C`, línea del release aprobado más hotfixes revalidados y sin drift libre por sucursal;
- BBVA integrado es obligatorio para la aceptación final integral después de satisfacer DEC-14 y el gate BBVA/PCI de DEC-16; si no está listo, el piloto final se pospone;
- fiscalidad deriva de DEC-16/ZM-FIN-007 y exige matriz validada para la entidad real;
- clean start, opening state y exclusión de seeds/demo permanecen regidos por DEC-19;
- reconciliación ocurre en cada cierre, diariamente, después de eventos extraordinarios y antes de expansión.

#### Alineación por tarea existente

| Tareas | Criterio DEC-20 obligatorio |
|---|---|
| `ZM-FIN-003` | DEC-01–20 tienen propietario, estado aprobado y reglas trazables; sus criterios documentales están satisfechos y queda lista para cierre sin iniciar ZM-FIN-004. |
| `ZM-FIN-007` | Matriz fiscal validada para la entidad real de Sucursal Matriz antes de G7/G8; los blockers aplicables se satisfacen antes del cutover. |
| `ZM-FIN-046`, `065` | BBVA/provider boundary, hardware, PCI, idempotencia, `UNKNOWN`, conciliación y reversas deben pasar sus gates antes del piloto final integral. |
| `ZM-FIN-059`, `105` | Ticket operativo, frontera fiscal, manuales, capacitación observada, stop, contingencia y soporte deben reflejar DEC-20. |
| `ZM-FIN-106`–`116` | Artefactos, LOCAL_FIRST, PostgreSQL, observabilidad, CI/CD, secretos, backup/restore, rollback/DR, hosting, instalación y SLO/runbooks producen evidencia para G7/G8; no se prueban destructivamente en el sitio real. |
| `ZM-FIN-117` | Staging/drill cubre fallos peligrosos, misma versión/semántica, BBVA/fiscal cuando apliquen y evidencia reusable aprobable. |
| `ZM-FIN-118` | Dataset y UAT representan Sucursal Matriz sin usar seed demo como identidad productiva y cubren cadencias, stop y reconciliación. |
| `ZM-FIN-119` | Ensayo integral cubre ciclos, autoridades, stop/resume, contingencia, BBVA gated, fiscalidad y reconciliaciones extraordinarias. |
| `ZM-FIN-120` | Production Ready precede Pilot Ready; valida sitio, duración, stop, gates BBVA/fiscales, dual authority y evidencia sin permitir que piloto sustituya QA. |
| `ZM-FIN-121` | Preparar exclusivamente Sucursal Matriz, una branch, sin mapping implícito con `MAIN`; hardware/LAN/standby/opening state/scopes/backup/soporte. |
| `ZM-FIN-122` | Capacitación observada y firmada, cutover firmado, stop-only inicial, rollback, reanudación crítica dual y BBVA sólo con gates completos. |
| `ZM-FIN-123` | Reconciliar cada cierre, diariamente y después de incidente/hotfix/restore/failover/contingencia/correctivo; preservar alertas e incidentes. |
| `ZM-FIN-124` | Dos ciclos semanales completos, cobertura obligatoria, extensión automática, taxonomía stop, cero blockers y doble aprobación de expansión. |
| `ZM-FIN-125` | Una sucursal por oleada, línea de release controlada, pausa ante incidente material, aislamiento y aprobación antes de avanzar. |
| `ZM-FIN-126` | Handover, capacidad de soporte, reconciliación, versiones, runbooks, ownership y evidencia por sucursal. |

#### Gates y cierre

G8 y G9 incorporan DEC-20 conforme a sus filas canónicas. Ninguno queda cumplido por esta sincronización documental.

El Plan Maestro no contiene una convención explícita de estado de tarea; no se inventa un campo. Se registra `ZM_FIN_003_ACCEPTANCE_CRITERIA_SATISFIED=true`, `ZM_FIN_003_READY_TO_CLOSE=true`, `ZM_FIN_004_NOT_ADVANCED=true`, `ZM_FIN_117_126_ALIGNED_DEC20=true`, `ZM_FIN_121_MATRIZ=true`, `ZM_FIN_124_TWO_CYCLES=true`, `ZM_FIN_125_ONE_BRANCH_WAVE=true`, `NO_TASK_IMPLEMENTED_BY_DEC20_DOC_CHANGE=true` y `GATES_NOT_FAKE_COMPLETED=true`.

## 7. Orden exacto y razón de la secuencia

1. **Preservar antes de cambiar.** Sin commit canónico y pruebas seguras, cualquier resultado puede corresponder a otro producto o destruir datos.
2. **Decidir antes de codificar.** Stock, cierre, devolución, descuentos, sesión, offline y requisitos externos alteran esquema y contratos; implementarlos sin decisión provoca retrabajo o datos incompatibles.
3. **Cerrar acceso antes de ampliar funciones.** Añadir módulos sobre un Backoffice sin RBAC/scopes aumenta la superficie vulnerable.
4. **Cerrar idempotencia/concurrencia antes de ledgers.** Integrar inventario/caja sin replay seguro puede duplicar movimientos y volver más difícil corregir historia.
5. **Construir ledgers antes de reportes/dashboard/analítica.** Las visualizaciones sólo son confiables si derivan de fuentes canónicas reconciliadas.
6. **Completar verticales antes de hardening final.** Feature Complete debe existir antes de congelar E2E, performance, documentación y release candidate.
7. **Construir operación productiva antes del piloto.** Staging, restore, rollback, observabilidad y hardware son parte del producto, no anexos.
8. **Pilotear antes de expandir.** La producción general se aprueba sólo después de observar procesos reales y cerrar discrepancias con evidencia.
## 8. Fases, épicas, validación y gate de avance
### Fase 0 — Gobierno, alcance y línea base

**Objetivo:** Fijar la fuente de verdad, el alcance, las decisiones y una base de datos/pruebas reproducible antes de modificar funcionalidad.<br>
**Épicas:** Gobierno y reproducibilidad; decisiones de producto/dominio; migraciones; requisitos externos.<br>
**Tareas:** ZM-FIN-001 a ZM-FIN-007.<br>
**Validación de fase:** Estado Git inmutable durante inventario; toolchain reproducible; DB de pruebas protegida; fresh install/upgrade de esquema; decisiones y alcance aprobados.<br>
**Gate de avance:** Baseline Ready: existe commit canónico, DB de pruebas segura, cadena de migraciones validada y ninguna decisión P0 queda implícita.

### Fase 1 — Arquitectura, contratos y línea base de calidad

**Objetivo:** Conocer el comportamiento real del sistema y hacer obligatorias las validaciones de fundación.<br>
**Épicas:** Mapa funcional; OpenAPI; calidad API/worker/frontends; CI.<br>
**Tareas:** ZM-FIN-008 a ZM-FIN-014.<br>
**Validación de fase:** Rutas clasificadas; contratos sin drift; lint/typecheck/tests/builds ejecutados; CI verde desde checkout limpio.<br>
**Gate de avance:** Engineering Foundation Ready: cualquier cambio posterior puede validarse de manera aislada y reproducible.

### Fase 2 — Seguridad, identidad, autorización y scopes

**Objetivo:** Cerrar acceso administrativo, aislamiento por sucursal, ciclo de sesión y configuración productiva.<br>
**Épicas:** RBAC; branch scopes; sesiones; identidad; hardening; secretos.<br>
**Tareas:** ZM-FIN-015 a ZM-FIN-027.<br>
**Validación de fase:** Matriz 401/403/2xx; no fuga cross-branch; query token eliminado; revocación/login protegidos; producción falla cerrada; secretos rotables.<br>
**Gate de avance:** Security Foundation Ready: ninguna capacidad administrativa depende del frontend y ningún despliegue inseguro puede arrancar.

### Fase 3 — Idempotencia, concurrencia y límites transaccionales

**Objetivo:** Garantizar un único efecto útil, serialización de comandos incompatibles y transacciones completas.<br>
**Épicas:** Store idempotente; adopción por comando; locks; commits/rollbacks; correlación.<br>
**Tareas:** ZM-FIN-028 a ZM-FIN-040.<br>
**Validación de fase:** Replays y carreras deterministas; cero duplicados; venta/pagos no quedan fuera de cierre; audit/outbox comparten contexto.<br>
**Gate de avance:** Transaction Integrity Ready: los comandos críticos toleran retry, timeout y concurrencia sin estados imposibles.

### Fase 4 — Ledgers canónicos y Data Integrity

**Objetivo:** Unificar dinero, caja, inventario, producción y correcciones como fuentes reconstruibles y reconciliables.<br>
**Épicas:** Ledger financiero; cierre; pagos externos; ledger de inventario; backfills.<br>
**Tareas:** ZM-FIN-041 a ZM-FIN-055.<br>
**Validación de fase:** Ecuaciones de caja; suma de movimientos=balance; pedidos/mixed payments corregidos; rebuild/backfills secos y auditables.<br>
**Gate de avance:** Data Integrity Ready: todo efecto económico/físico habilitado tiene una causa, una sola contabilización y una reconciliación reproducible.

### Fase 5 — POS Feature Complete

**Objetivo:** Completar la operación diaria del cajero, hardware, conectividad y experiencia física.<br>
**Épicas:** Venta; pagos; pedidos; tickets; caja; logística; devoluciones; hardware; continuidad; UX.<br>
**Tareas:** ZM-FIN-056 a ZM-FIN-067.<br>
**Validación de fase:** E2E real del ciclo diario; impresión/terminal/reconexión; flujos inversos; accesibilidad y dispositivos objetivo.<br>
**Gate de avance:** POS Feature Complete: el POS cubre todos los procesos aprobados sin mocks, placeholders ni reglas críticas locales.

### Fase 6 — Backoffice y módulos de negocio Feature Complete

**Objetivo:** Finalizar administración, catálogo, precios, producción, compras, inventario, calidad, reportes y multi-sucursal.<br>
**Épicas:** Catálogo; recetas; producción; pricing; compras; inventario; administración; dashboard; reportes; auditoría; configuración.<br>
**Tareas:** ZM-FIN-068 a ZM-FIN-086.<br>
**Validación de fase:** Cada ruta productiva consume API real, funciona desde estado vacío, respeta RBAC/scope y persiste/reconcilia.<br>
**Gate de avance:** Feature Complete: no existen módulos simulados o funciones aprobadas parcialmente implementadas.

### Fase 7 — Worker, outbox, alertas, notificaciones y eventos

**Objetivo:** Volver confiables los procesos asíncronos y preparar alertas/comunicaciones/analítica.<br>
**Épicas:** Outbox; handlers; worker ops; scheduler; alertas; notificaciones; eventos versionados.<br>
**Tareas:** ZM-FIN-087 a ZM-FIN-093.<br>
**Validación de fase:** Dos workers; claim/lease; retries/backoff/DLQ; backlog/oldest age/throughput/latency; alerta real A/B/C; Telegram fake/sandbox; replay y rebuild determinista de proyecciones sin pérdida/duplicación.<br>
**Gate de avance:** Async Ready: el backlog converge, replay/consumidores son idempotentes, analytics no pierde ni duplica efectos y toda degradación es visible y recuperable.

### Fase 8 — QA, seguridad, rendimiento y documentación

**Objetivo:** Convertir las garantías implementadas en evidencia automatizada y operable.<br>
**Épicas:** Unit/integration/E2E; seguridad; rendimiento; hardware/a11y; documentación técnica/operativa.<br>
**Tareas:** ZM-FIN-094 a ZM-FIN-105.<br>
**Validación de fase:** Suites completas; fórmulas KPI críticas; data quality; correlation/causation; rebuilds deterministas; scans; load/hardware; UAT-ready docs; evidencia por requisito.<br>
**Gate de avance:** QA Ready: Development Complete, Feature Complete, Data Integrity Ready y Security Ready están respaldados por pruebas reproducibles, incluida la semántica DEC-18 aplicable.

### Fase 9 — Plataforma de producción, despliegue y recuperación

**Objetivo:** Construir la plataforma LOCAL_FIRST inmutable, observable, segura y recuperable de DEC-17, con cloud/off-site complementario.<br>
**Épicas:** Artefactos; infraestructura local reproducible; PostgreSQL autoritativo; standby controlado; observabilidad; CI/CD; secretos; backup off-site/DR; frontend/POS delivery; SRE.<br>
**Tareas:** ZM-FIN-106 a ZM-FIN-116.<br>
**Validación de fase:** Fresh provision local; release manifest; migration; probes; operación LAN sin Internet; standby; restore/failover con RPO/RTO observado; alert dashboard; Telegram crítico con retry no bloqueante; rollback; install/update; incident drills.<br>
**Gate de avance:** Production Ready: el mismo artefacto probado se despliega, observa y recupera en la topología LOCAL_FIRST, con responsables claros y sin depender de Telegram o cloud como autoridad de tienda.

### Fase 10 — Staging, piloto, estabilización y producción general

**Objetivo:** Validar el sistema completo en staging, pilotearlo en Sucursal Matriz (SITE-A) y después expandirlo de forma controlada.<br>
**Épicas:** Staging; UAT; gates; sitio piloto; cutover; reconciliación; estabilización; rollout; handover.<br>
**Tareas:** ZM-FIN-117 a ZM-FIN-126.<br>
**Validación de fase:** UAT integral; gate review; Sucursal Matriz/hardware/datos; dashboards KPI selectivos; alerting conservador; dos ciclos operativos semanales completos con cobertura obligatoria; reconciliación al cierre, diaria, extraordinaria y previa a expansión; política STOP-B; cero bloqueos; rollout de una sucursal por ola con línea de release controlada.<br>
**Gate de avance:** General Production: piloto en Sucursal Matriz estabilizado durante dos ciclos operativos semanales completos, cobertura obligatoria observada, reconciliaciones limpias, cero defectos `CRITICAL`, blockers `HIGH` o alertas `CRITICAL-A` activas sin resolver y doble aprobación para expandir; lakehouse/IA no son requisitos de v1.

## 9. Plan maestro ejecutable y prompts de Codex

## Fase 0 — Gobierno, alcance y línea base — Tareas ejecutables

### ZM-FIN-001 — Fijar la línea base canónica del repositorio

**Épica:** Gobierno y reproducibilidad

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-001 |
| **2. Nombre de la tarea** | Fijar la línea base canónica del repositorio |
| **3. Objetivo** | Asociar el estado que se va a finalizar a un commit y a un inventario reproducible sin perder trabajo existente. |
| **4. Problema que resuelve** | Las auditorías observaron un árbol `main` ampliamente modificado, migraciones y módulos no rastreados y artefactos generados alterados; no existe una entrega atribuible. |
| **5. Hallazgo relacionado** | ZM-REL-015; ZMA-REL-002; ZM-REL-018. |
| **6. Módulos afectados** | Repositorio completo, Git, migraciones, contratos y documentación. |
| **7. Archivos/áreas a inspeccionar** | Raíz del monorepo; `git status`; historial; `apps/api/alembic/versions`; `packages/api-client`; `apps/pos-web`; `apps/backoffice-web`; `.github/workflows`. |
| **8. Dependencias previas** | Ninguna. |
| **9. Cambios a implementar** | Capturar SHA, rama, estado Git, archivos rastreados/no rastreados/eliminados, cadena de migraciones, artefactos generados y procedencia conocida. Proponer agrupaciones revisables sin modificar ni descartar nada. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Perder o normalizar silenciosamente trabajo local; confundir artefactos generados con fuente; basar el plan en un estado distinto al auditado. |
| **13. Posibles regresiones** | No debe producir ninguna regresión porque no se permite modificar el repositorio. |
| **14. Pruebas requeridas** | Comparación de estado Git inicial/final; hashes de archivos relevantes; verificación de cadena `revision/down_revision`; comprobación de que no hubo cambios. |
| **15. Criterios de aceptación** | El propietario puede señalar una revisión canónica; el estado Git posterior es idéntico al inicial; todas las diferencias respecto de las auditorías están documentadas. |
| **16. Definition of Done específica** | El propietario puede señalar una revisión canónica; el estado Git posterior es idéntico al inicial; todas las diferencias respecto de las auditorías están documentadas. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Salida completa de comandos de sólo lectura, SHA de `HEAD`, inventario clasificado y confirmación de cero mutaciones. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-002, ZM-FIN-004, ZM-FIN-006 y todo trabajo posterior. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-001 — Fijar la línea base canónica del repositorio**.

**Objetivo**
Asociar el estado que se va a finalizar a un commit y a un inventario reproducible sin perder trabajo existente.

**Problema y contexto de ZeroMerma**
Las auditorías observaron un árbol `main` ampliamente modificado, migraciones y módulos no rastreados y artefactos generados alterados; no existe una entrega atribuible. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-REL-015; ZMA-REL-002; ZM-REL-018.

**Dependencias que puedes asumir terminadas**
Ninguna.

**Inspección inicial obligatoria**
Inspecciona primero `git rev-parse HEAD`, `git status --short`, `git ls-files`, las migraciones 0001–0039, referencias de pnpm y el cliente OpenAPI.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Capturar SHA, rama, estado Git, archivos rastreados/no rastreados/eliminados, cadena de migraciones, artefactos generados y procedencia conocida. Proponer agrupaciones revisables sin modificar ni descartar nada.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No modificar, formatear, regenerar, hacer commit, branch, stash, restore, clean, checkout ni borrar archivos. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Submódulos, archivos ignorados relevantes, directorios no rastreados expandidos, migraciones duplicadas o múltiples heads.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Comparación de estado Git inicial/final; hashes de archivos relevantes; verificación de cadena `revision/down_revision`; comprobación de que no hubo cambios.

**Validación y comandos**
Usa exclusivamente comandos de lectura de Git y del sistema de archivos. No instales dependencias, no ejecutes pruebas, migraciones ni generación de contratos. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
El propietario puede señalar una revisión canónica; el estado Git posterior es idéntico al inicial; todas las diferencias respecto de las auditorías están documentadas.
Definition of Done específica: El propietario puede señalar una revisión canónica; el estado Git posterior es idéntico al inicial; todas las diferencias respecto de las auditorías están documentadas. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
No crear un documento de control nuevo; entregar el inventario en la respuesta de Codex y señalar qué documento vigente debería actualizarse tras la decisión del propietario.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-002 — Definir el alcance de producto y la política de visibilidad

**Épica:** Gobierno de producto

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-002 |
| **2. Nombre de la tarea** | Definir el alcance de producto y la política de visibilidad |
| **3. Objetivo** | Establecer qué funcionalidades forman parte de ZeroMerma terminado y qué superficies deben quedar implementadas, retiradas u ocultas hasta completarse. |
| **4. Problema que resuelve** | Las auditorías detectaron módulos simulados, funciones inexistentes y capacidades condicionadas por decisiones de negocio; sin una frontera aprobada no existe Feature Complete verificable. |
| **5. Hallazgo relacionado** | ZM-FUNC-013; ZMA-BO-001; elementos no verificables de ambas auditorías. |
| **6. Módulos afectados** | Producto completo, POS, Backoffice, API, worker, hardware e infraestructura. |
| **7. Archivos/áreas a inspeccionar** | Mapas de rutas; navegación POS/Backoffice; documentación funcional; flags o configuración de módulos; endpoints registrados. |
| **8. Dependencias previas** | ZM-FIN-001. |
| **9. Cambios a implementar** | Construir una matriz módulo→capacidad→estado real→requisito de lanzamiento→política de visibilidad. Registrar en el documento de decisiones vigente qué se implementa y qué no puede presentarse como funcional. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Declarar terminado un módulo sólo porque existe una pantalla o ruta; ocultar una dependencia operativa crítica. |
| **13. Posibles regresiones** | Ocultar accidentalmente funciones ya aprobadas o romper enlaces directos y permisos. |
| **14. Pruebas requeridas** | Revisión cruzada de cada ruta con endpoint, persistencia y prueba; validación de que ninguna ruta marcada disponible depende de datos simulados. |
| **15. Criterios de aceptación** | Todas las superficies tienen estado aprobado: incluida, excluida explícitamente o bloqueada por decisión; una función excluida no aparece como operativa en producción. |
| **16. Definition of Done específica** | Todas las superficies tienen estado aprobado: incluida, excluida explícitamente o bloqueada por decisión; una función excluida no aparece como operativa en producción. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Matriz aprobada por el propietario y lista de rutas/flags afectadas; contradicciones pendientes claramente separadas. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-008 y la priorización funcional de Fases 5–7. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-002 — Definir el alcance de producto y la política de visibilidad**.

**Objetivo**
Establecer qué funcionalidades forman parte de ZeroMerma terminado y qué superficies deben quedar implementadas, retiradas u ocultas hasta completarse.

**Problema y contexto de ZeroMerma**
Las auditorías detectaron módulos simulados, funciones inexistentes y capacidades condicionadas por decisiones de negocio; sin una frontera aprobada no existe Feature Complete verificable. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-FUNC-013; ZMA-BO-001; elementos no verificables de ambas auditorías.

**Dependencias que puedes asumir terminadas**
ZM-FIN-001.

**Inspección inicial obligatoria**
Inspecciona la navegación, las rutas registradas, `AdminModulePage`, `useAdminModuleRecords`, `adminData.ts`, módulos POS y documentación funcional existente.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Construir una matriz módulo→capacidad→estado real→requisito de lanzamiento→política de visibilidad. Registrar en el documento de decisiones vigente qué se implementa y qué no puede presentarse como funcional.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No completar módulos ni refactorizar navegación en esta tarea; sólo clasificar y registrar decisiones aprobadas. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Rutas profundas, acceso por URL directa, módulos sólo lectura, funciones disponibles sólo en una sucursal o rol, hardware no conectado.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Revisión cruzada de cada ruta con endpoint, persistencia y prueba; validación de que ninguna ruta marcada disponible depende de datos simulados.

**Validación y comandos**
Ejecuta búsquedas estáticas y, si la línea base ya es segura, pruebas de rutas sin mutaciones. No implementes todavía funcionalidades faltantes. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Todas las superficies tienen estado aprobado: incluida, excluida explícitamente o bloqueada por decisión; una función excluida no aparece como operativa en producción.
Definition of Done específica: Todas las superficies tienen estado aprobado: incluida, excluida explícitamente o bloqueada por decisión; una función excluida no aparece como operativa en producción. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar únicamente el plan maestro vigente y el documento único de decisiones; no crear un segundo roadmap.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-003 — Cerrar y registrar invariantes de negocio pendientes

**Épica:** Decisiones de dominio
**Alineación canónica DEC-17–DEC-20 — criterio adicional obligatorio:** las veinte decisiones están aprobadas documentalmente; LOCAL_FIRST, KPI, clean start y piloto/rollout quedan trazados; append-only transversal no se presume y ninguna aprobación equivale a implementación.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-003 |
| **2. Nombre de la tarea** | Cerrar y registrar invariantes de negocio pendientes |
| **3. Objetivo** | Convertir las reglas ambiguas que afectan dinero, inventario, producción y operación multi-sucursal en decisiones aprobadas y comprobables. |
| **4. Problema que resuelve** | DEC-01–DEC-20 están aprobadas y trazadas; el cierre documental debe reconocer que ya no quedan decisiones bloqueantes sin convertir esa aprobación en implementación ni iniciar ZM-FIN-004. |
| **5. Hallazgo relacionado** | ZMA-WASTE-001; ZMA-FIN-001; ZMA-REP-001; ZMA-PROD-001; ZMA-CAT-001; reglas indefinidas de la auditoría activa. |
| **6. Módulos afectados** | Ventas, pedidos, caja, inventario, producción, descuentos, identidad, multi-sucursal, hardware y continuidad. |
| **7. Archivos/áreas a inspeccionar** | Documento de decisiones vigente; modelos y enums de dominio; servicios de venta/cierre/inventario/producción; contratos de UI. |
| **8. Dependencias previas** | ZM-FIN-001 y participación del propietario. |
| **9. Cambios a implementar** | Preservar DEC-01–DEC-20, verificar propietario/estado/regla/ejemplos/tareas afectadas y registrar que los criterios documentales están satisfechos; cerrar exclusivamente el trabajo de gobierno, sin implementar tareas posteriores. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Tomar decisiones técnicas que en realidad corresponden al negocio; aprobar reglas incompatibles entre caja e inventario. |
| **13. Posibles regresiones** | Cambiar una regla ya utilizada por datos existentes sin plan de migración o compensación. |
| **14. Pruebas requeridas** | Revisión de escenarios límite por dominio; ejemplos numéricos de caja/inventario; consistencia entre decisiones relacionadas. |
| **15. Criterios de aceptación** | DEC-01–DEC-20 tienen propietario, estado aprobado, regla inequívoca, ejemplos y tareas afectadas; no quedan supuestos silenciosos P0/P1; `ZM_FIN_003_ACCEPTANCE_CRITERIA_SATISFIED=true` y `ZM_FIN_003_READY_TO_CLOSE=true`, sin iniciar ZM-FIN-004. |
| **16. Definition of Done específica** | Cada decisión bloqueante tiene propietario, estado aprobado, regla inequívoca, ejemplos y tareas afectadas; no quedan supuestos silenciosos en P0/P1. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Documento único con 20 decisiones aprobadas, IDs estables, trazabilidad a tareas, Plan Maestro alineado y controles `ZM_FIN_003_ACCEPTANCE_CRITERIA_SATISFIED=true` / `ZM_FIN_003_READY_TO_CLOSE=true`. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-019, ZM-FIN-024, ZM-FIN-038, ZM-FIN-045 y módulos funcionales. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-003 — Cerrar y registrar invariantes de negocio pendientes**.

**Objetivo**
Convertir las reglas ambiguas que afectan dinero, inventario, producción y operación multi-sucursal en decisiones aprobadas y comprobables.

**Problema y contexto de ZeroMerma**
Las auditorías no definen stock negativo, momento de afectación de inventario, merma, liquidación de pedidos, pago mixto, cierre concurrente, descuentos, producción cancelada, offline y scopes. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-WASTE-001; ZMA-FIN-001; ZMA-REP-001; ZMA-PROD-001; ZMA-CAT-001; reglas indefinidas de la auditoría activa.

**Dependencias que puedes asumir terminadas**
ZM-FIN-001 y participación del propietario.

**Inspección inicial obligatoria**
Localiza todas las reglas pendientes listadas en ambas auditorías y contrástalas con enums, estados, restricciones y documentación del repositorio.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Preparar alternativas técnicas con impactos; obtener decisión del propietario; registrar reglas, ejemplos, excepciones y pruebas que las harán obligatorias.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No implementar reglas antes de su aprobación; no crear documentos paralelos de decisión. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Operación sin conteo, pago mixto, devolución a vendible/merma/cuarentena, stock negativo, recepción parcial, cierre concurrente, sucursal global y desconexión.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Revisión de escenarios límite por dominio; ejemplos numéricos de caja/inventario; consistencia entre decisiones relacionadas.

**Validación y comandos**
No ejecutar cambios de código. Puede ejecutar búsquedas y consultas de sólo lectura para ilustrar el estado actual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada decisión bloqueante tiene propietario, estado aprobado, regla inequívoca, ejemplos y tareas afectadas; no quedan supuestos silenciosos en P0/P1.
Definition of Done específica: Cada decisión bloqueante tiene propietario, estado aprobado, regla inequívoca, ejemplos y tareas afectadas; no quedan supuestos silenciosos en P0/P1. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar el documento único de decisiones; cada decisión debe citar hallazgo, módulos y pruebas futuras.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-004 — Unificar toolchain e instalación determinista

**Épica:** Reproducibilidad

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-004 |
| **2. Nombre de la tarea** | Unificar toolchain e instalación determinista |
| **3. Objetivo** | Conseguir que un checkout limpio instale las mismas versiones y produzca el mismo árbol de dependencias. |
| **4. Problema que resuelve** | README/CI y `packageManager` declaran versiones distintas de pnpm; el estado auditado depende de herramientas no uniformes. |
| **5. Hallazgo relacionado** | ZM-REL-018; ZMA-REL-002. |
| **6. Módulos afectados** | Monorepo, Python, Node, pnpm, lockfiles, scripts y CI. |
| **7. Archivos/áreas a inspeccionar** | `package.json`; lockfiles; README; scripts; `.github/workflows/foundation.yml`; configuración de `uv`/Python. |
| **8. Dependencias previas** | ZM-FIN-001 y decisión de versión canónica. |
| **9. Cambios a implementar** | Fijar versiones canónicas; alinear documentación, CI y preflight; impedir instalaciones con versiones no compatibles; validar lockfiles sin actualización funcional; separar bootstrap necesario de datos demo y no depender de una DB sembrada para una instalación productiva. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Actualizar dependencias de forma accidental o invalidar el lockfile sin necesidad. |
| **13. Posibles regresiones** | Incompatibilidad con desarrolladores/CI existentes y cambios de resolución transitoria. |
| **14. Pruebas requeridas** | Instalación desde checkout limpio con `--frozen-lockfile`; `uv sync`; verificación de versión; build sin diff de lockfiles. |
| **15. Criterios de aceptación** | Todos los puntos de entrada usan una sola versión; instalación limpia no modifica archivos, falla con toolchain incompatible y no presenta seeds/demo como configuración o historia productiva. |
| **16. Definition of Done específica** | Todos los puntos de entrada usan una sola versión; instalación limpia no modifica archivos y falla con toolchain incompatible. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Logs de instalación limpia, versiones exactas y `git status` sin cambios. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-009, ZM-FIN-010, ZM-FIN-014 y producción de artefactos. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-004 — Unificar toolchain e instalación determinista**.

**Objetivo**
Conseguir que un checkout limpio instale las mismas versiones y produzca el mismo árbol de dependencias.

**Problema y contexto de ZeroMerma**
README/CI y `packageManager` declaran versiones distintas de pnpm; el estado auditado depende de herramientas no uniformes. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-REL-018; ZMA-REL-002.

**Dependencias que puedes asumir terminadas**
ZM-FIN-001 y decisión de versión canónica.

**Inspección inicial obligatoria**
Inspecciona todas las referencias de Python, Node, pnpm, corepack y comandos de instalación antes de editar.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Fijar versiones canónicas; alinear documentación, CI y preflight; impedir instalaciones con versiones no compatibles; validar lockfiles sin actualización funcional.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No realizar actualización general de dependencias ni cambiar framework o package manager. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
CI Windows frente a Linux, Corepack deshabilitado, lockfile creado por otra versión, cachés previas.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Instalación desde checkout limpio con `--frozen-lockfile`; `uv sync`; verificación de versión; build sin diff de lockfiles.

**Validación y comandos**
Ejecuta versiones, instalación congelada y builds mínimos desde un entorno limpio; no actualices paquetes salvo que sea estrictamente necesario y justificado. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Todos los puntos de entrada usan una sola versión; instalación limpia no modifica archivos y falla con toolchain incompatible.
Definition of Done específica: Todos los puntos de entrada usan una sola versión; instalación limpia no modifica archivos y falla con toolchain incompatible. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar README y scripts canónicos de instalación/preflight.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-005 — Proteger y aislar la base de datos de pruebas

**Épica:** Seguridad de pruebas

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-005 |
| **2. Nombre de la tarea** | Proteger y aislar la base de datos de pruebas |
| **3. Objetivo** | Hacer imposible que pytest migre o trunque una base no autorizada y proporcionar PostgreSQL efímero para validaciones destructivas. |
| **4. Problema que resuelve** | La fixture backend usa la configuración efectiva y ejecuta migraciones/TRUNCATE sin una guarda inequívoca. |
| **5. Hallazgo relacionado** | ZM-QA-010; ZMA-QA-001. |
| **6. Módulos afectados** | API tests, configuración, CI y PostgreSQL de pruebas. |
| **7. Archivos/áreas a inspeccionar** | `apps/api/tests/conftest.py`; settings/engine/session; scripts de test; CI; `infra/docker` o equivalente efímero. |
| **8. Dependencias previas** | ZM-FIN-001 y convención aprobada de base de pruebas. |
| **9. Cambios a implementar** | Añadir guardas fail-fast por ambiente, host, base, identidad de dataset y confirmación explícita antes del primer SQL; crear credenciales y servicio efímero aislado; impedir targets operacionales, staging real y producción; probar allow/deny. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Una guarda basada sólo en el nombre puede ser eludida; credenciales de producción disponibles en CI. |
| **13. Posibles regresiones** | Bloquear legítimamente el entorno local de pruebas o dejar recursos efímeros sin limpiar. |
| **14. Pruebas requeridas** | Unitarias de la guarda; integración contra DB efímera; URLs prohibidas sin conexión ni SQL destructivo; inspección de logs. |
| **15. Criterios de aceptación** | Una configuración no reconocida o no demostrablemente `TEST` aborta antes de conectar o ejecutar el primer SQL; CI usa exclusivamente una base efímera identificable y no tiene credenciales/ruta hacia DB operacional, staging real o producción. La clasificación no productiva de un volumen no sustituye estas guardas. |
| **16. Definition of Done específica** | Una configuración no reconocida aborta antes de migrar/truncar; CI usa exclusivamente una base efímera identificable y sin acceso a datos operativos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas allow/deny, URL efectiva anonimizada, logs de creación/destrucción del entorno y confirmación de cero acceso a otras bases. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-006, ZM-FIN-010–014 y todas las pruebas transaccionales. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-005 — Proteger y aislar la base de datos de pruebas**.

**Objetivo**
Hacer imposible que pytest migre o trunque una base no autorizada y proporcionar PostgreSQL efímero para validaciones destructivas.

**Problema y contexto de ZeroMerma**
La fixture backend usa la configuración efectiva y ejecuta migraciones/TRUNCATE sin una guarda inequívoca. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-QA-010; ZMA-QA-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-001 y convención aprobada de base de pruebas.

**Inspección inicial obligatoria**
Inspecciona la fixture, orden exacto de conexión/migración/TRUNCATE, settings y secretos disponibles en CI.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Añadir guardas fail-fast por ambiente, host, base y confirmación explícita antes del primer SQL; crear credenciales y servicio efímero aislado; probar allow/deny.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No reescribir toda la fixture ni ejecutar pytest contra la configuración actual antes de verificar la guarda. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Host remoto, nombre engañoso, variable ausente, URL con parámetros, conexión a proxy, ejecución local y CI paralela.

**Concurrencia y consistencia**
Probar ejecuciones paralelas de suites para evitar compartir la misma base o esquema.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Unitarias de la guarda; integración contra DB efímera; URLs prohibidas sin conexión ni SQL destructivo; inspección de logs.

**Validación y comandos**
Ejecuta primero sólo pruebas unitarias de la guarda. Después crea PostgreSQL efímero y ejecuta una prueba de integración controlada. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Una configuración no reconocida aborta antes de migrar/truncar; CI usa exclusivamente una base efímera identificable y sin acceso a datos operativos.
Definition of Done específica: Una configuración no reconocida aborta antes de migrar/truncar; CI usa exclusivamente una base efímera identificable y sin acceso a datos operativos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Documentar la convención de DB de pruebas y los comandos seguros.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-006 — Validar la cadena de migraciones y la línea base de esquema

**Épica:** Esquema y migraciones

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-006 |
| **2. Nombre de la tarea** | Validar la cadena de migraciones y la línea base de esquema |
| **3. Objetivo** | Demostrar que una base vacía y una base en cada versión soportada pueden llegar al esquema objetivo de forma reproducible. |
| **4. Problema que resuelve** | La cadena 0001–0039 parece lineal, pero instalación limpia, upgrade, compatibilidad y restauración no fueron probados. Los dos volúmenes conocidos fueron clasificados por el propietario como no productivos y no constituyen una baseline empresarial. |
| **5. Hallazgo relacionado** | ZM-REL-015; ZM-OPS-014; elementos no verificables de migraciones. |
| **6. Módulos afectados** | Alembic, modelos SQLAlchemy, PostgreSQL, CI y release. |
| **7. Archivos/áreas a inspeccionar** | `apps/api/alembic.ini`; `apps/api/alembic/versions`; modelos; scripts; bootstrap/seed; metadatos de DB. |
| **8. Dependencias previas** | ZM-FIN-001, ZM-FIN-004 y ZM-FIN-005. |
| **9. Cambios a implementar** | Versionar todas las migraciones válidas; comprobar un solo head; ejecutar upgrade desde DB vacía y snapshots/datasets representativos; detectar drift modelo/esquema; documentar expand-contract; demostrar preservación mediante datos sintéticos controlados sin tratar volúmenes demo/test como historia productiva. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Migraciones locales no validadas, locks prolongados, pérdida de datos en downgrade o backfill. |
| **13. Posibles regresiones** | Bases existentes incompatibles, seeds rotos o modelos que asumen columnas nuevas antes de tiempo. |
| **14. Pruebas requeridas** | Alembic upgrade head en DB vacía; upgrade desde snapshots soportados; inspección de constraints/indexes; test de datos preservados; downgrade sólo donde sea seguro y aprobado. |
| **15. Criterios de aceptación** | La cadena canónica está rastreada, tiene un head autorizado, fresh install y upgrades representativos preservan datos/mappings y no dejan drift; ninguna prueba exige conservar demo/test como negocio ni toca una DB real. |
| **16. Definition of Done específica** | La cadena canónica está rastreada, tiene un head autorizado, fresh install y upgrades preservan datos y no dejan drift. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Logs de Alembic, revisión antes/después, comparación de esquema y resultados de reconciliación de datos de prueba. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Todas las tareas con migración y ZM-FIN-088. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-006 — Validar la cadena de migraciones y la línea base de esquema**.

**Objetivo**
Demostrar que una base vacía y una base en cada versión soportada pueden llegar al esquema objetivo de forma reproducible.

**Problema y contexto de ZeroMerma**
La cadena 0001–0039 parecía lineal y la base activa estaba en head, pero instalación limpia, upgrade, compatibilidad y restauración no fueron probados. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-REL-015; ZM-OPS-014; elementos no verificables de migraciones.

**Dependencias que puedes asumir terminadas**
ZM-FIN-001, ZM-FIN-004 y ZM-FIN-005.

**Inspección inicial obligatoria**
Inspecciona cada `revision/down_revision`, operaciones destructivas, defaults, índices y cualquier migración no rastreada.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Versionar todas las migraciones válidas; comprobar un solo head; ejecutar upgrade desde cero y desde versiones soportadas; detectar drift modelo/esquema; documentar estrategia expand-contract.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No reescribir el historial de migraciones aplicado sin una justificación y estrategia explícitas. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
DB vacía, DB en una revisión intermedia, datos con valores nulos/duplicados, dos heads, migración interrumpida.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Alembic upgrade head en DB vacía; upgrade desde snapshots soportados; inspección de constraints/indexes; test de datos preservados; downgrade sólo donde sea seguro y aprobado.

**Validación y comandos**
Usa Alembic contra bases efímeras protegidas; ejecuta inspección de esquema y pruebas de preservación. No tocar bases operativas. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
La cadena canónica está rastreada, tiene un head autorizado, fresh install y upgrades preservan datos y no dejan drift.
Definition of Done específica: La cadena canónica está rastreada, tiene un head autorizado, fresh install y upgrades preservan datos y no dejan drift. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Crear/actualizar el runbook de migraciones y compatibilidad de versiones.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-007 — Definir requisitos fiscales, regulatorios, privacidad y retención

**Épica:** Requisitos externos
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: preservar LOCAL_FIRST, contrato KPI/eventos versionado, privacidad/retención y separación entre decisión e implementación.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-007 |
| **2. Nombre de la tarea** | Definir requisitos fiscales, regulatorios, privacidad y retención |
| **3. Objetivo** | Evitar que el producto sea declarado completo sin conocer obligaciones externas que afecten tickets, pagos, auditoría, datos personales y conservación. |
| **4. Problema que resuelve** | Las auditorías no verificaron requisitos fiscales, regulatorios o de privacidad; el alcance productivo los necesita como decisión de negocio/jurisdicción. |
| **5. Hallazgo relacionado** | Brecha profesional no cubierta por auditoría; riesgos residuales regulatorios. |
| **6. Módulos afectados** | Tickets, pagos, usuarios, auditoría, reportes, exportaciones, backups y datos personales. |
| **7. Archivos/áreas a inspeccionar** | Documentación de producto; modelos de identidad/venta/ticket/auditoría; exportaciones; configuración de retención. |
| **8. Dependencias previas** | ZM-FIN-002 y participación del propietario/asesoría competente. |
| **9. Cambios a implementar** | Inventariar datos/documentos y requisitos aplicables; validar para la entidad real de Sucursal Matriz la matriz `obligation -> module -> control -> evidence`; registrar numeración, ticket/CFDI/FiscalAdapter, retención, acceso, eliminación, exportación y blockers previos a G7/G8. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Asumir requisitos de una jurisdicción incorrecta o convertir asesoría técnica en asesoría legal. |
| **13. Posibles regresiones** | Cambios posteriores de numeración, retención o contenido de ticket que invaliden datos históricos. |
| **14. Pruebas requeridas** | Revisión de flujos y campos contra requisitos aprobados; pruebas de retención/exportación/redacción definidas, sin asumir una jurisdicción. |
| **15. Criterios de aceptación** | Existe matriz aprobada para la entidad de Sucursal Matriz; todo requisito fiscal blocker está satisfecho antes de cutover; ticket operativo, CFDI y comprobante del proveedor permanecen separados; cualquier requisito fuera de alcance tiene aceptación explícita. |
| **16. Definition of Done específica** | Existe una matriz aprobada de obligación→módulo→control→evidencia; cualquier requisito fuera de alcance tiene aceptación explícita del propietario. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Matriz aprobada, responsables y tareas derivadas; no se incluyen afirmaciones legales no verificadas. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-054, ZM-FIN-071, ZM-FIN-085 y Gate Production Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-007 — Definir requisitos fiscales, regulatorios, privacidad y retención**.

**Objetivo**
Evitar que el producto sea declarado completo sin conocer obligaciones externas que afecten tickets, pagos, auditoría, datos personales y conservación.

**Problema y contexto de ZeroMerma**
Las auditorías no verificaron requisitos fiscales, regulatorios o de privacidad; el alcance productivo los necesita como decisión de negocio/jurisdicción. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Brecha profesional no cubierta por auditoría; riesgos residuales regulatorios.

**Dependencias que puedes asumir terminadas**
ZM-FIN-002 y participación del propietario/asesoría competente.

**Inspección inicial obligatoria**
Inspecciona qué datos personales, económicos y de auditoría se almacenan y qué documentos se generan actualmente.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Inventariar datos y documentos; obtener requisitos aplicables; registrar decisiones de numeración, contenido de ticket, retención, acceso, eliminación, exportación y evidencia.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No emitir conclusiones jurídicas ni implementar obligaciones no aprobadas. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Múltiples sucursales, exportación de datos, borrado vs inmutabilidad, backup con PII, usuarios dados de baja, tickets reimpresos.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Revisión de flujos y campos contra requisitos aprobados; pruebas de retención/exportación/redacción definidas, sin asumir una jurisdicción.

**Validación y comandos**
Sólo análisis y consultas de metadatos; no modificar código hasta que el propietario apruebe los requisitos. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Existe una matriz aprobada de obligación→módulo→control→evidencia; cualquier requisito fuera de alcance tiene aceptación explícita del propietario.
Definition of Done específica: Existe una matriz aprobada de obligación→módulo→control→evidencia; cualquier requisito fuera de alcance tiene aceptación explícita del propietario. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar el documento único de decisiones y el inventario de datos/retención.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```


## Fase 1 — Arquitectura, contratos y línea base de calidad — Tareas ejecutables

### ZM-FIN-008 — Construir la matriz ruta–caso de uso–persistencia–estado real

**Épica:** Arquitectura funcional
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Añadir hecho analítico, envelope/schema, correlation/causation, lineage, atomicidad business/state/audit/outbox, consumidor idempotente y KPI aplicables.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-008 |
| **2. Nombre de la tarea** | Construir la matriz ruta–caso de uso–persistencia–estado real |
| **3. Objetivo** | Disponer de un mapa verificable de qué hace realmente cada ruta y módulo antes de completar el producto. |
| **4. Problema que resuelve** | Las auditorías demostraron que una pantalla o ruta puede ser real, parcial, simulada o desconectada; hay 223 operaciones y múltiples flujos transversales. |
| **5. Hallazgo relacionado** | ZM-FUNC-013; ZMA-BO-001; matriz funcional de ambas auditorías. |
| **6. Módulos afectados** | API, POS, Backoffice, worker y base de datos. |
| **7. Archivos/áreas a inspeccionar** | Registro de routers; rutas TanStack; servicios; modelos; `AdminModulePage`; documentación; outbox handlers. |
| **8. Dependencias previas** | ZM-FIN-001, ZM-FIN-002 y ZM-FIN-006. |
| **9. Cambios a implementar** | Mapear cada operación a autenticación, permiso, scope, servicio, transacción, entidades, auditoría, outbox, UI consumidora, pruebas y estado real. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Crear una matriz manual que quede desfasada o asumir funcionalidad por nombres de archivos. |
| **13. Posibles regresiones** | Ninguna funcional; riesgo documental si el mapa no se automatiza. |
| **14. Pruebas requeridas** | Cobertura automática del registro de rutas; muestreo de persistencia; verificación de que no quedan rutas sin clasificación. |
| **15. Criterios de aceptación** | Todas las rutas productivas tienen dueño, comportamiento, autorización, datos y prueba asignados; placeholders están marcados y fuera del gate Feature Complete. |
| **16. Definition of Done específica** | Todas las rutas productivas tienen dueño, comportamiento, autorización, datos y prueba asignados; placeholders están marcados y fuera del gate Feature Complete. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Matriz versionada dentro del plan o documentación arquitectónica vigente, más script/reporte reproducible de rutas. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-015–020, ZM-FIN-060–077 y Gate Feature Complete. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-008 — Construir la matriz ruta–caso de uso–persistencia–estado real**.

**Objetivo**
Disponer de un mapa verificable de qué hace realmente cada ruta y módulo antes de completar el producto.

**Problema y contexto de ZeroMerma**
Las auditorías demostraron que una pantalla o ruta puede ser real, parcial, simulada o desconectada; hay 223 operaciones y múltiples flujos transversales. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-FUNC-013; ZMA-BO-001; matriz funcional de ambas auditorías.

**Dependencias que puedes asumir terminadas**
ZM-FIN-001, ZM-FIN-002 y ZM-FIN-006.

**Inspección inicial obligatoria**
Inspecciona routers FastAPI registrados, rutas de ambos frontends, servicios de aplicación, modelos y pruebas asociadas.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Mapear cada operación a autenticación, permiso, scope, servicio, transacción, entidades, auditoría, outbox, UI consumidora, pruebas y estado real.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No corregir todavía módulos incompletos ni refactorizar rutas. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Rutas dinámicas, aliases, endpoints internos, acciones sólo por worker, páginas genéricas y módulos de sólo lectura.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Cobertura automática del registro de rutas; muestreo de persistencia; verificación de que no quedan rutas sin clasificación.

**Validación y comandos**
Usa scripts de introspección de rutas y búsquedas estáticas. Puede levantar la app en entorno de pruebas protegido para comparar OpenAPI. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Todas las rutas productivas tienen dueño, comportamiento, autorización, datos y prueba asignados; placeholders están marcados y fuera del gate Feature Complete.
Definition of Done específica: Todas las rutas productivas tienen dueño, comportamiento, autorización, datos y prueba asignados; placeholders están marcados y fuera del gate Feature Complete. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar la documentación de arquitectura funcional; evitar duplicar el plan maestro.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-009 — Normalizar la política API y bloquear deriva OpenAPI/cliente

**Épica:** Contratos
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: preservar LOCAL_FIRST, contrato KPI/eventos versionado, privacidad/retención y separación entre decisión e implementación.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-009 |
| **2. Nombre de la tarea** | Normalizar la política API y bloquear deriva OpenAPI/cliente |
| **3. Objetivo** | Hacer que API, POS y Backoffice compartan contratos reproducibles y errores/paginación coherentes. |
| **4. Problema que resuelve** | La auditoría activa encontró coincidencia del snapshot, pero la estática detectó artefactos locales modificados y riesgo de deriva futura. |
| **5. Hallazgo relacionado** | ZM-REL-018; ZMA-REL-002; contraste OpenAPI activo. |
| **6. Módulos afectados** | API schemas/routers, `packages/api-client`, POS y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | OpenAPI servido; generador de cliente; schemas Pydantic; adapters frontend; scripts `contracts:generate`; CI. |
| **8. Dependencias previas** | ZM-FIN-004, ZM-FIN-006 y ZM-FIN-008. |
| **9. Cambios a implementar** | Definir convenciones de errores, IDs, decimales, paginación, filtros y versionado; regenerar cliente; añadir gate de cero diff y compatibilidad. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Introducir cambios incompatibles o esconder deriva mediante commits manuales del cliente. |
| **13. Posibles regresiones** | Ruptura de tipos/serialización en POS o Backoffice; pérdida de precisión decimal. |
| **14. Pruebas requeridas** | Comparación canónica OpenAPI servido/artefacto; contract tests; compilación de frontends; casos 400/401/403/404/409/422. |
| **15. Criterios de aceptación** | Regenerar contratos desde un checkout limpio no produce diff; cada cambio contractual requerido actualiza cliente y pruebas en la misma tarea. |
| **16. Definition of Done específica** | Regenerar contratos desde un checkout limpio no produce diff; cada cambio contractual requerido actualiza cliente y pruebas en la misma tarea. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | OpenAPI y cliente generados, log de cero diff, catálogo de errores y pruebas contractuales. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Todas las tareas que cambian API y ZM-FIN-014. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-009 — Normalizar la política API y bloquear deriva OpenAPI/cliente**.

**Objetivo**
Hacer que API, POS y Backoffice compartan contratos reproducibles y errores/paginación coherentes.

**Problema y contexto de ZeroMerma**
La auditoría activa encontró coincidencia del snapshot, pero la estática detectó artefactos locales modificados y riesgo de deriva futura. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-REL-018; ZMA-REL-002; contraste OpenAPI activo.

**Dependencias que puedes asumir terminadas**
ZM-FIN-004, ZM-FIN-006 y ZM-FIN-008.

**Inspección inicial obligatoria**
Inspecciona el generador, el OpenAPI actual, schemas de error, tipos locales duplicados y adaptadores manuales.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir convenciones de errores, IDs, decimales, paginación, filtros y versionado; regenerar cliente; añadir gate de cero diff y compatibilidad.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No introducir GraphQL, una API paralela ni tipos de dominio frontend no generados. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Campos opcionales/nulos, decimales como string, enums, paginación vacía, deprecación y endpoints sin response_model.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Comparación canónica OpenAPI servido/artefacto; contract tests; compilación de frontends; casos 400/401/403/404/409/422.

**Validación y comandos**
Ejecuta generación contractual, diff, typecheck y builds de ambos frontends; usa los scripts canónicos del repositorio. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Regenerar contratos desde un checkout limpio no produce diff; cada cambio contractual requerido actualiza cliente y pruebas en la misma tarea.
Definition of Done específica: Regenerar contratos desde un checkout limpio no produce diff; cada cambio contractual requerido actualiza cliente y pruebas en la misma tarea. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar estándar de API y proceso de cambio contractual.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-010 — Establecer la línea base ejecutada de API

**Épica:** Calidad backend

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-010 |
| **2. Nombre de la tarea** | Establecer la línea base ejecutada de API |
| **3. Objetivo** | Conocer y corregir sólo los fallos de compilación, lint, typing, pruebas y seeds que impidan una base backend verde. |
| **4. Problema que resuelve** | La auditoría estática no ejecutó validaciones y la activa evitó la suite por la fixture destructiva; se desconoce el estado real. |
| **5. Hallazgo relacionado** | ZM-QA-011; elementos no verificables de ambas auditorías. |
| **6. Módulos afectados** | API, pruebas, Alembic y bootstrap/seed. |
| **7. Archivos/áreas a inspeccionar** | `apps/api/src`; `apps/api/tests`; `apps/api/unit_tests`; `pyproject.toml`; scripts; seeds. |
| **8. Dependencias previas** | ZM-FIN-004, ZM-FIN-005 y ZM-FIN-006. |
| **9. Cambios a implementar** | Corregir descubrimiento de tests; ejecutar Ruff, mypy y pytest; clasificar fallos; resolver únicamente defectos de fundación sin mezclar funcionalidades. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Convertir esta tarea en una corrección indiscriminada de funcionalidad o relajar reglas para obtener verde. |
| **13. Posibles regresiones** | Cambios en configuración de tests que oculten suites o alteren comportamiento de producción. |
| **14. Pruebas requeridas** | Ruff, mypy estricto, pytest completo, migración/seed en DB efímera y reporte de pruebas excluidas/flaky. |
| **15. Criterios de aceptación** | La suite backend canónica se descubre completa y pasa; cualquier exclusión está justificada y visible en CI. |
| **16. Definition of Done específica** | La suite backend canónica se descubre completa y pasa; cualquier exclusión está justificada y visible en CI. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Logs de comandos, lista de pruebas, fallos corregidos, cobertura estructural y `git status` limpio. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-014 y todas las tareas backend. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-010 — Establecer la línea base ejecutada de API**.

**Objetivo**
Conocer y corregir sólo los fallos de compilación, lint, typing, pruebas y seeds que impidan una base backend verde.

**Problema y contexto de ZeroMerma**
La auditoría estática no ejecutó validaciones y la activa evitó la suite por la fixture destructiva; se desconoce el estado real. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-QA-011; elementos no verificables de ambas auditorías.

**Dependencias que puedes asumir terminadas**
ZM-FIN-004, ZM-FIN-005 y ZM-FIN-006.

**Inspección inicial obligatoria**
Inspecciona `pytest.testpaths`, `unit_tests/test_training_mode.py`, plugins, fixtures y comandos de `check-foundation.ps1`.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Corregir descubrimiento de tests; ejecutar Ruff, mypy y pytest; clasificar fallos; resolver únicamente defectos de fundación sin mezclar funcionalidades.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No bajar severidad de lint/mypy, borrar pruebas ni cambiar reglas de negocio para hacer pasar casos sin análisis. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Pruebas dependientes de zona horaria, orden, red, datos compartidos, Windows/Linux y DB paralela.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Ruff, mypy estricto, pytest completo, migración/seed en DB efímera y reporte de pruebas excluidas/flaky.

**Validación y comandos**
`uv sync --all-packages --dev`; `uv run ruff check .`; `uv run mypy apps/api/src apps/worker/src`; `uv run pytest` contra DB efímera protegida. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
La suite backend canónica se descubre completa y pasa; cualquier exclusión está justificada y visible en CI.
Definition of Done específica: La suite backend canónica se descubre completa y pasa; cualquier exclusión está justificada y visible en CI. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar instrucciones de pruebas y registrar exclusiones temporales con dueño y criterio de salida.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-011 — Establecer la línea base ejecutada del worker

**Épica:** Calidad worker

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-011 |
| **2. Nombre de la tarea** | Establecer la línea base ejecutada del worker |
| **3. Objetivo** | Asegurar que el worker compila, tiene pruebas descubiertas y puede ejecutarse de manera controlada antes de implementar consumo real. |
| **4. Problema que resuelve** | El proceso estuvo vivo pero su función era incompleta; no hay evidencia ejecutada de typing, tests o manejo de configuración. |
| **5. Hallazgo relacionado** | ZM-ASYNC-006; ZMA-ASYNC-001; ZM-QA-011. |
| **6. Módulos afectados** | Worker, outbox, configuración y pruebas. |
| **7. Archivos/áreas a inspeccionar** | `apps/worker/src`; `apps/worker/tests`; settings compartidos; `OutboxPoller.poll_once`; scripts de arranque. |
| **8. Dependencias previas** | ZM-FIN-004, ZM-FIN-005 y ZM-FIN-006. |
| **9. Cambios a implementar** | Ejecutar calidad y pruebas del worker; documentar ciclo actual, configuración, shutdown y comportamiento sin eventos; corregir fallos básicos sin implementar aún handlers. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Procesar eventos reales durante la caracterización o ocultar la falta de handlers. |
| **13. Posibles regresiones** | Cambiar polling/locks antes de definir la máquina de estados. |
| **14. Pruebas requeridas** | Mypy, pytest worker, start/stop controlado, DB indisponible, tabla vacía y lectura segura de outbox. |
| **15. Criterios de aceptación** | El worker inicia y termina limpiamente, las pruebas pasan y su comportamiento incompleto queda caracterizado para ZM-FIN-073. |
| **16. Definition of Done específica** | El worker inicia y termina limpiamente, las pruebas pasan y su comportamiento incompleto queda caracterizado para ZM-FIN-073. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Logs de ejecución, pruebas, diagrama del ciclo actual y lista de riesgos confirmados. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-073–077. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-011 — Establecer la línea base ejecutada del worker**.

**Objetivo**
Asegurar que el worker compila, tiene pruebas descubiertas y puede ejecutarse de manera controlada antes de implementar consumo real.

**Problema y contexto de ZeroMerma**
El proceso estuvo vivo pero su función era incompleta; no hay evidencia ejecutada de typing, tests o manejo de configuración. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-ASYNC-006; ZMA-ASYNC-001; ZM-QA-011.

**Dependencias que puedes asumir terminadas**
ZM-FIN-004, ZM-FIN-005 y ZM-FIN-006.

**Inspección inicial obligatoria**
Inspecciona poller, modelo OutboxEvent, configuración, logging y pruebas existentes antes de iniciar el proceso.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Ejecutar calidad y pruebas del worker; documentar ciclo actual, configuración, shutdown y comportamiento sin eventos; corregir fallos básicos sin implementar aún handlers.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No declarar exactamente-una-vez ni implementar consumidores de negocio en esta tarea. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
DB caída, señal de terminación, lote vacío, evento malformado y dos instancias accidentales.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Mypy, pytest worker, start/stop controlado, DB indisponible, tabla vacía y lectura segura de outbox.

**Validación y comandos**
Ejecuta mypy/pytest del worker y una ejecución controlada contra DB efímera sin datos operativos. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
El worker inicia y termina limpiamente, las pruebas pasan y su comportamiento incompleto queda caracterizado para ZM-FIN-073.
Definition of Done específica: El worker inicia y termina limpiamente, las pruebas pasan y su comportamiento incompleto queda caracterizado para ZM-FIN-073. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar documentación de ejecución local del worker y su estado real.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-012 — Establecer la línea base ejecutada del POS y su harness E2E real

**Épica:** Calidad POS

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-012 |
| **2. Nombre de la tarea** | Establecer la línea base ejecutada del POS y su harness E2E real |
| **3. Objetivo** | Conseguir que el POS compile y que Playwright pueda apuntar a API/PostgreSQL reales sin interceptar `v1`. |
| **4. Problema que resuelve** | Las pruebas E2E observadas simulan la API; no existe evidencia de integración real del recorrido operativo. |
| **5. Hallazgo relacionado** | ZM-QA-011; limitaciones E2E de la auditoría estática. |
| **6. Módulos afectados** | POS, cliente API, Playwright, API y DB de pruebas. |
| **7. Archivos/áreas a inspeccionar** | `apps/pos-web`; configuración Vite/Playwright/Vitest; stores; mocks/intercepts; paquetes UI/client. |
| **8. Dependencias previas** | ZM-FIN-004, ZM-FIN-005, ZM-FIN-009 y ZM-FIN-010. |
| **9. Cambios a implementar** | Ejecutar lint/typecheck/unit/build; crear configuración E2E real aislada; conservar mocks unitarios pero impedir que la suite de integración intercepte toda la API. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Crear una suite inestable o usar datos compartidos; filtrar credenciales en artefactos. |
| **13. Posibles regresiones** | Romper pruebas unitarias existentes o comportamiento táctil al cambiar configuración. |
| **14. Pruebas requeridas** | Lint, typecheck, Vitest, build y smoke Playwright contra API real con login/apertura sin operaciones económicas destructivas todavía. |
| **15. Criterios de aceptación** | POS compila; el harness real arranca servicios y puede autenticar/consultar estado; mocks e integración están claramente separados. |
| **16. Definition of Done específica** | POS compila; el harness real arranca servicios y puede autenticar/consultar estado; mocks e integración están claramente separados. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Logs, artefactos Playwright, configuración reproducible y trazas de red sin secretos. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-051–059 y ZM-FIN-082. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-012 — Establecer la línea base ejecutada del POS y su harness E2E real**.

**Objetivo**
Conseguir que el POS compile y que Playwright pueda apuntar a API/PostgreSQL reales sin interceptar `v1`.

**Problema y contexto de ZeroMerma**
Las pruebas E2E observadas simulan la API; no existe evidencia de integración real del recorrido operativo. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-QA-011; limitaciones E2E de la auditoría estática.

**Dependencias que puedes asumir terminadas**
ZM-FIN-004, ZM-FIN-005, ZM-FIN-009 y ZM-FIN-010.

**Inspección inicial obligatoria**
Inspecciona todos los intercepts `**/v1/**`, configuración de baseURL, seed de usuarios/estaciones y stores de sesión.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Ejecutar lint/typecheck/unit/build; crear configuración E2E real aislada; conservar mocks unitarios pero impedir que la suite de integración intercepte toda la API.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No implementar flujos funcionales faltantes ni cambiar UX en esta tarea. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Servidor no listo, token expirado, viewport objetivo, datos de prueba repetidos y ejecución paralela.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Lint, typecheck, Vitest, build y smoke Playwright contra API real con login/apertura sin operaciones económicas destructivas todavía.

**Validación y comandos**
`corepack pnpm install --frozen-lockfile`; lint/typecheck/test/build del workspace POS; Playwright con API/DB efímeras. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
POS compila; el harness real arranca servicios y puede autenticar/consultar estado; mocks e integración están claramente separados.
Definition of Done específica: POS compila; el harness real arranca servicios y puede autenticar/consultar estado; mocks e integración están claramente separados. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Documentar diferencias entre unit/mocked E2E/integration E2E y cómo obtener evidencia segura.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-013 — Establecer la línea base ejecutada del Backoffice y su harness E2E real

**Épica:** Calidad Backoffice

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-013 |
| **2. Nombre de la tarea** | Establecer la línea base ejecutada del Backoffice y su harness E2E real |
| **3. Objetivo** | Conseguir que Backoffice compile y que una suite autenticada pueda recorrer módulos reales contra API/PostgreSQL aislados. |
| **4. Problema que resuelve** | La auditoría activa probó navegación manual, mientras la suite E2E estática cubría principalmente el shell público. |
| **5. Hallazgo relacionado** | ZM-QA-011; ZMA-BO-001; ZMA-BO-002. |
| **6. Módulos afectados** | Backoffice, cliente API, Playwright, API y DB de pruebas. |
| **7. Archivos/áreas a inspeccionar** | `apps/backoffice-web`; rutas; `AdminLayout`; `AdminModulePage`; módulos API; Playwright/Vitest. |
| **8. Dependencias previas** | ZM-FIN-004, ZM-FIN-005, ZM-FIN-009 y ZM-FIN-010. |
| **9. Cambios a implementar** | Ejecutar lint/typecheck/unit/build; crear login administrativo E2E real; separar páginas reales de placeholders; capturar rutas y llamadas efectivas. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Usar un superadministrador para ocultar defectos de permisos; pruebas dependientes de datos locales. |
| **13. Posibles regresiones** | Romper navegación condicional o adaptadores de tipos generados. |
| **14. Pruebas requeridas** | Lint, typecheck, Vitest, build y smoke autenticado en módulos de sólo lectura contra API real. |
| **15. Criterios de aceptación** | Backoffice compila; E2E puede autenticar y abrir al menos una ruta real por familia; las superficies simuladas no se confunden con integración. |
| **16. Definition of Done específica** | Backoffice compila; E2E puede autenticar y abrir al menos una ruta real por familia; las superficies simuladas no se confunden con integración. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Artefactos Playwright, trazas de red, lista de rutas cubiertas y cero secretos. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-060–072 y ZM-FIN-083. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-013 — Establecer la línea base ejecutada del Backoffice y su harness E2E real**.

**Objetivo**
Conseguir que Backoffice compile y que una suite autenticada pueda recorrer módulos reales contra API/PostgreSQL aislados.

**Problema y contexto de ZeroMerma**
La auditoría activa probó navegación manual, mientras la suite E2E estática cubría principalmente el shell público. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-QA-011; ZMA-BO-001; ZMA-BO-002.

**Dependencias que puedes asumir terminadas**
ZM-FIN-004, ZM-FIN-005, ZM-FIN-009 y ZM-FIN-010.

**Inspección inicial obligatoria**
Inspecciona configuración E2E, rutas condicionales, fuentes de datos por módulo y credenciales de seed.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Ejecutar lint/typecheck/unit/build; crear login administrativo E2E real; separar páginas reales de placeholders; capturar rutas y llamadas efectivas.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No completar aún dashboard, alertas u otros módulos; sólo establecer línea base y harness. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Colecciones vacías, 401/403, rutas directas, recarga, filtros de sucursal y módulos desconectados.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Lint, typecheck, Vitest, build y smoke autenticado en módulos de sólo lectura contra API real.

**Validación y comandos**
Ejecuta los comandos del workspace Backoffice y Playwright contra API/DB efímeras; conserva artefactos en CI. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Backoffice compila; E2E puede autenticar y abrir al menos una ruta real por familia; las superficies simuladas no se confunden con integración.
Definition of Done específica: Backoffice compila; E2E puede autenticar y abrir al menos una ruta real por familia; las superficies simuladas no se confunden con integración. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Documentar el mapa de rutas E2E y manejo seguro de credenciales de prueba.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-014 — Construir el pipeline de validación de fundación

**Épica:** Integración continua

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-014 |
| **2. Nombre de la tarea** | Construir el pipeline de validación de fundación |
| **3. Objetivo** | Hacer obligatorias las verificaciones reproducibles de toolchain, migraciones, contratos, calidad, pruebas y builds. |
| **4. Problema que resuelve** | Existe un workflow principal, pero hay deriva de herramientas, pruebas incompletas y ausencia de gates de contrato/migración reproducibles. |
| **5. Hallazgo relacionado** | ZM-REL-018; ZM-QA-011; ZM-OPS-014. |
| **6. Módulos afectados** | CI, API, worker, POS, Backoffice, DB y artefactos. |
| **7. Archivos/áreas a inspeccionar** | `.github/workflows`; scripts `check-foundation.ps1`; lockfiles; configuración de servicios; publicación de resultados. |
| **8. Dependencias previas** | ZM-FIN-004–013. |
| **9. Cambios a implementar** | Definir etapas separadas: preflight, DB efímera, migraciones, backend, worker, contratos, frontends y artefactos; bloquear merge ante diff o fallo; publicar evidencia. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Pipeline demasiado acoplado a Windows, cachés contaminadas o pruebas destructivas con secretos incorrectos. |
| **13. Posibles regresiones** | Aumentar flakiness o permitir que una etapa omitida deje pasar regresiones. |
| **14. Pruebas requeridas** | Ejecución desde checkout limpio en runners soportados; fallo intencional por contrato/toolchain/DB; cachés que no cambian resultado. |
| **15. Criterios de aceptación** | Un commit limpio ejecuta todas las validaciones; no se usan credenciales productivas; cada etapa conserva logs y artefactos suficientes. |
| **16. Definition of Done específica** | Un commit limpio ejecuta todas las validaciones; no se usan credenciales productivas; cada etapa conserva logs y artefactos suficientes. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Run de CI verde, run de fallo controlado, hashes y `git status` limpio tras generación. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Todas las fases de implementación y Gate Development Complete. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-014 — Construir el pipeline de validación de fundación**.

**Objetivo**
Hacer obligatorias las verificaciones reproducibles de toolchain, migraciones, contratos, calidad, pruebas y builds.

**Problema y contexto de ZeroMerma**
Existe un workflow principal, pero hay deriva de herramientas, pruebas incompletas y ausencia de gates de contrato/migración reproducibles. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-REL-018; ZM-QA-011; ZM-OPS-014.

**Dependencias que puedes asumir terminadas**
ZM-FIN-004–013.

**Inspección inicial obligatoria**
Inspecciona workflow actual, scripts, secretos, permisos de GitHub Actions y orden de ejecución.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir etapas separadas: preflight, DB efímera, migraciones, backend, worker, contratos, frontends y artefactos; bloquear merge ante diff o fallo; publicar evidencia.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No añadir despliegue productivo en esta tarea; no relajar checks para reducir tiempo. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Forks sin secretos, cancelación, ejecución concurrente, cache miss, Windows/Linux y artefacto generado con diff.

**Concurrencia y consistencia**
Probar dos ejecuciones CI concurrentes con bases aisladas y sin compartir estado mutable.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Ejecución desde checkout limpio en runners soportados; fallo intencional por contrato/toolchain/DB; cachés que no cambian resultado.

**Validación y comandos**
Ejecuta localmente los scripts equivalentes y valida el workflow en una rama de prueba; no habilites despliegue aún. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Un commit limpio ejecuta todas las validaciones; no se usan credenciales productivas; cada etapa conserva logs y artefactos suficientes.
Definition of Done específica: Un commit limpio ejecuta todas las validaciones; no se usan credenciales productivas; cada etapa conserva logs y artefactos suficientes. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar documentación de CI, fallos esperados y cómo reproducir cada etapa localmente.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```


## Fase 2 — Seguridad, identidad, autorización y scopes — Tareas ejecutables

### ZM-FIN-015 — Implementar el catálogo canónico de capacidades y el contexto de permisos efectivos

**Épica:** RBAC
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: capabilities/scopes/secrets cubren dashboard, alertas/ACK/resolución, exportación, branch y Telegram con mínimo privilegio.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-015 |
| **2. Nombre de la tarea** | Implementar el catálogo canónico de capacidades y el contexto de permisos efectivos |
| **3. Objetivo** | Convertir roles y permisos existentes en una decisión de autorización backend determinista y reutilizable. |
| **4. Problema que resuelve** | Los modelos RBAC existen, pero los routers sólo exigen acceso general a Backoffice. |
| **5. Hallazgo relacionado** | ZM-SEC-001; ZMA-SEC-001. |
| **6. Módulos afectados** | Identity, roles, permisos, dependencias FastAPI y contrato de sesión. |
| **7. Archivos/áreas a inspeccionar** | Modelos `Role`, `Permission`, `UserRoleAssignment`; `_require_backoffice_user`; `user_can_access_surface`; dependencias de routers; `AdminLayout.tsx`. |
| **8. Dependencias previas** | ZM-FIN-003, ZM-FIN-008 y ZM-FIN-014. |
| **9. Cambios a implementar** | Definir capacidades estables; materializar rol Superadministrador explícito; provisionar de forma controlada a `ZEROMERMA_OWNER` como único `GLOBAL` inicial; impedir promoción de admin seed/legacy; resolver grants activos y dependencia deny-by-default; exponer grants efectivos al cliente sin delegar seguridad. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Sobreconceder por herencia o conservar un bypass implícito de superadministrador. |
| **13. Posibles regresiones** | Bloquear administradores legítimos o cambiar permisos sembrados sin migración de datos. |
| **14. Pruebas requeridas** | Unitarias de composición de roles; usuario sin rol; rol/permiso inactivo; superadministrador; contrato `/me` o equivalente. |
| **15. Criterios de aceptación** | El contexto devuelve permisos/scopes deterministas; existe exactamente un Superadministrador inicial `GLOBAL` explícitamente designado; ningún admin seed/legacy hereda privilegio; ninguna ruta administrativa omite política explícita salvo excepción pública documentada. |
| **16. Definition of Done específica** | El contexto devuelve permisos deterministas; ninguna ruta administrativa puede omitir una política explícita salvo excepción pública documentada. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Matriz de capacidades, pruebas allow/deny y contrato de grants generado. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-016–019 y ZM-FIN-079. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-015 — Implementar el catálogo canónico de capacidades y el contexto de permisos efectivos**.

**Objetivo**
Convertir roles y permisos existentes en una decisión de autorización backend determinista y reutilizable.

**Problema y contexto de ZeroMerma**
Los modelos RBAC existen, pero los routers sólo exigen acceso general a Backoffice. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-001; ZMA-SEC-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-003, ZM-FIN-008 y ZM-FIN-014.

**Inspección inicial obligatoria**
Inspecciona modelos, seeds, routers, helpers de acceso y cualquier permiso declarado pero no consumido.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir capacidades estables, política de superadministrador, resolución de grants activos y dependencia deny-by-default; exponer grants efectivos al cliente sin delegar seguridad.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No aplicar todavía permisos a todos los routers en el mismo cambio; no usar visibilidad UI como control. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Múltiples roles, rol inactivo, permiso retirado durante sesión, usuario bloqueado y rol global explícito.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Unitarias de composición de roles; usuario sin rol; rol/permiso inactivo; superadministrador; contrato `/me` o equivalente.

**Validación y comandos**
Ejecuta unitarias e integración de identidad, genera OpenAPI/cliente y typecheck Backoffice. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
El contexto devuelve permisos deterministas; ninguna ruta administrativa puede omitir una política explícita salvo excepción pública documentada.
Definition of Done específica: El contexto devuelve permisos deterministas; ninguna ruta administrativa puede omitir una política explícita salvo excepción pública documentada. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar matriz de capacidades y ADR de autorización.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-016 — Proteger administración de usuarios, roles y permisos

**Épica:** RBAC
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: capabilities/scopes/secrets cubren dashboard, alertas/ACK/resolución, exportación, branch y Telegram con mínimo privilegio.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-016 |
| **2. Nombre de la tarea** | Proteger administración de usuarios, roles y permisos |
| **3. Objetivo** | Impedir que un usuario Backoffice sin capacidades de identidad consulte o modifique cuentas y privilegios. |
| **4. Problema que resuelve** | La superficie de identidad está accesible con el gate genérico de Backoffice. |
| **5. Hallazgo relacionado** | ZM-SEC-001; ZMA-SEC-001. |
| **6. Módulos afectados** | Identity API, Backoffice de usuarios/roles y auditoría. |
| **7. Archivos/áreas a inspeccionar** | Routers/servicios `admin_users`, `admin_roles` o equivalentes; páginas de usuarios/roles; modelos de asignación. |
| **8. Dependencias previas** | ZM-FIN-015. |
| **9. Cambios a implementar** | Asignar capacidades a cada método; exigirlas en backend; auditar cambios; ajustar UI a grants; preservar reglas de usuario activo/bloqueado. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Escalamiento de privilegio por autoasignación o modificación del último superadministrador. |
| **13. Posibles regresiones** | Administradores existentes pierden acceso; UI muestra acciones que backend rechaza. |
| **14. Pruebas requeridas** | API 401/403/2xx; lectura, alta, edición, bloqueo, cambio de roles; verificación de cero mutación en 403. |
| **15. Criterios de aceptación** | Sin `users.manage`/`roles.manage` se obtiene 403; con permiso correcto se conserva el comportamiento y la auditoría registra actor/cambios. |
| **16. Definition of Done específica** | Sin `users.manage`/`roles.manage` se obtiene 403; con permiso correcto se conserva el comportamiento y la auditoría registra actor/cambios. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Matriz endpoint-permiso, filas de auditoría y pruebas negativas/positivas. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-066 y Gate Security Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-016 — Proteger administración de usuarios, roles y permisos**.

**Objetivo**
Impedir que un usuario Backoffice sin capacidades de identidad consulte o modifique cuentas y privilegios.

**Problema y contexto de ZeroMerma**
La superficie de identidad está accesible con el gate genérico de Backoffice. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-001; ZMA-SEC-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-015.

**Inspección inicial obligatoria**
Localiza todos los endpoints y acciones de identidad, incluidos reseteos, bloqueo, asignaciones y listados.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Asignar capacidades a cada método; exigirlas en backend; auditar cambios; ajustar UI a grants; preservar reglas de usuario activo/bloqueado.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No rediseñar toda la UI de administración ni crear un sistema de políticas paralelo. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Autoedición, autoelevación, último administrador, rol inactivo, usuario de otra sucursal y operación concurrente.

**Concurrencia y consistencia**
Probar dos cambios concurrentes de roles y retirada de permiso durante una sesión.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
API 401/403/2xx; lectura, alta, edición, bloqueo, cambio de roles; verificación de cero mutación en 403.

**Validación y comandos**
Ejecuta pruebas API de identidad, OpenAPI/cliente y pruebas de componentes/rutas afectadas. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Sin `users.manage`/`roles.manage` se obtiene 403; con permiso correcto se conserva el comportamiento y la auditoría registra actor/cambios.
Definition of Done específica: Sin `users.manage`/`roles.manage` se obtiene 403; con permiso correcto se conserva el comportamiento y la auditoría registra actor/cambios. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar matriz endpoint-capacidad y manual administrativo de roles.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-017 — Proteger configuración, auditoría, reportes y exportaciones

**Épica:** RBAC
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: capabilities/scopes/secrets cubren dashboard, alertas/ACK/resolución, exportación, branch y Telegram con mínimo privilegio.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-017 |
| **2. Nombre de la tarea** | Proteger configuración, auditoría, reportes y exportaciones |
| **3. Objetivo** | Restringir superficies de lectura sensible y cambios de configuración a capacidades explícitas. |
| **4. Problema que resuelve** | Cualquier usuario Backoffice puede potencialmente consultar auditoría, configuración y reportes o exportar datos. |
| **5. Hallazgo relacionado** | ZM-SEC-001; ZM-FUNC-013; ZMA-SEC-001. |
| **6. Módulos afectados** | Settings, audit, reports, exports y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Routers `admin_settings`, `admin_audit`, `admin_reports`; definiciones `required_permissions`; páginas y acciones de exportación. |
| **8. Dependencias previas** | ZM-FIN-015. |
| **9. Cambios a implementar** | Aplicar permisos diferenciados de lectura/modificación/exportación; conservar enmascaramiento; auditar accesos y cambios sensibles. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Exponer PII/secrets por exportación o permitir modificar controles de seguridad sin separación de funciones. |
| **13. Posibles regresiones** | Reportes legítimos dejan de cargar; settings enmascarados se sobrescriben con valores enmascarados. |
| **14. Pruebas requeridas** | 401/403/2xx por operación; exportación fuera de scope; cambio de settings; consulta de audit; verificación de redacción. |
| **15. Criterios de aceptación** | Cada operación exige su capacidad; `required_permissions` deja de ser metadata sin efecto; 403 no filtra datos ni crea exportaciones. |
| **16. Definition of Done específica** | Cada operación exige su capacidad; `required_permissions` deja de ser metadata sin efecto; 403 no filtra datos ni crea exportaciones. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas de matriz, ejemplos de respuesta enmascarada y eventos de auditoría. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-071, ZM-FIN-072 y Gate Security Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-017 — Proteger configuración, auditoría, reportes y exportaciones**.

**Objetivo**
Restringir superficies de lectura sensible y cambios de configuración a capacidades explícitas.

**Problema y contexto de ZeroMerma**
Cualquier usuario Backoffice puede potencialmente consultar auditoría, configuración y reportes o exportar datos. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-001; ZM-FUNC-013; ZMA-SEC-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-015.

**Inspección inicial obligatoria**
Inspecciona permisos declarados en reportes, endpoints de preview/export, almacenamiento de settings y filtros de audit.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Aplicar permisos diferenciados de lectura/modificación/exportación; conservar enmascaramiento; auditar accesos y cambios sensibles.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No completar todavía los reportes pendientes; sólo asegurar las superficies existentes. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Exportación grande, filtro omitido, secreto enmascarado, permiso sólo lectura, audit de la propia consulta.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
401/403/2xx por operación; exportación fuera de scope; cambio de settings; consulta de audit; verificación de redacción.

**Validación y comandos**
Ejecuta pruebas API/contractuales y E2E de acceso directo a rutas, además de generación del cliente. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada operación exige su capacidad; `required_permissions` deja de ser metadata sin efecto; 403 no filtra datos ni crea exportaciones.
Definition of Done específica: Cada operación exige su capacidad; `required_permissions` deja de ser metadata sin efecto; 403 no filtra datos ni crea exportaciones. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar matriz de permisos y política de exportación/auditoría.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-018 — Proteger operaciones económicas, inventario y producción

**Épica:** RBAC
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: capabilities/scopes/secrets cubren dashboard, alertas/ACK/resolución, exportación, branch y Telegram con mínimo privilegio.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-018 |
| **2. Nombre de la tarea** | Proteger operaciones económicas, inventario y producción |
| **3. Objetivo** | Aplicar autorización específica a mutaciones con impacto monetario o físico. |
| **4. Problema que resuelve** | Ajustes de inventario, compras, producción, caja y otras operaciones administrativas usan el gate general. |
| **5. Hallazgo relacionado** | ZM-SEC-001; ZMA-SEC-001; ZM-DATA-004. |
| **6. Módulos afectados** | Inventory, purchases, production, cash, payments, returns, transfers y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Routers/servicios administrativos por dominio; permisos existentes como `inventory.adjust`; botones/acciones de UI. |
| **8. Dependencias previas** | ZM-FIN-015 y decisiones de separación de funciones. |
| **9. Cambios a implementar** | Asignar capacidades de lectura, creación, aprobación, reversa y ajuste; exigirlas en servicio/backend; auditar denegaciones y mutaciones. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Permisos demasiado amplios o inconsistentes entre operaciones equivalentes POS/Backoffice. |
| **13. Posibles regresiones** | Operaciones diarias legítimas bloqueadas; acciones UI desalineadas con backend. |
| **14. Pruebas requeridas** | Pruebas por familia 401/403/2xx; no mutación; actor/sucursal/turno; aprobación distinta cuando esté decidida. |
| **15. Criterios de aceptación** | Toda mutación económica/física habilitada tiene permiso explícito y prueba negativa; no existe bypass por URL o método alternativo. |
| **16. Definition of Done específica** | Toda mutación económica/física habilitada tiene permiso explícito y prueba negativa; no existe bypass por URL o método alternativo. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Matriz completa de operaciones sensibles y resultados de persistencia/auditoría. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-045–050 y módulos Backoffice operativos. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-018 — Proteger operaciones económicas, inventario y producción**.

**Objetivo**
Aplicar autorización específica a mutaciones con impacto monetario o físico.

**Problema y contexto de ZeroMerma**
Ajustes de inventario, compras, producción, caja y otras operaciones administrativas usan el gate general. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-001; ZMA-SEC-001; ZM-DATA-004.

**Dependencias que puedes asumir terminadas**
ZM-FIN-015 y decisiones de separación de funciones.

**Inspección inicial obligatoria**
Inventaría todos los endpoints de mutación económica/física y los permisos semánticamente equivalentes.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Asignar capacidades de lectura, creación, aprobación, reversa y ajuste; exigirlas en servicio/backend; auditar denegaciones y mutaciones.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No cambiar todavía la lógica económica o de inventario salvo lo mínimo para ubicar el control. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Aprobación propia, reversa, operación en sucursal distinta, recurso ya cerrado/cancelado y método HTTP alterno.

**Concurrencia y consistencia**
Probar retirada de permiso entre lectura y commit; backend debe revalidar en la transacción cuando aplique.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Pruebas por familia 401/403/2xx; no mutación; actor/sucursal/turno; aprobación distinta cuando esté decidida.

**Validación y comandos**
Ejecuta suites de autorización por dominio y verificación de cero filas ante 403. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Toda mutación económica/física habilitada tiene permiso explícito y prueba negativa; no existe bypass por URL o método alternativo.
Definition of Done específica: Toda mutación económica/física habilitada tiene permiso explícito y prueba negativa; no existe bypass por URL o método alternativo. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar matriz de permisos y SOP de separación de funciones.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-019 — Completar enforcement deny-by-default en el resto del Backoffice

**Épica:** RBAC
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: capabilities/scopes/secrets cubren dashboard, alertas/ACK/resolución, exportación, branch y Telegram con mínimo privilegio.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-019 |
| **2. Nombre de la tarea** | Completar enforcement deny-by-default en el resto del Backoffice |
| **3. Objetivo** | Cerrar cualquier endpoint administrativo que permanezca sin capacidad explícita. |
| **4. Problema que resuelve** | Una corrección por familias puede dejar rutas nuevas u olvidadas con el gate genérico. |
| **5. Hallazgo relacionado** | ZM-SEC-001; ZMA-SEC-001. |
| **6. Módulos afectados** | Todos los routers administrativos restantes y navegación Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Registro OpenAPI/routers; matriz de ZM-FIN-008; dependencia `_require_backoffice_user`; pruebas de cobertura de políticas. |
| **8. Dependencias previas** | ZM-FIN-016–018. |
| **9. Cambios a implementar** | Añadir una prueba automática que falle si una operación administrativa no declara capacidad/excepción; migrar las familias restantes. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Excepciones públicas demasiado amplias o política aplicada sólo en router y omitida en invocaciones internas. |
| **13. Posibles regresiones** | Rutas técnicas/health inadvertidamente protegidas o clients sin permisos actualizados. |
| **14. Pruebas requeridas** | Introspección de rutas; 401/403/2xx; método alternativo; ruta nueva sin política debe romper CI. |
| **15. Criterios de aceptación** | Cien por ciento de operaciones administrativas clasificadas; no existe autorización implícita por mera pertenencia a Backoffice. |
| **16. Definition of Done específica** | Cien por ciento de operaciones administrativas clasificadas; no existe autorización implícita por mera pertenencia a Backoffice. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Reporte automático de cobertura de políticas y suite verde. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Security Ready y ZM-FIN-020–023. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-019 — Completar enforcement deny-by-default en el resto del Backoffice**.

**Objetivo**
Cerrar cualquier endpoint administrativo que permanezca sin capacidad explícita.

**Problema y contexto de ZeroMerma**
Una corrección por familias puede dejar rutas nuevas u olvidadas con el gate genérico. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-001; ZMA-SEC-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-016–018.

**Inspección inicial obligatoria**
Compara registro de rutas con matriz endpoint-capacidad y busca todos los usos del gate genérico.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Añadir una prueba automática que falle si una operación administrativa no declara capacidad/excepción; migrar las familias restantes.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No introducir un segundo framework de políticas ni duplicar lógica por router. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Rutas OPTIONS/docs, endpoints internos, aliases, webhooks y acciones de sólo lectura sensibles.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Introspección de rutas; 401/403/2xx; método alternativo; ruta nueva sin política debe romper CI.

**Validación y comandos**
Ejecuta script de cobertura, pruebas de autorización y generación contractual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cien por ciento de operaciones administrativas clasificadas; no existe autorización implícita por mera pertenencia a Backoffice.
Definition of Done específica: Cien por ciento de operaciones administrativas clasificadas; no existe autorización implícita por mera pertenencia a Backoffice. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Mantener la matriz como artefacto generado o validado por CI.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-020 — Modelar y resolver scopes administrativos por sucursal

**Épica:** Aislamiento
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: capabilities/scopes/secrets cubren dashboard, alertas/ACK/resolución, exportación, branch y Telegram con mínimo privilegio.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-020 |
| **2. Nombre de la tarea** | Modelar y resolver scopes administrativos por sucursal |
| **3. Objetivo** | Derivar en backend el conjunto de sucursales permitidas para cada usuario/rol. |
| **4. Problema que resuelve** | Los roles scoped se declaran no soportados y los filtros controlados por cliente no constituyen autorización. |
| **5. Hallazgo relacionado** | ZM-SEC-002; ZMA-SEC-002. |
| **6. Módulos afectados** | Identity, branches, roles, sesión y base de datos. |
| **7. Archivos/áreas a inspeccionar** | Modelos/asignaciones de rol; contratos `AdminRoleScopeView`; `_scope_summary`; contexto de autenticación. |
| **8. Dependencias previas** | ZM-FIN-003, ZM-FIN-015 y decisión de roles globales/scoped. |
| **9. Cambios a implementar** | Implementar modelo/asignación si falta, resolver `GLOBAL` o `BRANCH_SET` explícito, inicializar `GLOBAL` sólo para el Superadministrador designado por DEC-19, invalidar cachés/sesiones y exponer resumen efectivo. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Convertir accidentalmente a todos los roles existentes en globales o perder acceso de administración central. |
| **13. Posibles regresiones** | Asignaciones actuales incompatibles; usuarios POS afectados por un modelo administrativo distinto. |
| **14. Pruebas requeridas** | Unitarias de una/múltiples sucursales, rol global, rol inactivo, intersección de roles y cambio de asignación. |
| **15. Criterios de aceptación** | El backend produce un scope inequívoco; usuario sin scope no obtiene acceso; `GLOBAL` exige rol/asignación explícitos y sólo el Superadministrador designado lo tiene inicialmente; seed, nombre admin o ausencia de branch nunca lo infieren. |
| **16. Definition of Done específica** | El backend produce un scope inequívoco; usuario sin scope no obtiene acceso; global exige una capacidad/rol explícito. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Migración, datos de prueba multi-sucursal, contrato de scope y pruebas. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-021–023 y operación multi-sucursal. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-020 — Modelar y resolver scopes administrativos por sucursal**.

**Objetivo**
Derivar en backend el conjunto de sucursales permitidas para cada usuario/rol.

**Problema y contexto de ZeroMerma**
Los roles scoped se declaran no soportados y los filtros controlados por cliente no constituyen autorización. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-002; ZMA-SEC-002.

**Dependencias que puedes asumir terminadas**
ZM-FIN-003, ZM-FIN-015 y decisión de roles globales/scoped.

**Inspección inicial obligatoria**
Inspecciona todas las tablas/asignaciones de usuario, rol, branch y workstation y cualquier campo de scope ya existente.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Implementar modelo/asignación si falta, resolver scope global o conjunto explícito, invalidar cachés/sesiones y exponer resumen efectivo.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No implementar particionamiento físico ni multi-tenancy por base. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Cero sucursales, múltiples roles con scopes distintos, sucursal desactivada, rol global y revocación durante sesión.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Unitarias de una/múltiples sucursales, rol global, rol inactivo, intersección de roles y cambio de asignación.

**Validación y comandos**
Ejecuta migración en DB efímera, pruebas unitarias/integración y generación contractual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
El backend produce un scope inequívoco; usuario sin scope no obtiene acceso; global exige una capacidad/rol explícito.
Definition of Done específica: El backend produce un scope inequívoco; usuario sin scope no obtiene acceso; global exige una capacidad/rol explícito. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
ADR de scopes y guía de migración de roles existentes.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-021 — Aplicar scopes a lecturas, reportes y exportaciones

**Épica:** Aislamiento
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: capabilities/scopes/secrets cubren dashboard, alertas/ACK/resolución, exportación, branch y Telegram con mínimo privilegio.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-021 |
| **2. Nombre de la tarea** | Aplicar scopes a lecturas, reportes y exportaciones |
| **3. Objetivo** | Impedir fuga de datos de otras sucursales en listados, agregados, dashboard, auditoría y archivos exportados. |
| **4. Problema que resuelve** | Los servicios aceptan filtros elegidos por el solicitante y los agregados pueden ignorar scope. |
| **5. Hallazgo relacionado** | ZM-SEC-002; ZMA-SEC-002. |
| **6. Módulos afectados** | Todos los dominios con `branch_id`, reports, audit y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Repositorios/queries/listados; filtros; paginación; reportes/exportaciones; dashboard. |
| **8. Dependencias previas** | ZM-FIN-020 y ZM-FIN-017. |
| **9. Cambios a implementar** | Aplicar scope obligatorio dentro de queries/servicios; intersectar filtros; definir comportamiento sin filtro; evitar paginación previa al scope. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Filtrar después de agregar o paginar; fuga por relaciones, búsqueda o IDs directos. |
| **13. Posibles regresiones** | Cambios de totales para administradores globales o consultas significativamente más lentas. |
| **14. Pruebas requeridas** | Dos o más sucursales; IDs conocidos de otra sucursal; agregados; exportación; conteos/paginación; acceso global explícito. |
| **15. Criterios de aceptación** | Ninguna lectura devuelve registros o totales fuera de scope; los counts y archivos coinciden con el conjunto autorizado. |
| **16. Definition of Done específica** | Ninguna lectura devuelve registros o totales fuera de scope; los counts y archivos coinciden con el conjunto autorizado. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Consultas SQL/resultados, pruebas de no fuga y exportaciones comparadas. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-070–072 y Gate Security Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-021 — Aplicar scopes a lecturas, reportes y exportaciones**.

**Objetivo**
Impedir fuga de datos de otras sucursales en listados, agregados, dashboard, auditoría y archivos exportados.

**Problema y contexto de ZeroMerma**
Los servicios aceptan filtros elegidos por el solicitante y los agregados pueden ignorar scope. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-002; ZMA-SEC-002.

**Dependencias que puedes asumir terminadas**
ZM-FIN-020 y ZM-FIN-017.

**Inspección inicial obligatoria**
Inventaría todos los listados, búsquedas, agregados, reportes, auditoría y exportaciones con branch explícita o implícita.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Aplicar scope obligatorio dentro de queries/servicios; intersectar filtros; definir comportamiento sin filtro; evitar paginación previa al scope.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No confiar en ocultar opciones de sucursal en frontend. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Filtro omitido, lista vacía, varias sucursales permitidas, recurso relacionado en otra sucursal y paginación profunda.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Dos o más sucursales; IDs conocidos de otra sucursal; agregados; exportación; conteos/paginación; acceso global explícito.

**Validación y comandos**
Ejecuta integración multi-sucursal y planes de consulta cuando cambien queries críticas. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Ninguna lectura devuelve registros o totales fuera de scope; los counts y archivos coinciden con el conjunto autorizado.
Definition of Done específica: Ninguna lectura devuelve registros o totales fuera de scope; los counts y archivos coinciden con el conjunto autorizado. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Documentar semántica de filtros y permisos globales.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-022 — Aplicar scopes a mutaciones y relaciones de dominio

**Épica:** Aislamiento
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: capabilities/scopes/secrets cubren dashboard, alertas/ACK/resolución, exportación, branch y Telegram con mínimo privilegio.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-022 |
| **2. Nombre de la tarea** | Aplicar scopes a mutaciones y relaciones de dominio |
| **3. Objetivo** | Impedir crear o modificar documentos usando sucursales, cajas, estaciones, turnos o entidades fuera del scope autorizado. |
| **4. Problema que resuelve** | Un `branch_id` válido enviado por el cliente puede atravesar relaciones si sólo se filtra la UI. |
| **5. Hallazgo relacionado** | ZM-SEC-002; ZMA-SEC-002; principios de aislamiento del proyecto. |
| **6. Módulos afectados** | Ventas admin, inventario, compras, producción, transferencias, users, settings y worker. |
| **7. Archivos/áreas a inspeccionar** | Command services; validadores de relaciones; repositorios; jobs y eventos con branch; modelos de workstation/cash session. |
| **8. Dependencias previas** | ZM-FIN-020, ZM-FIN-021 y permisos de cada dominio. |
| **9. Cambios a implementar** | Derivar o validar branch dentro del servicio; comprobar relaciones cruzadas; propagar scope causal a audit/outbox/jobs; denegar antes de mutar. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | IDOR, confusión entre 403/404 y eventos asíncronos sin contexto de branch. |
| **13. Posibles regresiones** | Flujos globales legítimos de transferencia o administración central dejan de funcionar. |
| **14. Pruebas requeridas** | Mutación con branch ajena; caja/estación/turno cruzados; recurso existente ajeno; job/worker; rollback y cero filas. |
| **15. Criterios de aceptación** | Toda mutación fuera de scope devuelve 403/404 según política sin efecto; relaciones internas pertenecen a la misma sucursal autorizada. |
| **16. Definition of Done específica** | Toda mutación fuera de scope devuelve 403/404 según política sin efecto; relaciones internas pertenecen a la misma sucursal autorizada. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas multi-sucursal y grafos de IDs que demuestren aislamiento. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | Gate Security Ready y flujos multi-sucursal confiables. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-022 — Aplicar scopes a mutaciones y relaciones de dominio**.

**Objetivo**
Impedir crear o modificar documentos usando sucursales, cajas, estaciones, turnos o entidades fuera del scope autorizado.

**Problema y contexto de ZeroMerma**
Un `branch_id` válido enviado por el cliente puede atravesar relaciones si sólo se filtra la UI. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-002; ZMA-SEC-002; principios de aislamiento del proyecto.

**Dependencias que puedes asumir terminadas**
ZM-FIN-020, ZM-FIN-021 y permisos de cada dominio.

**Inspección inicial obligatoria**
Inspecciona cada command service que recibe `branch_id`, `cash_register_id`, `workstation_id`, `session_id` o relaciones equivalentes.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Derivar o validar branch dentro del servicio; comprobar relaciones cruzadas; propagar scope causal a audit/outbox/jobs; denegar antes de mutar.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No duplicar datos por sucursal ni introducir filtros sólo en frontend. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Transferencia entre dos sucursales autorizadas/no autorizadas, recurso desactivado, job retrasado tras revocación y usuario global.

**Concurrencia y consistencia**
Probar revocación de scope mientras una transacción está en curso y mutaciones concurrentes sobre entidades relacionadas.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Mutación con branch ajena; caja/estación/turno cruzados; recurso existente ajeno; job/worker; rollback y cero filas.

**Validación y comandos**
Ejecuta integración multi-sucursal, pruebas de persistencia y generación contractual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Toda mutación fuera de scope devuelve 403/404 según política sin efecto; relaciones internas pertenecen a la misma sucursal autorizada.
Definition of Done específica: Toda mutación fuera de scope devuelve 403/404 según política sin efecto; relaciones internas pertenecen a la misma sucursal autorizada. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar ADR de aislamiento y matriz de relaciones por dominio.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-023 — Implementar un traspaso seguro de sesión POS–Backoffice

**Épica:** Sesiones

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-023 |
| **2. Nombre de la tarea** | Implementar un traspaso seguro de sesión POS–Backoffice |
| **3. Objetivo** | Eliminar el bearer persistente en URL y sustituirlo por un mecanismo efímero y de un solo uso o por la arquitectura de sesión aprobada. |
| **4. Problema que resuelve** | POS envía token en fragmento; Backoffice acepta además query string; el bearer queda accesible a JavaScript. |
| **5. Hallazgo relacionado** | ZM-SEC-008; ZMA-SEC-003. |
| **6. Módulos afectados** | Auth API, POS, Backoffice y despliegue web. |
| **7. Archivos/áreas a inspeccionar** | Stores de autenticación; bootstrap Backoffice; `readAccessTokenFromUrl`; rutas de navegación; TokenService/session store. |
| **8. Dependencias previas** | ZM-FIN-003 y decisión de arquitectura de sesión. |
| **9. Cambios a implementar** | Eliminar query token; implementar intercambio de un solo uso o cookie segura; limpiar URL antes de cargar recursos; auditar el traspaso y caducidad. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Romper navegación entre superficies o introducir CSRF/session fixation. |
| **13. Posibles regresiones** | Usuarios quedan en bucle de login o sesiones válidas se pierden al recargar. |
| **14. Pruebas requeridas** | Query rechazado; código de un solo uso replay; URL/history/referer limpios; navegación exitosa; sesión inválida/expirada. |
| **15. Criterios de aceptación** | Ningún bearer aparece en query, fragmento persistente, logs o history; el traspaso sólo puede consumirse una vez y por el cliente esperado. |
| **16. Definition of Done específica** | Ningún bearer aparece en query, fragmento persistente, logs o history; el traspaso sólo puede consumirse una vez y por el cliente esperado. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Trazas de navegación sin secretos, pruebas de replay y contrato generado. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-024, ZM-FIN-026 y Gate Security Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-023 — Implementar un traspaso seguro de sesión POS–Backoffice**.

**Objetivo**
Eliminar el bearer persistente en URL y sustituirlo por un mecanismo efímero y de un solo uso o por la arquitectura de sesión aprobada.

**Problema y contexto de ZeroMerma**
POS envía token en fragmento; Backoffice acepta además query string; el bearer queda accesible a JavaScript. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-008; ZMA-SEC-003.

**Dependencias que puedes asumir terminadas**
ZM-FIN-003 y decisión de arquitectura de sesión.

**Inspección inicial obligatoria**
Inspecciona stores, bootstrap, dominios/orígenes de despliegue, política CORS/cookies y cualquier enlace con `access_token`.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Eliminar query token; implementar intercambio de un solo uso o cookie segura; limpiar URL antes de cargar recursos; auditar el traspaso y caducidad.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No conservar compatibilidad silenciosa con query token; no almacenar secretos en localStorage como solución transitoria sin aprobación. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Replay, código expirado, pestañas múltiples, origen incorrecto, back/forward, refresh y logout simultáneo.

**Concurrencia y consistencia**
Probar dos intentos concurrentes de canjear el mismo código; sólo uno debe prosperar.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Query rechazado; código de un solo uso replay; URL/history/referer limpios; navegación exitosa; sesión inválida/expirada.

**Validación y comandos**
Ejecuta pruebas API, frontend unitarias/E2E, escaneo de URL/logs y generación contractual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Ningún bearer aparece en query, fragmento persistente, logs o history; el traspaso sólo puede consumirse una vez y por el cliente esperado.
Definition of Done específica: Ningún bearer aparece en query, fragmento persistente, logs o history; el traspaso sólo puede consumirse una vez y por el cliente esperado. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
ADR de sesión y actualización de manuales de despliegue.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-024 — Completar ciclo de sesión, expiración, renovación, revocación y logout

**Épica:** Sesiones

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-024 |
| **2. Nombre de la tarea** | Completar ciclo de sesión, expiración, renovación, revocación y logout |
| **3. Objetivo** | Hacer que una sesión tenga identidad, estado y revocación verificables durante todo su ciclo. |
| **4. Problema que resuelve** | El token HMAC sólo contiene sub/exp, dura hasta ocho horas y no tiene jti, audience, issuer, sesión o revocación. |
| **5. Hallazgo relacionado** | ZM-SEC-009; ZM-SEC-008; ZMA-SEC-003. |
| **6. Módulos afectados** | Identity, token/session service, POS, Backoffice y auditoría. |
| **7. Archivos/áreas a inspeccionar** | `TokenService`; dependencias bearer; stores; login/logout; modelos de usuario/sesión; middleware. |
| **8. Dependencias previas** | ZM-FIN-023 y política aprobada de sesión. |
| **9. Cambios a implementar** | Crear sesiones identificables; issuer/audience/jti o equivalente; renovación segura; revocación por logout/bloqueo/cambio de credenciales; validación en cada request. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Almacenar tokens sensibles, carrera de refresh o invalidar sesiones de operación crítica sin UX. |
| **13. Posibles regresiones** | Sesiones se cierran inesperadamente; POS pierde operación en curso; cookies mal configuradas. |
| **14. Pruebas requeridas** | Token expirado, revocado, usuario bloqueado, refresh replay, logout, múltiples sesiones y reloj desfasado. |
| **15. Criterios de aceptación** | Logout y revocación impiden nuevas solicitudes; renovación no prolonga indefinidamente una sesión; auditoría conserva sesión/actor sin exponer token. |
| **16. Definition of Done específica** | Logout y revocación impiden nuevas solicitudes; renovación no prolonga indefinidamente una sesión; auditoría conserva sesión/actor sin exponer token. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Migración/modelo de sesiones, pruebas de ciclo completo y evidencia de revocación. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-025, ZM-FIN-079 y Gate Security Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-024 — Completar ciclo de sesión, expiración, renovación, revocación y logout**.

**Objetivo**
Hacer que una sesión tenga identidad, estado y revocación verificables durante todo su ciclo.

**Problema y contexto de ZeroMerma**
El token HMAC sólo contiene sub/exp, dura hasta ocho horas y no tiene jti, audience, issuer, sesión o revocación. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-009; ZM-SEC-008; ZMA-SEC-003.

**Dependencias que puedes asumir terminadas**
ZM-FIN-023 y política aprobada de sesión.

**Inspección inicial obligatoria**
Inspecciona generación/validación de tokens, commits de login, stores y manejo actual de 401.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Crear sesiones identificables; issuer/audience/jti o equivalente; renovación segura; revocación por logout/bloqueo/cambio de credenciales; validación en cada request.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No introducir SSO corporativo salvo decisión explícita. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Refresh concurrente, revocación global vs individual, bloqueo de usuario, expiración durante venta y cambio de hora.

**Concurrencia y consistencia**
Dos refresh concurrentes no deben producir dos cadenas válidas si la política usa rotación.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Token expirado, revocado, usuario bloqueado, refresh replay, logout, múltiples sesiones y reloj desfasado.

**Validación y comandos**
Ejecuta unitarias, integración de autenticación, E2E de expiración/logout y generación contractual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Logout y revocación impiden nuevas solicitudes; renovación no prolonga indefinidamente una sesión; auditoría conserva sesión/actor sin exponer token.
Definition of Done específica: Logout y revocación impiden nuevas solicitudes; renovación no prolonga indefinidamente una sesión; auditoría conserva sesión/actor sin exponer token. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Documentar ciclo de sesión, tiempos configurables y procedimientos de revocación.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-025 — Completar contraseñas temporales, reset y protección del login

**Épica:** Identidad

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-025 |
| **2. Nombre de la tarea** | Completar contraseñas temporales, reset y protección del login |
| **3. Objetivo** | Evitar contraseñas temporales permanentes y ataques repetidos, y persistir correctamente la actividad de acceso. |
| **4. Problema que resuelve** | No se fuerza `password_reset_required`, faltan rate limiting/auditoría de fallos y `last_login_at` quedó nulo tras logins activos. |
| **5. Hallazgo relacionado** | ZM-SEC-009; ZMA-ID-001; ZMA-UI-001. |
| **6. Módulos afectados** | Auth, users, audit, POS/Backoffice login y configuración. |
| **7. Archivos/áreas a inspeccionar** | `AuthService.login`; `PasswordHasher`; user admin service; campos de reset/lock; formularios de login. |
| **8. Dependencias previas** | ZM-FIN-024 y política de identidad. |
| **9. Cambios a implementar** | Persistir último acceso; forzar cambio temporal; implementar reset seguro; registrar fallos; rate limit/lockout configurables; limpiar estado de formulario/autocomplete según terminal compartida. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Denegación de servicio por lockout, filtración de existencia de usuarios o tokens de reset reutilizables. |
| **13. Posibles regresiones** | Usuarios legítimos bloqueados, login lento o incompatibilidad con seeds locales. |
| **14. Pruebas requeridas** | Login correcto/fallido; reset expirado/replay; contraseña temporal; bloqueo/desbloqueo; límite por usuario/IP; last_login commit. |
| **15. Criterios de aceptación** | Usuario con reset requerido no accede a funciones; fallos quedan auditados sin contraseña; último acceso persiste; controles no permiten enumeración de cuentas. |
| **16. Definition of Done específica** | Usuario con reset requerido no accede a funciones; fallos quedan auditados sin contraseña; último acceso persiste; controles no permiten enumeración de cuentas. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas de identidad, filas de auditoría y capturas de UX sin datos sensibles. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Security Ready y administración de usuarios completa. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-025 — Completar contraseñas temporales, reset y protección del login**.

**Objetivo**
Evitar contraseñas temporales permanentes y ataques repetidos, y persistir correctamente la actividad de acceso.

**Problema y contexto de ZeroMerma**
No se fuerza `password_reset_required`, faltan rate limiting/auditoría de fallos y `last_login_at` quedó nulo tras logins activos. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-009; ZMA-ID-001; ZMA-UI-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-024 y política de identidad.

**Inspección inicial obligatoria**
Inspecciona el flujo completo de commit en login, campos de usuario, seeds, manejo de errores y formularios.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Persistir último acceso; forzar cambio temporal; implementar reset seguro; registrar fallos; rate limit/lockout configurables; limpiar estado de formulario/autocomplete según terminal compartida.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No registrar contraseñas, hashes, tokens o respuestas que permitan enumeración. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Usuario inexistente, bloqueado/inactivo, reset simultáneo, token vencido, terminal compartida y zona horaria.

**Concurrencia y consistencia**
Probar intentos simultáneos y consumo concurrente del mismo token de reset.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Login correcto/fallido; reset expirado/replay; contraseña temporal; bloqueo/desbloqueo; límite por usuario/IP; last_login commit.

**Validación y comandos**
Ejecuta suites auth, pruebas de rate limit en entorno aislado, E2E de cambio obligatorio y generación contractual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Usuario con reset requerido no accede a funciones; fallos quedan auditados sin contraseña; último acceso persiste; controles no permiten enumeración de cuentas.
Definition of Done específica: Usuario con reset requerido no accede a funciones; fallos quedan auditados sin contraseña; último acceso persiste; controles no permiten enumeración de cuentas. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar política de identidad y procedimientos de soporte/reset.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-026 — Endurecer configuración productiva y seguridad del navegador

**Épica:** Hardening

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-026 |
| **2. Nombre de la tarea** | Endurecer configuración productiva y seguridad del navegador |
| **3. Objetivo** | Hacer que producción falle cerrada y reducir superficie de ataque web. |
| **4. Problema que resuelve** | Se aceptan secretos/default DB, CORS añade orígenes de desarrollo, docs/dev audit pueden exponerse y no hay cabeceras/CSP verificables. |
| **5. Hallazgo relacionado** | ZM-SEC-007; ZM-SEC-008; ZMA-SEC-003. |
| **6. Módulos afectados** | API settings/main, POS, Backoffice, proxy y entornos. |
| **7. Archivos/áreas a inspeccionar** | `core/config.py`; `main.py`; `.env.example`; CORS; docs URLs; dev audit; configuración Vite/proxy; headers. |
| **8. Dependencias previas** | ZM-FIN-004, ZM-FIN-023–025 y dominios aprobados. |
| **9. Cambios a implementar** | Validar secretos/DB/ambiente; CORS exacto; deshabilitar docs/dev endpoints por defecto; aplicar TLS/header/CSP/CSRF según sesión; configurar trusted proxies y redacción. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | CORS/CSP demasiado permisivos o demasiado restrictivos; confiar en headers sin TLS real. |
| **13. Posibles regresiones** | Desarrollo local roto, assets bloqueados o cookies no enviadas por SameSite/domain. |
| **14. Pruebas requeridas** | Matriz de arranque válido/inválido; origen no autorizado; docs ausentes; CSP; CSRF si cookies; host/proxy spoofing; logs sin secretos. |
| **15. Criterios de aceptación** | Producción no inicia con defaults; sólo orígenes aprobados funcionan; superficies dev no existen; cabeceras y política de sesión pasan pruebas. |
| **16. Definition of Done específica** | Producción no inicia con defaults; sólo orígenes aprobados funcionan; superficies dev no existen; cabeceras y política de sesión pasan pruebas. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Logs de arranque negativo, escaneo de headers/CORS y configuración no secreta aprobada. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Posible |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-087, ZM-FIN-090 y Gate Security Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-026 — Endurecer configuración productiva y seguridad del navegador**.

**Objetivo**
Hacer que producción falle cerrada y reducir superficie de ataque web.

**Problema y contexto de ZeroMerma**
Se aceptan secretos/default DB, CORS añade orígenes de desarrollo, docs/dev audit pueden exponerse y no hay cabeceras/CSP verificables. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-007; ZM-SEC-008; ZMA-SEC-003.

**Dependencias que puedes asumir terminadas**
ZM-FIN-004, ZM-FIN-023–025 y dominios aprobados.

**Inspección inicial obligatoria**
Inspecciona todos los valores default, orígenes añadidos, URLs de docs, endpoints de desarrollo y configuración del proxy.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Validar secretos/DB/ambiente; CORS exacto; deshabilitar docs/dev endpoints por defecto; aplicar TLS/header/CSP/CSRF según sesión; configurar trusted proxies y redacción.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No asumir que WAF/TLS externos existen sin evidencia; no codificar secretos. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Subdominios, puertos, preflight, assets CDN, websocket si existe, cookie cross-site y modo training.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Posible. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Matriz de arranque válido/inválido; origen no autorizado; docs ausentes; CSP; CSRF si cookies; host/proxy spoofing; logs sin secretos.

**Validación y comandos**
Ejecuta pruebas de settings, arranque por ambiente, requests CORS/headers y E2E en topología de staging equivalente. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Producción no inicia con defaults; sólo orígenes aprobados funcionan; superficies dev no existen; cabeceras y política de sesión pasan pruebas.
Definition of Done específica: Producción no inicia con defaults; sólo orígenes aprobados funcionan; superficies dev no existen; cabeceras y política de sesión pasan pruebas. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Documentar perfiles de entorno y checklist de hardening.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-027 — Implementar gestión y rotación de secretos por entorno

**Épica:** Secretos
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: capabilities/scopes/secrets cubren dashboard, alertas/ACK/resolución, exportación, branch y Telegram con mínimo privilegio.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-027 |
| **2. Nombre de la tarea** | Implementar gestión y rotación de secretos por entorno |
| **3. Objetivo** | Separar secretos de código/configuración pública y permitir rotación sin reconstruir el producto. |
| **4. Problema que resuelve** | La configuración actual admite valores conocidos y no existe evidencia de un gestor de secretos productivo. |
| **5. Hallazgo relacionado** | ZM-SEC-007; ZM-OPS-014; elemento no verificable de gestión real de secretos. |
| **6. Módulos afectados** | API, worker, DB, CI/CD, frontends y operación. |
| **7. Archivos/áreas a inspeccionar** | Settings; workflows; manifests; `.env.example`; credenciales DB; claves de sesión; proveedores externos. |
| **8. Dependencias previas** | ZM-FIN-026 y plataforma objetivo aprobada. |
| **9. Cambios a implementar** | Definir inventario, propietarios, inyección runtime, permisos mínimos, rotación, revocación y escaneo; eliminar defaults utilizables en producción. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Bloquear despliegues por secretos no disponibles o dejar claves antiguas válidas indefinidamente. |
| **13. Posibles regresiones** | Sesiones/worker/DB dejan de funcionar durante rotación. |
| **14. Pruebas requeridas** | Arranque con secreto inyectado; secreto ausente; rotación de clave compatible con sesiones según política; escaneo Git/logs/artefactos. |
| **15. Criterios de aceptación** | Ningún secreto productivo reside en Git, imagen, frontend o logs; rotación está documentada y probada en staging. |
| **16. Definition of Done específica** | Ningún secreto productivo reside en Git, imagen, frontend o logs; rotación está documentada y probada en staging. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Inventario anonimizado, evidencia de escaneo y simulacro de rotación. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-090–092 y Gate Production Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-027 — Implementar gestión y rotación de secretos por entorno**.

**Objetivo**
Separar secretos de código/configuración pública y permitir rotación sin reconstruir el producto.

**Problema y contexto de ZeroMerma**
La configuración actual admite valores conocidos y no existe evidencia de un gestor de secretos productivo. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-007; ZM-OPS-014; elemento no verificable de gestión real de secretos.

**Dependencias que puedes asumir terminadas**
ZM-FIN-026 y plataforma objetivo aprobada.

**Inspección inicial obligatoria**
Inspecciona todas las variables sensibles, secretos de CI, imágenes y configuraciones frontend/runtime.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir inventario, propietarios, inyección runtime, permisos mínimos, rotación, revocación y escaneo; eliminar defaults utilizables en producción.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No compartir secretos en la respuesta de Codex ni introducir un gestor casero si la plataforma ofrece uno. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Rotación con instancias mixtas, rollback, secreto comprometido, acceso de desarrollador y entorno de pruebas.

**Concurrencia y consistencia**
Probar rotación durante despliegue gradual con versiones compatibles.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Arranque con secreto inyectado; secreto ausente; rotación de clave compatible con sesiones según política; escaneo Git/logs/artefactos.

**Validación y comandos**
Ejecuta escaneo de secretos, pruebas de arranque y simulacro de rotación en staging; nunca imprimas valores. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Ningún secreto productivo reside en Git, imagen, frontend o logs; rotación está documentada y probada en staging.
Definition of Done específica: Ningún secreto productivo reside en Git, imagen, frontend o logs; rotación está documentada y probada en staging. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Runbook de alta, rotación, revocación y acceso de emergencia.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```


## Fase 3 — Idempotencia, concurrencia y límites transaccionales — Tareas ejecutables

### ZM-FIN-028 — Crear el contrato y almacenamiento idempotente transaccional

**Épica:** Idempotencia
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: el hecho relevante preserva atomicidad business mutation + canonical state/ledger + audit + outbox, identidad causal e idempotencia.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-028 |
| **2. Nombre de la tarea** | Crear el contrato y almacenamiento idempotente transaccional |
| **3. Objetivo** | Proporcionar una infraestructura común para que un mismo comando produzca un único efecto observable. |
| **4. Problema que resuelve** | No existe un store/índice de idempotencia; algunas claves sólo funcionan como correlación. |
| **5. Hallazgo relacionado** | ZM-REL-005; ZMA-REL-001. |
| **6. Módulos afectados** | API core/application, PostgreSQL, auditoría y contratos HTTP. |
| **7. Archivos/áreas a inspeccionar** | Servicios de venta/pedidos/pagos; schemas; modelos; migraciones; request/correlation IDs. |
| **8. Dependencias previas** | ZM-FIN-003, ZM-FIN-006 y ZM-FIN-009. |
| **9. Cambios a implementar** | Definir header/campo, scope por actor/sucursal/estación/operación, fingerprint canónico, estados reserve/complete/fail, respuesta persistida, TTL/retención y conflicto por payload distinto. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Guardar respuestas sensibles, scope demasiado global o liberar una reserva antes de saber el resultado real. |
| **13. Posibles regresiones** | Cambiar respuestas HTTP, aumentar contención o dejar claves atascadas tras crash. |
| **14. Pruebas requeridas** | Reserva secuencial/concurrente; mismo payload; payload distinto; crash antes/después del commit; respuesta sensible; limpieza. |
| **15. Criterios de aceptación** | Dos solicitudes con misma clave/payload observan el mismo resultado y un solo efecto; payload distinto devuelve 409; la reserva vive en la misma transacción útil. |
| **16. Definition of Done específica** | Dos solicitudes con misma clave/payload observan el mismo resultado y un solo efecto; payload distinto devuelve 409; la reserva vive en la misma transacción útil. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Migración, modelo, pruebas PostgreSQL concurrentes y especificación OpenAPI. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-029–035. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-028 — Crear el contrato y almacenamiento idempotente transaccional**.

**Objetivo**
Proporcionar una infraestructura común para que un mismo comando produzca un único efecto observable.

**Problema y contexto de ZeroMerma**
No existe un store/índice de idempotencia; algunas claves sólo funcionan como correlación. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-REL-005; ZMA-REL-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-003, ZM-FIN-006 y ZM-FIN-009.

**Inspección inicial obligatoria**
Inspecciona todos los campos llamados idempotency/request/correlation y los límites de commit de los servicios económicos.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir header/campo, scope por actor/sucursal/estación/operación, fingerprint canónico, estados reserve/complete/fail, respuesta persistida, TTL/retención y conflicto por payload distinto.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No adoptar todavía el mecanismo en todos los comandos ni deduplicar por importe/tiempo. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Clave vacía/larga, JSON semánticamente igual con orden distinto, error 4xx/5xx, expiración y cambio de usuario/sucursal.

**Concurrencia y consistencia**
Dos transacciones concurrentes con la misma clave deben serializar sin ejecutar dos veces; probar crash después de commit antes de respuesta.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Reserva secuencial/concurrente; mismo payload; payload distinto; crash antes/después del commit; respuesta sensible; limpieza.

**Validación y comandos**
Ejecuta migración en DB efímera, unitarias, integración concurrente y contract tests. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Dos solicitudes con misma clave/payload observan el mismo resultado y un solo efecto; payload distinto devuelve 409; la reserva vive en la misma transacción útil.
Definition of Done específica: Dos solicitudes con misma clave/payload observan el mismo resultado y un solo efecto; payload distinto devuelve 409; la reserva vive en la misma transacción útil. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
ADR de idempotencia, política de retención y guía para clientes.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-029 — Hacer idempotente la confirmación de venta

**Épica:** Idempotencia
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: el hecho relevante preserva atomicidad business mutation + canonical state/ledger + audit + outbox, identidad causal e idempotencia.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-029 |
| **2. Nombre de la tarea** | Hacer idempotente la confirmación de venta |
| **3. Objetivo** | Evitar ventas, pagos, caja, auditoría, outbox e inventario duplicados ante retry o doble cliente. |
| **4. Problema que resuelve** | La venta no exige clave idempotente y la prevención UI no cubre timeout/replay. |
| **5. Hallazgo relacionado** | ZM-REL-005; ZMA-REL-001. |
| **6. Módulos afectados** | Sales, payments, cash, audit, outbox, POS y cliente API. |
| **7. Archivos/áreas a inspeccionar** | `SaleCommandService`; endpoint/schemas de confirmación; mutación POS; pruebas de venta. |
| **8. Dependencias previas** | ZM-FIN-028 y contrato de venta vigente. |
| **9. Cambios a implementar** | Exigir clave; reservar dentro del límite transaccional; persistir respuesta original; rechazar fingerprint distinto; propagar clave/operation ID a auditoría y outbox. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Reservar antes de validar y conservar eternamente errores del cliente; incompatibilidad con clientes antiguos. |
| **13. Posibles regresiones** | Venta normal rechazada, ticket duplicado o cambio de código HTTP inesperado. |
| **14. Pruebas requeridas** | Replay secuencial/concurrente; timeout post-commit; doble clic; mismo carrito con otra clave; payload distinto; rollback. |
| **15. Criterios de aceptación** | El replay devuelve el mismo sale/ticket ID y no añade líneas, pagos, movimientos, audit ni outbox. |
| **16. Definition of Done específica** | El replay devuelve el mismo sale/ticket ID y no añade líneas, pagos, movimientos, audit ni outbox. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Conteos de tablas antes/después, respuestas iguales y trazas por operation ID. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-046, ZM-FIN-053 y ZM-FIN-080. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-029 — Hacer idempotente la confirmación de venta**.

**Objetivo**
Evitar ventas, pagos, caja, auditoría, outbox e inventario duplicados ante retry o doble cliente.

**Problema y contexto de ZeroMerma**
La venta no exige clave idempotente y la prevención UI no cubre timeout/replay. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-REL-005; ZMA-REL-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-028 y contrato de venta vigente.

**Inspección inicial obligatoria**
Inspecciona endpoint, servicio, commit único, creación de ticket/pago/cash/audit/outbox y mutación POS.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Exigir clave; reservar dentro del límite transaccional; persistir respuesta original; rechazar fingerprint distinto; propagar clave/operation ID a auditoría y outbox.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No introducir cambios de pricing o inventario no necesarios para la idempotencia. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Carrito vacío, pago inválido, sesión cerrada, retry tras 409, clave reutilizada por otra estación.

**Concurrencia y consistencia**
Ejecutar dos confirmaciones simultáneas con la misma clave y con claves distintas sobre la misma sesión.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Replay secuencial/concurrente; timeout post-commit; doble clic; mismo carrito con otra clave; payload distinto; rollback.

**Validación y comandos**
Pruebas API PostgreSQL, E2E POS de doble submit, generación OpenAPI/cliente y regresión de venta. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
El replay devuelve el mismo sale/ticket ID y no añade líneas, pagos, movimientos, audit ni outbox.
Definition of Done específica: El replay devuelve el mismo sale/ticket ID y no añade líneas, pagos, movimientos, audit ni outbox. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar contrato POS y guía de retries.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-030 — Hacer idempotente el ciclo de pedidos y sus pagos

**Épica:** Idempotencia
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: el hecho relevante preserva atomicidad business mutation + canonical state/ledger + audit + outbox, identidad causal e idempotencia.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-030 |
| **2. Nombre de la tarea** | Hacer idempotente el ciclo de pedidos y sus pagos |
| **3. Objetivo** | Evitar pedidos, transiciones, pagos y entregas duplicados cuando el cliente reintenta. |
| **4. Problema que resuelve** | La clave de pedidos se usa como correlación y no como replay; el pago de pedido tiene efectos económicos propios. |
| **5. Hallazgo relacionado** | ZM-REL-005; ZMA-REL-001; ZMA-FIN-001. |
| **6. Módulos afectados** | Orders, order payments, cash, audit, outbox, POS y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | `OrdersCommandService`; endpoints create/pay/status/cancel/refund; stores/mutations de pedido. |
| **8. Dependencias previas** | ZM-FIN-028 y decisiones del ciclo de pedido. |
| **9. Cambios a implementar** | Aplicar idempotencia por comando; usar claves independientes para crear, pagar y transicionar; persistir respuesta y detectar transición incompatible. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Usar la misma clave para comandos distintos o permitir dos entregas/pagos concurrentes. |
| **13. Posibles regresiones** | Pedidos existentes no pueden avanzar; UI pierde reintentos legítimos. |
| **14. Pruebas requeridas** | Replay create/pay/deliver/cancel; pago duplicado; estado ya alcanzado; payload distinto; timeout; dos clientes. |
| **15. Criterios de aceptación** | Cada comando produce una sola transición/efecto; replay devuelve el mismo recurso; transiciones incompatibles devuelven conflicto sin mutar. |
| **16. Definition of Done específica** | Cada comando produce una sola transición/efecto; replay devuelve el mismo recurso; transiciones incompatibles devuelven conflicto sin mutar. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Historial de estados, pagos y outbox sin duplicados; respuestas y pruebas concurrentes. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-045, ZM-FIN-062 y ZM-FIN-080. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-030 — Hacer idempotente el ciclo de pedidos y sus pagos**.

**Objetivo**
Evitar pedidos, transiciones, pagos y entregas duplicados cuando el cliente reintenta.

**Problema y contexto de ZeroMerma**
La clave de pedidos se usa como correlación y no como replay; el pago de pedido tiene efectos económicos propios. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-REL-005; ZMA-REL-001; ZMA-FIN-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-028 y decisiones del ciclo de pedido.

**Inspección inicial obligatoria**
Inspecciona todos los endpoints/transiciones de pedido y dónde se almacena actualmente `idempotency_key`.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Aplicar idempotencia por comando; usar claves independientes para crear, pagar y transicionar; persistir respuesta y detectar transición incompatible.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No redefinir todavía el ledger de caja; sólo garantizar replay seguro. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Pago parcial/total, cancelación tras pago, entrega repetida, pedido ya cerrado y sucursal/turno diferente.

**Concurrencia y consistencia**
Dos pagos o dos transiciones concurrentes sobre el mismo pedido deben producir un estado válido único.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Replay create/pay/deliver/cancel; pago duplicado; estado ya alcanzado; payload distinto; timeout; dos clientes.

**Validación y comandos**
Pruebas API concurrentes, E2E de retry y generación contractual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada comando produce una sola transición/efecto; replay devuelve el mismo recurso; transiciones incompatibles devuelven conflicto sin mutar.
Definition of Done específica: Cada comando produce una sola transición/efecto; replay devuelve el mismo recurso; transiciones incompatibles devuelven conflicto sin mutar. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Documentar clave por comando y máquina de estados.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-031 — Hacer idempotentes devoluciones y reembolsos

**Épica:** Idempotencia
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: el hecho relevante preserva atomicidad business mutation + canonical state/ledger + audit + outbox, identidad causal e idempotencia.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-031 |
| **2. Nombre de la tarea** | Hacer idempotentes devoluciones y reembolsos |
| **3. Objetivo** | Impedir documentos, salidas de caja, reversiones y movimientos físicos duplicados. |
| **4. Problema que resuelve** | Las devoluciones producen reembolso/documento pero no tienen deduplicación backend. |
| **5. Hallazgo relacionado** | ZM-REL-005; ZMA-REL-001; ZM-DATA-004. |
| **6. Módulos afectados** | Returns, refunds, payments, cash, inventory, audit, outbox, POS/Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Servicios/endpoints de returns/refunds; disposición; mutaciones UI; referencias a venta/pago. |
| **8. Dependencias previas** | ZM-FIN-028 y política de devolución aprobada. |
| **9. Cambios a implementar** | Aplicar clave por solicitud; validar cantidades acumuladas; persistir respuesta; asegurar que compensaciones financiera/física comparten el mismo resultado idempotente. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Sobredevolución concurrente o compensación parcial si falla una integración externa. |
| **13. Posibles regresiones** | Devoluciones válidas rechazadas por historial previo o redondeo. |
| **14. Pruebas requeridas** | Replay parcial/total; dos devoluciones sobre la misma línea; payload distinto; refund externo pendiente; rollback. |
| **15. Criterios de aceptación** | No se devuelve más de lo vendido ni se duplica dinero/stock; replay conserva el mismo return/refund ID. |
| **16. Definition of Done específica** | No se devuelve más de lo vendido ni se duplica dinero/stock; replay conserva el mismo return/refund ID. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Reconciliación venta→devolución→reembolso y conteos de movimientos/audit/outbox. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-047, ZM-FIN-055 y ZM-FIN-080. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-031 — Hacer idempotentes devoluciones y reembolsos**.

**Objetivo**
Impedir documentos, salidas de caja, reversiones y movimientos físicos duplicados.

**Problema y contexto de ZeroMerma**
Las devoluciones producen reembolso/documento pero no tienen deduplicación backend. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-REL-005; ZMA-REL-001; ZM-DATA-004.

**Dependencias que puedes asumir terminadas**
ZM-FIN-028 y política de devolución aprobada.

**Inspección inicial obligatoria**
Inspecciona validación de cantidades, vínculos a venta/pago, commits y disposición de inventario.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Aplicar clave por solicitud; validar cantidades acumuladas; persistir respuesta; asegurar que compensaciones financiera/física comparten el mismo resultado idempotente.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No simular una reversión bancaria inexistente como completada. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Múltiples devoluciones parciales, item no restock, pago mixto, método no reversible y pedido vs venta.

**Concurrencia y consistencia**
Dos devoluciones concurrentes de la última cantidad disponible deben serializar y sólo una prosperar.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Replay parcial/total; dos devoluciones sobre la misma línea; payload distinto; refund externo pendiente; rollback.

**Validación y comandos**
Pruebas API PostgreSQL, E2E de replay, contract tests y reconciliación. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
No se devuelve más de lo vendido ni se duplica dinero/stock; replay conserva el mismo return/refund ID.
Definition of Done específica: No se devuelve más de lo vendido ni se duplica dinero/stock; replay conserva el mismo return/refund ID. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar política de devolución/reembolso y guía operativa.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-032 — Hacer idempotentes apertura, movimientos operativos y cierre de caja

**Épica:** Idempotencia
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: el hecho relevante preserva atomicidad business mutation + canonical state/ledger + audit + outbox, identidad causal e idempotencia.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-032 |
| **2. Nombre de la tarea** | Hacer idempotentes apertura, movimientos operativos y cierre de caja |
| **3. Objetivo** | Evitar sesiones, entradas/salidas y cierres duplicados por reintento. |
| **4. Problema que resuelve** | La UI bloquea algunos dobles clics, pero apertura, pagos operativos y cierre carecen de replay persistente. |
| **5. Hallazgo relacionado** | ZM-REL-005; ZMA-REL-001; ZM-DATA-003. |
| **6. Módulos afectados** | Cash session, operational payments, cash close, audit, outbox y POS. |
| **7. Archivos/áreas a inspeccionar** | Servicios/endpoints de apertura, cash movements, descuentos/cargos operativos y cierre; UI de caja. |
| **8. Dependencias previas** | ZM-FIN-028 y decisiones de cierre/fondo. |
| **9. Cambios a implementar** | Adoptar clave por comando; persistir respuestas; validar estado; asegurar que un replay no crea otra sesión/movimiento/cierre. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Bloquear recuperación tras una respuesta perdida o reutilizar clave entre turnos. |
| **13. Posibles regresiones** | Apertura/cierre normales fallan o el POS no puede recuperar el resultado. |
| **14. Pruebas requeridas** | Doble apertura, movimiento repetido, cierre repetido, payload distinto, timeout post-commit y sesión ya cerrada. |
| **15. Criterios de aceptación** | Cada operación de caja produce un solo documento/asiento; replay devuelve el mismo ID y conflicto semántico no muta. |
| **16. Definition of Done específica** | Cada operación de caja produce un solo documento/asiento; replay devuelve el mismo ID y conflicto semántico no muta. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Conteos por sesión, respuestas, audit/outbox y pruebas concurrentes. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-049, ZM-FIN-065 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-032 — Hacer idempotentes apertura, movimientos operativos y cierre de caja**.

**Objetivo**
Evitar sesiones, entradas/salidas y cierres duplicados por reintento.

**Problema y contexto de ZeroMerma**
La UI bloquea algunos dobles clics, pero apertura, pagos operativos y cierre carecen de replay persistente. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-REL-005; ZMA-REL-001; ZM-DATA-003.

**Dependencias que puedes asumir terminadas**
ZM-FIN-028 y decisiones de cierre/fondo.

**Inspección inicial obligatoria**
Inspecciona restricciones únicas parciales, endpoints y límites de commit de caja.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Adoptar clave por comando; persistir respuestas; validar estado; asegurar que un replay no crea otra sesión/movimiento/cierre.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No cambiar todavía la fórmula de conciliación. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Fondo cero, cierre sin conteo si se permite, sesión ya abierta, usuario/estación diferente y cambio de turno.

**Concurrencia y consistencia**
Dos aperturas/cierres simultáneos con misma y distinta clave sobre la misma estación.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Doble apertura, movimiento repetido, cierre repetido, payload distinto, timeout post-commit y sesión ya cerrada.

**Validación y comandos**
Pruebas API concurrentes, E2E de retry y generación contractual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada operación de caja produce un solo documento/asiento; replay devuelve el mismo ID y conflicto semántico no muta.
Definition of Done específica: Cada operación de caja produce un solo documento/asiento; replay devuelve el mismo ID y conflicto semántico no muta. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Documentar semántica idempotente por operación de caja.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-033 — Hacer idempotentes transferencias y recepciones

**Épica:** Idempotencia
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: el hecho relevante preserva atomicidad business mutation + canonical state/ledger + audit + outbox, identidad causal e idempotencia.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-033 |
| **2. Nombre de la tarea** | Hacer idempotentes transferencias y recepciones |
| **3. Objetivo** | Evitar despachos, recepciones y movimientos de inventario duplicados. |
| **4. Problema que resuelve** | Los flujos POS/Backoffice crean documentos y algunos movimientos, pero no existe replay seguro común. |
| **5. Hallazgo relacionado** | ZM-REL-005; ZM-DATA-004; ZMA-DATA-001. |
| **6. Módulos afectados** | Transfers, receipts, inventory, audit, outbox, POS y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Servicios/endpoints de transferencias POS/admin; send/receive; líneas y estados. |
| **8. Dependencias previas** | ZM-FIN-028 y máquina de estados de transferencia aprobada. |
| **9. Cambios a implementar** | Aplicar idempotencia a crear, enviar y recibir; validar cantidades acumuladas; asegurar que documento y movimientos comparten transacción. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Doble decremento/incremento o estados divergentes entre POS y Backoffice. |
| **13. Posibles regresiones** | Transferencias existentes no pueden completarse o recepción parcial se rompe. |
| **14. Pruebas requeridas** | Replay create/send/receive; recepción parcial; exceso; dos receptores; payload distinto; timeout. |
| **15. Criterios de aceptación** | No se despacha/recibe dos veces; cantidades no exceden envío; replay devuelve el mismo resultado. |
| **16. Definition of Done específica** | No se despacha/recibe dos veces; cantidades no exceden envío; replay devuelve el mismo resultado. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Historial de transferencia, movimientos y pruebas de cantidades. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-056, ZM-FIN-066 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-033 — Hacer idempotentes transferencias y recepciones**.

**Objetivo**
Evitar despachos, recepciones y movimientos de inventario duplicados.

**Problema y contexto de ZeroMerma**
Los flujos POS/Backoffice crean documentos y algunos movimientos, pero no existe replay seguro común. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-REL-005; ZM-DATA-004; ZMA-DATA-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-028 y máquina de estados de transferencia aprobada.

**Inspección inicial obligatoria**
Inspecciona ambos caminos POS/admin y compara sus efectos reales en inventory ledger.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Aplicar idempotencia a crear, enviar y recibir; validar cantidades acumuladas; asegurar que documento y movimientos comparten transacción.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No unificar visualmente POS y Backoffice; unificar sólo semántica backend. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Recepción parcial, daño/rechazo, origen=destino, sucursal fuera de scope y documento cancelado.

**Concurrencia y consistencia**
Dos recepciones simultáneas del remanente deben serializar.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Replay create/send/receive; recepción parcial; exceso; dos receptores; payload distinto; timeout.

**Validación y comandos**
Pruebas integración PostgreSQL, E2E por superficie y generación contractual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
No se despacha/recibe dos veces; cantidades no exceden envío; replay devuelve el mismo resultado.
Definition of Done específica: No se despacha/recibe dos veces; cantidades no exceden envío; replay devuelve el mismo resultado. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar máquina de estados y procedimiento de recepción.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-034 — Hacer idempotentes correcciones y merma

**Épica:** Idempotencia
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: el hecho relevante preserva atomicidad business mutation + canonical state/ledger + audit + outbox, identidad causal e idempotencia.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-034 |
| **2. Nombre de la tarea** | Hacer idempotentes correcciones y merma |
| **3. Objetivo** | Garantizar que una corrección o disposición de merma no se registre ni afecte stock más de una vez. |
| **4. Problema que resuelve** | Correcciones y merma son auditables pero sus efectos físicos son incompletos y no deduplicados. |
| **5. Hallazgo relacionado** | ZM-REL-005; ZM-DATA-004; ZMA-WASTE-001. |
| **6. Módulos afectados** | Corrections, waste, returns disposition, inventory, audit y outbox. |
| **7. Archivos/áreas a inspeccionar** | OperationDocument y servicios POS/admin de corrections/waste; endpoints y formularios. |
| **8. Dependencias previas** | ZM-FIN-028 y decisión de merma/devolución. |
| **9. Cambios a implementar** | Aplicar clave y fingerprint; vincular a documento causal; impedir duplicados semánticos; preparar integración atómica con ledger. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Usar correcciones para editar historia en vez de compensar o generar merma doble desde devolución. |
| **13. Posibles regresiones** | Flujos manuales existentes dejan de registrar causa o se rechazan por claves ausentes. |
| **14. Pruebas requeridas** | Replay; corrección sobre recurso cerrado; `SEND_TO_WASTE`; cantidad superior; payload distinto; rollback. |
| **15. Criterios de aceptación** | Una clave produce un solo documento y un solo efecto; replay conserva ID; las cantidades y relaciones son válidas. |
| **16. Definition of Done específica** | Una clave produce un solo documento y un solo efecto; replay conserva ID; las cantidades y relaciones son válidas. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Documentos/movimientos/audit/outbox reconciliados y pruebas. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-055, ZM-FIN-067 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-034 — Hacer idempotentes correcciones y merma**.

**Objetivo**
Garantizar que una corrección o disposición de merma no se registre ni afecte stock más de una vez.

**Problema y contexto de ZeroMerma**
Correcciones y merma son auditables pero sus efectos físicos son incompletos y no deduplicados. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-REL-005; ZM-DATA-004; ZMA-WASTE-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-028 y decisión de merma/devolución.

**Inspección inicial obligatoria**
Inspecciona cómo se representan correcciones, merma y disposición de devolución y dónde se generan eventos.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Aplicar clave y fingerprint; vincular a documento causal; impedir duplicados semánticos; preparar integración atómica con ledger.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No permitir edición destructiva de documentos históricos. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Documento ya corregido, cantidad cero/negativa, unidad distinta, recurso de otra sucursal y causa obligatoria.

**Concurrencia y consistencia**
Dos correcciones concurrentes sobre el mismo saldo deben validar el remanente.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Replay; corrección sobre recurso cerrado; `SEND_TO_WASTE`; cantidad superior; payload distinto; rollback.

**Validación y comandos**
Pruebas API, integración de persistencia y generación contractual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Una clave produce un solo documento y un solo efecto; replay conserva ID; las cantidades y relaciones son válidas.
Definition of Done específica: Una clave produce un solo documento y un solo efecto; replay conserva ID; las cantidades y relaciones son válidas. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Documentar compensaciones y relación con merma.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-035 — Hacer idempotentes los comandos de producción

**Épica:** Idempotencia
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: el hecho relevante preserva atomicidad business mutation + canonical state/ledger + audit + outbox, identidad causal e idempotencia.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-035 |
| **2. Nombre de la tarea** | Hacer idempotentes los comandos de producción |
| **3. Objetivo** | Evitar iniciar, cancelar o completar un lote más de una vez y duplicar consumos/salidas. |
| **4. Problema que resuelve** | Producción tiene estados reales y eventos, pero no existe semántica de replay; la cancelación mostró contradicciones. |
| **5. Hallazgo relacionado** | ZM-REL-005; ZMA-PROD-001. |
| **6. Módulos afectados** | Production, recipes, inventory, audit, outbox y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Servicios/endpoints create/start/cancel/complete; modelos de lote; UI de producción. |
| **8. Dependencias previas** | ZM-FIN-028 y decisiones de producción cancelada. |
| **9. Cambios a implementar** | Aplicar idempotencia por transición; validar estado actual; persistir respuesta; preparar consumos/outputs atómicos sin duplicación. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Completar y cancelar simultáneamente o dejar movimientos sin estado final. |
| **13. Posibles regresiones** | Lotes existentes quedan atascados o mensajes UI no reflejan el estado idempotente. |
| **14. Pruebas requeridas** | Start/cancel/complete replay; dos transiciones incompatibles; faltantes 409; crash tras movimientos; payload distinto. |
| **15. Criterios de aceptación** | Cada transición ocurre una vez; replay devuelve el mismo estado; no se duplican reservas, consumos, salidas ni eventos. |
| **16. Definition of Done específica** | Cada transición ocurre una vez; replay devuelve el mismo estado; no se duplican reservas, consumos, salidas ni eventos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Historial del lote, movimientos y pruebas concurrentes. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-058, ZM-FIN-062 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-035 — Hacer idempotentes los comandos de producción**.

**Objetivo**
Evitar iniciar, cancelar o completar un lote más de una vez y duplicar consumos/salidas.

**Problema y contexto de ZeroMerma**
Producción tiene estados reales y eventos, pero no existe semántica de replay; la cancelación mostró contradicciones. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-REL-005; ZMA-PROD-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-028 y decisiones de producción cancelada.

**Inspección inicial obligatoria**
Inspecciona máquina de estados, shortage check, commits, movimientos y mensajes calculados.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Aplicar idempotencia por transición; validar estado actual; persistir respuesta; preparar consumos/outputs atómicos sin duplicación.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No redefinir aún costing o receta; sólo replay y transición segura. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Start con faltantes, cancelación después de consumo, complete parcial, lote ya final y receta desactivada.

**Concurrencia y consistencia**
Dos transiciones concurrentes sobre el mismo lote deben serializar y producir un único estado terminal.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Start/cancel/complete replay; dos transiciones incompatibles; faltantes 409; crash tras movimientos; payload distinto.

**Validación y comandos**
Pruebas API PostgreSQL, E2E de transiciones, generación contractual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada transición ocurre una vez; replay devuelve el mismo estado; no se duplican reservas, consumos, salidas ni eventos.
Definition of Done específica: Cada transición ocurre una vez; replay devuelve el mismo estado; no se duplican reservas, consumos, salidas ni eventos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar máquina de estados de producción.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-036 — Serializar venta y cierre de turno

**Épica:** Concurrencia
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: el hecho relevante preserva atomicidad business mutation + canonical state/ledger + audit + outbox, identidad causal e idempotencia.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-036 |
| **2. Nombre de la tarea** | Serializar venta y cierre de turno |
| **3. Objetivo** | Garantizar que una venta se incluya antes del cierre o sea rechazada después, nunca quede asociada fuera de sus totales. |
| **4. Problema que resuelve** | Venta y cierre consultan sesión abierta sin `FOR UPDATE` común; la carrera fue identificada estáticamente. |
| **5. Hallazgo relacionado** | ZM-DATA-003; ZMA-DATA-002. |
| **6. Módulos afectados** | Sales, cash session, cash close y PostgreSQL. |
| **7. Archivos/áreas a inspeccionar** | `SaleCommandService`; `CashCloseService.commit_close`; queries de sesión; locks y orden de acceso. |
| **8. Dependencias previas** | ZM-FIN-005, ZM-FIN-029 y decisión de política de cierre. |
| **9. Cambios a implementar** | Definir orden único de locks; bloquear sesión en ambas transacciones; revalidar `OPEN`; traducir conflicto de forma recuperable. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Deadlock por orden inconsistente o contención excesiva de la sesión. |
| **13. Posibles regresiones** | Latencia de venta/cierre, errores 500 en conflicto o sesiones bloqueadas. |
| **14. Pruebas requeridas** | Dos conexiones coordinadas venta-vs-cierre; venta antes/después; doble cierre; timeout/deadlock; replay. |
| **15. Criterios de aceptación** | Estados finales sólo permiten: venta confirmada e incluida, o venta rechazada; nunca venta en sesión cerrada ausente del corte. |
| **16. Definition of Done específica** | Estados finales sólo permiten: venta confirmada e incluida, o venta rechazada; nunca venta en sesión cerrada ausente del corte. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Harness concurrente, trazas SQL/transaction ID y reconciliación final. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-049, ZM-FIN-065 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-036 — Serializar venta y cierre de turno**.

**Objetivo**
Garantizar que una venta se incluya antes del cierre o sea rechazada después, nunca quede asociada fuera de sus totales.

**Problema y contexto de ZeroMerma**
Venta y cierre consultan sesión abierta sin `FOR UPDATE` común; la carrera fue identificada estáticamente. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-DATA-003; ZMA-DATA-002.

**Dependencias que puedes asumir terminadas**
ZM-FIN-005, ZM-FIN-029 y decisión de política de cierre.

**Inspección inicial obligatoria**
Inspecciona todas las lecturas/locks de CashSession y el orden de commits en venta/cierre.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir orden único de locks; bloquear sesión en ambas transacciones; revalidar `OPEN`; traducir conflicto de forma recuperable.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No usar un mutex en memoria ni cambiar la UX salvo manejo mínimo del conflicto. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Cierre ya preparado, venta con timeout, sesión de otra estación, rollback y segundo cierre.

**Concurrencia y consistencia**
Es el núcleo de la tarea: coordina dos transacciones reales con barreras deterministas y repite el escenario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Dos conexiones coordinadas venta-vs-cierre; venta antes/después; doble cierre; timeout/deadlock; replay.

**Validación y comandos**
Ejecuta integración PostgreSQL con dos conexiones y regresión completa de venta/cierre. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Estados finales sólo permiten: venta confirmada e incluida, o venta rechazada; nunca venta en sesión cerrada ausente del corte.
Definition of Done específica: Estados finales sólo permiten: venta confirmada e incluida, o venta rechazada; nunca venta en sesión cerrada ausente del corte. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
ADR de locking y respuesta de conflicto.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-037 — Serializar pagos de pedido y movimientos de caja contra el cierre

**Épica:** Concurrencia
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: el hecho relevante preserva atomicidad business mutation + canonical state/ledger + audit + outbox, identidad causal e idempotencia.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-037 |
| **2. Nombre de la tarea** | Serializar pagos de pedido y movimientos de caja contra el cierre |
| **3. Objetivo** | Extender la garantía de cierre a todos los efectos financieros que pertenecen a la sesión. |
| **4. Problema que resuelve** | La liquidación de pedido se omitió del corte y otros movimientos pueden competir con el cierre si no bloquean la misma sesión. |
| **5. Hallazgo relacionado** | ZMA-FIN-001; ZM-DATA-003; ZMA-DATA-002. |
| **6. Módulos afectados** | Orders payments, operational payments, refunds, cash session/close. |
| **7. Archivos/áreas a inspeccionar** | Servicios de pago de pedido, pago operativo, devolución y cualquier creador de `CashMovement`. |
| **8. Dependencias previas** | ZM-FIN-036 y ZM-FIN-030–032. |
| **9. Cambios a implementar** | Adquirir el mismo lock/protocolo de sesión antes de todo efecto de caja; revalidar estado; documentar qué comandos se rechazan durante cierre. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Omitir un creador de cash movement o introducir locks en orden distinto. |
| **13. Posibles regresiones** | Flujos válidos de pedido/devolución dejan de funcionar cerca del cierre. |
| **14. Pruebas requeridas** | Pago pedido-vs-cierre; operativo-vs-cierre; refund-vs-cierre; dos movimientos simultáneos; retry tras conflicto. |
| **15. Criterios de aceptación** | Ningún movimiento confirmado queda fuera del corte; todo comando posterior al cierre es rechazado sin efecto. |
| **16. Definition of Done específica** | Ningún movimiento confirmado queda fuera del corte; todo comando posterior al cierre es rechazado sin efecto. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas concurrentes y ecuación de caja final. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-045–049 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-037 — Serializar pagos de pedido y movimientos de caja contra el cierre**.

**Objetivo**
Extender la garantía de cierre a todos los efectos financieros que pertenecen a la sesión.

**Problema y contexto de ZeroMerma**
La liquidación de pedido se omitió del corte y otros movimientos pueden competir con el cierre si no bloquean la misma sesión. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-FIN-001; ZM-DATA-003; ZMA-DATA-002.

**Dependencias que puedes asumir terminadas**
ZM-FIN-036 y ZM-FIN-030–032.

**Inspección inicial obligatoria**
Busca todos los lugares que crean pagos o `CashMovement` y su relación con CashSession.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Adquirir el mismo lock/protocolo de sesión antes de todo efecto de caja; revalidar estado; documentar qué comandos se rechazan durante cierre.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No rehacer todavía el cálculo de totales; asegurar primero el límite transaccional. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Pago sin turno, medio no efectivo, pago externo pendiente, refund parcial y sesión cambiada.

**Concurrencia y consistencia**
Coordinar cada tipo de movimiento contra el cierre con dos conexiones reales.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Pago pedido-vs-cierre; operativo-vs-cierre; refund-vs-cierre; dos movimientos simultáneos; retry tras conflicto.

**Validación y comandos**
Pruebas integración PostgreSQL y regresión POS/Backoffice relacionada. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Ningún movimiento confirmado queda fuera del corte; todo comando posterior al cierre es rechazado sin efecto.
Definition of Done específica: Ningún movimiento confirmado queda fuera del corte; todo comando posterior al cierre es rechazado sin efecto. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar protocolo de cierre y catálogo de movimientos incluidos.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-038 — Cerrar concurrencia de balances y primera fila de inventario

**Épica:** Concurrencia
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: el hecho relevante preserva atomicidad business mutation + canonical state/ledger + audit + outbox, identidad causal e idempotencia.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-038 |
| **2. Nombre de la tarea** | Cerrar concurrencia de balances y primera fila de inventario |
| **3. Objetivo** | Evitar dobles balances, pérdidas de actualización o errores no recuperables cuando se crea/actualiza stock concurrentemente. |
| **4. Problema que resuelve** | Las filas existentes usan algunos locks, pero la primera creación puede competir por la restricción única. |
| **5. Hallazgo relacionado** | Diagnóstico de concurrencia en ZM-DATA-004 y sección backend de la auditoría estática. |
| **6. Módulos afectados** | InventoryBalance, InventoryMovement, servicios de inventario y PostgreSQL. |
| **7. Archivos/áreas a inspeccionar** | Modelo/índices de balance; helpers de lock; todos los servicios que ajustan balance. |
| **8. Dependencias previas** | ZM-FIN-005 y política de inventario aprobada. |
| **9. Cambios a implementar** | Definir estrategia de upsert/insert-retry/lock advisory justificada; centralizar actualización; manejar `IntegrityError` sin perder movimiento. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Lost update, deadlock o movimiento persistido sin balance. |
| **13. Posibles regresiones** | Rendimiento de inventario y comportamiento de stock negativo. |
| **14. Pruebas requeridas** | Dos primeras entradas concurrentes; incrementos/decrementos; stock insuficiente; deadlock; rollback tras movimiento. |
| **15. Criterios de aceptación** | Existe una sola fila por clave; saldo final equivale a la suma de movimientos; errores de unicidad se recuperan de forma determinista. |
| **16. Definition of Done específica** | Existe una sola fila por clave; saldo final equivale a la suma de movimientos; errores de unicidad se recuperan de forma determinista. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas concurrentes y reconciliación movimiento→saldo. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-053–059 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-038 — Cerrar concurrencia de balances y primera fila de inventario**.

**Objetivo**
Evitar dobles balances, pérdidas de actualización o errores no recuperables cuando se crea/actualiza stock concurrentemente.

**Problema y contexto de ZeroMerma**
Las filas existentes usan algunos locks, pero la primera creación puede competir por la restricción única. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Diagnóstico de concurrencia en ZM-DATA-004 y sección backend de la auditoría estática.

**Dependencias que puedes asumir terminadas**
ZM-FIN-005 y política de inventario aprobada.

**Inspección inicial obligatoria**
Inspecciona restricciones únicas, locks, orden movimiento/balance y manejo de IntegrityError en cada servicio.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir estrategia de upsert/insert-retry/lock advisory justificada; centralizar actualización; manejar `IntegrityError` sin perder movimiento.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No introducir cachés de saldo ni base alternativa. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Primera fila, saldo cero, múltiples UOM, sucursales distintas y reintento tras unicidad.

**Concurrencia y consistencia**
Pruebas con múltiples conexiones sobre la misma y distintas claves de balance.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Dos primeras entradas concurrentes; incrementos/decrementos; stock insuficiente; deadlock; rollback tras movimiento.

**Validación y comandos**
Ejecuta integración PostgreSQL concurrente y reconciliación. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Existe una sola fila por clave; saldo final equivale a la suma de movimientos; errores de unicidad se recuperan de forma determinista.
Definition of Done específica: Existe una sola fila por clave; saldo final equivale a la suma de movimientos; errores de unicidad se recuperan de forma determinista. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Documentar política de lock/update de inventario.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-039 — Auditar y normalizar límites de commit/rollback

**Épica:** Transacciones
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: el hecho relevante preserva atomicidad business mutation + canonical state/ledger + audit + outbox, identidad causal e idempotencia.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-039 |
| **2. Nombre de la tarea** | Auditar y normalizar límites de commit/rollback |
| **3. Objetivo** | Asegurar que cada caso de uso crítico confirma o revierte todos sus efectos y que no hay `flush()` sin persistencia esperada. |
| **4. Problema que resuelve** | `last_login_at` quedó nulo y cada servicio maneja commits individualmente; pueden existir omisiones similares. |
| **5. Hallazgo relacionado** | ZMA-ID-001; diagnóstico backend de la auditoría estática. |
| **6. Módulos afectados** | API services, session lifecycle, audit, outbox y DB. |
| **7. Archivos/áreas a inspeccionar** | `get_session`; servicios con `commit/rollback/flush`; `AuthService.login`; excepciones traducidas a HTTP. |
| **8. Dependencias previas** | ZM-FIN-010 y casos de uso P0 caracterizados. |
| **9. Cambios a implementar** | Inventariar límites transaccionales; corregir commits omitidos; establecer convención/UoW ligera compatible; asegurar rollback y traducción de errores. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Refactor transversal excesivo o commits dobles en llamadas anidadas. |
| **13. Posibles regresiones** | Cambiar semántica de transacciones no críticas o cerrar sesión SQLAlchemy demasiado pronto. |
| **14. Pruebas requeridas** | Fallos inyectados antes/después de flush; IntegrityError; excepción de audit/outbox; login persistente; nested calls. |
| **15. Criterios de aceptación** | Cada caso de uso tiene dueño del commit; no hay efectos parciales; `last_login_at` persiste; rollback deja cero filas adicionales. |
| **16. Definition of Done específica** | Cada caso de uso tiene dueño del commit; no hay efectos parciales; `last_login_at` persiste; rollback deja cero filas adicionales. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Matriz caso de uso→transacción, pruebas de fallo inyectado y diff acotado. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-040 y todas las integraciones de ledgers. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-039 — Auditar y normalizar límites de commit/rollback**.

**Objetivo**
Asegurar que cada caso de uso crítico confirma o revierte todos sus efectos y que no hay `flush()` sin persistencia esperada.

**Problema y contexto de ZeroMerma**
`last_login_at` quedó nulo y cada servicio maneja commits individualmente; pueden existir omisiones similares. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-ID-001; diagnóstico backend de la auditoría estática.

**Dependencias que puedes asumir terminadas**
ZM-FIN-010 y casos de uso P0 caracterizados.

**Inspección inicial obligatoria**
Busca todos los `commit`, `rollback`, `flush`, context managers y servicios que llaman a otros servicios.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Inventariar límites transaccionales; corregir commits omitidos; establecer convención/UoW ligera compatible; asegurar rollback y traducción de errores.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No introducir un framework UoW complejo ni reescribir todos los servicios sin evidencia. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Excepción tras outbox, audit fallido, respuesta perdida, sesión reutilizada y operación read-only.

**Concurrencia y consistencia**
Verificar que la convención no amplíe locks más de lo necesario ni rompa las pruebas concurrentes.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Fallos inyectados antes/después de flush; IntegrityError; excepción de audit/outbox; login persistente; nested calls.

**Validación y comandos**
Ejecuta pruebas unitarias/integración por caso de uso y mypy/ruff. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada caso de uso tiene dueño del commit; no hay efectos parciales; `last_login_at` persiste; rollback deja cero filas adicionales.
Definition of Done específica: Cada caso de uso tiene dueño del commit; no hay efectos parciales; `last_login_at` persiste; rollback deja cero filas adicionales. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
ADR de límites transaccionales y patrón de servicio.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-040 — Unificar contexto de operación, auditoría y outbox

**Épica:** Trazabilidad
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Implementar event_id/type, schema_version, correlation_id, causation_id, entity_type/id, branch/workstation/actor, occurred_at, recorded_at y payload versionado.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-040 |
| **2. Nombre de la tarea** | Unificar contexto de operación, auditoría y outbox |
| **3. Objetivo** | Correlacionar request, usuario, superficie, sucursal, estación, turno, entidad, auditoría y evento en la misma transacción. |
| **4. Problema que resuelve** | Operaciones POS aparecen como BACKOFFICE, faltan estación/contexto y la observabilidad técnica no se correlaciona. |
| **5. Hallazgo relacionado** | ZM-OBS-017; ZMA-AUD-001; ZMA-ID-001. |
| **6. Módulos afectados** | Middleware, audit, outbox, API, POS, Backoffice y worker. |
| **7. Archivos/áreas a inspeccionar** | `AuditLog`; `OutboxEvent`; `_source_app`; request ID; metadatos de servicios; logging. |
| **8. Dependencias previas** | ZM-FIN-023–025 y ZM-FIN-039. |
| **9. Cambios a implementar** | Crear contexto tipado; exigir `source_app`; propagar operation/request/idempotency IDs; registrar sucursal/caja/estación/turno; eliminar fallback semántico incorrecto. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Alta cardinalidad, PII en logs o contexto mutable que se pierde en jobs. |
| **13. Posibles regresiones** | Cambiar formato de audit/reportes o romper consumidores de eventos. |
| **14. Pruebas requeridas** | Venta POS, acción Backoffice, job worker, cierre, denegación, request sin ID y ID inválido. |
| **15. Criterios de aceptación** | Una operación se rastrea con un ID común desde HTTP hasta audit/outbox; origen y contexto son correctos y no contienen secretos. |
| **16. Definition of Done específica** | Una operación se rastrea con un ID común desde HTTP hasta audit/outbox; origen y contexto son correctos y no contienen secretos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Filas correlacionadas, logs y pruebas de propagación. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Posible |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-073–077, ZM-FIN-089 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-040 — Unificar contexto de operación, auditoría y outbox**.

**Objetivo**
Correlacionar request, usuario, superficie, sucursal, estación, turno, entidad, auditoría y evento en la misma transacción.

**Problema y contexto de ZeroMerma**
Operaciones POS aparecen como BACKOFFICE, faltan estación/contexto y la observabilidad técnica no se correlaciona. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-OBS-017; ZMA-AUD-001; ZMA-ID-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-023–025 y ZM-FIN-039.

**Inspección inicial obligatoria**
Inspecciona creación de AuditLog/OutboxEvent, naming de acciones, middleware y metadatos POS/Backoffice.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Crear contexto tipado; exigir `source_app`; propagar operation/request/idempotency IDs; registrar sucursal/caja/estación/turno; eliminar fallback semántico incorrecto.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No usar logs técnicos como sustituto de AuditLog ni viceversa. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Request sin actor, job asíncrono, replay idempotente, acción cross-branch y error antes del commit.

**Concurrencia y consistencia**
Asegurar que contextos concurrentes no se mezclan entre requests/threads.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Posible. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Venta POS, acción Backoffice, job worker, cierre, denegación, request sin ID y ID inválido.

**Validación y comandos**
Pruebas de propagación, integración por superficie, mypy/ruff y generación contractual si cambia respuesta. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Una operación se rastrea con un ID común desde HTTP hasta audit/outbox; origen y contexto son correctos y no contienen secretos.
Definition of Done específica: Una operación se rastrea con un ID común desde HTTP hasta audit/outbox; origen y contexto son correctos y no contienen secretos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Catálogo de contexto/auditoría y esquema de correlación.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```


## Fase 4 — Ledgers canónicos y Data Integrity — Tareas ejecutables

### ZM-FIN-041 — Definir el modelo canónico de movimientos financieros y caja

**Épica:** Ledger financiero
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: fuente canónica granular, Decimal/Numeric o UOM, lineage, reconciliación, validez y rebuild para KPI aplicables.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-041 |
| **2. Nombre de la tarea** | Definir el modelo canónico de movimientos financieros y caja |
| **3. Objetivo** | Establecer una fuente única y causal para todo ingreso, egreso, medio de pago, ajuste y reversa. |
| **4. Problema que resuelve** | Ventas y pagos existen, pero la liquidación de pedido no entra en caja/corte y los reportes interpretan pagos de forma inconsistente. |
| **5. Hallazgo relacionado** | ZMA-FIN-001; ZMA-REP-001; diagnóstico de caja de ambas auditorías. |
| **6. Módulos afectados** | Sales, orders, payments, cash movements, refunds, operational payments, cash close y reports. |
| **7. Archivos/áreas a inspeccionar** | Modelos `SalePayment`, `CashMovement`, pagos de pedido, cierres, servicios de reportes y enums de métodos. |
| **8. Dependencias previas** | ZM-FIN-003, ZM-FIN-028–040. |
| **9. Cambios a implementar** | Diseñar catálogo de tipos/signos/causas; referencia causal; estado pendiente/confirmado/revertido; relación con sesión; proyección de esperado; inmutabilidad y compensación; representar opening economic state explícito sin importar efectos demo/test ni fabricar historia. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Crear un segundo ledger paralelo sin migrar consumidores o confundir autorización de pago con liquidación real. |
| **13. Posibles regresiones** | Reportes/cierres históricos cambian sin explicación o se duplican movimientos existentes. |
| **14. Pruebas requeridas** | Ejemplos de venta, pedido, devolución, pago operativo, descuento/cargo, efectivo, tarjeta y mixto; constraints y redondeo. |
| **15. Criterios de aceptación** | Cada flujo financiero aprobado y todo opening state tienen una única regla/referencia; no hay doble conteo entre tablas; la ecuación de caja es derivable y ninguna fila demo/test participa en historia productiva. |
| **16. Definition of Done específica** | Cada flujo financiero aprobado tiene una única regla y referencia; no hay doble conteo entre tablas; la ecuación de caja es derivable. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | ADR/diccionario financiero, migración propuesta y casos numéricos aprobados. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | Posible |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-042–047 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-041 — Definir el modelo canónico de movimientos financieros y caja**.

**Objetivo**
Establecer una fuente única y causal para todo ingreso, egreso, medio de pago, ajuste y reversa.

**Problema y contexto de ZeroMerma**
Ventas y pagos existen, pero la liquidación de pedido no entra en caja/corte y los reportes interpretan pagos de forma inconsistente. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-FIN-001; ZMA-REP-001; diagnóstico de caja de ambas auditorías.

**Dependencias que puedes asumir terminadas**
ZM-FIN-003, ZM-FIN-028–040.

**Inspección inicial obligatoria**
Inspecciona todos los modelos y servicios que representan dinero, incluidas tablas separadas de pedidos y caja.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Diseñar catálogo de tipos/signos/causas; referencia causal; estado pendiente/confirmado/revertido; relación con sesión; proyección de esperado; inmutabilidad y compensación.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No introducir contabilidad general completa ni integración bancaria fuera del alcance aprobado. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Pago mixto, devolución parcial, tarjeta pendiente, cambio en efectivo, propina si existe, cancelación y moneda única/múltiple.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: Posible. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Ejemplos de venta, pedido, devolución, pago operativo, descuento/cargo, efectivo, tarjeta y mixto; constraints y redondeo.

**Validación y comandos**
Ejecuta pruebas de dominio del modelo y migración en DB efímera; no backfillear datos todavía. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada flujo financiero aprobado tiene una única regla y referencia; no hay doble conteo entre tablas; la ecuación de caja es derivable.
Definition of Done específica: Cada flujo financiero aprobado tiene una única regla y referencia; no hay doble conteo entre tablas; la ecuación de caja es derivable. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
ADR y diccionario de ledger financiero con ejemplos de ecuaciones.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-042 — Integrar pagos de pedidos en flujo de efectivo y corte

**Épica:** Ledger financiero
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: fuente canónica granular, Decimal/Numeric o UOM, lineage, reconciliación, validez y rebuild para KPI aplicables.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-042 |
| **2. Nombre de la tarea** | Integrar pagos de pedidos en flujo de efectivo y corte |
| **3. Objetivo** | Eliminar la diferencia artificial observada y hacer que el pago de pedido pertenezca a la sesión correcta. |
| **4. Problema que resuelve** | Un pago de pedido de 6.00 quedó fuera de `cash_movements`; el cierre esperó 521.00 en vez de 527.00. |
| **5. Hallazgo relacionado** | ZMA-FIN-001. |
| **6. Módulos afectados** | Orders, order payments, cash movements, cash close, POS y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Servicio de pago de pedido; modelos `customer_order_payments`/`CashMovement`; cash-flow/cuts; UI de pedido. |
| **8. Dependencias previas** | ZM-FIN-030, ZM-FIN-037 y ZM-FIN-041. |
| **9. Cambios a implementar** | Crear el movimiento financiero/caja en la misma transacción del pago; vincular pedido/sesión/actor; incluirlo una sola vez en resumen/cierre y reversas. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Doble conteo si el pago ya alimenta otra fuente o reconocer pago antes de confirmación real. |
| **13. Posibles regresiones** | Totales de cierres existentes, reportes y cancelaciones de pedido. |
| **14. Pruebas requeridas** | Pago efectivo/tarjeta/mixto; sin sesión; sesión cerrándose; replay; cancelación/refund; cierre con conteo. |
| **15. Criterios de aceptación** | Todo pago confirmado de pedido aparece una vez en flujo y corte; el caso auditado produce esperado 527.00 y diferencia 0.00. |
| **16. Definition of Done específica** | Todo pago confirmado de pedido aparece una vez en flujo y corte; el caso auditado produce esperado 527.00 y diferencia 0.00. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Prueba de reproducción del caso auditado, IDs cruzados y ecuación de caja. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-045, ZM-FIN-062 y ZM-FIN-080. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-042 — Integrar pagos de pedidos en flujo de efectivo y corte**.

**Objetivo**
Eliminar la diferencia artificial observada y hacer que el pago de pedido pertenezca a la sesión correcta.

**Problema y contexto de ZeroMerma**
Un pago de pedido de 6.00 quedó fuera de `cash_movements`; el cierre esperó 521.00 en vez de 527.00. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-FIN-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-030, ZM-FIN-037 y ZM-FIN-041.

**Inspección inicial obligatoria**
Inspecciona el commit de pago de pedido, cash flow, cash close y cualquier outbox/audit asociado.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Crear el movimiento financiero/caja en la misma transacción del pago; vincular pedido/sesión/actor; incluirlo una sola vez en resumen/cierre y reversas.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No cambiar otras reglas de pedido salvo las necesarias para el efecto financiero. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Pago parcial, entrega antes/después del pago, método no efectivo, sesión distinta y refund.

**Concurrencia y consistencia**
Probar pago-vs-cierre y dos pagos concurrentes del saldo restante.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Pago efectivo/tarjeta/mixto; sin sesión; sesión cerrándose; replay; cancelación/refund; cierre con conteo.

**Validación y comandos**
Pruebas API PostgreSQL, E2E POS/Backoffice, generación contractual y reconciliación. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Todo pago confirmado de pedido aparece una vez en flujo y corte; el caso auditado produce esperado 527.00 y diferencia 0.00.
Definition of Done específica: Todo pago confirmado de pedido aparece una vez en flujo y corte; el caso auditado produce esperado 527.00 y diferencia 0.00. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar regla de reconocimiento de pedido y manual de caja.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-043 — Unificar ventas y pagos operativos en el ledger financiero

**Épica:** Ledger financiero
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: fuente canónica granular, Decimal/Numeric o UOM, lineage, reconciliación, validez y rebuild para KPI aplicables.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-043 |
| **2. Nombre de la tarea** | Unificar ventas y pagos operativos en el ledger financiero |
| **3. Objetivo** | Asegurar que venta, cobro, cambio y pagos/cargos operativos usan la misma semántica causal y de sesión. |
| **4. Problema que resuelve** | Las ventas tienen persistencia monetaria real y los pagos operativos un flujo separado; se requiere una fuente reconciliable común. |
| **5. Hallazgo relacionado** | Diagnóstico de ventas/pagos; ZMA-FIN-001; ZM-DATA-003. |
| **6. Módulos afectados** | Sales, payments, operational payments, cash, audit, reports. |
| **7. Archivos/áreas a inspeccionar** | Servicios de confirmación de venta; `SalePayment`; `CashMovement`; pagos/descuentos operativos; resúmenes. |
| **8. Dependencias previas** | ZM-FIN-029, ZM-FIN-032, ZM-FIN-037 y ZM-FIN-041. |
| **9. Cambios a implementar** | Mapear cada pago/entrada/salida al catálogo; persistir referencia causal; eliminar cálculos paralelos; mantener cambio y totales decimales. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Doble conteo durante transición o mezclar valor de venta con efectivo recibido/cambio. |
| **13. Posibles regresiones** | Tickets, cash flow y cierres cambian sus totales. |
| **14. Pruebas requeridas** | Efectivo, tarjeta, mixto, cambio, entrada/salida operativa, fondo inicial, replay y cierre. |
| **15. Criterios de aceptación** | Cada efecto aparece una vez; ventas y movimientos operativos se explican por IDs causales; los totales coinciden entre API/DB/reportes. |
| **16. Definition of Done específica** | Cada efecto aparece una vez; ventas y movimientos operativos se explican por IDs causales; los totales coinciden entre API/DB/reportes. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Reconciliación por sesión y pruebas de todos los métodos. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Posible |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-045, ZM-FIN-065 y reportes confiables. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-043 — Unificar ventas y pagos operativos en el ledger financiero**.

**Objetivo**
Asegurar que venta, cobro, cambio y pagos/cargos operativos usan la misma semántica causal y de sesión.

**Problema y contexto de ZeroMerma**
Las ventas tienen persistencia monetaria real y los pagos operativos un flujo separado; se requiere una fuente reconciliable común. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Diagnóstico de ventas/pagos; ZMA-FIN-001; ZM-DATA-003.

**Dependencias que puedes asumir terminadas**
ZM-FIN-029, ZM-FIN-032, ZM-FIN-037 y ZM-FIN-041.

**Inspección inicial obligatoria**
Inspecciona cómo se calculan subtotal/total/paid/change y qué tablas alimentan cada reporte.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Mapear cada pago/entrada/salida al catálogo; persistir referencia causal; eliminar cálculos paralelos; mantener cambio y totales decimales.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No añadir nuevas promociones o métodos de pago. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Pago superior, redondeo, venta cero no permitida, tarjeta sin efectivo, movimiento operativo sin sesión.

**Concurrencia y consistencia**
Probar múltiples ventas/movimientos simultáneos en la misma sesión bajo el lock definido.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Posible. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Efectivo, tarjeta, mixto, cambio, entrada/salida operativa, fondo inicial, replay y cierre.

**Validación y comandos**
Pruebas de integración, reconciliación SQL y regresión POS/Backoffice. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada efecto aparece una vez; ventas y movimientos operativos se explican por IDs causales; los totales coinciden entre API/DB/reportes.
Definition of Done específica: Cada efecto aparece una vez; ventas y movimientos operativos se explican por IDs causales; los totales coinciden entre API/DB/reportes. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Diccionario de movimientos y ejemplos de caja.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-044 — Integrar devoluciones, reembolsos y reversas financieras

**Épica:** Ledger financiero
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: fuente canónica granular, Decimal/Numeric o UOM, lineage, reconciliación, validez y rebuild para KPI aplicables.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-044 |
| **2. Nombre de la tarea** | Integrar devoluciones, reembolsos y reversas financieras |
| **3. Objetivo** | Representar toda devolución de dinero como compensación causal y conciliable. |
| **4. Problema que resuelve** | La devolución en efectivo existe, pero la reversión bancaria no está implementada y los efectos no están unificados. |
| **5. Hallazgo relacionado** | ZM-DATA-004; elementos no verificables de reversión bancaria; ZMA-FIN-001. |
| **6. Módulos afectados** | Returns, refunds, payments, cash, external payment adapter, reports. |
| **7. Archivos/áreas a inspeccionar** | Servicios de devolución; modelos de refund; cash movements; provider/terminal interfaces si existen. |
| **8. Dependencias previas** | ZM-FIN-031, ZM-FIN-041 y decisión de métodos reembolsables. |
| **9. Cambios a implementar** | Crear movimientos compensatorios; estados pending/succeeded/failed; enlazar al pago original; manejar reversión externa sin marcar éxito prematuro. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Marcar un refund externo como exitoso sin confirmación o duplicarlo tras timeout. |
| **13. Posibles regresiones** | Devoluciones en efectivo existentes y reportes de net sales. |
| **14. Pruebas requeridas** | Refund efectivo/tarjeta/mixto; parcial; provider timeout; replay; cierre concurrente; monto acumulado. |
| **15. Criterios de aceptación** | No se reembolsa más de lo pagado; cada reversa se rastrea al pago original; caja/corte reflejan sólo efectos confirmados. |
| **16. Definition of Done específica** | No se reembolsa más de lo pagado; cada reversa se rastrea al pago original; caja/corte reflejan sólo efectos confirmados. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Grafo venta→pago→refund, respuestas de proveedor simuladas y reconciliación. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-046, ZM-FIN-067 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-044 — Integrar devoluciones, reembolsos y reversas financieras**.

**Objetivo**
Representar toda devolución de dinero como compensación causal y conciliable.

**Problema y contexto de ZeroMerma**
La devolución en efectivo existe, pero la reversión bancaria no está implementada y los efectos no están unificados. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-DATA-004; elementos no verificables de reversión bancaria; ZMA-FIN-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-031, ZM-FIN-041 y decisión de métodos reembolsables.

**Inspección inicial obligatoria**
Inspecciona refund actual, métodos de pago, estados y cualquier integración/placeholder de terminal.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Crear movimientos compensatorios; estados pending/succeeded/failed; enlazar al pago original; manejar reversión externa sin marcar éxito prematuro.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No fingir soporte bancario real sin un proveedor y certificación aprobados. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Pago mixto, reversión parcial, método no reversible, provider offline, pago antiguo y sesión cerrada.

**Concurrencia y consistencia**
Dos refunds concurrentes deben respetar el saldo reembolsable acumulado.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Refund efectivo/tarjeta/mixto; parcial; provider timeout; replay; cierre concurrente; monto acumulado.

**Validación y comandos**
Pruebas integración con adapter fake, replay, reconciliación y generación contractual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
No se reembolsa más de lo pagado; cada reversa se rastrea al pago original; caja/corte reflejan sólo efectos confirmados.
Definition of Done específica: No se reembolsa más de lo pagado; cada reversa se rastrea al pago original; caja/corte reflejan sólo efectos confirmados. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Política de refund/reversa y runbook de fallo externo.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-045 — Definir pagos mixtos y recalcular el cierre desde la fuente canónica

**Épica:** Conciliación
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: fuente canónica granular, Decimal/Numeric o UOM, lineage, reconciliación, validez y rebuild para KPI aplicables.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-045 |
| **2. Nombre de la tarea** | Definir pagos mixtos y recalcular el cierre desde la fuente canónica |
| **3. Objetivo** | Corregir la semántica de método mixto y hacer reproducible esperado, contado y variación por sesión/medio. |
| **4. Problema que resuelve** | Una venta con filas CASH y CARD no contó como mixta; tarjeta tenía esperado/diferencia nulos y el cierre omitió pedidos. |
| **5. Hallazgo relacionado** | ZMA-REP-001; ZMA-FIN-001. |
| **6. Módulos afectados** | Cash close, reports, payments, POS/Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Servicio de cierre; reportes de payment methods; modelos de conteo; UI de cortes/conciliación. |
| **8. Dependencias previas** | ZM-FIN-041–044 y decisión de pago mixto/cierre. |
| **9. Cambios a implementar** | Derivar clasificación a nivel venta; calcular esperado por medio; definir qué medios se cuentan; explicar variación; eliminar queries que buscan un código MIXED inexistente. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Cambiar métricas históricas sin versión o mezclar total de venta con total por medio. |
| **13. Posibles regresiones** | Reportes y UI de cierre muestran cifras distintas o más campos nulos. |
| **14. Pruebas requeridas** | Venta sólo cash/card, dos métodos, tres componentes, refund, pedido, operativo, cierre con/sin conteo y redondeo. |
| **15. Criterios de aceptación** | El reporte identifica ventas mixtas según regla aprobada; el cierre satisface ecuaciones documentadas y toda variación es explicable por movimientos. |
| **16. Definition of Done específica** | El reporte identifica ventas mixtas según regla aprobada; el cierre satisface ecuaciones documentadas y toda variación es explicable por movimientos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Casos numéricos, queries reconciliadas y E2E de corte. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-071, ZM-FIN-080 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-045 — Definir pagos mixtos y recalcular el cierre desde la fuente canónica**.

**Objetivo**
Corregir la semántica de método mixto y hacer reproducible esperado, contado y variación por sesión/medio.

**Problema y contexto de ZeroMerma**
Una venta con filas CASH y CARD no contó como mixta; tarjeta tenía esperado/diferencia nulos y el cierre omitió pedidos. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-REP-001; ZMA-FIN-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-041–044 y decisión de pago mixto/cierre.

**Inspección inicial obligatoria**
Inspecciona todas las queries de métodos y cómo se persisten múltiples `SalePayment` por venta.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Derivar clasificación a nivel venta; calcular esperado por medio; definir qué medios se cuentan; explicar variación; eliminar queries que buscan un código MIXED inexistente.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No introducir métricas comerciales sin definición aprobada. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Una sola fila con código legacy MIXED, tarjeta contable/no contable, monto cero y refunds parciales.

**Concurrencia y consistencia**
Validar que el snapshot de cierre se calcula bajo el lock y no cambia durante conteo/commit.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Venta sólo cash/card, dos métodos, tres componentes, refund, pedido, operativo, cierre con/sin conteo y redondeo.

**Validación y comandos**
Pruebas de dominio, integración SQL y E2E de cierre/reportes. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
El reporte identifica ventas mixtas según regla aprobada; el cierre satisface ecuaciones documentadas y toda variación es explicable por movimientos.
Definition of Done específica: El reporte identifica ventas mixtas según regla aprobada; el cierre satisface ecuaciones documentadas y toda variación es explicable por movimientos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Definición métrica de venta mixta y ecuaciones de cierre.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-046 — Implementar la frontera de terminal y liquidación de pagos electrónicos

**Épica:** Pagos externos
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: fuente canónica granular, Decimal/Numeric o UOM, lineage, reconciliación, validez y rebuild para KPI aplicables.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-046 |
| **2. Nombre de la tarea** | Implementar la frontera de terminal y liquidación de pagos electrónicos |
| **3. Objetivo** | Separar autorización/captura/liquidación/reversa del proveedor de la lógica central sin comprometer idempotencia. |
| **4. Problema que resuelve** | La terminal bancaria y reversión real están ausentes; los pagos tarjeta actuales son registros internos. |
| **5. Hallazgo relacionado** | Funcionalidad ausente y elemento no verificable de hardware/pagos. |
| **6. Módulos afectados** | Payments, terminal adapter, POS, worker/outbox, reconciliation y secrets. |
| **7. Archivos/áreas a inspeccionar** | Interfaces de métodos de pago; POS payment UI; configuración; outbox; provider clients futuros. |
| **8. Dependencias previas** | ZM-FIN-003, ZM-FIN-024, ZM-FIN-028, ZM-FIN-041 y proveedor/hardware aprobado. |
| **9. Cambios a implementar** | Implementar adapter/provider boundary BBVA; estados; binding workstation-terminal; idempotency provider/client; timeout/retry; webhook/polling; `UNKNOWN` recovery; separación sandbox/production; conciliación, refund/reversa, observabilidad y gate BBVA/PCI antes del piloto final en Sucursal Matriz. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Cobro doble, inconsistencia proveedor/local, manejo de datos sensibles y dependencia de red. |
| **13. Posibles regresiones** | Pagos manuales existentes o cierre de caja con tarjeta. |
| **14. Pruebas requeridas** | Aprobado/rechazado/timeout/duplicado; respuesta perdida; webhook repetido; terminal offline; refund; cierre con pago pendiente. |
| **15. Criterios de aceptación** | BBVA integrado sólo se habilita tras DEC-14 implementada y gate BBVA/PCI; no atraviesan datos sensibles prohibidos; un pago no confirma sin evidencia; retries no duplican; `UNKNOWN`, callbacks, refund/reversa y conciliación pasan; si no está listo, `FINAL_PILOT_START=POSTPONED`. |
| **16. Definition of Done específica** | Un pago electrónico no se marca confirmado sin evidencia; retries no duplican cargo; estados pendientes son visibles y conciliables. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas contractuales con fake provider, certificación del hardware/proveedor y trazabilidad completa. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-056, ZM-FIN-069 y Gate Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-046 — Implementar la frontera de terminal y liquidación de pagos electrónicos**.

**Objetivo**
Separar autorización/captura/liquidación/reversa del proveedor de la lógica central sin comprometer idempotencia.

**Problema y contexto de ZeroMerma**
La terminal bancaria y reversión real están ausentes; los pagos tarjeta actuales son registros internos. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Funcionalidad ausente y elemento no verificable de hardware/pagos.

**Dependencias que puedes asumir terminadas**
ZM-FIN-003, ZM-FIN-024, ZM-FIN-028, ZM-FIN-041 y proveedor/hardware aprobado.

**Inspección inicial obligatoria**
Inspecciona cómo se representa CARD hoy, configuración, placeholders de terminal y necesidades del hardware objetivo.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Diseñar adapter; estados; idempotency provider/client; timeout/retry; webhook/polling; modo manual controlado; conciliación y reversa.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No almacenar PAN/CVV ni declarar cumplimiento/certificación sin evidencia del proveedor. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Offline, timeout post-cargo, terminal distinta, webhook tardío, reversa parcial, moneda/centavos.

**Concurrencia y consistencia**
Probar retries concurrentes y webhook/poll simultáneos con la misma referencia externa.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Aprobado/rechazado/timeout/duplicado; respuesta perdida; webhook repetido; terminal offline; refund; cierre con pago pendiente.

**Validación y comandos**
Pruebas con adapter fake, integración sandbox aprobada, E2E en hardware y escaneo de secretos. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Un pago electrónico no se marca confirmado sin evidencia; retries no duplican cargo; estados pendientes son visibles y conciliables.
Definition of Done específica: Un pago electrónico no se marca confirmado sin evidencia; retries no duplican cargo; estados pendientes son visibles y conciliables. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
ADR de pagos externos, runbook y manual POS.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-047 — Diagnosticar, backfillear y reconciliar datos financieros existentes

**Épica:** Reconciliación
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: fuente canónica granular, Decimal/Numeric o UOM, lineage, reconciliación, validez y rebuild para KPI aplicables.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-047 |
| **2. Nombre de la tarea** | Diagnosticar, backfillear y reconciliar datos financieros existentes |
| **3. Objetivo** | Diagnosticar y reconciliar opening state, staging o cualquier fuente real futura; backfillear sólo evidencia legítima sin perder trazabilidad ni reescribir historia silenciosamente. |
| **4. Problema que resuelve** | El lanzamiento actual es clean-start y los volúmenes conocidos son demo/test, pero opening state y una fuente real futura deben tratarse de forma idempotente; los defectos observados en datos no productivos siguen siendo casos representativos de regresión. |
| **5. Hallazgo relacionado** | ZMA-FIN-001; ZMA-REP-001; ZM-REL-015. |
| **6. Módulos afectados** | DB financiera, cash closes, orders, sales, payments, audit y reporting. |
| **7. Archivos/áreas a inspeccionar** | Tablas financieras; scripts de backfill; migraciones de datos; queries de reconciliación. |
| **8. Dependencias previas** | ZM-FIN-041–046 y DEC-19. |
| **9. Cambios a implementar** | Construir diagnóstico read-only; rechazar demo/test como historia productiva; clasificar diferencias; soportar opening state y fuentes reales futuras; diseñar backfill idempotente/reanudable; reconciliar antes/después; generar compensaciones o recalcular proyecciones sólo según reglas aprobadas. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Corregir datos con reglas equivocadas o perder evidencia histórica. |
| **13. Posibles regresiones** | Cierres/reportes históricos cambian sin versión o backfill bloquea producción. |
| **14. Pruebas requeridas** | Dry run; datos completos/incompletos/duplicados; interrupción/reanudación; comparación antes/después; rollback/restore. |
| **15. Criterios de aceptación** | Ningún dato demo/test se backfillea a producción; cada diferencia real tiene causa/tratamiento; opening state conserva evidencia; backfill no duplica; totales antes/después reconcilian y no se inventa ledger history ni se modifica evidencia original sin compensación. |
| **16. Definition of Done específica** | Cada diferencia tiene causa y tratamiento; backfill no duplica; totales reconciliados y auditables; no se modifica evidencia original sin compensación. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Informe de dry run, hashes/conteos, script/migración y reconciliación firmada. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Data Integrity Ready y reportes confiables. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-047 — Diagnosticar, backfillear y reconciliar datos financieros existentes**.

**Objetivo**
Corregir datos históricos afectados por omisiones sin perder trazabilidad ni reescribir historia silenciosamente.

**Problema y contexto de ZeroMerma**
El entorno activo ya mostró un cierre con diferencia artificial y pueden existir pagos/movimientos previos no representados. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-FIN-001; ZMA-REP-001; ZM-REL-015.

**Dependencias que puedes asumir terminadas**
ZM-FIN-041–046 y decisión sobre datos operativos reales.

**Inspección inicial obligatoria**
Inspecciona volumen, versiones de esquema y todas las fuentes históricas antes de escribir.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Construir diagnóstico read-only; clasificar diferencias; diseñar backfill idempotente/reanudable; generar compensaciones o recalcular proyecciones según reglas aprobadas.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No editar manualmente filas ni borrar documentos para cuadrar totales. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Fila huérfana, pago sin sesión, cierre ya aprobado, duplicado, zona horaria y ejecución parcial.

**Concurrencia y consistencia**
El backfill debe convivir con escritura o exigir ventana controlada explícita; probar reanudación.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Dry run; datos completos/incompletos/duplicados; interrupción/reanudación; comparación antes/después; rollback/restore.

**Validación y comandos**
Ejecuta primero dry run de sólo lectura; después en copia restaurada; nunca iniciar sobre producción sin gate. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada diferencia tiene causa y tratamiento; backfill no duplica; totales reconciliados y auditables; no se modifica evidencia original sin compensación.
Definition of Done específica: Cada diferencia tiene causa y tratamiento; backfill no duplica; totales reconciliados y auditables; no se modifica evidencia original sin compensación. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Runbook de backfill, criterio de aprobación y resultados.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-048 — Definir política, taxonomía, unidades y reservas de inventario

**Épica:** Ledger de inventario
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: fuente canónica granular, Decimal/Numeric o UOM, lineage, reconciliación, validez y rebuild para KPI aplicables.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-048 |
| **2. Nombre de la tarea** | Definir política, taxonomía, unidades y reservas de inventario |
| **3. Objetivo** | Crear una semántica única para todo efecto físico antes de integrar los flujos. |
| **4. Problema que resuelve** | El inventario está fragmentado; venta/devolución carecen de tipos canónicos y la política de stock negativo no está cerrada. |
| **5. Hallazgo relacionado** | ZM-DATA-004; ZMA-DATA-001; ZMA-WASTE-001. |
| **6. Módulos afectados** | Inventory, catalog/UOM, sales modes, orders, transfers, purchases y production. |
| **7. Archivos/áreas a inspeccionar** | `InventoryMovement`; `InventoryBalance`; UOM/product models; services por flujo; reglas `PRODUCT_DIRECT`/`CLASS_CAPTURE`. |
| **8. Dependencias previas** | ZM-FIN-003, ZM-FIN-038 y decisiones de stock/unidades/reservas. |
| **9. Cambios a implementar** | Definir tipos/signos, causa/documento, UOM/conversión, reserva vs on-hand, stock negativo, costo, reversa y momento de afectación por flujo. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Doble afectación, conversiones incorrectas o permitir stock negativo sin control. |
| **13. Posibles regresiones** | Compras/producción/transferencias actuales cambian semántica. |
| **14. Pruebas requeridas** | Matriz evento→movimiento; unidades compatibles/incompatibles; reserva/liberación; stock insuficiente; reversa y replay. |
| **15. Criterios de aceptación** | Cada flujo físico aprobado y todo opening inventory state tienen una sola regla; el primer saldo productivo procede de conteo/opening state aprobado, no de seed/demo; no existe doble descuento entre venta y conciliación y el saldo es reconstruible. |
| **16. Definition of Done específica** | Cada flujo físico aprobado tiene una sola regla; no existe doble descuento entre venta y conciliación; saldo es reconstruible. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | ADR/diccionario, migración de enums/constraints y ejemplos de reconciliación. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | Posible |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-049–055 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-048 — Definir política, taxonomía, unidades y reservas de inventario**.

**Objetivo**
Crear una semántica única para todo efecto físico antes de integrar los flujos.

**Problema y contexto de ZeroMerma**
El inventario está fragmentado; venta/devolución carecen de tipos canónicos y la política de stock negativo no está cerrada. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-DATA-004; ZMA-DATA-001; ZMA-WASTE-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-003, ZM-FIN-038 y decisiones de stock/unidades/reservas.

**Inspección inicial obligatoria**
Inspecciona todos los creadores de InventoryMovement, campos de unidad/costo y documentos POS que hoy no lo crean.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir tipos/signos, causa/documento, UOM/conversión, reserva vs on-hand, stock negativo, costo, reversa y momento de afectación por flujo.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No introducir forecasting ni un WMS separado. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Producto terminado vs insumo, unidad fraccional, devolución no vendible, reserva de pedido y sucursal origen/destino.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: Posible. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Matriz evento→movimiento; unidades compatibles/incompatibles; reserva/liberación; stock insuficiente; reversa y replay.

**Validación y comandos**
Pruebas de dominio y migración en DB efímera; no integrar flujos aún. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada flujo físico aprobado tiene una sola regla; no existe doble descuento entre venta y conciliación; saldo es reconstruible.
Definition of Done específica: Cada flujo físico aprobado tiene una sola regla; no existe doble descuento entre venta y conciliación; saldo es reconstruible. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Diccionario de inventario y decisiones de stock/UOM.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-049 — Integrar venta directa con inventario canónico

**Épica:** Ledger de inventario
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: fuente canónica granular, Decimal/Numeric o UOM, lineage, reconciliación, validez y rebuild para KPI aplicables.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-049 |
| **2. Nombre de la tarea** | Integrar venta directa con inventario canónico |
| **3. Objetivo** | Descontar stock `PRODUCT_DIRECT` en la misma transacción de venta sin duplicación. |
| **4. Problema que resuelve** | Las ventas directas activas no produjeron balance/movimiento; el POS y Backoffice divergen del ledger. |
| **5. Hallazgo relacionado** | ZM-DATA-004; ZMA-DATA-001. |
| **6. Módulos afectados** | Sales, inventory, POS, audit y outbox. |
| **7. Archivos/áreas a inspeccionar** | `SaleCommandService`; líneas de venta; Inventory service; product availability; pruebas. |
| **8. Dependencias previas** | ZM-FIN-029, ZM-FIN-038 y ZM-FIN-048. |
| **9. Cambios a implementar** | Crear movimiento por línea según UOM; actualizar balance con lock; aplicar política de stock; vincular sale/line; confirmar todo atómicamente. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Doble descuento, deadlock o rechazo tardío después del cobro. |
| **13. Posibles regresiones** | Venta existente, disponibilidad POS, tiempos de respuesta y stock negativo. |
| **14. Pruebas requeridas** | Stock suficiente/insuficiente/negativo permitido; múltiples líneas; replay; rollback; dos ventas concurrentes. |
| **15. Criterios de aceptación** | Venta, pago, caja, inventario, audit y outbox confirman o revierten juntos; replay no descuenta dos veces. |
| **16. Definition of Done específica** | Venta, pago, caja, inventario, audit y outbox confirman o revierten juntos; replay no descuenta dos veces. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Grafo sale line→movement→balance y reconciliación antes/después. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-060, ZM-FIN-080 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-049 — Integrar venta directa con inventario canónico**.

**Objetivo**
Descontar stock `PRODUCT_DIRECT` en la misma transacción de venta sin duplicación.

**Problema y contexto de ZeroMerma**
Las ventas directas activas no produjeron balance/movimiento; el POS y Backoffice divergen del ledger. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-DATA-004; ZMA-DATA-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-029, ZM-FIN-038 y ZM-FIN-048.

**Inspección inicial obligatoria**
Inspecciona orden actual de validación/cobro/commit y cómo se identifica producto/UOM en líneas.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Crear movimiento por línea según UOM; actualizar balance con lock; aplicar política de stock; vincular sale/line; confirmar todo atómicamente.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No integrar `CLASS_CAPTURE` en esta tarea. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Producto inactivo, stock exacto, cantidad fraccional, múltiple sucursal, cambio de precio y replay.

**Concurrencia y consistencia**
Dos ventas simultáneas del último stock deben cumplir la política aprobada sin lost update.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Stock suficiente/insuficiente/negativo permitido; múltiples líneas; replay; rollback; dos ventas concurrentes.

**Validación y comandos**
Pruebas integración PostgreSQL, replay, concurrencia, E2E POS y generación contractual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Venta, pago, caja, inventario, audit y outbox confirman o revierten juntos; replay no descuenta dos veces.
Definition of Done específica: Venta, pago, caja, inventario, audit y outbox confirman o revierten juntos; replay no descuenta dos veces. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar flujo de venta y política de disponibilidad.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-050 — Integrar `CLASS_CAPTURE` y conciliación física

**Épica:** Ledger de inventario
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: fuente canónica granular, Decimal/Numeric o UOM, lineage, reconciliación, validez y rebuild para KPI aplicables.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-050 |
| **2. Nombre de la tarea** | Integrar `CLASS_CAPTURE` y conciliación física |
| **3. Objetivo** | Representar correctamente la captura por clase sin descontar dos veces ni perder atribución al producto real. |
| **4. Problema que resuelve** | La venta por clase tiene conciliación física posterior, pero no converge de forma demostrable con el ledger canónico. |
| **5. Hallazgo relacionado** | ZM-DATA-004; ZMA-DATA-001. |
| **6. Módulos afectados** | Sales class capture, reconciliation, catalog/classes, inventory, POS/Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Servicios de captura/conciliación; modelos de atribución física; InventoryMovement; pantallas relacionadas. |
| **8. Dependencias previas** | ZM-FIN-048 y decisión aprobada del momento de afectación. |
| **9. Cambios a implementar** | Implementar la regla aprobada: reserva/clase/proyección al vender y movimiento definitivo al conciliar, o alternativa; vincular y compensar diferencias. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Duplicar descuento o dejar ventas sin resolver indefinidamente. |
| **13. Posibles regresiones** | Flujo rápido del POS y reportes de clase/producto. |
| **14. Pruebas requeridas** | Venta sin conciliación, conciliación parcial/completa, producto incorrecto, exceso, replay, cancelación y cierre. |
| **15. Criterios de aceptación** | Cada unidad vendida por clase se atribuye una vez; saldos y diferencias son trazables; no hay doble movimiento. |
| **16. Definition of Done específica** | Cada unidad vendida por clase se atribuye una vez; saldos y diferencias son trazables; no hay doble movimiento. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Relación class sale→reconciliation→movement, pruebas y reporte de pendientes. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-060, ZM-FIN-067 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-050 — Integrar `CLASS_CAPTURE` y conciliación física**.

**Objetivo**
Representar correctamente la captura por clase sin descontar dos veces ni perder atribución al producto real.

**Problema y contexto de ZeroMerma**
La venta por clase tiene conciliación física posterior, pero no converge de forma demostrable con el ledger canónico. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-DATA-004; ZMA-DATA-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-048 y decisión aprobada del momento de afectación.

**Inspección inicial obligatoria**
Inspecciona modelos de captura física, estados pendientes y cómo se relacionan con sale lines.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Implementar la regla aprobada: reserva/clase/proyección al vender y movimiento definitivo al conciliar, o alternativa; vincular y compensar diferencias.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No convertir todas las ventas a PRODUCT_DIRECT ni eliminar el modo existente. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Conciliación después de cierre, producto sin clase, cantidad distinta, dos conciliadores y sucursal equivocada.

**Concurrencia y consistencia**
Dos conciliaciones sobre el mismo pendiente deben serializar y respetar remanente.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Venta sin conciliación, conciliación parcial/completa, producto incorrecto, exceso, replay, cancelación y cierre.

**Validación y comandos**
Pruebas integración, E2E POS/Backoffice y reconciliación de ledger. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada unidad vendida por clase se atribuye una vez; saldos y diferencias son trazables; no hay doble movimiento.
Definition of Done específica: Cada unidad vendida por clase se atribuye una vez; saldos y diferencias son trazables; no hay doble movimiento. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Documentar semántica `CLASS_CAPTURE` y manejo de diferencias.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-051 — Integrar devoluciones, disposición, merma y correcciones

**Épica:** Ledger de inventario
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: fuente canónica granular, Decimal/Numeric o UOM, lineage, reconciliación, validez y rebuild para KPI aplicables.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-051 |
| **2. Nombre de la tarea** | Integrar devoluciones, disposición, merma y correcciones |
| **3. Objetivo** | Materializar cada flujo inverso o de pérdida como movimiento causal y compensatorio. |
| **4. Problema que resuelve** | `SEND_TO_WASTE` no creó merma ni movimiento; devoluciones/correcciones POS no alimentan siempre el ledger. |
| **5. Hallazgo relacionado** | ZM-DATA-004; ZMA-DATA-001; ZMA-WASTE-001. |
| **6. Módulos afectados** | Returns, waste, corrections, inventory, POS/Backoffice y audit. |
| **7. Archivos/áreas a inspeccionar** | Servicios de devolución/merma/corrección; disposición; InventoryMovement; módulos admin/POS. |
| **8. Dependencias previas** | ZM-FIN-031, ZM-FIN-034 y ZM-FIN-048. |
| **9. Cambios a implementar** | Mapear disposición a restock/quarantine/waste/no-stock; crear movimientos y documentos relacionados; aplicar límites acumulados y compensación. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Restituir producto no vendible, merma doble o corrección usada para ocultar pérdidas. |
| **13. Posibles regresiones** | Flujos de devolución existentes y reportes de merma. |
| **14. Pruebas requeridas** | Restock vendible, merma, cuarentena, no restock, corrección positiva/negativa, replay y rollback. |
| **15. Criterios de aceptación** | Cada disposición produce exactamente el efecto aprobado; merma es visible; no se devuelve al stock más de lo vendido. |
| **16. Definition of Done específica** | Cada disposición produce exactamente el efecto aprobado; merma es visible; no se devuelve al stock más de lo vendido. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Grafo causal y reconciliación por producto/sucursal. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-067, ZM-FIN-079 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-051 — Integrar devoluciones, disposición, merma y correcciones**.

**Objetivo**
Materializar cada flujo inverso o de pérdida como movimiento causal y compensatorio.

**Problema y contexto de ZeroMerma**
`SEND_TO_WASTE` no creó merma ni movimiento; devoluciones/correcciones POS no alimentan siempre el ledger. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-DATA-004; ZMA-DATA-001; ZMA-WASTE-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-031, ZM-FIN-034 y ZM-FIN-048.

**Inspección inicial obligatoria**
Inspecciona enums de disposición, módulos de waste/corrections y cualquier movimiento admin equivalente.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Mapear disposición a restock/quarantine/waste/no-stock; crear movimientos y documentos relacionados; aplicar límites acumulados y compensación.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No borrar ni editar el movimiento original; usar compensaciones. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Devolución parcial múltiple, producto dañado, lote/fecha, cantidad fraccional y sucursal distinta.

**Concurrencia y consistencia**
Dos devoluciones/correcciones sobre el mismo remanente deben respetar límites.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Restock vendible, merma, cuarentena, no restock, corrección positiva/negativa, replay y rollback.

**Validación y comandos**
Pruebas integración, E2E y reconciliación; generación contractual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada disposición produce exactamente el efecto aprobado; merma es visible; no se devuelve al stock más de lo vendido.
Definition of Done específica: Cada disposición produce exactamente el efecto aprobado; merma es visible; no se devuelve al stock más de lo vendido. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Política de disposición, merma y correcciones.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-052 — Unificar transferencias y recepciones POS/Backoffice

**Épica:** Ledger de inventario
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: fuente canónica granular, Decimal/Numeric o UOM, lineage, reconciliación, validez y rebuild para KPI aplicables.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-052 |
| **2. Nombre de la tarea** | Unificar transferencias y recepciones POS/Backoffice |
| **3. Objetivo** | Conseguir que ambos canales usen la misma máquina de estados y produzcan movimientos origen/destino consistentes. |
| **4. Problema que resuelve** | Backoffice integra inventario; POS registra documentos pero no siempre actualiza el ledger. |
| **5. Hallazgo relacionado** | ZM-DATA-004; ZMA-DATA-001. |
| **6. Módulos afectados** | Transfers, receipts, inventory, POS y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Servicios POS/admin; modelos de transferencia; movement types; send/receive endpoints. |
| **8. Dependencias previas** | ZM-FIN-033, ZM-FIN-038 y ZM-FIN-048. |
| **9. Cambios a implementar** | Centralizar dispatch/receive; movimiento de salida, tránsito y entrada según regla; recepción parcial; rechazo/daño; una sola implementación backend. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Pérdida de stock en tránsito o duplicación al mantener dos servicios. |
| **13. Posibles regresiones** | Transferencias administrativas ya funcionales y filtros de sucursal. |
| **14. Pruebas requeridas** | Total/parcial, exceso, cancelación antes/después de envío, replay, origen=destino y scope. |
| **15. Criterios de aceptación** | POS y Backoffice observan el mismo estado; balances origen/destino reconcilian; no hay doble movimiento. |
| **16. Definition of Done específica** | POS y Backoffice observan el mismo estado; balances origen/destino reconcilian; no hay doble movimiento. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas cruzadas de ambas superficies y reconciliación de transferencia. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-066, ZM-FIN-080 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-052 — Unificar transferencias y recepciones POS/Backoffice**.

**Objetivo**
Conseguir que ambos canales usen la misma máquina de estados y produzcan movimientos origen/destino consistentes.

**Problema y contexto de ZeroMerma**
Backoffice integra inventario; POS registra documentos pero no siempre actualiza el ledger. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-DATA-004; ZMA-DATA-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-033, ZM-FIN-038 y ZM-FIN-048.

**Inspección inicial obligatoria**
Compara explícitamente servicios POS y Backoffice y todos los tipos de movimiento existentes.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Centralizar dispatch/receive; movimiento de salida, tránsito y entrada según regla; recepción parcial; rechazo/daño; una sola implementación backend.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No mantener dos implementaciones divergentes por compatibilidad. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Recepción parcial, daño, sucursal no autorizada, reapertura y documento legacy.

**Concurrencia y consistencia**
Dos recepciones del mismo remanente y envío/recepción simultáneos.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Total/parcial, exceso, cancelación antes/después de envío, replay, origen=destino y scope.

**Validación y comandos**
Pruebas integración/E2E por superficie, replay y reconciliación. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
POS y Backoffice observan el mismo estado; balances origen/destino reconcilian; no hay doble movimiento.
Definition of Done específica: POS y Backoffice observan el mismo estado; balances origen/destino reconcilian; no hay doble movimiento. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Máquina de estados y SOP de transferencia/recepción.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-053 — Asegurar compras y recepciones de proveedor en el ledger canónico

**Épica:** Ledger de inventario
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: fuente canónica granular, Decimal/Numeric o UOM, lineage, reconciliación, validez y rebuild para KPI aplicables.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-053 |
| **2. Nombre de la tarea** | Asegurar compras y recepciones de proveedor en el ledger canónico |
| **3. Objetivo** | Preservar el flujo administrativo que sí movía inventario y cerrarlo para recepción parcial, corrección y costo. |
| **4. Problema que resuelve** | La compra administrativa creó balance/movimiento, pero no fue validada bajo idempotencia, concurrencia y reglas completas. |
| **5. Hallazgo relacionado** | ZMA-DATA-001; fortalezas de compras/inventario. |
| **6. Módulos afectados** | Suppliers, purchases, receipts, inventory, costing y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Servicios de purchase/receipt; movimientos; balance; costos; estados y formularios. |
| **8. Dependencias previas** | ZM-FIN-033, ZM-FIN-038 y ZM-FIN-048. |
| **9. Cambios a implementar** | Validar/centralizar recepción; cantidades pendientes; costo/unidad; corrección/reversa; referencias proveedor/documento; no mutar balances directamente. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Cambiar el único flujo de inventario probado o costear con precisión incorrecta. |
| **13. Posibles regresiones** | Compras existentes, reportes de proveedor y balances. |
| **14. Pruebas requeridas** | Recepción total/parcial/exceso; duplicate invoice si aplica; costo decimal; replay; concurrencia; cancelación. |
| **15. Criterios de aceptación** | Cada recepción produce movimientos/costos correctos una vez; remanente y estado del documento son consistentes. |
| **16. Definition of Done específica** | Cada recepción produce movimientos/costos correctos una vez; remanente y estado del documento son consistentes. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas de recepción y reconciliación compra→movimiento→balance/costo. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-064 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-053 — Asegurar compras y recepciones de proveedor en el ledger canónico**.

**Objetivo**
Preservar el flujo administrativo que sí movía inventario y cerrarlo para recepción parcial, corrección y costo.

**Problema y contexto de ZeroMerma**
La compra administrativa creó balance/movimiento, pero no fue validada bajo idempotencia, concurrencia y reglas completas. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-DATA-001; fortalezas de compras/inventario.

**Dependencias que puedes asumir terminadas**
ZM-FIN-033, ZM-FIN-038 y ZM-FIN-048.

**Inspección inicial obligatoria**
Inspecciona recepción actual, constraints, UOM/costos y manejo de exceso/partial.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Validar/centralizar recepción; cantidades pendientes; costo/unidad; corrección/reversa; referencias proveedor/documento; no mutar balances directamente.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No implementar contabilidad de proveedores completa si no está aprobada. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Factura duplicada, recepción sin PO, costo cero/negativo, unidad distinta y proveedor inactivo.

**Concurrencia y consistencia**
Dos recepciones concurrentes del mismo pendiente deben respetar el remanente.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Recepción total/parcial/exceso; duplicate invoice si aplica; costo decimal; replay; concurrencia; cancelación.

**Validación y comandos**
Pruebas integración/E2E Backoffice, replay y reconciliación. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada recepción produce movimientos/costos correctos una vez; remanente y estado del documento son consistentes.
Definition of Done específica: Cada recepción produce movimientos/costos correctos una vez; remanente y estado del documento son consistentes. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
SOP de compra/recepción y reglas de costo.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-054 — Integrar producción, recetas y versiones con inventario

**Épica:** Ledger de inventario
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: fuente canónica granular, Decimal/Numeric o UOM, lineage, reconciliación, validez y rebuild para KPI aplicables.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-054 |
| **2. Nombre de la tarea** | Integrar producción, recetas y versiones con inventario |
| **3. Objetivo** | Hacer reproducibles consumos, outputs, rendimiento y merma usando una versión inmutable de receta. |
| **4. Problema que resuelve** | Producción existe, pero no fue verificada integralmente; cancelación/insumos muestran semánticas contradictorias. |
| **5. Hallazgo relacionado** | ZMA-PROD-001; ZMA-CAT-001; ZM-DATA-004. |
| **6. Módulos afectados** | Production, recipes, catalog, inventory, costing y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Recipe/version models; production services; shortage checks; movement types; UI de producción. |
| **8. Dependencias previas** | ZM-FIN-035, ZM-FIN-038 y ZM-FIN-048. |
| **9. Cambios a implementar** | Snapshot de receta/inputs; movimientos de reserva/consumo/output/merma; semántica cancel/complete; separar active/sellable/usable_as_input. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Modificar receta histórica, consumir dos veces o revertir físicamente algo ya usado. |
| **13. Posibles regresiones** | Producción existente, cálculo de costos y disponibilidad de insumos. |
| **14. Pruebas requeridas** | Faltantes 409, inicio, cancelación antes/después de consumo, complete, rendimiento distinto, receta desactivada, replay. |
| **15. Criterios de aceptación** | Cada lote se explica por versión y movimientos; cancelar/terminar deja métricas coherentes; insumo activo no se marca inactivo por no vendible. |
| **16. Definition of Done específica** | Cada lote se explica por versión y movimientos; cancelar/terminar deja métricas coherentes; insumo activo no se marca inactivo por no vendible. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Grafo producción→receta version→movimientos/costo y E2E de estados. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-061–062 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-054 — Integrar producción, recetas y versiones con inventario**.

**Objetivo**
Hacer reproducibles consumos, outputs, rendimiento y merma usando una versión inmutable de receta.

**Problema y contexto de ZeroMerma**
Producción existe, pero no fue verificada integralmente; cancelación/insumos muestran semánticas contradictorias. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-PROD-001; ZMA-CAT-001; ZM-DATA-004.

**Dependencias que puedes asumir terminadas**
ZM-FIN-035, ZM-FIN-038 y ZM-FIN-048.

**Inspección inicial obligatoria**
Inspecciona versionado, receta activa, `_product_status`, shortage summary y servicios de movimiento.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Snapshot de receta/inputs; movimientos de reserva/consumo/output/merma; semántica cancel/complete; separar active/sellable/usable_as_input.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No añadir planificación predictiva ni sustituciones automáticas sin decisión. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Receta sin versión, insumo inactivo/no vendible, sustitución no aprobada, lote parcial y merma de proceso.

**Concurrencia y consistencia**
Dos lotes consumiendo el último insumo; cancel/complete concurrentes.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Faltantes 409, inicio, cancelación antes/después de consumo, complete, rendimiento distinto, receta desactivada, replay.

**Validación y comandos**
Pruebas dominio/integración/E2E, migración, replay y reconciliación. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada lote se explica por versión y movimientos; cancelar/terminar deja métricas coherentes; insumo activo no se marca inactivo por no vendible.
Definition of Done específica: Cada lote se explica por versión y movimientos; cancelar/terminar deja métricas coherentes; insumo activo no se marca inactivo por no vendible. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Máquina de producción, versionado de receta y reglas de costo.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-055 — Reconstruir balances, costear y corregir historia de inventario

**Épica:** Reconciliación física
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: fuente canónica granular, Decimal/Numeric o UOM, lineage, reconciliación, validez y rebuild para KPI aplicables.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-055 |
| **2. Nombre de la tarea** | Reconstruir balances, costear y corregir historia de inventario |
| **3. Objetivo** | Demostrar que saldos materializados coinciden con movimientos y que el inventario inicial productivo nace de conteo físico/opening state aprobado o historia causal fiable. |
| **4. Problema que resuelve** | Los volúmenes auditados son no productivos y no pueden aportar saldos de apertura; el sistema necesita rebuild determinista, opening adjustment auditable y reconciliación para datos reales futuros. |
| **5. Hallazgo relacionado** | ZMA-DATA-001; ZM-DATA-004; ZM-REL-015. |
| **6. Módulos afectados** | Inventory DB, costing, all physical domains, migrations y reports. |
| **7. Archivos/áreas a inspeccionar** | Balances/movements; scripts de rebuild; costos; datos legacy; auditoría. |
| **8. Dependencias previas** | ZM-FIN-048–054 y DEC-19. |
| **9. Cambios a implementar** | Crear reconciliación read-only y rebuild determinista; tomar conteo físico validado como autoridad de cutover; implementar opening state/adjustment idempotente y auditable; hacer backfill sólo con causalidad fiable; detectar negativos/anomalías y rechazar balances demo/test. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Inventar movimientos históricos, costo equivocado o bloquear operación durante rebuild. |
| **13. Posibles regresiones** | Disponibilidad, producción y reportes cambian por corrección de saldos. |
| **14. Pruebas requeridas** | Rebuild desde movimientos; datos sin movimiento; duplicados; UOM; interrupción/reanudación; comparación antes/después; restore. |
| **15. Criterios de aceptación** | Todo balance real se reconstruye desde causalidad fiable o tiene opening adjustment explicado y firmado; costo y stock coinciden; balances demo/test nunca son autoridad; ninguna diferencia genera movimientos ficticios ni altera historia silenciosamente. |
| **16. Definition of Done específica** | Todo balance se reconstruye o tiene ajuste inicial explicado; costo y stock coinciden; backfill no altera historia silenciosamente. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Informe de diferencias, dry run, scripts/migraciones y reconciliación firmada. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Data Integrity Ready, reportes y analítica. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-055 — Reconstruir balances, costear y corregir historia de inventario**.

**Objetivo**
Demostrar que saldos materializados coinciden con movimientos y tratar datos históricos previos al ledger canónico.

**Problema y contexto de ZeroMerma**
El entorno auditado tenía sólo un movimiento de compra pese a múltiples operaciones POS; los saldos históricos pueden ser incompletos. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-DATA-001; ZM-DATA-004; ZM-REL-015.

**Dependencias que puedes asumir terminadas**
ZM-FIN-048–054 y decisión sobre datos reales a migrar.

**Inspección inicial obligatoria**
Inspecciona volumen y calidad de datos reales, fuentes documentales y todos los tipos de movimiento.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Crear reconciliación read-only y rebuild determinista; política de costo aprobada; backfill idempotente o ajuste inicial auditable; detectar negativos/anomalías.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No corregir manualmente saldos productivos ni borrar movimientos. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Saldo negativo, producto sin UOM, movimiento huérfano, fecha histórica, costo faltante y sucursal cerrada.

**Concurrencia y consistencia**
Definir si rebuild requiere ventana o puede operar con snapshot; probar reanudación y escrituras concurrentes si se permiten.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Rebuild desde movimientos; datos sin movimiento; duplicados; UOM; interrupción/reanudación; comparación antes/después; restore.

**Validación y comandos**
Dry run en copia restaurada, reconciliación, pruebas de idempotencia y restore antes de producción. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Todo balance se reconstruye o tiene ajuste inicial explicado; costo y stock coinciden; backfill no altera historia silenciosamente.
Definition of Done específica: Todo balance se reconstruye o tiene ajuste inicial explicado; costo y stock coinciden; backfill no altera historia silenciosamente. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Runbook de rebuild/backfill y política de costo.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```


## Fase 5 — POS Feature Complete — Tareas ejecutables

### ZM-FIN-056 — Completar carrito, disponibilidad y confirmación de venta

**Épica:** POS ventas

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-056 |
| **2. Nombre de la tarea** | Completar carrito, disponibilidad y confirmación de venta |
| **3. Objetivo** | Hacer que el flujo de venta sea consistente con catálogo, precio, inventario, sesión e idempotencia backend. |
| **4. Problema que resuelve** | El flujo funciona, pero carece de inventario canónico, descuentos comerciales y validación integrada exhaustiva. |
| **5. Hallazgo relacionado** | ZM-DATA-004; ZMA-DATA-001; ZM-QA-011. |
| **6. Módulos afectados** | POS sale UI, catalog/pricing API, sales, inventory y session. |
| **7. Archivos/áreas a inspeccionar** | Pantallas/hooks/store de venta; `operation-module-screen.tsx` o equivalentes; mutations; cliente generado. |
| **8. Dependencias previas** | ZM-FIN-029, ZM-FIN-036, ZM-FIN-049–050 y ZM-FIN-060/063 según precio. |
| **9. Cambios a implementar** | Validar estado de turno, disponibilidad, cantidades, duplicados de línea, totales backend y recuperación de conflicto; reducir sólo el acoplamiento estrictamente necesario. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Duplicar reglas críticas en frontend o refactorizar una pantalla grande sin caracterización. |
| **13. Posibles regresiones** | Flujo táctil, teclado, selección por clase y rendimiento en terminal. |
| **14. Pruebas requeridas** | Carrito vacío, cantidad cero/negativa/fraccional, producto inactivo/sin stock, precio cambia, sesión cierra, replay y recarga. |
| **15. Criterios de aceptación** | El POS no confirma una venta inválida; muestra el resultado backend definitivo; recarga/retry no duplica; totales coinciden con ticket/DB. |
| **16. Definition of Done específica** | El POS no confirma una venta inválida; muestra el resultado backend definitivo; recarga/retry no duplica; totales coinciden con ticket/DB. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E real, trazas de red, IDs y reconciliación sale/payment/inventory. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-057, ZM-FIN-082 y Gate Feature Complete. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-056 — Completar carrito, disponibilidad y confirmación de venta**.

**Objetivo**
Hacer que el flujo de venta sea consistente con catálogo, precio, inventario, sesión e idempotencia backend.

**Problema y contexto de ZeroMerma**
El flujo funciona, pero carece de inventario canónico, descuentos comerciales y validación integrada exhaustiva. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-DATA-004; ZMA-DATA-001; ZM-QA-011.

**Dependencias que puedes asumir terminadas**
ZM-FIN-029, ZM-FIN-036, ZM-FIN-049–050 y ZM-FIN-060/063 según precio.

**Inspección inicial obligatoria**
Inspecciona componentes grandes, hooks de carrito, cálculo local, estados de mutación y errores API.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Validar estado de turno, disponibilidad, cantidades, duplicados de línea, totales backend y recuperación de conflicto; reducir sólo el acoplamiento estrictamente necesario.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No reescribir toda la pantalla ni mover reglas de negocio al frontend. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Dos pestañas, cambio de catálogo durante carrito, stock exacto, clase sin producto reconciliado y reconexión.

**Concurrencia y consistencia**
Probar conflicto de stock y cierre concurrente; frontend debe presentar respuesta recuperable.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Carrito vacío, cantidad cero/negativa/fraccional, producto inactivo/sin stock, precio cambia, sesión cierra, replay y recarga.

**Validación y comandos**
Unitarias/Vitest, typecheck/build y E2E real apertura→venta→persistencia. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
El POS no confirma una venta inválida; muestra el resultado backend definitivo; recarga/retry no duplica; totales coinciden con ticket/DB.
Definition of Done específica: El POS no confirma una venta inválida; muestra el resultado backend definitivo; recarga/retry no duplica; totales coinciden con ticket/DB. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar manual POS de venta y mensajes de error.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-057 — Completar cobro, validación y recuperación de pagos

**Épica:** POS pagos

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-057 |
| **2. Nombre de la tarea** | Completar cobro, validación y recuperación de pagos |
| **3. Objetivo** | Permitir efectivo, tarjeta y mixto con estados claros, precisión decimal y recuperación tras timeout. |
| **4. Problema que resuelve** | Los pagos funcionan conceptualmente, pero no hay terminal real y faltan pruebas exhaustivas de insuficiente/excesivo/retry. |
| **5. Hallazgo relacionado** | Casos POS-025–030 no verificados; ZM-REL-005; ZMA-REP-001. |
| **6. Módulos afectados** | POS payment UI, sales/payments, terminal adapter, cash ledger. |
| **7. Archivos/áreas a inspeccionar** | Componentes de pago; keypad/input; mutations; schemas; manejo de response/timeout. |
| **8. Dependencias previas** | ZM-FIN-029, ZM-FIN-043–046 y ZM-FIN-056. |
| **9. Cambios a implementar** | Validar montos por backend; mostrar cambio; componer pago mixto; estados pending/confirmed/failed; recuperar resultado por idempotency key tras timeout. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Cobro doble, UX ambigua tras timeout o errores de redondeo. |
| **13. Posibles regresiones** | Venta en efectivo ya funcional y atajos de teclado. |
| **14. Pruebas requeridas** | Pago insuficiente/excesivo, centavos, dos medios, tarjeta rechazada/pendiente, doble Enter, respuesta perdida y sesión cerrada. |
| **15. Criterios de aceptación** | El usuario nunca desconoce si se cobró; el total confirmado coincide con backend; retry no duplica; pagos pendientes no cierran venta indebidamente. |
| **16. Definition of Done específica** | El usuario nunca desconoce si se cobró; el total confirmado coincide con backend; retry no duplica; pagos pendientes no cierran venta indebidamente. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E por método, capturas de estados y reconciliación de payment rows. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-065, ZM-FIN-082 y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-057 — Completar cobro, validación y recuperación de pagos**.

**Objetivo**
Permitir efectivo, tarjeta y mixto con estados claros, precisión decimal y recuperación tras timeout.

**Problema y contexto de ZeroMerma**
Los pagos funcionan conceptualmente, pero no hay terminal real y faltan pruebas exhaustivas de insuficiente/excesivo/retry. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Casos POS-025–030 no verificados; ZM-REL-005; ZMA-REP-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-029, ZM-FIN-043–046 y ZM-FIN-056.

**Inspección inicial obligatoria**
Inspecciona cálculo local de total/pago/cambio, bloqueo `isPending` y manejo de errores de red.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Validar montos por backend; mostrar cambio; componer pago mixto; estados pending/confirmed/failed; recuperar resultado por idempotency key tras timeout.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No emular un pago aprobado si el backend/proveedor no lo confirma. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Pago exacto, sobrepago permitido sólo en efectivo, monto 0, tarjeta+cash, provider timeout y refresh.

**Concurrencia y consistencia**
Doble submit y resolución tardía del proveedor deben converger en un solo estado.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Pago insuficiente/excesivo, centavos, dos medios, tarjeta rechazada/pendiente, doble Enter, respuesta perdida y sesión cerrada.

**Validación y comandos**
Vitest, E2E real, pruebas de adapter y typecheck/build. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
El usuario nunca desconoce si se cobró; el total confirmado coincide con backend; retry no duplica; pagos pendientes no cierran venta indebidamente.
Definition of Done específica: El usuario nunca desconoce si se cobró; el total confirmado coincide con backend; retry no duplica; pagos pendientes no cierran venta indebidamente. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Manual de cobro y matriz de mensajes/recuperación.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-058 — Completar el ciclo de pedidos del cliente

**Épica:** POS pedidos

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-058 |
| **2. Nombre de la tarea** | Completar el ciclo de pedidos del cliente |
| **3. Objetivo** | Permitir crear, reservar, pagar, entregar, cancelar y reembolsar pedidos con estados e impactos coherentes. |
| **4. Problema que resuelve** | El flujo básico funcionó, pero el pago quedó fuera de caja y no se verificaron todas las transiciones/reversas. |
| **5. Hallazgo relacionado** | ZMA-FIN-001; ZM-QA-011; reglas de pedido indefinidas. |
| **6. Módulos afectados** | POS orders, orders API, payments, inventory/reservations, tickets y audit. |
| **7. Archivos/áreas a inspeccionar** | `orders-screen.tsx`; services/endpoints de pedido; status UI; payment mutations. |
| **8. Dependencias previas** | ZM-FIN-030, ZM-FIN-042, ZM-FIN-048 y decisión de reconocimiento/reserva. |
| **9. Cambios a implementar** | Implementar máquina de estados aprobada; reserva/liberación; saldos/pagos; entrega; cancel/refund; recuperación idempotente y mensajes. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Reservas eternas, doble pago/entrega o pedido ligado a turno incorrecto. |
| **13. Posibles regresiones** | Pedido básico existente y ventas rápidas. |
| **14. Pruebas requeridas** | Pago parcial/total, entrega sin saldo, cancelación con/sin pago, stock insuficiente, cambio de turno, replay y expiración. |
| **15. Criterios de aceptación** | No hay transición inválida; dinero/inventario/auditoría reconcilian; el pedido es operable desde creación hasta estado terminal. |
| **16. Definition of Done específica** | No hay transición inválida; dinero/inventario/auditoría reconcilian; el pedido es operable desde creación hasta estado terminal. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E completo, grafo de estados y reconciliación. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-067, ZM-FIN-082 y Gate Feature Complete. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-058 — Completar el ciclo de pedidos del cliente**.

**Objetivo**
Permitir crear, reservar, pagar, entregar, cancelar y reembolsar pedidos con estados e impactos coherentes.

**Problema y contexto de ZeroMerma**
El flujo básico funcionó, pero el pago quedó fuera de caja y no se verificaron todas las transiciones/reversas. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-FIN-001; ZM-QA-011; reglas de pedido indefinidas.

**Dependencias que puedes asumir terminadas**
ZM-FIN-030, ZM-FIN-042, ZM-FIN-048 y decisión de reconocimiento/reserva.

**Inspección inicial obligatoria**
Inspecciona todas las transiciones, saldos, relaciones con inventario/caja y estados visuales.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Implementar máquina de estados aprobada; reserva/liberación; saldos/pagos; entrega; cancel/refund; recuperación idempotente y mensajes.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No introducir e-commerce externo ni logística de entrega no aprobada. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Pedido de otra sucursal, pago en otro turno, entrega parcial, cancelación tardía y producto desactivado.

**Concurrencia y consistencia**
Dos cajeros pagando/entregando el mismo pedido deben serializar.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Pago parcial/total, entrega sin saldo, cancelación con/sin pago, stock insuficiente, cambio de turno, replay y expiración.

**Validación y comandos**
Pruebas API/estado, E2E real y reconciliación. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
No hay transición inválida; dinero/inventario/auditoría reconcilian; el pedido es operable desde creación hasta estado terminal.
Definition of Done específica: No hay transición inválida; dinero/inventario/auditoría reconcilian; el pedido es operable desde creación hasta estado terminal. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
SOP de pedidos y máquina de estados.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-059 — Completar ticket, reimpresión y render de impresión

**Épica:** POS tickets

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-059 |
| **2. Nombre de la tarea** | Completar ticket, reimpresión y render de impresión |
| **3. Objetivo** | Producir tickets consistentes, consultables y reimprimibles sin alterar la transacción. |
| **4. Problema que resuelve** | La consulta/reimpresión por navegador existe, pero impresión física y criterios fiscales no fueron verificados. |
| **5. Hallazgo relacionado** | Funcional con deficiencias; elementos no verificables de impresión; ZM-FIN-007. |
| **6. Módulos afectados** | Tickets API, POS ticket UI, print renderer, sales/orders/refunds. |
| **7. Archivos/áreas a inspeccionar** | Servicios de ticket; plantillas/componentes de impresión; rutas de tickets; folios. |
| **8. Dependencias previas** | ZM-FIN-007, ZM-FIN-041–046 y ZM-FIN-056–058. |
| **9. Cambios a implementar** | Definir snapshot inmutable del ticket operativo; contenido/folio; render e impresión; reimpresión auditada; incluir descuentos, medios, devoluciones y metadatos; validar la frontera ticket/CFDI/comprobante y la matriz fiscal aplicable a Sucursal Matriz. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Recalcular históricos con reglas actuales o duplicar transacciones al reimprimir. |
| **13. Posibles regresiones** | Consulta de tickets existente y estilos táctiles. |
| **14. Pruebas requeridas** | Venta cash/card/mixta, pedido, devolución, reimpresión, producto largo, caracteres especiales, caída de impresora. |
| **15. Criterios de aceptación** | Ticket/API/DB coinciden; reimpresión no crea venta/pago; contenido requerido es legible en hardware de Sucursal Matriz; no se presenta ticket como CFDI o comprobante BBVA y los blockers fiscales de la matriz están resueltos antes del piloto. |
| **16. Definition of Done específica** | Ticket/API/DB coinciden; reimpresión no crea venta/pago; contenido requerido está presente y es legible en hardware objetivo. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Snapshots, pruebas de render, E2E y ejemplares impresos anonimizados. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-064, ZM-FIN-085 y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-059 — Completar ticket, reimpresión y render de impresión**.

**Objetivo**
Producir tickets consistentes, consultables y reimprimibles sin alterar la transacción.

**Problema y contexto de ZeroMerma**
La consulta/reimpresión por navegador existe, pero impresión física y criterios fiscales no fueron verificados. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Funcional con deficiencias; elementos no verificables de impresión; ZM-FIN-007.

**Dependencias que puedes asumir terminadas**
ZM-FIN-007, ZM-FIN-041–046 y ZM-FIN-056–058.

**Inspección inicial obligatoria**
Inspecciona modelo/snapshot de ticket, generación de folio, CSS print y flujo de reprint.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir snapshot inmutable del ticket; contenido/folio; render específico de impresión; reimpresión auditada; incluir descuentos, medios, devoluciones y metadatos aprobados.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No depender de la pantalla de venta viva para reconstruir un ticket histórico. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Ticket histórico, datos faltantes, venta anulada, nombres largos, moneda/decimales y impresora sin papel.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Venta cash/card/mixta, pedido, devolución, reimpresión, producto largo, caracteres especiales, caída de impresora.

**Validación y comandos**
Pruebas snapshot/render, E2E de reimpresión, impresión en dispositivo objetivo y build. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Ticket/API/DB coinciden; reimpresión no crea venta/pago; contenido requerido está presente y es legible en hardware objetivo.
Definition of Done específica: Ticket/API/DB coinciden; reimpresión no crea venta/pago; contenido requerido está presente y es legible en hardware objetivo. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Especificación de ticket y guía de impresión/reimpresión.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-060 — Implementar entrega digital de tickets

**Épica:** POS comunicaciones

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-060 |
| **2. Nombre de la tarea** | Implementar entrega digital de tickets |
| **3. Objetivo** | Permitir email/SMS u otro canal aprobado con consentimiento, estado y retry observables. |
| **4. Problema que resuelve** | Email/SMS de tickets está ausente y el worker aún no tiene consumidores reales. |
| **5. Hallazgo relacionado** | Funcionalidad ausente; ZM-ASYNC-006; ZMA-ASYNC-001. |
| **6. Módulos afectados** | Tickets, notifications, worker/outbox, POS y privacy. |
| **7. Archivos/áreas a inspeccionar** | UI de ticket; eventos de ticket; proveedores de email/SMS; settings y consentimientos. |
| **8. Dependencias previas** | ZM-FIN-007, ZM-FIN-059, ZM-FIN-073–076 y proveedor aprobado. |
| **9. Cambios a implementar** | Capturar destino/consentimiento; publicar evento; handler idempotente; estados queued/sent/failed; retry manual; redacción y retención. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Fuga de PII, mensajes duplicados o proveedor externo que bloquea operación. |
| **13. Posibles regresiones** | Flujo de ticket y worker backlog. |
| **14. Pruebas requeridas** | Destino inválido, provider timeout, duplicado, opt-out, ticket reimpreso, cambio de número/email. |
| **15. Criterios de aceptación** | Enviar no bloquea la venta; retry no duplica; estado es visible; PII no aparece en logs y se respeta la política aprobada. |
| **16. Definition of Done específica** | Enviar no bloquea la venta; retry no duplica; estado es visible; PII no aparece en logs y se respeta la política aprobada. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas con provider fake/sandbox, eventos y evidencia de redacción. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Feature Complete/Pilot Ready si el canal está incluido. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-060 — Implementar entrega digital de tickets**.

**Objetivo**
Permitir email/SMS u otro canal aprobado con consentimiento, estado y retry observables.

**Problema y contexto de ZeroMerma**
Email/SMS de tickets está ausente y el worker aún no tiene consumidores reales. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Funcionalidad ausente; ZM-ASYNC-006; ZMA-ASYNC-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-007, ZM-FIN-059, ZM-FIN-073–076 y proveedor aprobado.

**Inspección inicial obligatoria**
Inspecciona eventos disponibles, UI de ticket, settings y cualquier placeholder de email/SMS.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Capturar destino/consentimiento; publicar evento; handler idempotente; estados queued/sent/failed; retry manual; redacción y retención.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No enviar datos reales durante pruebas ni hacer la venta dependiente del proveedor. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Sin consentimiento, contacto vacío, reintento tras crash, proveedor caído y eliminación/retención de PII.

**Concurrencia y consistencia**
Dos solicitudes de envío del mismo ticket/canal deben deduplicarse.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Destino inválido, provider timeout, duplicado, opt-out, ticket reimpreso, cambio de número/email.

**Validación y comandos**
Pruebas unitarias/integración con fake, E2E POS y sandbox sólo con datos de prueba. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Enviar no bloquea la venta; retry no duplica; estado es visible; PII no aparece en logs y se respeta la política aprobada.
Definition of Done específica: Enviar no bloquea la venta; retry no duplica; estado es visible; PII no aparece en logs y se respeta la política aprobada. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Política de comunicaciones, privacidad y runbook del proveedor.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-061 — Completar apertura, movimientos operativos y cierre en el POS

**Épica:** POS caja

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-061 |
| **2. Nombre de la tarea** | Completar apertura, movimientos operativos y cierre en el POS |
| **3. Objetivo** | Ofrecer un ciclo diario claro, reconciliado e idempotente para el cajero. |
| **4. Problema que resuelve** | Apertura/cierre funcionan, pero existen carrera, pagos omitidos y reglas de conteo/medios no cerradas. |
| **5. Hallazgo relacionado** | ZM-DATA-003; ZMA-FIN-001; ZMA-DATA-002. |
| **6. Módulos afectados** | POS cash UI, cash API, reconciliation, audit y reports. |
| **7. Archivos/áreas a inspeccionar** | Pantallas de apertura/cierre; archivo eliminado `cash-close/ui.tsx` si sigue relevante; mutations; summaries. |
| **8. Dependencias previas** | ZM-FIN-032, ZM-FIN-036–037 y ZM-FIN-045. |
| **9. Cambios a implementar** | Implementar UX de fondo, entradas/salidas, conteo por medio, diferencias explicadas, confirmación, recuperación de retry y bloqueo posterior. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | UX que permita confirmar cifras incorrectas o esconder una diferencia. |
| **13. Posibles regresiones** | Apertura/cierre ya operativos y navegación del POS. |
| **14. Pruebas requeridas** | Fondo cero, cierre sin conteo si aprobado, diferencia, pago pendiente, doble cierre, operación tras cierre, refresh. |
| **15. Criterios de aceptación** | El cajero completa el ciclo sin estados ambiguos; corte coincide con ledger; después del cierre no hay mutaciones permitidas. |
| **16. Definition of Done específica** | El cajero completa el ciclo sin estados ambiguos; corte coincide con ledger; después del cierre no hay mutaciones permitidas. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E de ciclo diario y ecuación por sesión. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-082 y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-061 — Completar apertura, movimientos operativos y cierre en el POS**.

**Objetivo**
Ofrecer un ciclo diario claro, reconciliado e idempotente para el cajero.

**Problema y contexto de ZeroMerma**
Apertura/cierre funcionan, pero existen carrera, pagos omitidos y reglas de conteo/medios no cerradas. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-DATA-003; ZMA-FIN-001; ZMA-DATA-002.

**Dependencias que puedes asumir terminadas**
ZM-FIN-032, ZM-FIN-036–037 y ZM-FIN-045.

**Inspección inicial obligatoria**
Inspecciona pantallas actuales, archivo eliminado, resumen backend y estados de sesión/store.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Implementar UX de fondo, entradas/salidas, conteo por medio, diferencias explicadas, confirmación, recuperación de retry y bloqueo posterior.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No calcular totales críticos en frontend ni permitir editar movimientos históricos. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Cierre con operaciones pendientes, sesión expirada, conteo decimal, otra estación y reapertura.

**Concurrencia y consistencia**
Probar cierre contra ventas/pagos y doble interacción UI.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Fondo cero, cierre sin conteo si aprobado, diferencia, pago pendiente, doble cierre, operación tras cierre, refresh.

**Validación y comandos**
Vitest, E2E real, reconciliación y build POS. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
El cajero completa el ciclo sin estados ambiguos; corte coincide con ledger; después del cierre no hay mutaciones permitidas.
Definition of Done específica: El cajero completa el ciclo sin estados ambiguos; corte coincide con ledger; después del cierre no hay mutaciones permitidas. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Manual de apertura, movimientos y cierre.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-062 — Completar transferencias y recepciones en el POS

**Épica:** POS logística

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-062 |
| **2. Nombre de la tarea** | Completar transferencias y recepciones en el POS |
| **3. Objetivo** | Permitir al personal despachar y recibir con cantidades/estados consistentes y aislamiento de sucursal. |
| **4. Problema que resuelve** | El despacho se probó, la recepción destino no; el camino POS no alimentaba el inventario canónico. |
| **5. Hallazgo relacionado** | POS-014 no verificado; ZM-DATA-004; ZMA-DATA-001. |
| **6. Módulos afectados** | POS transfers UI, transfer API, inventory y branch scope. |
| **7. Archivos/áreas a inspeccionar** | `counter-transfer-screen.tsx` y pantallas de sucursal; mutations; endpoints send/receive. |
| **8. Dependencias previas** | ZM-FIN-033, ZM-FIN-052 y ZM-FIN-022. |
| **9. Cambios a implementar** | Implementar selección autorizada, despacho, recepción total/parcial, discrepancia/daño y recuperación idempotente; mostrar estado compartido con Backoffice. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Recepción en sucursal equivocada o doble movimiento. |
| **13. Posibles regresiones** | Despacho ya funcional y UX de mostrador. |
| **14. Pruebas requeridas** | Origen=destino, destino no autorizado, parcial, exceso, ya recibido, offline/retry y cierre de sesión. |
| **15. Criterios de aceptación** | Cada transferencia completa el flujo físico una vez; POS y Backoffice muestran cantidades/estado idénticos. |
| **16. Definition of Done específica** | Cada transferencia completa el flujo físico una vez; POS y Backoffice muestran cantidades/estado idénticos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E de dos sucursales y reconciliación de movimientos. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-065, ZM-FIN-080 y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-062 — Completar transferencias y recepciones en el POS**.

**Objetivo**
Permitir al personal despachar y recibir con cantidades/estados consistentes y aislamiento de sucursal.

**Problema y contexto de ZeroMerma**
El despacho se probó, la recepción destino no; el camino POS no alimentaba el inventario canónico. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
POS-014 no verificado; ZM-DATA-004; ZMA-DATA-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-033, ZM-FIN-052 y ZM-FIN-022.

**Inspección inicial obligatoria**
Inspecciona ambas pantallas de transferencia, permisos de estación y endpoints POS/admin.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Implementar selección autorizada, despacho, recepción total/parcial, discrepancia/daño y recuperación idempotente; mostrar estado compartido con Backoffice.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No crear un segundo flujo de transferencia distinto al backend canónico. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Recepción parcial, rechazo, daño, transferencia cancelada, usuario con varias sucursales.

**Concurrencia y consistencia**
Dos receptores del mismo remanente y retry tras timeout.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Origen=destino, destino no autorizado, parcial, exceso, ya recibido, offline/retry y cierre de sesión.

**Validación y comandos**
E2E real multi-sucursal, integración y build. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada transferencia completa el flujo físico una vez; POS y Backoffice muestran cantidades/estado idénticos.
Definition of Done específica: Cada transferencia completa el flujo físico una vez; POS y Backoffice muestran cantidades/estado idénticos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
SOP de despacho/recepción POS.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-063 — Completar devoluciones, correcciones y merma en el POS

**Épica:** POS flujos inversos

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-063 |
| **2. Nombre de la tarea** | Completar devoluciones, correcciones y merma en el POS |
| **3. Objetivo** | Permitir compensaciones operativas seguras con causa, permiso, disposición y efectos financieros/físicos claros. |
| **4. Problema que resuelve** | Las pantallas producen documentos, pero inventario y merma no siempre se materializan; faltan reversas completas. |
| **5. Hallazgo relacionado** | ZM-DATA-004; ZMA-DATA-001; ZMA-WASTE-001. |
| **6. Módulos afectados** | POS returns/corrections/waste, payments, inventory, audit y RBAC. |
| **7. Archivos/áreas a inspeccionar** | Pantallas de devolución/corrección/merma; search de ticket; mutations; permisos. |
| **8. Dependencias previas** | ZM-FIN-031, ZM-FIN-034, ZM-FIN-044 y ZM-FIN-051. |
| **9. Cambios a implementar** | Implementar selección de origen, límites, disposición, causa obligatoria, autorización, confirmación idempotente y recibo/resultado. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Fraude operativo, devolución a stock incorrecto o reembolso sin confirmación. |
| **13. Posibles regresiones** | Búsqueda de tickets, flujos de devolución existentes y cierre de caja. |
| **14. Pruebas requeridas** | Parcial múltiple, sin ticket si aprobado, no restock, merma, método no reversible, cantidad excedida y retry. |
| **15. Criterios de aceptación** | No hay sobredevolución; dinero/stock/merma/auditoría coinciden; el usuario conoce estado final y siguiente acción. |
| **16. Definition of Done específica** | No hay sobredevolución; dinero/stock/merma/auditoría coinciden; el usuario conoce estado final y siguiente acción. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E por disposición y grafo causal. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-068, ZM-FIN-082 y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-063 — Completar devoluciones, correcciones y merma en el POS**.

**Objetivo**
Permitir compensaciones operativas seguras con causa, permiso, disposición y efectos financieros/físicos claros.

**Problema y contexto de ZeroMerma**
Las pantallas producen documentos, pero inventario y merma no siempre se materializan; faltan reversas completas. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-DATA-004; ZMA-DATA-001; ZMA-WASTE-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-031, ZM-FIN-034, ZM-FIN-044 y ZM-FIN-051.

**Inspección inicial obligatoria**
Inspecciona validaciones, permisos, causas, disposición y respuesta visual de cada flujo.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Implementar selección de origen, límites, disposición, causa obligatoria, autorización, confirmación idempotente y recibo/resultado.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No permitir borrado o edición de la venta original. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Ticket de otra sucursal, venta cerrada, refund parcial, producto no vendible y operación offline.

**Concurrencia y consistencia**
Dos devoluciones sobre el mismo ticket/cantidad y cierre concurrente.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: No. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Parcial múltiple, sin ticket si aprobado, no restock, merma, método no reversible, cantidad excedida y retry.

**Validación y comandos**
Vitest, E2E real, integración y reconciliación. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
No hay sobredevolución; dinero/stock/merma/auditoría coinciden; el usuario conoce estado final y siguiente acción.
Definition of Done específica: No hay sobredevolución; dinero/stock/merma/auditoría coinciden; el usuario conoce estado final y siguiente acción. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Manual de devoluciones/correcciones/merma y matriz de permisos.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-064 — Implementar adaptador de impresora y cajón de efectivo

**Épica:** POS hardware

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-064 |
| **2. Nombre de la tarea** | Implementar adaptador de impresora y cajón de efectivo |
| **3. Objetivo** | Operar periféricos sin acoplar la lógica de venta a un fabricante o driver concreto. |
| **4. Problema que resuelve** | Impresora física y cajón no fueron verificados; actualmente se depende de impresión del navegador. |
| **5. Hallazgo relacionado** | Funcionalidad ausente/no verificable de hardware. |
| **6. Módulos afectados** | POS, tickets, hardware adapter, deployment local y support. |
| **7. Archivos/áreas a inspeccionar** | Print services; browser APIs; bridge/local agent si existe; configuración por workstation. |
| **8. Dependencias previas** | ZM-FIN-002, ZM-FIN-059 y hardware objetivo aprobado. |
| **9. Cambios a implementar** | Definir interfaz; capacidades por estación; print/open drawer; retry/reprint; errores no bloqueantes; diagnóstico y fallback aprobado. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Vendor lock-in, permisos del navegador, apertura de cajón indebida y soporte heterogéneo. |
| **13. Posibles regresiones** | Impresión web existente y tiempos de confirmación. |
| **14. Pruebas requeridas** | Impresora ausente/sin papel/offline, cajón no disponible, reimpresión, venta confirmada con fallo periférico y dos dispositivos. |
| **15. Criterios de aceptación** | El fallo de hardware no duplica ni revierte una venta confirmada; reimpresión y diagnóstico son posibles; matriz soportada está documentada. |
| **16. Definition of Done específica** | El fallo de hardware no duplica ni revierte una venta confirmada; reimpresión y diagnóstico son posibles; matriz soportada está documentada. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas en hardware objetivo, logs de adapter y runbook. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-084, ZM-FIN-092 y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-064 — Implementar adaptador de impresora y cajón de efectivo**.

**Objetivo**
Operar periféricos sin acoplar la lógica de venta a un fabricante o driver concreto.

**Problema y contexto de ZeroMerma**
Impresora física y cajón no fueron verificados; actualmente se depende de impresión del navegador. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Funcionalidad ausente/no verificable de hardware.

**Dependencias que puedes asumir terminadas**
ZM-FIN-002, ZM-FIN-059 y hardware objetivo aprobado.

**Inspección inicial obligatoria**
Inspecciona print CSS, configuración por workstation y cualquier integración local existente.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir interfaz; capacidades por estación; print/open drawer; retry/reprint; errores no bloqueantes; diagnóstico y fallback aprobado.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No acoplar reglas de venta al driver ni fingir confirmación de impresión. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Venta confirmada antes del fallo, reprint, impresoras múltiples, permisos revocados y reinicio del bridge.

**Concurrencia y consistencia**
Cola de impresión concurrente debe conservar orden y no duplicar trabajos.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Impresora ausente/sin papel/offline, cajón no disponible, reimpresión, venta confirmada con fallo periférico y dos dispositivos.

**Validación y comandos**
Pruebas unitarias con fake, integración con dispositivo y E2E de fallo/reimpresión. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
El fallo de hardware no duplica ni revierte una venta confirmada; reimpresión y diagnóstico son posibles; matriz soportada está documentada.
Definition of Done específica: El fallo de hardware no duplica ni revierte una venta confirmada; reimpresión y diagnóstico son posibles; matriz soportada está documentada. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Matriz de hardware, instalación y troubleshooting.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-065 — Integrar terminal de pago en la experiencia POS

**Épica:** POS hardware

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-065 |
| **2. Nombre de la tarea** | Integrar terminal de pago en la experiencia POS |
| **3. Objetivo** | Conectar el adapter de pagos externos con un flujo táctil seguro y recuperable. |
| **4. Problema que resuelve** | La terminal está ausente y la UI tarjeta actual no representa estados reales del proveedor. |
| **5. Hallazgo relacionado** | Funcionalidad ausente/no verificable; ZM-FIN-046. |
| **6. Módulos afectados** | POS payment UI, terminal adapter, payments, audit y support. |
| **7. Archivos/áreas a inspeccionar** | Componentes de pago; workstation config; provider adapter; polling/webhook status. |
| **8. Dependencias previas** | ZM-FIN-046, ZM-FIN-057 y hardware/proveedor aprobados. |
| **9. Cambios a implementar** | Solicitar/cancelar/consultar BBVA; mostrar instrucciones/estado; recuperar por referencia; manejar `UNKNOWN`, callbacks y retry; fallback sólo autorizado; evitar datos sensibles; validar terminal/binding y gate BBVA/PCI antes de habilitarlo en Sucursal Matriz. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Cobro doble, UX ambigua, exposición de datos de tarjeta o caída del proveedor. |
| **13. Posibles regresiones** | Pago manual con tarjeta y flujo mixto. |
| **14. Pruebas requeridas** | Aprobado, rechazado, timeout, terminal offline, cliente cancela, app recarga, webhook tardío y retry. |
| **15. Criterios de aceptación** | El cajero determina estado definitivo o `UNKNOWN` conciliable; no se duplica cargo; venta sólo confirma con evidencia aprobada; hardware, PCI, refunds/reversas, observabilidad y separación sandbox/production pasan; BBVA forma parte de la aceptación final o el piloto se pospone. |
| **16. Definition of Done específica** | El cajero puede determinar el estado definitivo; no se duplica cargo; la venta sólo confirma con pago aprobado según política. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E sandbox/hardware, referencias externas y conciliación. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-065 — Integrar terminal de pago en la experiencia POS**.

**Objetivo**
Conectar el adapter de pagos externos con un flujo táctil seguro y recuperable.

**Problema y contexto de ZeroMerma**
La terminal está ausente y la UI tarjeta actual no representa estados reales del proveedor. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Funcionalidad ausente/no verificable; ZM-FIN-046.

**Dependencias que puedes asumir terminadas**
ZM-FIN-046, ZM-FIN-057 y hardware/proveedor aprobados.

**Inspección inicial obligatoria**
Inspecciona UI actual CARD, manejo de pending/error y configuración por estación.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Solicitar/cancelar/consultar pago; mostrar instrucciones/estado; recuperar por referencia; fallback manual sólo con permiso; evitar datos sensibles.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No almacenar ni mostrar datos de tarjeta innecesarios. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Terminal equivocada, dos terminales, timeout post-cargo, refund y cierre con pendiente.

**Concurrencia y consistencia**
Dos intentos sobre la misma venta/referencia deben converger en un pago.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Aprobado, rechazado, timeout, terminal offline, cliente cancela, app recarga, webhook tardío y retry.

**Validación y comandos**
Vitest, E2E sandbox/hardware, pruebas de adapter y reconciliación. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
El cajero puede determinar el estado definitivo; no se duplica cargo; la venta sólo confirma con pago aprobado según política.
Definition of Done específica: El cajero puede determinar el estado definitivo; no se duplica cargo; la venta sólo confirma con pago aprobado según política. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Manual de terminal y procedimientos de contingencia.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-066 — Implementar política de conectividad, reconexión y offline aprobada

**Épica:** POS continuidad
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** POS -> LAN -> backend local: sin Internet no autoriza mutaciones offline del browser ni cola local; ante LAN/backend/DB caído se bloquea y recupera idempotentemente.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-066 |
| **2. Nombre de la tarea** | Implementar política de conectividad, reconexión y offline aprobada |
| **3. Objetivo** | Evitar pérdida o duplicación de operaciones cuando la red se degrada y hacer explícito qué puede operar offline. |
| **4. Problema que resuelve** | La pérdida temporal de conexión y operación offline no fueron verificadas; offline figura ausente. |
| **5. Hallazgo relacionado** | POS-028 no verificado; operación offline ausente. |
| **6. Módulos afectados** | POS networking, service worker/local storage si se aprueba, API idempotency y support. |
| **7. Archivos/áreas a inspeccionar** | Query client; fetch layer; stores; service worker; mutation queue si existe; health/readiness. |
| **8. Dependencias previas** | ZM-FIN-003, ZM-FIN-028–035 y DEC-17 LOCAL_FIRST aprobada. |
| **9. Cambios a implementar** | Implementar detección de Internet/LAN/backend, estados, retry seguro y recuperación de resultado. La caída de Internet conserva POS→LAN→backend local; no implementar mutaciones offline del browser ni cola local. Si LAN/backend/PostgreSQL no están disponibles, bloquear claramente la mutación. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Cola local inconsistente, exposición de datos o vender con stock/precio obsoleto. |
| **13. Posibles regresiones** | Flujos online y expiración de sesión. |
| **14. Pruebas requeridas** | Desconexión antes/durante/después del commit, refresh, cola repetida, reloj local, almacenamiento lleno y sesión expirada. |
| **15. Criterios de aceptación** | La UI nunca crea duplicados; el usuario distingue Internet externo de backend local y sabe si la operación está pendiente/confirmada/no enviada; sin Internet la tienda opera por LAN, pero no existe mutación browser-offline ni cola local. |
| **16. Definition of Done específica** | La UI nunca crea duplicados; el usuario sabe si la operación está pendiente/confirmada/no enviada; capacidades offline coinciden con la política. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas de red controlada, replay y reconciliación tras reconexión. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Posible |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-084 y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-066 — Implementar política de conectividad, reconexión y offline aprobada**.

**Objetivo**
Evitar pérdida o duplicación de operaciones cuando la red se degrada y hacer explícito qué puede operar offline.

**Problema y contexto de ZeroMerma**
La pérdida temporal de conexión y operación offline no fueron verificadas; offline figura ausente. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
POS-028 no verificado; operación offline ausente.

**Dependencias que puedes asumir terminadas**
ZM-FIN-003, ZM-FIN-028–035 y DEC-17 LOCAL_FIRST aprobada.

**Inspección inicial obligatoria**
Inspecciona capa de red, persistencia local, service worker y manejo actual de errores/timeouts.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Implementar detección de Internet/LAN/backend, estados, retry seguro y recuperación de resultado. La caída de Internet conserva POS→LAN→backend local; no implementar mutaciones offline del browser ni cola local. Si LAN/backend/PostgreSQL no están disponibles, bloquear claramente.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No implementar offline completo por defecto ni permitir comandos críticos sin una estrategia aprobada. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Commit exitoso/respuesta perdida, múltiples pestañas, reinicio, usuario distinto, datos obsoletos y conflicto al sincronizar.

**Concurrencia y consistencia**
Sincronización de varias operaciones debe respetar orden/clave y no ejecutarse dos veces.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Posible. Cambios POS: Sí. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Desconexión antes/durante/después del commit, refresh, cola repetida, reloj local, almacenamiento lleno y sesión expirada.

**Validación y comandos**
Pruebas E2E con network emulation, unitarias de cola si existe y reconciliación backend. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
La UI nunca crea duplicados; el usuario sabe si la operación está pendiente/confirmada/no enviada; capacidades offline coinciden con la política.
Definition of Done específica: La UI nunca crea duplicados; el usuario sabe si la operación está pendiente/confirmada/no enviada; capacidades offline coinciden con la política. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Política de continuidad/offline y mensajes al usuario.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-067 — Validar accesibilidad, experiencia táctil, teclado, localización y sesión

**Épica:** POS UX

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-067 |
| **2. Nombre de la tarea** | Validar accesibilidad, experiencia táctil, teclado, localización y sesión |
| **3. Objetivo** | Reducir error humano y asegurar uso consistente en dispositivos reales y terminales compartidas. |
| **4. Problema que resuelve** | La experiencia física no fue verificable; hay pantallas muy grandes, textos/enums inconsistentes y autocomplete de contraseña observado. |
| **5. Hallazgo relacionado** | ZM-MAINT-016; ZMA-UX-001; ZMA-UI-001; POS-031 no verificado. |
| **6. Módulos afectados** | POS UI, shared UI, auth/session y hardware viewports. |
| **7. Archivos/áreas a inspeccionar** | Componentes críticos; focus/keyboard; i18n labels; login/logout; CSS responsive; pantallas grandes. |
| **8. Dependencias previas** | ZM-FIN-056–066 y dispositivos objetivo. |
| **9. Cambios a implementar** | Ejecutar auditoría de tareas; corregir foco, targets táctiles, contraste, traducción, errores obsoletos, autocomplete y estados de carga; modularizar sólo con caracterización. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Cambios visuales que reduzcan densidad operativa o refactor masivo de pantallas grandes. |
| **13. Posibles regresiones** | Atajos, layout táctil, scroll y rendimiento. |
| **14. Pruebas requeridas** | Viewports objetivo/reducido/amplio, teclado, touch, lector si aplica, sesión expirada, errores y flujo con una mano. |
| **15. Criterios de aceptación** | Los flujos críticos se completan por touch/teclado; mensajes son accionables y en lenguaje aprobado; logout limpia estado de app. |
| **16. Definition of Done específica** | Los flujos críticos se completan por touch/teclado; mensajes son accionables y en lenguaje aprobado; logout limpia estado de app. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Informe UX/accesibilidad, capturas y pruebas automatizadas/manuales en hardware. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Feature Complete y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-067 — Validar accesibilidad, experiencia táctil, teclado, localización y sesión**.

**Objetivo**
Reducir error humano y asegurar uso consistente en dispositivos reales y terminales compartidas.

**Problema y contexto de ZeroMerma**
La experiencia física no fue verificable; hay pantallas muy grandes, textos/enums inconsistentes y autocomplete de contraseña observado. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-MAINT-016; ZMA-UX-001; ZMA-UI-001; POS-031 no verificado.

**Dependencias que puedes asumir terminadas**
ZM-FIN-056–066 y dispositivos objetivo.

**Inspección inicial obligatoria**
Inspecciona pantallas críticas y componentes compartidos; prioriza bugs observados y tareas reales.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Ejecutar auditoría de tareas; corregir foco, targets táctiles, contraste, traducción, errores obsoletos, autocomplete y estados de carga; modularizar sólo con caracterización.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No rediseñar la marca ni modularizar por métricas arbitrarias. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Zoom, teclado virtual, alto contraste, foco tras modal, sesión caducada y terminal compartida.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Viewports objetivo/reducido/amplio, teclado, touch, lector si aplica, sesión expirada, errores y flujo con una mano.

**Validación y comandos**
Vitest, pruebas a11y, Playwright por viewport y validación en dispositivo. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Los flujos críticos se completan por touch/teclado; mensajes son accionables y en lenguaje aprobado; logout limpia estado de app.
Definition of Done específica: Los flujos críticos se completan por touch/teclado; mensajes son accionables y en lenguaje aprobado; logout limpia estado de app. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Guía UX POS, glosario y matriz de dispositivos soportados.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```


## Fase 6 — Backoffice y módulos de negocio Feature Complete — Tareas ejecutables

### ZM-FIN-068 — Completar productos, clases, categorías, UOM y disponibilidad

**Épica:** Catálogo
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-068 |
| **2. Nombre de la tarea** | Completar productos, clases, categorías, UOM y disponibilidad |
| **3. Objetivo** | Consolidar un catálogo operativo que diferencie estado activo, vendibilidad, uso como insumo y disponibilidad por sucursal. |
| **4. Problema que resuelve** | Un insumo activo/no vendible se reportó inactivo y la visibilidad de un producto nuevo en POS quedó bloqueada. |
| **5. Hallazgo relacionado** | ZMA-CAT-001; XT-015 bloqueado; ZM-DATA-004. |
| **6. Módulos afectados** | Catalog, products, classes, categories, UOM, branch availability, POS y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Modelos/servicios de producto/clase; `_product_status`; páginas de catálogo; endpoints consumidos por POS. |
| **8. Dependencias previas** | ZM-FIN-003, ZM-FIN-048 y ZM-FIN-056. |
| **9. Cambios a implementar** | Separar estados semánticos; validar tipos de producto; gestionar UOM y disponibilidad por sucursal; publicar cambios al POS; impedir combinaciones inválidas. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Cambiar semántica de campos legacy o vender insumos por error. |
| **13. Posibles regresiones** | Filtros, recetas, pricing y catálogo POS. |
| **14. Pruebas requeridas** | Activo/inactivo, sellable/no sellable, input/finished good, sin precio, sin disponibilidad, clase vacía, UOM fraccional y sucursal. |
| **15. Criterios de aceptación** | El mismo producto tiene estado coherente en API/POS/Backoffice; insumo activo no se etiqueta inactivo por no ser vendible; cambios persisten tras recarga. |
| **16. Definition of Done específica** | El mismo producto tiene estado coherente en API/POS/Backoffice; insumo activo no se etiqueta inactivo por no ser vendible; cambios persisten tras recarga. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E creación→publicación→consulta POS y pruebas de estados. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-069–072, producción y ventas Feature Complete. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-068 — Completar productos, clases, categorías, UOM y disponibilidad**.

**Objetivo**
Consolidar un catálogo operativo que diferencie estado activo, vendibilidad, uso como insumo y disponibilidad por sucursal.

**Problema y contexto de ZeroMerma**
Un insumo activo/no vendible se reportó inactivo y la visibilidad de un producto nuevo en POS quedó bloqueada. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-CAT-001; XT-015 bloqueado; ZM-DATA-004.

**Dependencias que puedes asumir terminadas**
ZM-FIN-003, ZM-FIN-048 y ZM-FIN-056.

**Inspección inicial obligatoria**
Inspecciona enums/campos de producto, funciones de status, disponibilidad y adapters frontend.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Separar estados semánticos; validar tipos de producto; gestionar UOM y disponibilidad por sucursal; publicar cambios al POS; impedir combinaciones inválidas.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No mezclar estado de producto con stock ni crear catálogos paralelos. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Producto sin clase/precio/UOM, sucursal desactivada, código duplicado y cambio mientras hay ventas/pedidos.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Activo/inactivo, sellable/no sellable, input/finished good, sin precio, sin disponibilidad, clase vacía, UOM fraccional y sucursal.

**Validación y comandos**
Pruebas API, E2E Backoffice→POS, contract tests y builds. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
El mismo producto tiene estado coherente en API/POS/Backoffice; insumo activo no se etiqueta inactivo por no ser vendible; cambios persisten tras recarga.
Definition of Done específica: El mismo producto tiene estado coherente en API/POS/Backoffice; insumo activo no se etiqueta inactivo por no ser vendible; cambios persisten tras recarga. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Diccionario de estados/tipos/UOM y manual de catálogo.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-069 — Completar versionado, activación y cálculo de costo de recetas

**Épica:** Recetas
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-069 |
| **2. Nombre de la tarea** | Completar versionado, activación y cálculo de costo de recetas |
| **3. Objetivo** | Hacer que cada receta usada por producción sea inmutable, reproducible y tenga un costo explicable. |
| **4. Problema que resuelve** | Existe versionado y receta activa única, pero no se verificó inmutabilidad histórica; la UI mostró estados de insumo incorrectos. |
| **5. Hallazgo relacionado** | ZMA-CAT-001; ZM-DATA-004; elementos no verificables de recetas. |
| **6. Módulos afectados** | Recipes, catalog, costing, inventory y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Modelos Recipe/version; restricciones de activa; servicios de costo; páginas recetas-costos. |
| **8. Dependencias previas** | ZM-FIN-054 y ZM-FIN-068. |
| **9. Cambios a implementar** | Bloquear edición de versión usada; crear nueva versión; validar componentes/UOM/rendimiento; calcular costo con precisión; activar/desactivar atómicamente. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Alterar costos históricos o permitir dos recetas activas. |
| **13. Posibles regresiones** | Producción, disponibilidad de insumos y reportes de costo. |
| **14. Pruebas requeridas** | Receta sin componentes, insumo inactivo, dos activas concurrentes, versión usada, costo faltante, rendimiento cero y redondeo. |
| **15. Criterios de aceptación** | Producción referencia una versión inmutable; sólo una activa por producto; costo se reconstruye desde componentes y reglas aprobadas. |
| **16. Definition of Done específica** | Producción referencia una versión inmutable; sólo una activa por producto; costo se reconstruye desde componentes y reglas aprobadas. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas de constraints/concurrencia, ejemplos de costo y E2E de versionado. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-070 y Gate Feature Complete. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-069 — Completar versionado, activación y cálculo de costo de recetas**.

**Objetivo**
Hacer que cada receta usada por producción sea inmutable, reproducible y tenga un costo explicable.

**Problema y contexto de ZeroMerma**
Existe versionado y receta activa única, pero no se verificó inmutabilidad histórica; la UI mostró estados de insumo incorrectos. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-CAT-001; ZM-DATA-004; elementos no verificables de recetas.

**Dependencias que puedes asumir terminadas**
ZM-FIN-054 y ZM-FIN-068.

**Inspección inicial obligatoria**
Inspecciona modelos, índices parciales, cálculo de costo y edición de recetas utilizadas.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Bloquear edición de versión usada; crear nueva versión; validar componentes/UOM/rendimiento; calcular costo con precisión; activar/desactivar atómicamente.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No sobreescribir una versión histórica ni introducir optimización de recetas. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Activación concurrente, ingrediente duplicado, conversión UOM, versión clonada y costo sin precio de insumo.

**Concurrencia y consistencia**
Dos activaciones concurrentes deben dejar una sola receta activa.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Receta sin componentes, insumo inactivo, dos activas concurrentes, versión usada, costo faltante, rendimiento cero y redondeo.

**Validación y comandos**
Pruebas dominio/DB/E2E, migración y generación contractual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Producción referencia una versión inmutable; sólo una activa por producto; costo se reconstruye desde componentes y reglas aprobadas.
Definition of Done específica: Producción referencia una versión inmutable; sólo una activa por producto; costo se reconstruye desde componentes y reglas aprobadas. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Manual de versionado y fórmula de costo.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-070 — Completar planificación y ciclo start/cancel/complete

**Épica:** Producción
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-070 |
| **2. Nombre de la tarea** | Completar planificación y ciclo start/cancel/complete |
| **3. Objetivo** | Ofrecer una operación de producción coherente desde la planificación hasta el cierre del lote. |
| **4. Problema que resuelve** | La cancelación dejó mensajes/métricas contradictorios y faltan garantías integrales de consumo, rendimiento y estados. |
| **5. Hallazgo relacionado** | ZMA-PROD-001; ZM-DATA-004. |
| **6. Módulos afectados** | Production API, inventory, recipes, Backoffice y audit. |
| **7. Archivos/áreas a inspeccionar** | Servicios y páginas de producción; summaries; shortage logic; estados y acciones. |
| **8. Dependencias previas** | ZM-FIN-035, ZM-FIN-054 y ZM-FIN-069. |
| **9. Cambios a implementar** | Aplicar máquina de estados; mostrar acciones válidas; resolver shortages; registrar plan/real/rendimiento; limpiar errores obsoletos; alinear métricas con estados. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Permitir transiciones imposibles o borrar evidencia de faltantes/consumos. |
| **13. Posibles regresiones** | Resumen de producción y lotes existentes. |
| **14. Pruebas requeridas** | Crear, iniciar con/sin faltantes, cancelar, completar, parcial si aprobado, replay, dos usuarios y receta desactivada. |
| **15. Criterios de aceptación** | UI/API/DB muestran un único estado coherente; lote cancelado no cuenta como pendiente ni muestra mensajes incompatibles; movimientos reconcilian. |
| **16. Definition of Done específica** | UI/API/DB muestran un único estado coherente; lote cancelado no cuenta como pendiente ni muestra mensajes incompatibles; movimientos reconcilian. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E del ciclo y snapshots de resumen/ledger. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | Gate Feature Complete y producción piloto. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-070 — Completar planificación y ciclo start/cancel/complete**.

**Objetivo**
Ofrecer una operación de producción coherente desde la planificación hasta el cierre del lote.

**Problema y contexto de ZeroMerma**
La cancelación dejó mensajes/métricas contradictorios y faltan garantías integrales de consumo, rendimiento y estados. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-PROD-001; ZM-DATA-004.

**Dependencias que puedes asumir terminadas**
ZM-FIN-035, ZM-FIN-054 y ZM-FIN-069.

**Inspección inicial obligatoria**
Inspecciona filtros de summary/warnings, manejo de error 409 y botones/acciones por estado.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Aplicar máquina de estados; mostrar acciones válidas; resolver shortages; registrar plan/real/rendimiento; limpiar errores obsoletos; alinear métricas con estados.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No añadir planificación predictiva en esta tarea. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Faltante resuelto entre intentos, cancelación tras consumo, complete con rendimiento distinto y lote antiguo.

**Concurrencia y consistencia**
Start/cancel/complete concurrentes deben serializar por lote.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Crear, iniciar con/sin faltantes, cancelar, completar, parcial si aprobado, replay, dos usuarios y receta desactivada.

**Validación y comandos**
Pruebas API/DB/E2E y reconciliación de movimientos. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
UI/API/DB muestran un único estado coherente; lote cancelado no cuenta como pendiente ni muestra mensajes incompatibles; movimientos reconcilian.
Definition of Done específica: UI/API/DB muestran un único estado coherente; lote cancelado no cuenta como pendiente ni muestra mensajes incompatibles; movimientos reconcilian. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
SOP de producción y máquina de estados.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-071 — Completar listas de precios y resolución de precio efectivo

**Épica:** Pricing
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-071 |
| **2. Nombre de la tarea** | Completar listas de precios y resolución de precio efectivo |
| **3. Objetivo** | Garantizar que el backend resuelva un precio vigente, trazable y consistente por producto/sucursal/canal. |
| **4. Problema que resuelve** | Precios tienen CRUD real, pero la pantalla falló una vez y venta usa totales sin un motor comercial completo. |
| **5. Hallazgo relacionado** | BO-006 fallido; observación de pantalla en blanco; ZM-FUNC-012. |
| **6. Módulos afectados** | Pricing, catalog, sales, orders, POS y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Modelos/servicios de precios; páginas; SaleCommandService/OrdersCommandService; contratos. |
| **8. Dependencias previas** | ZM-FIN-003, ZM-FIN-068 y ZM-FIN-009. |
| **9. Cambios a implementar** | Cargar configuración empresarial inicial aprobada sin heredar precios demo; definir vigencia/prioridad/scope; resolver precio backend; snapshot en línea; validar solapamientos y precisión; corregir estados UI carga/error. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Cobrar precio equivocado o recalcular históricos. |
| **13. Posibles regresiones** | Catálogo POS, pedidos y reportes de ventas. |
| **14. Pruebas requeridas** | Sin precio, dos precios vigentes, cambio durante carrito, sucursal/canal, fecha/hora, redondeo y producto inactivo. |
| **15. Criterios de aceptación** | Ningún precio seed/demo se vuelve productivo sin aprobación empresarial; venta/pedido obtienen el mismo precio efectivo; línea conserva snapshot; conflictos de vigencia son rechazados o resueltos por regla aprobada. |
| **16. Definition of Done específica** | Venta/pedido obtienen el mismo precio efectivo; línea conserva snapshot; conflictos de vigencia son rechazados o resueltos por regla aprobada. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Casos de pricing, E2E y trazabilidad price→sale line. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-072, ZM-FIN-056 y Gate Feature Complete. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-071 — Completar listas de precios y resolución de precio efectivo**.

**Objetivo**
Garantizar que el backend resuelva un precio vigente, trazable y consistente por producto/sucursal/canal.

**Problema y contexto de ZeroMerma**
Precios tienen CRUD real, pero la pantalla falló una vez y venta usa totales sin un motor comercial completo. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
BO-006 fallido; observación de pantalla en blanco; ZM-FUNC-012.

**Dependencias que puedes asumir terminadas**
ZM-FIN-003, ZM-FIN-068 y ZM-FIN-009.

**Inspección inicial obligatoria**
Inspecciona modelos de precio, queries de vigencia, cálculo actual de subtotal/total y pantalla en blanco/error boundary.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir vigencia/prioridad/scope; resolver precio backend; snapshot en línea; validar solapamientos y precisión; corregir estados UI carga/error.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No introducir descuentos en esta tarea. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Solapamiento, timezone, precio cero, alta precisión, cambio tras agregar al carrito y sucursal sin override.

**Concurrencia y consistencia**
Dos actualizaciones de vigencia concurrentes no deben dejar reglas ambiguas.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Sin precio, dos precios vigentes, cambio durante carrito, sucursal/canal, fecha/hora, redondeo y producto inactivo.

**Validación y comandos**
Pruebas dominio/DB, E2E POS/Backoffice y contract tests. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Venta/pedido obtienen el mismo precio efectivo; línea conserva snapshot; conflictos de vigencia son rechazados o resueltos por regla aprobada.
Definition of Done específica: Venta/pedido obtienen el mismo precio efectivo; línea conserva snapshot; conflictos de vigencia son rechazados o resueltos por regla aprobada. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Política de pricing y manual de vigencias.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-072 — Implementar el motor de descuentos comerciales

**Épica:** Descuentos
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-072 |
| **2. Nombre de la tarea** | Implementar el motor de descuentos comerciales |
| **3. Objetivo** | Conectar reglas administrativas al cálculo real de ventas/pedidos con snapshot y explicación. |
| **4. Problema que resuelve** | `CommercialDiscount` tiene CRUD, pero venta/pedido no lo consultan y total=subtotal. |
| **5. Hallazgo relacionado** | ZM-FUNC-012; ZMA-FUNC-001. |
| **6. Módulos afectados** | Discounts, pricing, sales, orders, tickets, POS y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | `CommercialDiscount`; services; páginas de descuentos; cálculo de total; ticket schemas. |
| **8. Dependencias previas** | ZM-FIN-003, ZM-FIN-071 y reglas aprobadas de prioridad/acumulación/redondeo. |
| **9. Cambios a implementar** | Cargar sólo promociones/configuración empresarial aprobada; crear motor determinista; elegibilidad/vigencia; combinación; límites; autorización de excepción; snapshot de regla y desglose en respuesta/ticket. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Erosión de margen, reglas contradictorias o descuentos duplicados. |
| **13. Posibles regresiones** | Ventas/pedidos existentes, impuestos si aplican y tickets. |
| **14. Pruebas requeridas** | Regla expirada/futura, múltiples reglas, no acumulable, porcentaje/fijo, límite, redondeo, devolución y replay. |
| **15. Criterios de aceptación** | Commercial discounts demo no se migran como autoridad; backend calcula el mismo total para venta/pedido; regla aplicada queda versionada; UI no puede alterar el total; devolución preserva base. |
| **16. Definition of Done específica** | Backend calcula el mismo total para venta/pedido; regla aplicada queda versionada; UI no puede alterar el total; devolución preserva base. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Tabla de casos, E2E y snapshot discount→sale/order/ticket. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | Gate Feature Complete y reportes comerciales. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-072 — Implementar el motor de descuentos comerciales**.

**Objetivo**
Conectar reglas administrativas al cálculo real de ventas/pedidos con snapshot y explicación.

**Problema y contexto de ZeroMerma**
`CommercialDiscount` tiene CRUD, pero venta/pedido no lo consultan y total=subtotal. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-FUNC-012; ZMA-FUNC-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-003, ZM-FIN-071 y reglas aprobadas de prioridad/acumulación/redondeo.

**Inspección inicial obligatoria**
Inspecciona modelo de descuento, CRUD, servicios de venta/pedido y cualquier descuento operativo distinto.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Crear motor determinista; elegibilidad/vigencia; combinación; límites; autorización de excepción; snapshot de regla y desglose en respuesta/ticket.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No mezclar descuentos comerciales con pagos/cargos operativos ni usar lógica sólo frontend. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Dos reglas, cantidad mínima, producto/clase/sucursal, monto cero, refund parcial y cambio de reloj.

**Concurrencia y consistencia**
Cambio de regla durante venta: usar snapshot/resolución transaccional consistente.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Regla expirada/futura, múltiples reglas, no acumulable, porcentaje/fijo, límite, redondeo, devolución y replay.

**Validación y comandos**
Pruebas de dominio, integración, E2E y generación contractual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Backend calcula el mismo total para venta/pedido; regla aplicada queda versionada; UI no puede alterar el total; devolución preserva base.
Definition of Done específica: Backend calcula el mismo total para venta/pedido; regla aplicada queda versionada; UI no puede alterar el total; devolución preserva base. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Reglas comerciales, ejemplos y permisos.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-073 — Completar proveedores y órdenes de compra

**Épica:** Compras
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-073 |
| **2. Nombre de la tarea** | Completar proveedores y órdenes de compra |
| **3. Objetivo** | Gestionar proveedores y compromisos de compra con estados, cantidades y autorización claros. |
| **4. Problema que resuelve** | Proveedores/compras tienen implementación real, pero no fueron probados exhaustivamente ni ligados a un ciclo completo. |
| **5. Hallazgo relacionado** | Matriz funcional; ZMA-DATA-001. |
| **6. Módulos afectados** | Suppliers, purchase orders, catalog inputs, permissions y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Servicios/modelos/páginas de proveedores y compras; estados; referencias externas. |
| **8. Dependencias previas** | ZM-FIN-018, ZM-FIN-053 y ZM-FIN-068. |
| **9. Cambios a implementar** | Validar datos de proveedor; máquina de estados de PO; líneas/UOM/precios; aprobación/cancelación; duplicados y scope. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Compromisos duplicados o editar documentos ya recibidos. |
| **13. Posibles regresiones** | Recepción administrativa funcional y catálogo de insumos. |
| **14. Pruebas requeridas** | Proveedor inactivo, código/factura duplicada, PO vacía, parcial, cancelación, edición tras recepción y sucursal. |
| **15. Criterios de aceptación** | Puede crearse y administrar una PO válida; estados impiden mutaciones incompatibles; permisos/scope se respetan. |
| **16. Definition of Done específica** | Puede crearse y administrar una PO válida; estados impiden mutaciones incompatibles; permisos/scope se respetan. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E Backoffice y pruebas API/DB. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-074 y Gate Feature Complete. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-073 — Completar proveedores y órdenes de compra**.

**Objetivo**
Gestionar proveedores y compromisos de compra con estados, cantidades y autorización claros.

**Problema y contexto de ZeroMerma**
Proveedores/compras tienen implementación real, pero no fueron probados exhaustivamente ni ligados a un ciclo completo. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Matriz funcional; ZMA-DATA-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-018, ZM-FIN-053 y ZM-FIN-068.

**Inspección inicial obligatoria**
Inspecciona modelos/constraints, estados, formularios y relación con receipts.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Validar datos de proveedor; máquina de estados de PO; líneas/UOM/precios; aprobación/cancelación; duplicados y scope.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No implementar cuentas por pagar completas sin alcance aprobado. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Proveedor duplicado, PO parcial, cambio de precio, producto desactivado y sucursal no autorizada.

**Concurrencia y consistencia**
Dos aprobaciones/cancelaciones concurrentes de la misma PO.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Proveedor inactivo, código/factura duplicada, PO vacía, parcial, cancelación, edición tras recepción y sucursal.

**Validación y comandos**
Pruebas API/E2E y generación contractual. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Puede crearse y administrar una PO válida; estados impiden mutaciones incompatibles; permisos/scope se respetan.
Definition of Done específica: Puede crearse y administrar una PO válida; estados impiden mutaciones incompatibles; permisos/scope se respetan. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
SOP de proveedores y órdenes de compra.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-074 — Completar recepción, diferencias y correcciones de compra

**Épica:** Compras
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-074 |
| **2. Nombre de la tarea** | Completar recepción, diferencias y correcciones de compra |
| **3. Objetivo** | Cerrar el flujo físico de compra con recepción total/parcial, costo y compensaciones. |
| **4. Problema que resuelve** | Una recepción administrativa sí movió inventario; faltan validaciones completas de parcial/exceso/corrección. |
| **5. Hallazgo relacionado** | ZMA-DATA-001. |
| **6. Módulos afectados** | Purchase receipts, inventory, costing, suppliers y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Servicios/páginas de recepción; modelos de receipt; movement/cost; correcciones. |
| **8. Dependencias previas** | ZM-FIN-053 y ZM-FIN-073. |
| **9. Cambios a implementar** | Implementar recepción contra PO o directa si aprobada; diferencias; lote/fecha si aplica; corrección compensatoria; documento/folio y audit. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Sobreinventario, costo incorrecto o corrección destructiva. |
| **13. Posibles regresiones** | Flujo de recepción ya probado y reportes de compras. |
| **14. Pruebas requeridas** | Total/parcial/exceso, daño/rechazo, costo distinto, invoice duplicada, replay y cancelación. |
| **15. Criterios de aceptación** | Recepción y movimientos/costo coinciden; no excede pendiente; corrección no edita historia; estado PO es consistente. |
| **16. Definition of Done específica** | Recepción y movimientos/costo coinciden; no excede pendiente; corrección no edita historia; estado PO es consistente. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E y reconciliación purchase→receipt→movement. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-075 y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-074 — Completar recepción, diferencias y correcciones de compra**.

**Objetivo**
Cerrar el flujo físico de compra con recepción total/parcial, costo y compensaciones.

**Problema y contexto de ZeroMerma**
Una recepción administrativa sí movió inventario; faltan validaciones completas de parcial/exceso/corrección. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-DATA-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-053 y ZM-FIN-073.

**Inspección inicial obligatoria**
Inspecciona validaciones de receipt, costo, invoice y estado PO.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Implementar recepción contra PO o directa si aprobada; diferencias; lote/fecha si aplica; corrección compensatoria; documento/folio y audit.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No borrar receipts confirmados. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Recepción sin PO, parcial múltiple, UOM distinta, costo cero y proveedor inactivo.

**Concurrencia y consistencia**
Dos recepciones concurrentes del mismo pendiente.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Total/parcial/exceso, daño/rechazo, costo distinto, invoice duplicada, replay y cancelación.

**Validación y comandos**
Pruebas API/DB/E2E y reconciliación. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Recepción y movimientos/costo coinciden; no excede pendiente; corrección no edita historia; estado PO es consistente.
Definition of Done específica: Recepción y movimientos/costo coinciden; no excede pendiente; corrección no edita historia; estado PO es consistente. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
SOP de recepción y diferencias.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-075 — Completar balances, conteos y ajustes administrativos

**Épica:** Inventario Backoffice
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-075 |
| **2. Nombre de la tarea** | Completar balances, conteos y ajustes administrativos |
| **3. Objetivo** | Permitir consultar y corregir inventario con permisos, causa y conciliación sin romper el ledger. |
| **4. Problema que resuelve** | Inventario admin es real, pero permisos/scopes y políticas de concurrencia/stock negativo no estaban cerrados. |
| **5. Hallazgo relacionado** | ZM-SEC-001; ZM-SEC-002; ZM-DATA-004. |
| **6. Módulos afectados** | Inventory admin, stock counts, adjustments, reports y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Servicios/páginas de balances/movements/counts/adjustments; permisos y filtros. |
| **8. Dependencias previas** | ZM-FIN-018, ZM-FIN-021–022 y ZM-FIN-048–055. |
| **9. Cambios a implementar** | Mostrar on-hand/reserved/available; conteo con snapshot; ajuste compensatorio; causa/aprobación; filtros y exportación scoped. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Ajustes usados para ocultar defectos o conteo basado en snapshot obsoleto. |
| **13. Posibles regresiones** | Consultas de inventario y performance. |
| **14. Pruebas requeridas** | Conteo concurrente, stock negativo, ajuste cero, producto/sucursal ajena, replay y reconstrucción. |
| **15. Criterios de aceptación** | Ningún saldo se edita directamente; cada ajuste crea movimiento causal; UI reconcilia balance y movimientos. |
| **16. Definition of Done específica** | Ningún saldo se edita directamente; cada ajuste crea movimiento causal; UI reconcilia balance y movimientos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E de conteo/ajuste y reconciliación. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | Gate Feature Complete y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-075 — Completar balances, conteos y ajustes administrativos**.

**Objetivo**
Permitir consultar y corregir inventario con permisos, causa y conciliación sin romper el ledger.

**Problema y contexto de ZeroMerma**
Inventario admin es real, pero permisos/scopes y políticas de concurrencia/stock negativo no estaban cerrados. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-001; ZM-SEC-002; ZM-DATA-004.

**Dependencias que puedes asumir terminadas**
ZM-FIN-018, ZM-FIN-021–022 y ZM-FIN-048–055.

**Inspección inicial obligatoria**
Inspecciona todos los endpoints/páginas de inventory admin y cualquier update directo de balance.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Mostrar on-hand/reserved/available; conteo con snapshot; ajuste compensatorio; causa/aprobación; filtros y exportación scoped.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No permitir UPDATE directo del saldo desde UI. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Conteo parcial, dos conteos, saldo cambiado durante conteo, UOM y producto inactivo.

**Concurrencia y consistencia**
Commit de conteo debe detectar movimientos posteriores al snapshot o aplicar política aprobada.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Conteo concurrente, stock negativo, ajuste cero, producto/sucursal ajena, replay y reconstrucción.

**Validación y comandos**
Pruebas integración/E2E, scopes/permisos y reconciliación. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Ningún saldo se edita directamente; cada ajuste crea movimiento causal; UI reconcilia balance y movimientos.
Definition of Done específica: Ningún saldo se edita directamente; cada ajuste crea movimiento causal; UI reconcilia balance y movimientos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
SOP de conteo/ajuste y permisos.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-076 — Completar administración de transferencias y recepciones

**Épica:** Transferencias Backoffice
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-076 |
| **2. Nombre de la tarea** | Completar administración de transferencias y recepciones |
| **3. Objetivo** | Permitir crear, seguir y resolver transferencias multi-sucursal desde Backoffice usando el mismo backend canónico. |
| **4. Problema que resuelve** | Backoffice integra inventario, pero debe converger con POS y scopes. |
| **5. Hallazgo relacionado** | ZM-DATA-004; ZMA-DATA-001; ZM-SEC-002. |
| **6. Módulos afectados** | Transfers admin, inventory, branches y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Páginas/servicios de transferencias; filtros; estados; relación con POS. |
| **8. Dependencias previas** | ZM-FIN-052, ZM-FIN-021–022 y ZM-FIN-062. |
| **9. Cambios a implementar** | Completar list/detail/create/send/receive/cancel según máquina; mostrar tránsito, parcial y discrepancias; aplicar permissions/scopes. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Flujo administrativo divergente o fuga cross-branch. |
| **13. Posibles regresiones** | Transferencias ya operativas. |
| **14. Pruebas requeridas** | Origen/destino, parcial, exceso, cancelación, daño, acceso ajeno y retry. |
| **15. Criterios de aceptación** | Backoffice y POS comparten IDs/estado; sólo sucursales autorizadas; movimientos reconcilian. |
| **16. Definition of Done específica** | Backoffice y POS comparten IDs/estado; sólo sucursales autorizadas; movimientos reconcilian. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E cruzado POS↔Backoffice y reconciliación. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-086 y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-076 — Completar administración de transferencias y recepciones**.

**Objetivo**
Permitir crear, seguir y resolver transferencias multi-sucursal desde Backoffice usando el mismo backend canónico.

**Problema y contexto de ZeroMerma**
Backoffice integra inventario, pero debe converger con POS y scopes. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-DATA-004; ZMA-DATA-001; ZM-SEC-002.

**Dependencias que puedes asumir terminadas**
ZM-FIN-052, ZM-FIN-021–022 y ZM-FIN-062.

**Inspección inicial obligatoria**
Inspecciona adapters y servicios admin frente al core canónico.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Completar list/detail/create/send/receive/cancel según máquina; mostrar tránsito, parcial y discrepancias; aplicar permissions/scopes.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No duplicar lógica de dominio en frontend. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Administrador global/limitado, recepción parcial y documento creado por POS.

**Concurrencia y consistencia**
Dos acciones sobre el mismo estado/remanente.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Origen/destino, parcial, exceso, cancelación, daño, acceso ajeno y retry.

**Validación y comandos**
Pruebas API/E2E multi-sucursal y builds. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Backoffice y POS comparten IDs/estado; sólo sucursales autorizadas; movimientos reconcilian.
Definition of Done específica: Backoffice y POS comparten IDs/estado; sólo sucursales autorizadas; movimientos reconcilian. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Manual administrativo de transferencias.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-077 — Completar UX de usuarios, roles, sucursales, cajas y estaciones

**Épica:** Administración base
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-077 |
| **2. Nombre de la tarea** | Completar UX de usuarios, roles, sucursales, cajas y estaciones |
| **3. Objetivo** | Permitir configurar la topología operativa y accesos sin inconsistencias ni elevación de privilegios. |
| **4. Problema que resuelve** | El CRUD existe, pero RBAC/scopes estaban incompletos y la actividad/último login eran incorrectos. |
| **5. Hallazgo relacionado** | ZM-SEC-001; ZM-SEC-002; ZMA-ID-001. |
| **6. Módulos afectados** | Identity, branches, cash registers, workstations, POS access y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Páginas/servicios de usuarios/roles/branches/registers/workstations; assignments; activity views. |
| **8. Dependencias previas** | ZM-FIN-015–025 y ZM-FIN-040. |
| **9. Cambios a implementar** | Alinear formularios con grants/scopes; gestionar asignaciones; validar relaciones; mostrar actividad por superficie y último login real; impedir autoelevación. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Bloquear a todos los administradores o asignar caja/sucursal cruzada. |
| **13. Posibles regresiones** | Login POS, workstation access y seeds. |
| **14. Pruebas requeridas** | Primer usuario/rol, último superadmin, branch desactivada, workstation duplicada, caja asignada y usuario bloqueado. |
| **15. Criterios de aceptación** | Configuración persiste y controla acceso real; métricas de actividad son correctas; no hay asignaciones inválidas. |
| **16. Definition of Done específica** | Configuración persiste y controla acceso real; métricas de actividad son correctas; no hay asignaciones inválidas. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E por rol/scope y pruebas de persistencia/auditoría. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | Gate Feature Complete y operación multi-sucursal. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-077 — Completar UX de usuarios, roles, sucursales, cajas y estaciones**.

**Objetivo**
Permitir configurar la topología operativa y accesos sin inconsistencias ni elevación de privilegios.

**Problema y contexto de ZeroMerma**
El CRUD existe, pero RBAC/scopes estaban incompletos y la actividad/último login eran incorrectos. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-001; ZM-SEC-002; ZMA-ID-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-015–025 y ZM-FIN-040.

**Inspección inicial obligatoria**
Inspecciona formularios, assignments y queries de activity/last_login.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Alinear formularios con grants/scopes; gestionar asignaciones; validar relaciones; mostrar actividad por superficie y último login real; impedir autoelevación.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No crear permisos sólo visuales. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Desactivar recurso en uso, último admin, usuario con varias sucursales y estación ya asignada.

**Concurrencia y consistencia**
Dos cambios concurrentes de asignación/estado deben respetar constraints.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Primer usuario/rol, último superadmin, branch desactivada, workstation duplicada, caja asignada y usuario bloqueado.

**Validación y comandos**
Pruebas API/E2E, RBAC/scope y builds. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Configuración persiste y controla acceso real; métricas de actividad son correctas; no hay asignaciones inválidas.
Definition of Done específica: Configuración persiste y controla acceso real; métricas de actividad son correctas; no hay asignaciones inválidas. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Manual de topología/usuarios y matriz de roles.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-078 — Completar ventas, pedidos y tickets en Backoffice

**Épica:** Administración comercial
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-078 |
| **2. Nombre de la tarea** | Completar ventas, pedidos y tickets en Backoffice |
| **3. Objetivo** | Permitir consulta, soporte y acciones administrativas aprobadas sobre documentos comerciales sin alterar historia. |
| **4. Problema que resuelve** | Las rutas son reales y datos coinciden, pero necesitan permisos, scopes, estados y acciones de soporte completos. |
| **5. Hallazgo relacionado** | XT-001–003 aprobados; ZM-SEC-001/002. |
| **6. Módulos afectados** | Sales, orders, tickets, payments, Backoffice y audit. |
| **7. Archivos/áreas a inspeccionar** | Páginas list/detail; routers admin; filtros; reprint; acciones cancel/refund si existen. |
| **8. Dependencias previas** | ZM-FIN-017–022, ZM-FIN-041–046 y ZM-FIN-058–059. |
| **9. Cambios a implementar** | Completar búsqueda/filtros/detail; mostrar causalidad y pagos; acciones sólo por comando compensatorio; reimpresión; permisos/scopes. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Exponer datos cross-branch o permitir cambios destructivos. |
| **13. Posibles regresiones** | Listados actuales, filtros y performance. |
| **14. Pruebas requeridas** | ID inexistente, otra sucursal, pago mixto, pedido pagado, ticket histórico, export y acción no permitida. |
| **15. Criterios de aceptación** | El administrador puede investigar un documento extremo a extremo; ninguna acción edita filas históricas; permisos y audit son correctos. |
| **16. Definition of Done específica** | El administrador puede investigar un documento extremo a extremo; ninguna acción edita filas históricas; permisos y audit son correctos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E y grafo de IDs por documento. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-083–085 y soporte piloto. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-078 — Completar ventas, pedidos y tickets en Backoffice**.

**Objetivo**
Permitir consulta, soporte y acciones administrativas aprobadas sobre documentos comerciales sin alterar historia.

**Problema y contexto de ZeroMerma**
Las rutas son reales y datos coinciden, pero necesitan permisos, scopes, estados y acciones de soporte completos. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
XT-001–003 aprobados; ZM-SEC-001/002.

**Dependencias que puedes asumir terminadas**
ZM-FIN-017–022, ZM-FIN-041–046 y ZM-FIN-058–059.

**Inspección inicial obligatoria**
Inspecciona páginas dedicadas, acciones disponibles y queries/admin services.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Completar búsqueda/filtros/detail; mostrar causalidad y pagos; acciones sólo por comando compensatorio; reimpresión; permisos/scopes.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No añadir edición directa de ventas confirmadas. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Documento legacy, pago pendiente, refund, sesión cerrada, búsqueda por folio y paginación.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
ID inexistente, otra sucursal, pago mixto, pedido pagado, ticket histórico, export y acción no permitida.

**Validación y comandos**
Pruebas API/E2E y reconciliación. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
El administrador puede investigar un documento extremo a extremo; ninguna acción edita filas históricas; permisos y audit son correctos.
Definition of Done específica: El administrador puede investigar un documento extremo a extremo; ninguna acción edita filas históricas; permisos y audit son correctos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Manual de soporte de ventas/pedidos/tickets.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-079 — Completar devoluciones y correcciones en Backoffice

**Épica:** Administración de flujos inversos
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-079 |
| **2. Nombre de la tarea** | Completar devoluciones y correcciones en Backoffice |
| **3. Objetivo** | Permitir investigar y ejecutar compensaciones autorizadas con la misma semántica que POS. |
| **4. Problema que resuelve** | Los documentos existen, pero inventario/reversas eran incompletos y autorización granular ausente. |
| **5. Hallazgo relacionado** | ZM-DATA-004; ZMA-DATA-001; ZM-SEC-001. |
| **6. Módulos afectados** | Returns, corrections, refunds, inventory, Backoffice y audit. |
| **7. Archivos/áreas a inspeccionar** | Páginas/routers de devoluciones/correcciones; actions; detail; permisos. |
| **8. Dependencias previas** | ZM-FIN-018, ZM-FIN-031, ZM-FIN-044 y ZM-FIN-051. |
| **9. Cambios a implementar** | Completar list/detail/create/review según alcance; causas/disposición; permisos; enlaces a venta/pago/movimiento; compensación idempotente. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Bypass de controles POS o abuso administrativo. |
| **13. Posibles regresiones** | Módulos actuales y reportes netos. |
| **14. Pruebas requeridas** | Parcial, sobredevolución, no restock, pago no reversible, otra sucursal, replay y documento ya corregido. |
| **15. Criterios de aceptación** | Backoffice y POS crean el mismo tipo de resultado; no hay edición histórica; dinero/stock/audit reconcilian. |
| **16. Definition of Done específica** | Backoffice y POS crean el mismo tipo de resultado; no hay edición histórica; dinero/stock/audit reconcilian. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E y grafo causal. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | Soporte piloto y Gate Feature Complete. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-079 — Completar devoluciones y correcciones en Backoffice**.

**Objetivo**
Permitir investigar y ejecutar compensaciones autorizadas con la misma semántica que POS.

**Problema y contexto de ZeroMerma**
Los documentos existen, pero inventario/reversas eran incompletos y autorización granular ausente. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-DATA-004; ZMA-DATA-001; ZM-SEC-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-018, ZM-FIN-031, ZM-FIN-044 y ZM-FIN-051.

**Inspección inicial obligatoria**
Compara servicios admin/POS y todas las acciones UI.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Completar list/detail/create/review según alcance; causas/disposición; permisos; enlaces a venta/pago/movimiento; compensación idempotente.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No permitir UPDATE/DELETE de ventas o movimientos. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Refund externo pendiente, ticket de otra sucursal, cantidad acumulada y usuario sin permiso.

**Concurrencia y consistencia**
Dos devoluciones/correcciones concurrentes.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Parcial, sobredevolución, no restock, pago no reversible, otra sucursal, replay y documento ya corregido.

**Validación y comandos**
Pruebas API/E2E, RBAC/scope y reconciliación. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Backoffice y POS crean el mismo tipo de resultado; no hay edición histórica; dinero/stock/audit reconcilian.
Definition of Done específica: Backoffice y POS crean el mismo tipo de resultado; no hay edición histórica; dinero/stock/audit reconcilian. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
SOP administrativo de compensaciones.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-080 — Conectar el módulo administrativo de pagos operativos

**Épica:** Pagos operativos
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-080 |
| **2. Nombre de la tarea** | Conectar el módulo administrativo de pagos operativos |
| **3. Objetivo** | Reemplazar la superficie simulada por consulta y gestión real de entradas/salidas operativas autorizadas. |
| **4. Problema que resuelve** | La ruta Backoffice de pagos operativos estaba en preparación mientras el POS creó un pago real. |
| **5. Hallazgo relacionado** | ZM-FUNC-013; ZMA-BO-001. |
| **6. Módulos afectados** | Operational payments, cash ledger, Backoffice, reports y RBAC. |
| **7. Archivos/áreas a inspeccionar** | `AdminModulePage`/`adminData.ts`; endpoints de pagos operativos; cash flow; permisos. |
| **8. Dependencias previas** | ZM-FIN-017–018, ZM-FIN-032, ZM-FIN-043 y ZM-FIN-045. |
| **9. Cambios a implementar** | Implementar list/detail/filtros; mostrar sesión/causa/actor; crear/revertir sólo si aprobado; eliminar datos simulados y conectar API real. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Permitir pagos administrativos sin control o doble contabilización. |
| **13. Posibles regresiones** | Cash flow/cierre y navegación genérica. |
| **14. Pruebas requeridas** | Colección vacía, POS-created record, otra sucursal, refund/reversa, export y permiso denegado. |
| **15. Criterios de aceptación** | La ruta consume API real; el pago auditado aparece con monto/causa correctos; no se presenta `isBackendConnected:false`. |
| **16. Definition of Done específica** | La ruta consume API real; el pago auditado aparece con monto/causa correctos; no se presenta `isBackendConnected:false`. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E con registro POS y pruebas RBAC/scope. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | Dashboard/reportes y Gate Feature Complete. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-080 — Conectar el módulo administrativo de pagos operativos**.

**Objetivo**
Reemplazar la superficie simulada por consulta y gestión real de entradas/salidas operativas autorizadas.

**Problema y contexto de ZeroMerma**
La ruta Backoffice de pagos operativos estaba en preparación mientras el POS creó un pago real. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-FUNC-013; ZMA-BO-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-017–018, ZM-FIN-032, ZM-FIN-043 y ZM-FIN-045.

**Inspección inicial obligatoria**
Inspecciona placeholder, hooks de datos, API existente y permisos.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Implementar list/detail/filtros; mostrar sesión/causa/actor; crear/revertir sólo si aprobado; eliminar datos simulados y conectar API real.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No dejar una lista local o mock como fuente. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Cero registros, sesión cerrada, efectivo/no efectivo, reversa y paginación.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Colección vacía, POS-created record, otra sucursal, refund/reversa, export y permiso denegado.

**Validación y comandos**
Pruebas API/E2E y reconciliación con cash ledger. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
La ruta consume API real; el pago auditado aparece con monto/causa correctos; no se presenta `isBackendConnected:false`.
Definition of Done específica: La ruta consume API real; el pago auditado aparece con monto/causa correctos; no se presenta `isBackendConnected:false`. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Manual de pagos operativos y permisos.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-081 — Completar limpieza, sanidad, incidencias y equipos desde estado vacío

**Épica:** Calidad y mantenimiento
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-081 |
| **2. Nombre de la tarea** | Completar limpieza, sanidad, incidencias y equipos desde estado vacío |
| **3. Objetivo** | Permitir iniciar y operar módulos de calidad/mantenimiento sin dependencia circular de registros previos. |
| **4. Problema que resuelve** | Incidencias y equipos no podían crear el primer registro porque el selector de sucursal derivaba de la colección vacía. |
| **5. Hallazgo relacionado** | ZMA-BO-002; módulos de calidad funcionales con deficiencias. |
| **6. Módulos afectados** | Cleaning, sanitary, incidents, equipment, branches y Backoffice. |
| **7. Archivos/áreas a inspeccionar** | Servicios/páginas de cada módulo; selectores de sucursal; catálogo maestro de branches. |
| **8. Dependencias previas** | ZM-FIN-021–022 y ZM-FIN-077. |
| **9. Cambios a implementar** | Cargar catálogos maestros; completar CRUD/estados/adjuntos si están aprobados; permisos/scopes; estados vacío/error; auditoría. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Crear catálogos duplicados o exponer registros de otra sucursal. |
| **13. Posibles regresiones** | Limpieza/sanidad ya funcionales. |
| **14. Pruebas requeridas** | Cero registros, primera alta, branch desactivada, duplicado, cierre/cancelación y filtro. |
| **15. Criterios de aceptación** | Puede crearse el primer incidente/equipo; todos los módulos usan sucursales autorizadas y persisten tras recarga. |
| **16. Definition of Done específica** | Puede crearse el primer incidente/equipo; todos los módulos usan sucursales autorizadas y persisten tras recarga. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E desde DB vacía y pruebas de scope. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | Gate Feature Complete y operación piloto. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-081 — Completar limpieza, sanidad, incidencias y equipos desde estado vacío**.

**Objetivo**
Permitir iniciar y operar módulos de calidad/mantenimiento sin dependencia circular de registros previos.

**Problema y contexto de ZeroMerma**
Incidencias y equipos no podían crear el primer registro porque el selector de sucursal derivaba de la colección vacía. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-BO-002; módulos de calidad funcionales con deficiencias.

**Dependencias que puedes asumir terminadas**
ZM-FIN-021–022 y ZM-FIN-077.

**Inspección inicial obligatoria**
Inspecciona cómo se construyen opciones de branch y compara módulos que sí funcionan desde vacío.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Cargar catálogos maestros; completar CRUD/estados/adjuntos si están aprobados; permisos/scopes; estados vacío/error; auditoría.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No inventar workflows de mantenimiento no aprobados. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Colección vacía, branch sin registros, recurso cerrado, mantenimiento recurrente y usuario limitado.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Cero registros, primera alta, branch desactivada, duplicado, cierre/cancelación y filtro.

**Validación y comandos**
Pruebas API/E2E desde estado vacío y builds. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Puede crearse el primer incidente/equipo; todos los módulos usan sucursales autorizadas y persisten tras recarga.
Definition of Done específica: Puede crearse el primer incidente/equipo; todos los módulos usan sucursales autorizadas y persisten tras recarga. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
SOP de calidad/mantenimiento y estados.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-082 — Conectar el dashboard a métricas canónicas

**Épica:** Dashboard
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** DEC-18 es el diccionario: KPI mostrado exige versión, fórmula, fuente, lineage, dimensiones/scope, owner, freshness/validez/DQ y prueba; catálogo exhaustivo no significa dashboard saturado.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-082 |
| **2. Nombre de la tarea** | Conectar el dashboard a métricas canónicas |
| **3. Objetivo** | Reemplazar la superficie simulada por KPIs definidos, scoped y reconciliables. |
| **4. Problema que resuelve** | Dashboard mostraba shell genérico sin backend conectado. |
| **5. Hallazgo relacionado** | ZM-FUNC-013; ZMA-BO-001. |
| **6. Módulos afectados** | Dashboard API/Backoffice, sales, cash, inventory, production y alerts. |
| **7. Archivos/áreas a inspeccionar** | `AdminModulePage`; data hooks; queries/report services; definiciones KPI. |
| **8. Dependencias previas** | ZM-FIN-021, ZM-FIN-041–055 y DEC-18; ZM-FIN-093 integra posteriormente las proyecciones derivadas sin crear dependencia circular. |
| **9. Cambios a implementar** | Consumir el catálogo KPI DEC-18 versionado; implementar endpoints/read models; definición/fórmula/source/lineage/dimensions/owner/validity/DQ; filtros fecha/sucursal/timezone; estados loading/empty/error/stale/unavailable/reconciliation-required; enlaces a detalle. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | KPIs ambiguos o consultas pesadas sobre OLTP. |
| **13. Posibles regresiones** | Carga Backoffice y reportes. |
| **14. Pruebas requeridas** | Sin datos, múltiples sucursales, corte pendiente, stock negativo, worker degradado, fechas/timezone y permiso. |
| **15. Criterios de aceptación** | Cada cifra declara versión, fórmula, source/lineage, scope, owner y validez; coincide con reconciliación; no presenta simulación ni no_data/stale/estimated como cero/current/measured; las vistas son selectivas. |
| **16. Definition of Done específica** | Cada cifra tiene definición y query fuente; coincide con reconciliación; dashboard no presenta datos simulados. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Matriz KPI→consulta→dato fuente y E2E. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | No |
| **23. Tareas posteriores que desbloquea** | Gate Feature Complete y operación piloto. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-082 — Conectar el dashboard a métricas canónicas**.

**Objetivo**
Reemplazar la superficie simulada por KPIs definidos, scoped y reconciliables.

**Problema y contexto de ZeroMerma**
Dashboard mostraba shell genérico sin backend conectado. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-FUNC-013; ZMA-BO-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-021, ZM-FIN-041–055 y DEC-18; ZM-FIN-093 integra posteriormente las proyecciones derivadas sin crear dependencia circular.

**Inspección inicial obligatoria**
Inspecciona placeholder actual y datos canónicos disponibles; no reutilices métricas defectuosas.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir KPIs; implementar endpoints/read models; filtros fecha/sucursal/timezone; estados loading/empty/error; enlaces a detalle.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No construir un data warehouse en esta tarea. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Datos atrasados, timezone, scope global/múltiple, cero vs nulo y error parcial.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: No. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Sin datos, múltiples sucursales, corte pendiente, stock negativo, worker degradado, fechas/timezone y permiso.

**Validación y comandos**
Pruebas de queries, reconciliación, E2E y performance básica. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada cifra tiene definición y query fuente; coincide con reconciliación; dashboard no presenta datos simulados.
Definition of Done específica: Cada cifra tiene definición y query fuente; coincide con reconciliación; dashboard no presenta datos simulados. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Diccionario de KPIs y filtros.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-083 — Completar reportes y exportaciones operativas

**Épica:** Reportes
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-083 |
| **2. Nombre de la tarea** | Completar reportes y exportaciones operativas |
| **3. Objetivo** | Entregar reportes reales, autorizados y exportables con definiciones reconciliadas. |
| **4. Problema que resuelve** | Ocho reportes tenían queries reales, tres requerían backend y export sólo devolvía JSON; mixed payments era incorrecto. |
| **5. Hallazgo relacionado** | ZM-FUNC-013; ZMA-REP-001; ZM-SEC-001/002. |
| **6. Módulos afectados** | Reports API, exports, Backoffice, ledgers y RBAC/scopes. |
| **7. Archivos/áreas a inspeccionar** | Definiciones de reportes; `requires_backend`; preview/export; `required_permissions`; páginas. |
| **8. Dependencias previas** | ZM-FIN-017, ZM-FIN-021, ZM-FIN-045 y ZM-FIN-082. |
| **9. Cambios a implementar** | Completar cada reporte aprobado como vertical; CSV/XLSX/PDF sólo según decisión; filtros/paginación; permisos; timezone; generación streaming/job para volúmenes grandes. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Fuga de datos, agotamiento de memoria o definiciones distintas entre preview/export. |
| **13. Posibles regresiones** | Queries existentes y performance. |
| **14. Pruebas requeridas** | Sin datos, mixed payment, multi-sucursal, fecha límite, export grande, fórmula decimal, permiso y timeout. |
| **15. Criterios de aceptación** | Ningún reporte productivo está marcado `requires_backend`; preview/export coinciden con consulta canónica y scope. |
| **16. Definition of Done específica** | Ningún reporte productivo está marcado `requires_backend`; preview/export coinciden con consulta canónica y scope. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Reconciliación KPI/reporte, archivos de prueba y E2E. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Posible |
| **23. Tareas posteriores que desbloquea** | Gate Feature Complete y soporte operacional. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-083 — Completar reportes y exportaciones operativas**.

**Objetivo**
Entregar reportes reales, autorizados y exportables con definiciones reconciliadas.

**Problema y contexto de ZeroMerma**
Ocho reportes tenían queries reales, tres requerían backend y export sólo devolvía JSON; mixed payments era incorrecto. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-FUNC-013; ZMA-REP-001; ZM-SEC-001/002.

**Dependencias que puedes asumir terminadas**
ZM-FIN-017, ZM-FIN-021, ZM-FIN-045 y ZM-FIN-082.

**Inspección inicial obligatoria**
Inspecciona las 11 definiciones, SQL, flags, permisos y flujo export actual.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Completar cada reporte aprobado como vertical; CSV/XLSX/PDF sólo según decisión; filtros/paginación; permisos; timezone; generación streaming/job para volúmenes grandes.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No generar formatos no aprobados ni consultar tablas sin semántica. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Rango amplio, varias sucursales, caracteres/locale, nulos, cancelación de job y datos cambiantes.

**Concurrencia y consistencia**
Para export asíncrona, snapshot/consistencia y deduplicación de jobs.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: Posible. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Sin datos, mixed payment, multi-sucursal, fecha límite, export grande, fórmula decimal, permiso y timeout.

**Validación y comandos**
Pruebas de query/export, RBAC/scope, performance y E2E. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Ningún reporte productivo está marcado `requires_backend`; preview/export coinciden con consulta canónica y scope.
Definition of Done específica: Ningún reporte productivo está marcado `requires_backend`; preview/export coinciden con consulta canónica y scope. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Catálogo de reportes, definiciones y formatos.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-084 — Completar el explorador de auditoría y garantías de inmutabilidad

**Épica:** Auditoría
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-084 |
| **2. Nombre de la tarea** | Completar el explorador de auditoría y garantías de inmutabilidad |
| **3. Objetivo** | Permitir investigar acciones con contexto correcto sin exponer o modificar el rastro. |
| **4. Problema que resuelve** | AuditLog es amplio, pero origen/contexto eran incorrectos y no hay garantía DB de inmutabilidad. |
| **5. Hallazgo relacionado** | ZMA-AUD-001; ZM-OBS-017; ZM-SEC-001. |
| **6. Módulos afectados** | Audit API/DB, Backoffice, identity y all domains. |
| **7. Archivos/áreas a inspeccionar** | `AuditLog`; consultas; UI; permisos; roles DB; triggers/constraints si se justifican. |
| **8. Dependencias previas** | ZM-FIN-017, ZM-FIN-040 y política de retención. |
| **9. Cambios a implementar** | Corregir filtros/detail/labels; contexto legible; export autorizada; impedir update/delete por rol de aplicación; definir retención/archivo. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Bloquear mantenimiento legítimo o almacenar PII excesiva. |
| **13. Posibles regresiones** | Reportes de actividad y performance de audit. |
| **14. Pruebas requeridas** | POS/Backoffice/worker, ID crudo, actor eliminado, otra sucursal, intento de update/delete y rango grande. |
| **15. Criterios de aceptación** | Cada acción sensible es investigable; origen/scope/operation ID correctos; la app no puede modificar registros existentes. |
| **16. Definition of Done específica** | Cada acción sensible es investigable; origen/scope/operation ID correctos; la app no puede modificar registros existentes. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas de inmutabilidad, E2E y caso de investigación extremo a extremo. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Security Ready/Production Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-084 — Completar el explorador de auditoría y garantías de inmutabilidad**.

**Objetivo**
Permitir investigar acciones con contexto correcto sin exponer o modificar el rastro.

**Problema y contexto de ZeroMerma**
AuditLog es amplio, pero origen/contexto eran incorrectos y no hay garantía DB de inmutabilidad. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-AUD-001; ZM-OBS-017; ZM-SEC-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-017, ZM-FIN-040 y política de retención.

**Inspección inicial obligatoria**
Inspecciona permisos DB del usuario app, modelos, endpoints y UI actual.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Corregir filtros/detail/labels; contexto legible; export autorizada; impedir update/delete por rol de aplicación; definir retención/archivo.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No usar audit para reconstruir saldos si existe ledger canónico. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Actor borrado, request anónimo, evento asíncrono, retención y datos sensibles.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
POS/Backoffice/worker, ID crudo, actor eliminado, otra sucursal, intento de update/delete y rango grande.

**Validación y comandos**
Pruebas API/DB/E2E, intento de mutación y performance de consulta. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada acción sensible es investigable; origen/scope/operation ID correctos; la app no puede modificar registros existentes.
Definition of Done específica: Cada acción sensible es investigable; origen/scope/operation ID correctos; la app no puede modificar registros existentes. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Política de auditoría, retención y procedimiento de investigación.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-085 — Completar configuración administrativa segura

**Épica:** Configuración
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-085 |
| **2. Nombre de la tarea** | Completar configuración administrativa segura |
| **3. Objetivo** | Gestionar settings permitidos con validación, enmascaramiento, versionado y auditoría. |
| **4. Problema que resuelve** | Configuración persiste y enmascara, pero el acceso era demasiado amplio y producción no falla cerrada. |
| **5. Hallazgo relacionado** | ZM-SEC-001; ZM-SEC-007. |
| **6. Módulos afectados** | System settings API/DB, Backoffice, runtime config y audit. |
| **7. Archivos/áreas a inspeccionar** | Modelos/servicios de settings; página; schemas por key; secrets vs non-secrets. |
| **8. Dependencias previas** | ZM-FIN-017, ZM-FIN-026–027. |
| **9. Cambios a implementar** | Clasificar settings runtime vs deploy-time; validar tipos/rangos; impedir editar secretos en UI salvo política; versionar cambios y aplicar sin estado ambiguo. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Configurar producción en estado inseguro o sobrescribir secretos con máscara. |
| **13. Posibles regresiones** | Arranque y módulos que consumen settings. |
| **14. Pruebas requeridas** | Valor inválido, secreto enmascarado, concurrent update, restart required, scope global/branch y rollback. |
| **15. Criterios de aceptación** | Sólo settings aprobados son editables; cambios inválidos no persisten; secretos no se exponen; auditoría registra before/after redacted. |
| **16. Definition of Done específica** | Sólo settings aprobados son editables; cambios inválidos no persisten; secretos no se exponen; auditoría registra before/after redacted. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E, pruebas de validación y eventos de audit. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Feature Complete y Production Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-085 — Completar configuración administrativa segura**.

**Objetivo**
Gestionar settings permitidos con validación, enmascaramiento, versionado y auditoría.

**Problema y contexto de ZeroMerma**
Configuración persiste y enmascara, pero el acceso era demasiado amplio y producción no falla cerrada. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-001; ZM-SEC-007.

**Dependencias que puedes asumir terminadas**
ZM-FIN-017, ZM-FIN-026–027.

**Inspección inicial obligatoria**
Inspecciona catálogo de keys, defaults, enmascaramiento y cómo se cargan en runtime.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Clasificar settings runtime vs deploy-time; validar tipos/rangos; impedir editar secretos en UI salvo política; versionar cambios y aplicar sin estado ambiguo.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No almacenar secretos productivos en la tabla si la plataforma debe inyectarlos. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Update concurrente, valor vacío, restart, branch override y permiso read-only.

**Concurrencia y consistencia**
Usar versión/etag o conflicto para evitar lost update si varios admins editan.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Valor inválido, secreto enmascarado, concurrent update, restart required, scope global/branch y rollback.

**Validación y comandos**
Pruebas API/E2E, settings matrix y arranque con valores resultantes. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Sólo settings aprobados son editables; cambios inválidos no persisten; secretos no se exponen; auditoría registra before/after redacted.
Definition of Done específica: Sólo settings aprobados son editables; cambios inválidos no persisten; secretos no se exponen; auditoría registra before/after redacted. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Catálogo de settings y operación segura.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-086 — Completar flujos de administración central y operación entre sucursales

**Épica:** Multi-sucursal
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST y hechos de dominio/UI alimentan KPI sin autoridad analítica, vigilancia innecesaria ni alerta por cada métrica.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-086 |
| **2. Nombre de la tarea** | Completar flujos de administración central y operación entre sucursales |
| **3. Objetivo** | Demostrar que ZeroMerma opera varias sucursales con aislamiento, consolidación y transferencias controladas. |
| **4. Problema que resuelve** | Los scopes administrativos no existían y los escenarios cross-branch no fueron validados de extremo a extremo. |
| **5. Hallazgo relacionado** | ZM-SEC-002; ZMA-SEC-002; XT-016 no disponible. |
| **6. Módulos afectados** | Branches, identity, catalog/pricing, inventory, transfers, reports, dashboard y configuration. |
| **7. Archivos/áreas a inspeccionar** | Todos los servicios con branch; selector de contexto; asignaciones; reportes consolidados; transferencias. |
| **8. Dependencias previas** | ZM-FIN-020–022, ZM-FIN-068–085. |
| **9. Cambios a implementar** | Definir configuración global/override; catálogo por branch; usuarios multi-branch; consolidación autorizada; transferencias; cambio de contexto explícito y auditable. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Fuga de datos, configuración ambigua o producto/precio distinto sin visibilidad. |
| **13. Posibles regresiones** | Operación single-branch y queries de reportes. |
| **14. Pruebas requeridas** | Usuario una/múltiples/global, branch inactiva, datos compartidos/override, transferencia parcial y reporte consolidado. |
| **15. Criterios de aceptación** | Operaciones de una sucursal no fugan a otra; administración global sólo con permiso; consolidación y transferencias reconcilian. |
| **16. Definition of Done específica** | Operaciones de una sucursal no fugan a otra; administración global sólo con permiso; consolidación y transferencias reconcilian. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E con al menos dos sucursales y matriz de aislamiento/consolidación. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Feature Complete y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-086 — Completar flujos de administración central y operación entre sucursales**.

**Objetivo**
Demostrar que ZeroMerma opera varias sucursales con aislamiento, consolidación y transferencias controladas.

**Problema y contexto de ZeroMerma**
Los scopes administrativos no existían y los escenarios cross-branch no fueron validados de extremo a extremo. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-002; ZMA-SEC-002; XT-016 no disponible.

**Dependencias que puedes asumir terminadas**
ZM-FIN-020–022, ZM-FIN-068–085.

**Inspección inicial obligatoria**
Inspecciona cada entidad global/scoped y cómo el frontend selecciona contexto.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir configuración global/override; catálogo por branch; usuarios multi-branch; consolidación autorizada; transferencias; cambio de contexto explícito y auditable.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No introducir multi-tenancy físico ni duplicar catálogos sin necesidad. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Cambio de branch durante formulario, usuario global, branch cerrada, transferencia y timezone.

**Concurrencia y consistencia**
Cambios globales/overrides concurrentes y transferencias entre sucursales.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Usuario una/múltiples/global, branch inactiva, datos compartidos/override, transferencia parcial y reporte consolidado.

**Validación y comandos**
Suites multi-sucursal API/E2E y reconciliación. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Operaciones de una sucursal no fugan a otra; administración global sólo con permiso; consolidación y transferencias reconcilian.
Definition of Done específica: Operaciones de una sucursal no fugan a otra; administración global sólo con permiso; consolidación y transferencias reconcilian. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Modelo operativo multi-sucursal y matriz global/override.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```


## Fase 7 — Worker, outbox, alertas, notificaciones y eventos — Tareas ejecutables

### ZM-FIN-087 — Implementar la máquina de estados del outbox

**Épica:** Outbox
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Delivery at-least-once, claim/lease, attempts, retry/backoff, DLQ/escalamiento, stuck recovery y métricas ASY.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-087 |
| **2. Nombre de la tarea** | Implementar la máquina de estados del outbox |
| **3. Objetivo** | Convertir la tabla de eventos en una cola durable con claim seguro, retry y estado terminal observable. |
| **4. Problema que resuelve** | El worker selecciona y registra eventos, pero no actualiza processed_at/intentos/errores; 34 eventos quedaron pendientes con cero intentos. |
| **5. Hallazgo relacionado** | ZM-ASYNC-006; ZMA-ASYNC-001. |
| **6. Módulos afectados** | Outbox model, worker poller, PostgreSQL y migrations. |
| **7. Archivos/áreas a inspeccionar** | `OutboxEvent`; `OutboxPoller.poll_once`; queries `FOR UPDATE SKIP LOCKED`; worker settings/tests. |
| **8. Dependencias previas** | ZM-FIN-011, ZM-FIN-028 y ZM-FIN-040. |
| **9. Cambios a implementar** | Definir pending/processing/processed/failed/dead; lease/claimed_by/claimed_at; attempts; next_attempt_at; last_error redacted; backoff, DLQ/escalamiento, recuperación de lease/stuck event y métricas DEC-18. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Perder eventos, procesarlos en bucle o bloquear la cola por un mensaje venenoso. |
| **13. Posibles regresiones** | Creación transaccional actual de outbox y consultas existentes. |
| **14. Pruebas requeridas** | Éxito, fallo transitorio/permanente, crash tras claim, lease vencido, dos workers, poison message y DB caída. |
| **15. Criterios de aceptación** | Un evento durable se entrega at-least-once y avanza controladamente; dos workers no lo procesan simultáneamente bajo el mismo claim; fallos se reintentan y quedan recuperables/escalables sin perder el evento; outbox demo/test nunca se presenta como historia productiva. |
| **16. Definition of Done específica** | Un evento avanza de forma monotónica; dos workers no lo procesan simultáneamente; fallos se reintentan y finalmente quedan recuperables. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Migración, pruebas concurrentes con dos pollers y estados observados. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-088–093 y Gate Data Integrity Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-087 — Implementar la máquina de estados del outbox**.

**Objetivo**
Convertir la tabla de eventos en una cola durable con claim seguro, retry y estado terminal observable.

**Problema y contexto de ZeroMerma**
El worker selecciona y registra eventos, pero no actualiza processed_at/intentos/errores; 34 eventos quedaron pendientes con cero intentos. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-ASYNC-006; ZMA-ASYNC-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-011, ZM-FIN-028 y ZM-FIN-040.

**Inspección inicial obligatoria**
Inspecciona modelo, índice, poll query y toda escritura/lectura de estados.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir pending/processing/processed/failed/dead; lease/claimed_by/claimed_at; attempts; next_attempt_at; last_error redacted; backoff y recuperación de lease.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No prometer exactamente una vez sobre efectos externos; no introducir broker sin necesidad. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Reloj, lease expirado, batch parcial, error serializable, backlog antiguo y shutdown.

**Concurrencia y consistencia**
Dos o más workers con SKIP LOCKED; crash/reclaim; orden por agregado cuando sea necesario.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Éxito, fallo transitorio/permanente, crash tras claim, lease vencido, dos workers, poison message y DB caída.

**Validación y comandos**
Migración, pytest worker/integración PostgreSQL y ejecución controlada multi-worker. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Un evento avanza de forma monotónica; dos workers no lo procesan simultáneamente; fallos se reintentan y finalmente quedan recuperables.
Definition of Done específica: Un evento avanza de forma monotónica; dos workers no lo procesan simultáneamente; fallos se reintentan y finalmente quedan recuperables. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
ADR de entrega al menos una vez y máquina de estados.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-088 — Implementar registro de handlers y consumidores idempotentes

**Épica:** Outbox
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Consumidores idempotentes por event_id/effect identity, schema versionado, replay y deduplicación de proyecciones/KPI.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-088 |
| **2. Nombre de la tarea** | Implementar registro de handlers y consumidores idempotentes |
| **3. Objetivo** | Despachar eventos versionados a handlers explícitos que toleren entrega repetida. |
| **4. Problema que resuelve** | No existen handlers reales ni transición a procesado; las integraciones y analítica no ocurren. |
| **5. Hallazgo relacionado** | ZM-ASYNC-006; ZMA-ASYNC-001. |
| **6. Módulos afectados** | Worker, event contracts, outbox y consumidores iniciales. |
| **7. Archivos/áreas a inspeccionar** | Handler registry; event type/version; payload schemas; consumer state/deduplication. |
| **8. Dependencias previas** | ZM-FIN-087 y catálogo de eventos aprobado. |
| **9. Cambios a implementar** | Crear registry; validar event envelope/schema_version; handler result; deduplicación por event_id/effect identity; primer consumidor real y proyección analítica; pruebas de replay/rebuild. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Handler no idempotente, acoplamiento a modelos ORM o cambio de payload sin versión. |
| **13. Posibles regresiones** | Worker poll loop y contratos de eventos existentes. |
| **14. Pruebas requeridas** | Evento desconocido, versión no soportada, payload inválido, handler éxito/fallo, replay y side effect duplicado. |
| **15. Criterios de aceptación** | Evento soportado produce un efecto una sola vez en términos observables; desconocido/invalidado no se marca exitoso silenciosamente; replay o migración distingue evidencia histórica, opening adjustment, migration record y fact analítico backfilled. |
| **16. Definition of Done específica** | Evento soportado produce un efecto una sola vez en términos observables; desconocido/invalidado no se marca exitoso silenciosamente. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas handler/replay y ejemplo de evento procesado. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-091–093 y notificaciones/analítica. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-088 — Implementar registro de handlers y consumidores idempotentes**.

**Objetivo**
Despachar eventos versionados a handlers explícitos que toleren entrega repetida.

**Problema y contexto de ZeroMerma**
No existen handlers reales ni transición a procesado; las integraciones y analítica no ocurren. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-ASYNC-006; ZMA-ASYNC-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-087 y catálogo de eventos aprobado.

**Inspección inicial obligatoria**
Inspecciona tipos/payloads actuales y qué eventos ya se emiten en ventas, admin y caja.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Crear registry; validar schema/version; handler result; deduplicación por event ID/effect key; primer consumidor real de bajo riesgo y pruebas de replay.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No acceder directamente a UI ni modificar estado transaccional original desde analytics. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Evento duplicado, orden invertido, referencia ausente, versión futura y dependencia externa caída.

**Concurrencia y consistencia**
Dos workers/replays del mismo evento deben converger en un único efecto.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Evento desconocido, versión no soportada, payload inválido, handler éxito/fallo, replay y side effect duplicado.

**Validación y comandos**
Pruebas unitarias/integración, replay controlado y mypy/ruff. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Evento soportado produce un efecto una sola vez en términos observables; desconocido/invalidado no se marca exitoso silenciosamente.
Definition of Done específica: Evento soportado produce un efecto una sola vez en términos observables; desconocido/invalidado no se marca exitoso silenciosamente. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Catálogo de handlers, contratos y política de idempotencia de consumidores.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-089 — Añadir readiness, métricas, backpressure y herramientas de recuperación

**Épica:** Operación worker
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Medir backlog, oldest_event_age, throughput, latency, failures, attempts, DLQ, stuck, consumer lag, projection freshness y safe replay.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-089 |
| **2. Nombre de la tarea** | Añadir readiness, métricas, backpressure y herramientas de recuperación |
| **3. Objetivo** | Detectar cuando el worker está vivo pero no procesa y permitir operación segura del backlog. |
| **4. Problema que resuelve** | `/health` fue 200 mientras el outbox acumulaba pendientes; no hay métricas, umbrales ni tooling de replay/dead-letter. |
| **5. Hallazgo relacionado** | ZMA-ASYNC-001; ZM-OBS-017. |
| **6. Módulos afectados** | Worker, API health/readiness, metrics, admin tooling y runbooks. |
| **7. Archivos/áreas a inspeccionar** | Worker loop; health endpoints; métricas; admin/CLI de outbox; deployment probes. |
| **8. Dependencias previas** | ZM-FIN-087–088 y ZM-FIN-040. |
| **9. Cambios a implementar** | Exponer backlog, oldest_event_age, attempts, throughput, processing_latency, failures, DLQ, stuck_events, consumer_lag, projection_freshness y last_success; readiness sin thresholds inventados; pausa/reanuda; replay/dead-letter auditado; batch/backpressure. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Readiness demasiado sensible causa reinicios en bucle o tooling permite reprocesos peligrosos. |
| **13. Posibles regresiones** | Liveness y despliegue del worker. |
| **14. Pruebas requeridas** | Worker caído, backlog creciente, poison message, DB lenta, handler externo caído, replay autorizado y múltiples workers. |
| **15. Criterios de aceptación** | La degradación es visible y accionable; ningún replay duplica efecto; tooling exige permiso y deja auditoría. |
| **16. Definition of Done específica** | La degradación es visible y accionable; ningún replay duplica efecto; tooling exige permiso y deja auditoría. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Dashboard/métricas, prueba de alerta y simulacro de recuperación. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Posible |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Posible |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-091–093, ZM-FIN-089/infra y Gate Staging Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-089 — Añadir readiness, métricas, backpressure y herramientas de recuperación**.

**Objetivo**
Detectar cuando el worker está vivo pero no procesa y permitir operación segura del backlog.

**Problema y contexto de ZeroMerma**
`/health` fue 200 mientras el outbox acumulaba pendientes; no hay métricas, umbrales ni tooling de replay/dead-letter. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-ASYNC-001; ZM-OBS-017.

**Dependencias que puedes asumir terminadas**
ZM-FIN-087–088 y ZM-FIN-040.

**Inspección inicial obligatoria**
Inspecciona health actual, logging, settings de poll y controles administrativos existentes.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Exponer backlog/edad/attempts/last success; readiness con dependencias/umbrales aprobados; pausa/reanuda; replay/dead-letter por ID con auditoría; limitar batch/backpressure.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No declarar healthy sólo porque el proceso responde. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Backlog grande pero estable, dependencia degradada, mensaje terminal, restart y pérdida de métricas.

**Concurrencia y consistencia**
Pausa/replay con workers activos debe coordinarse sin doble claim.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Posible. Cambios POS: No. Cambios Backoffice: Posible. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Worker caído, backlog creciente, poison message, DB lenta, handler externo caído, replay autorizado y múltiples workers.

**Validación y comandos**
Pruebas de probes/métricas, simulación de backlog y replay en DB efímera. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
La degradación es visible y accionable; ningún replay duplica efecto; tooling exige permiso y deja auditoría.
Definition of Done específica: La degradación es visible y accionable; ningún replay duplica efecto; tooling exige permiso y deja auditoría. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Runbook de outbox, thresholds aprobados y permisos operativos.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-090 — Implementar scheduler y trabajos asíncronos recurrentes

**Épica:** Jobs
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: at-least-once, consumidor idempotente, claim/attempts/backoff/DLQ, alertas/Telegram y proyecciones granulares reconstruibles.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-090 |
| **2. Nombre de la tarea** | Implementar scheduler y trabajos asíncronos recurrentes |
| **3. Objetivo** | Ejecutar tareas periódicas necesarias sin duplicación entre instancias y con trazabilidad. |
| **4. Problema que resuelve** | Alertas, expiraciones, exportaciones y mantenimiento pueden requerir procesos programados, pero no hay scheduler operativo demostrado. |
| **5. Hallazgo relacionado** | Brecha profesional no cubierta completamente por auditoría. |
| **6. Módulos afectados** | Worker/jobs, DB, alerts, exports, sessions y maintenance. |
| **7. Archivos/áreas a inspeccionar** | Puntos de entrada worker; tablas de job/lease si existen; scripts cron; settings. |
| **8. Dependencias previas** | ZM-FIN-087–089 y lista aprobada de jobs. |
| **9. Cambios a implementar** | Definir registro de jobs, schedule configurable, singleton/lease distribuido, idempotencia, catch-up, timeout, estado y auditoría. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Duplicar jobs, deriva horaria o bloquear worker de outbox. |
| **13. Posibles regresiones** | Uso de recursos y tiempos del worker. |
| **14. Pruebas requeridas** | Dos instancias, job atrasado, DST/timezone, fallo parcial, ejecución larga, deshabilitado y replay manual. |
| **15. Criterios de aceptación** | Cada periodo produce como máximo un efecto útil por clave; fallos son visibles; horario usa timezone explícita. |
| **16. Definition of Done específica** | Cada periodo produce como máximo un efecto útil por clave; fallos son visibles; horario usa timezone explícita. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas con reloj controlado, dos workers y estado de job. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-091–093 y exportaciones asíncronas. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-090 — Implementar scheduler y trabajos asíncronos recurrentes**.

**Objetivo**
Ejecutar tareas periódicas necesarias sin duplicación entre instancias y con trazabilidad.

**Problema y contexto de ZeroMerma**
Alertas, expiraciones, exportaciones y mantenimiento pueden requerir procesos programados, pero no hay scheduler operativo demostrado. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Brecha profesional no cubierta completamente por auditoría.

**Dependencias que puedes asumir terminadas**
ZM-FIN-087–089 y lista aprobada de jobs.

**Inspección inicial obligatoria**
Inspecciona scripts/cron existentes y tareas que hoy se ejecutan en request o no se ejecutan.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir registro de jobs, schedule configurable, singleton/lease distribuido, idempotencia, catch-up, timeout, estado y auditoría.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No usar timers en cada proceso web ni crear un scheduler distribuido complejo sin necesidad. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
DST, downtime prolongado, catch-up múltiple, job manual y configuración cambiante.

**Concurrencia y consistencia**
Dos schedulers deben resolver lease/uniqueness por ejecución.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Dos instancias, job atrasado, DST/timezone, fallo parcial, ejecución larga, deshabilitado y replay manual.

**Validación y comandos**
Pruebas con clock fake, integración PostgreSQL y ejecución multi-worker. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada periodo produce como máximo un efecto útil por clave; fallos son visibles; horario usa timezone explícita.
Definition of Done específica: Cada periodo produce como máximo un efecto útil por clave; fallos son visibles; horario usa timezone explícita. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Catálogo de jobs, horarios, dueños y runbooks.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-091 — Implementar el motor y la superficie administrativa de alertas

**Épica:** Alertas
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Dashboard local con condition, CRITICAL-A/B/C, owner/action/evidence/dedup/ACK/escalation/resolution; A=5m, B=15m, C=60m operativo; sensibilidad conservadora.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-091 |
| **2. Nombre de la tarea** | Implementar el motor y la superficie administrativa de alertas |
| **3. Objetivo** | Generar alertas reales, deduplicadas y accionables desde eventos/métricas canónicos. |
| **4. Problema que resuelve** | La ruta de alertas era un placeholder sin backend conectado. |
| **5. Hallazgo relacionado** | ZM-FUNC-013; ZMA-BO-001. |
| **6. Módulos afectados** | Alerts domain, worker/jobs, Backoffice, permissions y metrics. |
| **7. Archivos/áreas a inspeccionar** | Placeholder `/admin/alertas`; `adminData.ts`; event handlers; alert models/endpoints. |
| **8. Dependencias previas** | ZM-FIN-017, ZM-FIN-082, ZM-FIN-087–090. |
| **9. Cambios a implementar** | Implementar dashboard local completo y tipos con condition, CRITICAL-A/B/C, owner, action, causal evidence, dedup key, estado, ACK, escalation y resolution; A=5m, B=15m, C=60m en horario operativo; reglas HIGH SIGNAL/LOW NOISE; endpoints scoped y enlaces a causa. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Fatiga de alertas, duplicados o reglas sin acción. |
| **13. Posibles regresiones** | Dashboard y carga del worker. |
| **14. Pruebas requeridas** | Misma condición repetida, condición resuelta/reaparece, otra sucursal, usuario sin permiso, backlog y stock negativo. |
| **15. Criterios de aceptación** | Alertas se crean/deduplican por condición, tienen acción/owner, son scoped y permiten ACK/escalamiento/resolución auditados; no dependen de datos simulados ni existe alerta sin acción definida. |
| **16. Definition of Done específica** | Alertas se crean una vez por condición, son scoped, se pueden reconocer/resolver según política y no dependen de datos simulados. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | E2E condición→evento/job→alerta→ack y pruebas de dedup. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Feature Complete y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-091 — Implementar el motor y la superficie administrativa de alertas**.

**Objetivo**
Generar alertas reales, deduplicadas y accionables desde eventos/métricas canónicos.

**Problema y contexto de ZeroMerma**
La ruta de alertas era un placeholder sin backend conectado. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-FUNC-013; ZMA-BO-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-017, ZM-FIN-082, ZM-FIN-087–090.

**Inspección inicial obligatoria**
Inspecciona placeholder, necesidades operativas y métricas/eventos ya disponibles.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir tipos/severidad/clave de deduplicación/estado/ack/resolve; crear reglas iniciales aprobadas; endpoints scoped; UI real y enlaces a causa.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No crear alertas sin runbook/propietario ni usar datos no reconciliados. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Condición intermitente, alertas masivas, sucursal desactivada, ack concurrente y regla cambiada.

**Concurrencia y consistencia**
Dos handlers/jobs que detectan la misma condición deben deduplicar por clave.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Misma condición repetida, condición resuelta/reaparece, otra sucursal, usuario sin permiso, backlog y stock negativo.

**Validación y comandos**
Pruebas dominio/integración/E2E y simulación de regla. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Alertas se crean una vez por condición, son scoped, se pueden reconocer/resolver según política y no dependen de datos simulados.
Definition of Done específica: Alertas se crean una vez por condición, son scoped, se pueden reconocer/resolver según política y no dependen de datos simulados. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Catálogo de alertas, severidad, dueño y acción esperada.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-092 — Implementar plataforma de notificaciones externas

**Épica:** Notificaciones
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** TELEGRAM sólo crítico: persistencia local, delivery state, retry idempotente al volver Internet y fallo no bloqueante; WhatsApp futuro, separado de comunicaciones DEC-16.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-092 |
| **2. Nombre de la tarea** | Implementar plataforma de notificaciones externas |
| **3. Objetivo** | Enviar tickets, alertas u otros mensajes aprobados mediante adapters confiables y observables. |
| **4. Problema que resuelve** | Email/SMS están ausentes y requieren worker, secretos, privacidad y retry. |
| **5. Hallazgo relacionado** | Funcionalidad ausente; ZM-ASYNC-006. |
| **6. Módulos afectados** | Notifications, worker, providers, tickets, alerts, settings y privacy. |
| **7. Archivos/áreas a inspeccionar** | Provider adapters; templates; outbox handlers; notification state; settings. |
| **8. Dependencias previas** | ZM-FIN-027, ZM-FIN-060, ZM-FIN-087–091. |
| **9. Cambios a implementar** | Separar alertas operativas de comunicaciones DEC-16; implementar adapter Telegram para críticas con queued/sent/failed/pending, provider IDs, persistencia local, retry idempotente tras recuperar Internet y redacción; WhatsApp queda futuro. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Spam, fuga de PII, costo externo o mensajes duplicados. |
| **13. Posibles regresiones** | Worker backlog y ticket/alert flows. |
| **14. Pruebas requeridas** | Proveedor caído, timeout, duplicado, destino inválido, opt-out, template version, rate limit y replay. |
| **15. Criterios de aceptación** | Una alerta crítica genera como máximo un envío útil Telegram por destino/identidad; el fallo o falta de Internet no bloquea negocio, queda pendiente/reintentable y es visible sin exponer PII; WhatsApp no bloquea. |
| **16. Definition of Done específica** | Un evento genera como máximo un envío útil por canal/destino; fallo no bloquea transacción; estado y error son visibles sin exponer PII. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas con fake/sandbox, métricas y evidencia de redacción. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-094 y Gate Pilot Ready si comunicaciones están incluidas. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-092 — Implementar plataforma de notificaciones externas**.

**Objetivo**
Enviar tickets, alertas u otros mensajes aprobados mediante adapters confiables y observables.

**Problema y contexto de ZeroMerma**
Email/SMS están ausentes y requieren worker, secretos, privacidad y retry. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Funcionalidad ausente; ZM-ASYNC-006.

**Dependencias que puedes asumir terminadas**
ZM-FIN-027, ZM-FIN-060, ZM-FIN-087–091.

**Inspección inicial obligatoria**
Inspecciona todos los puntos que prometen email/SMS y la política de datos aprobada.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Crear modelo/adapter/template; estado queued/sent/failed; provider IDs; retry idempotente; opt-in/out; redacción; límites.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No usar datos reales en sandbox ni acoplar provider al dominio. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Reintento, cambio de contacto, consentimiento retirado, provider callback y template no soportado.

**Concurrencia y consistencia**
Dos handlers del mismo evento/canal deben deduplicar.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Proveedor caído, timeout, duplicado, destino inválido, opt-out, template version, rate limit y replay.

**Validación y comandos**
Pruebas unitarias/integración, sandbox controlado y escaneo de logs. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Un evento genera como máximo un envío útil por canal/destino; fallo no bloquea transacción; estado y error son visibles sin exponer PII.
Definition of Done específica: Un evento genera como máximo un envío útil por canal/destino; fallo no bloquea transacción; estado y error son visibles sin exponer PII. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Runbook de proveedores, templates y privacidad.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-093 — Versionar eventos y construir proyecciones analíticas básicas

**Épica:** Eventos y analítica
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Fact layer derivada con envelope/schema, correlation/causation, lineage, DQ y replay/rebuild determinista; OLTP local sigue autoritativo.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-093 |
| **2. Nombre de la tarea** | Versionar eventos y construir proyecciones analíticas básicas |
| **3. Objetivo** | Preparar datos confiables para reportes, alertas e IA sin consultar semánticas inconsistentes del OLTP. |
| **4. Problema que resuelve** | Audit/outbox existen, pero no hay catálogo estable ni pipeline analítico procesado. |
| **5. Hallazgo relacionado** | ZM-ASYNC-006; ZM-OBS-017; objetivo estratégico de analítica/IA. |
| **6. Módulos afectados** | Event contracts, worker, analytics projections, sales, inventory, production y waste. |
| **7. Archivos/áreas a inspeccionar** | Outbox payloads; handler registry; tablas/proyecciones; diccionario de datos. |
| **8. Dependencias previas** | ZM-FIN-040, ZM-FIN-041–055 y ZM-FIN-087–092. |
| **9. Cambios a implementar** | Crear envelope con event_id/type, schema_version, correlation_id, causation_id, entity/branch/workstation/actor, occurred_at/recorded_at y payload versionado; modelar categorías distintas para historical event, backfilled analytical fact, migration record y opening adjustment; fact layer granular; proyecciones idempotentes; replay/backfill/rebuild; DQ y lineage. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Acoplar analítica al ORM/OLTP, romper compatibilidad o duplicar métricas. |
| **13. Posibles regresiones** | Payloads consumidos por notificaciones/alertas. |
| **14. Pruebas requeridas** | Evento duplicado/tardío/fuera de orden, versión nueva, backfill, dato faltante, branch/timezone y reconstrucción completa. |
| **15. Criterios de aceptación** | Replay/rebuild produce dataset determinista sin perder/duplicar efectos; no fabrica eventos retrospectivos ni incorpora audit/outbox demo a producción; cada KPI se rastrea a hechos, opening facts, documentos o movimientos; errores de calidad/validez son visibles y analytics no muta OLTP. |
| **16. Definition of Done específica** | Reproducir eventos produce el mismo dataset; cada métrica se rastrea a documentos/movimientos; errores de calidad son visibles. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Catálogo de eventos, pruebas de replay y reconciliación de proyecciones. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Analítica/IA posterior y Gate Production Ready para reportes derivados. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-093 — Versionar eventos y construir proyecciones analíticas básicas**.

**Objetivo**
Preparar datos confiables para reportes, alertas e IA sin consultar semánticas inconsistentes del OLTP.

**Problema y contexto de ZeroMerma**
Audit/outbox existen, pero no hay catálogo estable ni pipeline analítico procesado. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-ASYNC-006; ZM-OBS-017; objetivo estratégico de analítica/IA.

**Dependencias que puedes asumir terminadas**
ZM-FIN-040, ZM-FIN-041–055 y ZM-FIN-087–092.

**Inspección inicial obligatoria**
Inventaría eventos emitidos, payloads, consumidores y métricas requeridas.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Crear envelope/version; schemas compatibles; eventos canónicos; proyecciones idempotentes; replay/backfill; quality checks y lineage.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No entrenar modelos ni permitir que analytics modifique OLTP. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Versiones coexistentes, branch, corrección/reversa, replay masivo y PII.

**Concurrencia y consistencia**
Procesamiento paralelo debe conservar idempotencia y orden cuando el agregado lo exija.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Evento duplicado/tardío/fuera de orden, versión nueva, backfill, dato faltante, branch/timezone y reconstrucción completa.

**Validación y comandos**
Pruebas de schema/replay/reconciliación y rebuild en DB analítica de prueba. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Reproducir eventos produce el mismo dataset; cada métrica se rastrea a documentos/movimientos; errores de calidad son visibles.
Definition of Done específica: Reproducir eventos produce el mismo dataset; cada métrica se rastrea a documentos/movimientos; errores de calidad son visibles. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Catálogo de eventos, lineage y diccionario analítico.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```


## Fase 8 — QA, seguridad, rendimiento y documentación — Tareas ejecutables

### ZM-FIN-094 — Cerrar pruebas unitarias, typing, lint y caracterización de dominio

**Épica:** Calidad automatizada
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: probar fórmula/validez/DQ, correlation/causation, lineage, rebuild, privacidad y futuros no bloqueantes.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-094 |
| **2. Nombre de la tarea** | Cerrar pruebas unitarias, typing, lint y caracterización de dominio |
| **3. Objetivo** | Demostrar reglas de negocio y mantener cambios seguros sin metas de cobertura arbitrarias. |
| **4. Problema que resuelve** | Existe volumen de pruebas, pero no evidencia ejecutada ni cobertura suficiente de invariantes críticas; componentes grandes elevan regresión. |
| **5. Hallazgo relacionado** | ZM-QA-011; ZM-MAINT-016. |
| **6. Módulos afectados** | API, worker, POS, Backoffice y paquetes compartidos. |
| **7. Archivos/áreas a inspeccionar** | Suites unitarias; servicios/cálculos/máquinas de estado; componentes grandes; configuraciones Ruff/mypy/Vitest. |
| **8. Dependencias previas** | ZM-FIN-010–014 y funcionalidades de Fases 2–7. |
| **9. Cambios a implementar** | Añadir unitarias por regla; caracterización antes de extracción; criterios de cobertura por riesgo/mutación; eliminar exclusiones accidentales; mantener typing estricto. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Perseguir un porcentaje y crear tests frágiles o acoplados a implementación. |
| **13. Posibles regresiones** | Tiempo de suite y falsos positivos. |
| **14. Pruebas requeridas** | Ramas de cálculo, estados inválidos, decimales, permisos, errores y componentes críticos. |
| **15. Criterios de aceptación** | Toda regla crítica tiene prueba directa; lint/typecheck/unit pasan; refactors futuros cuentan con caracterización. |
| **16. Definition of Done específica** | Toda regla crítica tiene prueba directa; lint/typecheck/unit pasan; refactors futuros cuentan con caracterización. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Resultados de suites, mapa regla→prueba y reporte de mutación/cobertura donde aporte evidencia. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Development Complete y QA Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-094 — Cerrar pruebas unitarias, typing, lint y caracterización de dominio**.

**Objetivo**
Demostrar reglas de negocio y mantener cambios seguros sin metas de cobertura arbitrarias.

**Problema y contexto de ZeroMerma**
Existe volumen de pruebas, pero no evidencia ejecutada ni cobertura suficiente de invariantes críticas; componentes grandes elevan regresión. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-QA-011; ZM-MAINT-016.

**Dependencias que puedes asumir terminadas**
ZM-FIN-010–014 y funcionalidades de Fases 2–7.

**Inspección inicial obligatoria**
Inspecciona gaps contra las invariantes documentadas, no sólo líneas sin cubrir.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Añadir unitarias por regla; caracterización antes de extracción; criterios de cobertura por riesgo/mutación; eliminar exclusiones accidentales; mantener typing estricto.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No reducir reglas de calidad ni escribir tests que sólo afirmen mocks sin comportamiento. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Timezone, Decimal, enums, error branches, estado vacío y adapters externos fake.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Ramas de cálculo, estados inválidos, decimales, permisos, errores y componentes críticos.

**Validación y comandos**
Ruff, mypy, pytest, Vitest y herramienta de cobertura/mutation aprobada. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Toda regla crítica tiene prueba directa; lint/typecheck/unit pasan; refactors futuros cuentan con caracterización.
Definition of Done específica: Toda regla crítica tiene prueba directa; lint/typecheck/unit pasan; refactors futuros cuentan con caracterización. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar guía de pruebas por nivel y criterios de caracterización.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-095 — Construir la suite negativa de RBAC y scopes

**Épica:** Pruebas de seguridad
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: probar fórmula/validez/DQ, correlation/causation, lineage, rebuild, privacidad y futuros no bloqueantes.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-095 |
| **2. Nombre de la tarea** | Construir la suite negativa de RBAC y scopes |
| **3. Objetivo** | Probar sistemáticamente que identidades no autorizadas no leen ni mutan datos. |
| **4. Problema que resuelve** | Las pruebas existentes suelen cubrir POS-only→403, no Backoffice limitado ni cross-branch. |
| **5. Hallazgo relacionado** | ZM-QA-011; ZM-SEC-001/002. |
| **6. Módulos afectados** | API, identity, all admin routes, reports/exports y worker jobs. |
| **7. Archivos/áreas a inspeccionar** | Fixtures multi-rol/multi-sucursal; matriz de rutas; pruebas API/E2E. |
| **8. Dependencias previas** | ZM-FIN-015–022 y ZM-FIN-019. |
| **9. Cambios a implementar** | Generar casos 401/403/2xx por endpoint/capacidad/scope; IDOR; rutas directas; métodos alternos; exportación; jobs. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Matriz incompleta o fixtures que usan superadmin para todos los casos. |
| **13. Posibles regresiones** | Tiempo de CI y cambios de permisos legítimos. |
| **14. Pruebas requeridas** | Usuario anónimo, Backoffice sin permiso, scope una sucursal, global, recurso ajeno, rol revocado y endpoint nuevo. |
| **15. Criterios de aceptación** | La matriz completa pasa y CI falla si una ruta administrativa queda sin política o fuga datos. |
| **16. Definition of Done específica** | La matriz completa pasa y CI falla si una ruta administrativa queda sin política o fuga datos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Reporte endpoint→casos→resultado y consultas que demuestran cero mutación/fuga. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Security Ready y QA Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-095 — Construir la suite negativa de RBAC y scopes**.

**Objetivo**
Probar sistemáticamente que identidades no autorizadas no leen ni mutan datos.

**Problema y contexto de ZeroMerma**
Las pruebas existentes suelen cubrir POS-only→403, no Backoffice limitado ni cross-branch. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-QA-011; ZM-SEC-001/002.

**Dependencias que puedes asumir terminadas**
ZM-FIN-015–022 y ZM-FIN-019.

**Inspección inicial obligatoria**
Compara el registro OpenAPI con capacidades/scopes y cobertura existente.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Generar casos 401/403/2xx por endpoint/capacidad/scope; IDOR; rutas directas; métodos alternos; exportación; jobs.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No limitarse a ocultar botones ni probar sólo el camino feliz. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
ID válido ajeno, filtro malicioso, paginación, relación cross-branch, permiso retirado y export job.

**Concurrencia y consistencia**
Revocación de permiso/scope mientras se ejecuta una mutación sensible.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Usuario anónimo, Backoffice sin permiso, scope una sucursal, global, recurso ajeno, rol revocado y endpoint nuevo.

**Validación y comandos**
Pytest integración, E2E Backoffice y script de cobertura de políticas. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
La matriz completa pasa y CI falla si una ruta administrativa queda sin política o fuga datos.
Definition of Done específica: La matriz completa pasa y CI falla si una ruta administrativa queda sin política o fuga datos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Mantener matriz de autorización como evidencia generada.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-096 — Validar autenticación, sesión y hardening

**Épica:** Pruebas de seguridad
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: probar fórmula/validez/DQ, correlation/causation, lineage, rebuild, privacidad y futuros no bloqueantes.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-096 |
| **2. Nombre de la tarea** | Validar autenticación, sesión y hardening |
| **3. Objetivo** | Demostrar ciclo de sesión, revocación, protección de login y configuración segura en una topología equivalente a producción. |
| **4. Problema que resuelve** | Token expirado, revocación, headers/TLS/CSP y rate limiting no fueron verificados activamente. |
| **5. Hallazgo relacionado** | ZM-SEC-007–009; ZMA-SEC-003; casos bloqueados/no verificables. |
| **6. Módulos afectados** | Auth API, POS, Backoffice, proxy, config y secrets. |
| **7. Archivos/áreas a inspeccionar** | Tests auth; E2E; deployment headers; rate limit; session store. |
| **8. Dependencias previas** | ZM-FIN-023–027. |
| **9. Cambios a implementar** | Crear pruebas de expiración/refresh/replay/logout; login failures; CSRF/CSP/CORS; token URL/storage; config fail-closed y redacción. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Pruebas que filtran tokens o rate limit que afecta otros casos. |
| **13. Posibles regresiones** | Flakiness temporal y login de pruebas. |
| **14. Pruebas requeridas** | Reloj, pestañas múltiples, refresh concurrente, usuario bloqueado, origen malicioso, query token, secreto ausente y proxy spoof. |
| **15. Criterios de aceptación** | Sesión robada/revocada no funciona; query token no autentica; producción insegura no arranca; headers/políticas son verificables. |
| **16. Definition of Done específica** | Sesión robada/revocada no funciona; query token no autentica; producción insegura no arranca; headers/políticas son verificables. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Resultados E2E/HTTP, escaneo de logs/URLs y matriz de configuración. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Security Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-096 — Validar autenticación, sesión y hardening**.

**Objetivo**
Demostrar ciclo de sesión, revocación, protección de login y configuración segura en una topología equivalente a producción.

**Problema y contexto de ZeroMerma**
Token expirado, revocación, headers/TLS/CSP y rate limiting no fueron verificados activamente. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-007–009; ZMA-SEC-003; casos bloqueados/no verificables.

**Dependencias que puedes asumir terminadas**
ZM-FIN-023–027.

**Inspección inicial obligatoria**
Inspecciona todos los mecanismos de auth y configuración real de staging.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Crear pruebas de expiración/refresh/replay/logout; login failures; CSRF/CSP/CORS; token URL/storage; config fail-closed y redacción.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No registrar tokens/contraseñas ni probar contra producción. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Clock skew, revocación durante operación, cookie domain, CORS preflight y autocomplete terminal compartida.

**Concurrencia y consistencia**
Refresh/revocation concurrentes y login rate limit en paralelo.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Reloj, pestañas múltiples, refresh concurrente, usuario bloqueado, origen malicioso, query token, secreto ausente y proxy spoof.

**Validación y comandos**
Pytest auth, Playwright, curl/http tests de headers/CORS y escaneo de secretos. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Sesión robada/revocada no funciona; query token no autentica; producción insegura no arranca; headers/políticas son verificables.
Definition of Done específica: Sesión robada/revocada no funciona; query token no autentica; producción insegura no arranca; headers/políticas son verificables. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Informe de validación de sesión/hardening.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-097 — Construir la suite de idempotencia y concurrencia

**Épica:** Pruebas transaccionales
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: probar fórmula/validez/DQ, correlation/causation, lineage, rebuild, privacidad y futuros no bloqueantes.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-097 |
| **2. Nombre de la tarea** | Construir la suite de idempotencia y concurrencia |
| **3. Objetivo** | Probar todos los comandos críticos bajo replay, timeout y transacciones simultáneas. |
| **4. Problema que resuelve** | Las auditorías no localizaron pruebas de replay ni venta-cierre concurrente. |
| **5. Hallazgo relacionado** | ZM-QA-011; ZM-REL-005; ZM-DATA-003. |
| **6. Módulos afectados** | Sales, orders, payments, returns, cash, inventory, production, transfers y worker. |
| **7. Archivos/áreas a inspeccionar** | Harness PostgreSQL; barreras de transacción; fixtures; store idempotente. |
| **8. Dependencias previas** | ZM-FIN-028–040. |
| **9. Cambios a implementar** | Crear matriz por comando: replay secuencial/concurrente, respuesta perdida, payload distinto, deadlock y recuperación; ejecutar contra PostgreSQL real. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Pruebas no deterministas o que sólo reproducen concurrencia por casualidad. |
| **13. Posibles regresiones** | Tiempo/flakiness de CI. |
| **14. Pruebas requeridas** | Misma/diferente clave, crash post-commit, dos sesiones, lock timeout, deadlock y reintento. |
| **15. Criterios de aceptación** | Ningún comando crítico duplica o pierde efectos; carreras terminan en estados permitidos y respuestas recuperables. |
| **16. Definition of Done específica** | Ningún comando crítico duplica o pierde efectos; carreras terminan en estados permitidos y respuestas recuperables. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Conteos de tablas, estados finales, trazas de transacción y reporte por comando. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Data Integrity Ready y QA Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-097 — Construir la suite de idempotencia y concurrencia**.

**Objetivo**
Probar todos los comandos críticos bajo replay, timeout y transacciones simultáneas.

**Problema y contexto de ZeroMerma**
Las auditorías no localizaron pruebas de replay ni venta-cierre concurrente. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-QA-011; ZM-REL-005; ZM-DATA-003.

**Dependencias que puedes asumir terminadas**
ZM-FIN-028–040.

**Inspección inicial obligatoria**
Inventaría todos los comandos P0/P1 y sus locks/keys antes de diseñar casos.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Crear matriz por comando: replay secuencial/concurrente, respuesta perdida, payload distinto, deadlock y recuperación; ejecutar contra PostgreSQL real.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No usar SQLite ni mocks para validar locks. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Deadlock real, timeout, rollback, proceso reiniciado y dos workers.

**Concurrencia y consistencia**
Es el núcleo: usar barreras explícitas, no sleeps como sincronización principal.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Misma/diferente clave, crash post-commit, dos sesiones, lock timeout, deadlock y reintento.

**Validación y comandos**
Pytest integración PostgreSQL con dos conexiones/procesos; repetir escenarios determinísticamente. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Ningún comando crítico duplica o pierde efectos; carreras terminan en estados permitidos y respuestas recuperables.
Definition of Done específica: Ningún comando crítico duplica o pierde efectos; carreras terminan en estados permitidos y respuestas recuperables. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Matriz de invariantes concurrentes y cómo depurar fallos.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-098 — Construir la suite de reconciliación financiera

**Épica:** Pruebas de datos
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: probar fórmula/validez/DQ, correlation/causation, lineage, rebuild, privacidad y futuros no bloqueantes.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-098 |
| **2. Nombre de la tarea** | Construir la suite de reconciliación financiera |
| **3. Objetivo** | Validar que ventas, pedidos, pagos, refunds, movimientos y cierres satisfacen las ecuaciones aprobadas. |
| **4. Problema que resuelve** | El corte activo mostró una diferencia artificial y mixed payment incorrecto. |
| **5. Hallazgo relacionado** | ZMA-FIN-001; ZMA-REP-001. |
| **6. Módulos afectados** | Financial ledger, cash close, reports y E2E. |
| **7. Archivos/áreas a inspeccionar** | Fixtures financieras; queries de reconciliación; reportes; backfill. |
| **8. Dependencias previas** | ZM-FIN-041–047. |
| **9. Cambios a implementar** | Crear casos canónicos por medio/flujo; verificar clean start, opening economic state, mapping de IDs, totales brutos/netos, esperado/contado/variación, replay/backfill idempotente, rechazo de datos ambiguos y futura fuente real representativa. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Fixtures demasiado simples o aceptar tolerancias no justificadas. |
| **13. Posibles regresiones** | Cambio de definición métrica. |
| **14. Pruebas requeridas** | Cash/card/mixed, order, refund, operativo, descuento, cierre y datos legacy. |
| **15. Criterios de aceptación** | Seeds/demo no contaminan producción; opening state reconcilia y es reproducible; cada ecuación produce cero diferencia no explicada; datos ambiguos se rechazan para reconciliación manual y reportes/export coinciden con DB canónica. |
| **16. Definition of Done específica** | Cada ecuación produce cero diferencia no explicada; reportes/export coinciden con DB canónica. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Resultados de reconciliación y dataset de prueba versionado. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Data Integrity Ready y QA Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-098 — Construir la suite de reconciliación financiera**.

**Objetivo**
Validar que ventas, pedidos, pagos, refunds, movimientos y cierres satisfacen las ecuaciones aprobadas.

**Problema y contexto de ZeroMerma**
El corte activo mostró una diferencia artificial y mixed payment incorrecto. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-FIN-001; ZMA-REP-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-041–047.

**Inspección inicial obligatoria**
Inspecciona diccionario financiero y cada query de cierre/reporte.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Crear casos canónicos por medio/flujo; verificar totales brutos/netos, esperado/contado/variación, replay y backfill.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No cuadrar con ajustes artificiales. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Redondeo, refund parcial, método pendiente, timezone y backfill.

**Concurrencia y consistencia**
Incluir cierre contra movimientos concurrentes y snapshot consistente.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Cash/card/mixed, order, refund, operativo, descuento, cierre y datos legacy.

**Validación y comandos**
Pytest integración, E2E y scripts de reconciliación. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada ecuación produce cero diferencia no explicada; reportes/export coinciden con DB canónica.
Definition of Done específica: Cada ecuación produce cero diferencia no explicada; reportes/export coinciden con DB canónica. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Catálogo de ecuaciones y casos de aceptación.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-099 — Construir la suite de inventario, migraciones y backfills

**Épica:** Pruebas de datos
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: probar fórmula/validez/DQ, correlation/causation, lineage, rebuild, privacidad y futuros no bloqueantes.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-099 |
| **2. Nombre de la tarea** | Construir la suite de inventario, migraciones y backfills |
| **3. Objetivo** | Demostrar que todo movimiento físico y las migraciones/rebuild preservan saldos, costo y trazabilidad. |
| **4. Problema que resuelve** | El POS no movía inventario y los backfills/migraciones no fueron probados. |
| **5. Hallazgo relacionado** | ZMA-DATA-001; ZM-DATA-004; ZM-OPS-014. |
| **6. Módulos afectados** | Inventory ledger, all physical domains, Alembic y backfill tools. |
| **7. Archivos/áreas a inspeccionar** | Fixtures multi-product/UOM/branch; migrations; rebuild/reconcile scripts. |
| **8. Dependencias previas** | ZM-FIN-048–055 y ZM-FIN-006. |
| **9. Cambios a implementar** | Crear casos por flujo; demostrar que seed/demo no contamina producción; conteo físico/opening state; mapping de IDs; suma movimientos=balance; stock policy; rebuild; fresh/upgrade; backfill interrupted/replayed; rechazo de datos ambiguos; restore comparison. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Datos sintéticos no representan legacy o tests no cubren unidades/costo. |
| **13. Posibles regresiones** | Duración CI y constraints de migración. |
| **14. Pruebas requeridas** | Venta, class capture, return/waste, transfer, purchase, production, negative stock, UOM y legacy. |
| **15. Criterios de aceptación** | Todo saldo/costo se reconstruye desde causalidad fiable o opening adjustment explícito; migraciones y backfills son idempotentes/reanudables; demo/test no aporta opening balance; no hay huérfanos, duplicados ni movimientos ficticios. |
| **16. Definition of Done específica** | Todo saldo/costo se reconstruye; migraciones y backfills son idempotentes/reanudables; no hay huérfanos o duplicados. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Reconciliaciones, logs Alembic y resultados antes/después. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Data Integrity Ready y QA Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-099 — Construir la suite de inventario, migraciones y backfills**.

**Objetivo**
Demostrar que todo movimiento físico y las migraciones/rebuild preservan saldos, costo y trazabilidad.

**Problema y contexto de ZeroMerma**
El POS no movía inventario y los backfills/migraciones no fueron probados. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-DATA-001; ZM-DATA-004; ZM-OPS-014.

**Dependencias que puedes asumir terminadas**
ZM-FIN-048–055 y ZM-FIN-006.

**Inspección inicial obligatoria**
Inspecciona catálogo de movimientos, scripts y versiones soportadas.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Crear casos por flujo; suma movimientos=balance; stock policy; rebuild; fresh/upgrade; backfill interrupted/replayed; restore comparison.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No ejecutar backfill sobre producción. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Datos nulos/duplicados, UOM incompatible, interrupción y stock negativo.

**Concurrencia y consistencia**
Incluye primera fila de balance y backfill/escritura según política.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Venta, class capture, return/waste, transfer, purchase, production, negative stock, UOM y legacy.

**Validación y comandos**
Pytest PostgreSQL, Alembic fresh/upgrade y dry-run/rebuild. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Todo saldo/costo se reconstruye; migraciones y backfills son idempotentes/reanudables; no hay huérfanos o duplicados.
Definition of Done específica: Todo saldo/costo se reconstruye; migraciones y backfills son idempotentes/reanudables; no hay huérfanos o duplicados. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Matriz de datos y procedimientos de prueba.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-100 — Automatizar el recorrido operativo real del POS

**Épica:** E2E
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: probar fórmula/validez/DQ, correlation/causation, lineage, rebuild, privacidad y futuros no bloqueantes.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-100 |
| **2. Nombre de la tarea** | Automatizar el recorrido operativo real del POS |
| **3. Objetivo** | Probar un día operativo contra API y PostgreSQL reales sin mocks globales. |
| **4. Problema que resuelve** | El E2E POS interceptaba `v1`; la auditoría activa probó manualmente sólo parte de casos críticos. |
| **5. Hallazgo relacionado** | ZM-QA-011; matriz POS activa. |
| **6. Módulos afectados** | POS, API, DB, worker opcional, printer/terminal fakes. |
| **7. Archivos/áreas a inspeccionar** | Playwright POS; seeds; service orchestration; evidence hooks. |
| **8. Dependencias previas** | ZM-FIN-056–067 y suites 094–099. |
| **9. Cambios a implementar** | Automatizar login, apertura, venta cash/card/mixed, pedido, ticket, devolución, transferencia, operativo, cierre, logout y escenarios negativos aprobados. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Suite lenta/flaky o transacciones de prueba no aisladas. |
| **13. Posibles regresiones** | Dependencia de timing y hardware. |
| **14. Pruebas requeridas** | Refresh, double submit, 401/403/409, conexión perdida, sesión cerrada, hardware failure y multi-branch. |
| **15. Criterios de aceptación** | El recorrido completo pasa en artefacto real; DB/ledger/audit/outbox se verifican por IDs y no quedan datos simulados. |
| **16. Definition of Done específica** | El recorrido completo pasa en artefacto real; DB/ledger/audit/outbox se verifican por IDs y no quedan datos simulados. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Videos/traces/screenshots sin secretos, IDs y queries de verificación. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate QA Ready y Staging Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-100 — Automatizar el recorrido operativo real del POS**.

**Objetivo**
Probar un día operativo contra API y PostgreSQL reales sin mocks globales.

**Problema y contexto de ZeroMerma**
El E2E POS interceptaba `v1`; la auditoría activa probó manualmente sólo parte de casos críticos. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-QA-011; matriz POS activa.

**Dependencias que puedes asumir terminadas**
ZM-FIN-056–067 y suites 094–099.

**Inspección inicial obligatoria**
Reutiliza harness ZM-FIN-012 y elimina intercepts sólo en esta suite real.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Automatizar login, apertura, venta cash/card/mixed, pedido, ticket, devolución, transferencia, operativo, cierre, logout y escenarios negativos aprobados.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No sustituir validación de DB por sólo observar la pantalla. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Todos los fallos críticos y estados de red/hardware definidos.

**Concurrencia y consistencia**
Incluye escenarios coordinados de doble submit/cierre mediante helpers backend.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Refresh, double submit, 401/403/409, conexión perdida, sesión cerrada, hardware failure y multi-branch.

**Validación y comandos**
Playwright real, backend integration y publicación de artefactos. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
El recorrido completo pasa en artefacto real; DB/ledger/audit/outbox se verifican por IDs y no quedan datos simulados.
Definition of Done específica: El recorrido completo pasa en artefacto real; DB/ledger/audit/outbox se verifican por IDs y no quedan datos simulados. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Mapa caso E2E→requisito→evidencia.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-101 — Automatizar el recorrido administrativo real del Backoffice

**Épica:** E2E
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: probar fórmula/validez/DQ, correlation/causation, lineage, rebuild, privacidad y futuros no bloqueantes.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-101 |
| **2. Nombre de la tarea** | Automatizar el recorrido administrativo real del Backoffice |
| **3. Objetivo** | Probar configuración, catálogos y operaciones administrativas con roles/scopes reales. |
| **4. Problema que resuelve** | El E2E Backoffice cubría principalmente shell y la auditoría activa encontró placeholders/bugs de primer registro. |
| **5. Hallazgo relacionado** | ZM-QA-011; ZMA-BO-001; ZMA-BO-002. |
| **6. Módulos afectados** | Backoffice, API, DB, RBAC/scopes y worker. |
| **7. Archivos/áreas a inspeccionar** | Playwright Backoffice; fixtures multi-role/branch; pages/modules. |
| **8. Dependencias previas** | ZM-FIN-068–086 y suites 094–099. |
| **9. Cambios a implementar** | Automatizar first-record, CRUD seguro, permisos, scope, catálogo→POS, purchase→inventory, production, reports, audit y settings. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Usar sólo superadmin o depender de datos preexistentes. |
| **13. Posibles regresiones** | Tiempo/flakiness y rutas condicionales. |
| **14. Pruebas requeridas** | Estado vacío, 403, IDOR, recarga, filtros, export, módulo sin datos y error API. |
| **15. Criterios de aceptación** | Cada módulo productivo tiene al menos un camino feliz y uno negativo real; placeholders no existen en release. |
| **16. Definition of Done específica** | Cada módulo productivo tiene al menos un camino feliz y uno negativo real; placeholders no existen en release. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Traces/screenshots, IDs y verificación DB/API. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate QA Ready y Staging Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-101 — Automatizar el recorrido administrativo real del Backoffice**.

**Objetivo**
Probar configuración, catálogos y operaciones administrativas con roles/scopes reales.

**Problema y contexto de ZeroMerma**
El E2E Backoffice cubría principalmente shell y la auditoría activa encontró placeholders/bugs de primer registro. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-QA-011; ZMA-BO-001; ZMA-BO-002.

**Dependencias que puedes asumir terminadas**
ZM-FIN-068–086 y suites 094–099.

**Inspección inicial obligatoria**
Reutiliza harness ZM-FIN-013 y matriz de capacidades ZM-FIN-008.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Automatizar first-record, CRUD seguro, permisos, scope, catálogo→POS, purchase→inventory, production, reports, audit y settings.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No usar datos mock para declarar módulo completo. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Colecciones vacías, múltiples sucursales, permisos retirados, error de red y acceso directo.

**Concurrencia y consistencia**
Incluye edición concurrente donde existe version/conflict policy.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Estado vacío, 403, IDOR, recarga, filtros, export, módulo sin datos y error API.

**Validación y comandos**
Playwright real y verificaciones API/DB, con artefactos de CI. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada módulo productivo tiene al menos un camino feliz y uno negativo real; placeholders no existen en release.
Definition of Done específica: Cada módulo productivo tiene al menos un camino feliz y uno negativo real; placeholders no existen en release. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Mapa de cobertura funcional Backoffice.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-102 — Validar rendimiento, carga, seguridad, hardware y accesibilidad

**Épica:** Validación no funcional
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: probar fórmula/validez/DQ, correlation/causation, lineage, rebuild, privacidad y futuros no bloqueantes.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-102 |
| **2. Nombre de la tarea** | Validar rendimiento, carga, seguridad, hardware y accesibilidad |
| **3. Objetivo** | Demostrar que el sistema soporta escenarios aprobados sin romper invariantes ni operación física. |
| **4. Problema que resuelve** | Carga, rendimiento, hardware, viewports y accesibilidad no fueron verificados; seguridad requiere evaluación integral. |
| **5. Hallazgo relacionado** | Elementos no verificables de ambas auditorías; ZM-OPS-014; ZM-MAINT-016. |
| **6. Módulos afectados** | API, DB, worker, frontends, hardware, infrastructure y security. |
| **7. Archivos/áreas a inspeccionar** | Endpoints críticos; queries; worker; UI; adapters; deployment staging. |
| **8. Dependencias previas** | ZM-FIN-094–101 y escenarios/capacidad aprobados. |
| **9. Cambios a implementar** | Definir escenarios representativos; load/soak; planes SQL; límites; DAST; UX/touch/a11y; printer/drawer/terminal; degradación y recovery. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Pruebas irreales, afectar otros entornos o optimizar prematuramente. |
| **13. Posibles regresiones** | Cambios de índices/configuración degradan otros flujos. |
| **14. Pruebas requeridas** | Picos, backlog, lock contention, DB restart, red lenta, viewport, keyboard/touch, peripheral failure y datos grandes. |
| **15. Criterios de aceptación** | SLO/capacidad aprobados se cumplen; no hay errores de integridad; vulnerabilidades críticas/altas abiertas ni hardware no soportado presentado como compatible. |
| **16. Definition of Done específica** | SLO/capacidad aprobados se cumplen; no hay errores de integridad; vulnerabilidades críticas/altas abiertas ni hardware no soportado presentado como compatible. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Reportes de carga, seguridad, a11y y hardware con configuración reproducible. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Security Ready, QA Ready y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-102 — Validar rendimiento, carga, seguridad, hardware y accesibilidad**.

**Objetivo**
Demostrar que el sistema soporta escenarios aprobados sin romper invariantes ni operación física.

**Problema y contexto de ZeroMerma**
Carga, rendimiento, hardware, viewports y accesibilidad no fueron verificados; seguridad requiere evaluación integral. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Elementos no verificables de ambas auditorías; ZM-OPS-014; ZM-MAINT-016.

**Dependencias que puedes asumir terminadas**
ZM-FIN-094–101 y escenarios/capacidad aprobados.

**Inspección inicial obligatoria**
Perfila primero; define carga desde volumen/operación aprobados, no cifras arbitrarias.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir escenarios representativos; load/soak; planes SQL; límites; DAST; UX/touch/a11y; printer/drawer/terminal; degradación y recovery.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No ejecutar carga/DAST contra producción ni fijar umbrales sin decisión de negocio. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Contención, backlog, consultas de export, red intermitente y hardware heterogéneo.

**Concurrencia y consistencia**
Carga concurrente debe incluir venta/cierre, inventory y workers sin perder invariantes.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Picos, backlog, lock contention, DB restart, red lenta, viewport, keyboard/touch, peripheral failure y datos grandes.

**Validación y comandos**
Herramientas de carga/DAST/a11y aprobadas en staging aislado; EXPLAIN ANALYZE seguro; pruebas hardware. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
SLO/capacidad aprobados se cumplen; no hay errores de integridad; vulnerabilidades críticas/altas abiertas ni hardware no soportado presentado como compatible.
Definition of Done específica: SLO/capacidad aprobados se cumplen; no hay errores de integridad; vulnerabilidades críticas/altas abiertas ni hardware no soportado presentado como compatible. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Informe no funcional y matriz de compatibilidad.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-103 — Completar threat model, SAST, dependencias y SBOM

**Épica:** Seguridad de producto
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: probar fórmula/validez/DQ, correlation/causation, lineage, rebuild, privacidad y futuros no bloqueantes.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-103 |
| **2. Nombre de la tarea** | Completar threat model, SAST, dependencias y SBOM |
| **3. Objetivo** | Identificar y cerrar riesgos de diseño/cadena de suministro antes de release. |
| **4. Problema que resuelve** | Las auditorías detectaron fallos concretos, pero no existe evidencia de threat model, escaneo de dependencias/secrets o SBOM. |
| **5. Hallazgo relacionado** | ZM-SEC-001–009; ZM-OPS-014. |
| **6. Módulos afectados** | API, worker, POS, Backoffice, DB, CI/CD, providers y hardware bridges. |
| **7. Archivos/áreas a inspeccionar** | Código, manifests, lockfiles, workflows, images y architecture diagrams. |
| **8. Dependencias previas** | ZM-FIN-015–027, ZM-FIN-087–093 y ZM-FIN-102. |
| **9. Cambios a implementar** | Modelar activos/actores/fronteras/amenazas; ejecutar SAST/dependency/license/secret scan; producir SBOM; triage y excepciones con dueño. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Falsos positivos ignorados o excepciones permanentes sin dueño. |
| **13. Posibles regresiones** | Bloqueos CI por feeds o cambios de dependencia. |
| **14. Pruebas requeridas** | XSS, IDOR, CSRF, replay, supply chain, secret leak, malicious provider callback, local bridge y DB access. |
| **15. Criterios de aceptación** | No hay hallazgos críticos/altos abiertos sin mitigación/aceptación explícita; SBOM corresponde al artefacto de release. |
| **16. Definition of Done específica** | No hay hallazgos críticos/altos abiertos sin mitigación/aceptación explícita; SBOM corresponde al artefacto de release. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Threat model, reportes de scan, SBOM y registro de decisiones. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Security Ready y Production Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-103 — Completar threat model, SAST, dependencias y SBOM**.

**Objetivo**
Identificar y cerrar riesgos de diseño/cadena de suministro antes de release.

**Problema y contexto de ZeroMerma**
Las auditorías detectaron fallos concretos, pero no existe evidencia de threat model, escaneo de dependencias/secrets o SBOM. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-001–009; ZM-OPS-014.

**Dependencias que puedes asumir terminadas**
ZM-FIN-015–027, ZM-FIN-087–093 y ZM-FIN-102.

**Inspección inicial obligatoria**
Inspecciona arquitectura real y dependencias transitivas antes de modelar.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Modelar activos/actores/fronteras/amenazas; ejecutar SAST/dependency/license/secret scan; producir SBOM; triage y excepciones con dueño.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No afirmar cumplimiento normativo sólo por pasar un escáner. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Paquetes dev vs prod, imagen base, binary drivers, provider SDK y secretos históricos.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
XSS, IDOR, CSRF, replay, supply chain, secret leak, malicious provider callback, local bridge y DB access.

**Validación y comandos**
Ejecuta herramientas aprobadas en CI y verifica SBOM contra artefactos. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
No hay hallazgos críticos/altos abiertos sin mitigación/aceptación explícita; SBOM corresponde al artefacto de release.
Definition of Done específica: No hay hallazgos críticos/altos abiertos sin mitigación/aceptación explícita; SBOM corresponde al artefacto de release. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Threat model y política de vulnerabilidades/excepciones.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-104 — Completar ADRs, API y documentación de arquitectura

**Épica:** Documentación técnica
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: probar fórmula/validez/DQ, correlation/causation, lineage, rebuild, privacidad y futuros no bloqueantes.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-104 |
| **2. Nombre de la tarea** | Completar ADRs, API y documentación de arquitectura |
| **3. Objetivo** | Asegurar que código, decisiones y operación técnica puedan mantenerse sin conocimiento tácito. |
| **4. Problema que resuelve** | La documentación es valiosa pero parcialmente desfasada; faltan decisiones formales de sesión, ledgers, locking y despliegue. |
| **5. Hallazgo relacionado** | ZM-MAINT-016; ZM-REL-018; ZM-OPS-014. |
| **6. Módulos afectados** | Repositorio completo y docs. |
| **7. Archivos/áreas a inspeccionar** | README; docs existentes; AGENTS; OpenAPI; scripts; diagramas y ADRs. |
| **8. Dependencias previas** | ZM-FIN-001–103. |
| **9. Cambios a implementar** | Actualizar arquitectura, módulos, contratos, decisiones, migraciones, pruebas, local setup, events y troubleshooting; validar links/comandos. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Crear documentación duplicada o no vinculada a code owners. |
| **13. Posibles regresiones** | Ninguna funcional; deriva futura. |
| **14. Pruebas requeridas** | Checkout nuevo, desarrollador sin contexto, comandos por SO, docs desfasadas y cambio contractual. |
| **15. Criterios de aceptación** | Un integrante puede instalar, entender, probar y rastrear un flujo con documentación vigente; los comandos documentados pasan. |
| **16. Definition of Done específica** | Un integrante puede instalar, entender, probar y rastrear un flujo con documentación vigente; los comandos documentados pasan. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Build de docs/link check y walkthrough reproducido. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Development Complete y Production Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-104 — Completar ADRs, API y documentación de arquitectura**.

**Objetivo**
Asegurar que código, decisiones y operación técnica puedan mantenerse sin conocimiento tácito.

**Problema y contexto de ZeroMerma**
La documentación es valiosa pero parcialmente desfasada; faltan decisiones formales de sesión, ledgers, locking y despliegue. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-MAINT-016; ZM-REL-018; ZM-OPS-014.

**Dependencias que puedes asumir terminadas**
ZM-FIN-001–103.

**Inspección inicial obligatoria**
Revisa documentos existentes y conserva un único plan/decisiones; elimina o marca contenido obsoleto con trazabilidad.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Actualizar arquitectura, módulos, contratos, decisiones, migraciones, pruebas, local setup, events y troubleshooting; validar links/comandos.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No crear documentos de control redundantes ni copiar el código sin explicar decisiones. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Windows/Linux, entorno sin secretos, versión soportada y docs generadas.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Checkout nuevo, desarrollador sin contexto, comandos por SO, docs desfasadas y cambio contractual.

**Validación y comandos**
Ejecuta todos los comandos documentados en entorno limpio y link checks. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Un integrante puede instalar, entender, probar y rastrear un flujo con documentación vigente; los comandos documentados pasan.
Definition of Done específica: Un integrante puede instalar, entender, probar y rastrear un flujo con documentación vigente; los comandos documentados pasan. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Es la esencia de la tarea.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-105 — Completar manuales operativos, privacidad, fiscalidad y capacitación

**Épica:** Documentación operativa
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-18: probar fórmula/validez/DQ, correlation/causation, lineage, rebuild, privacidad y futuros no bloqueantes.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-105 |
| **2. Nombre de la tarea** | Completar manuales operativos, privacidad, fiscalidad y capacitación |
| **3. Objetivo** | Preparar a panaderías y soporte para operar, recuperar y auditar el producto correctamente. |
| **4. Problema que resuelve** | Hardware, instalación, backup, privacidad, fiscalidad y capacitación no estaban verificados; los flujos necesitan SOP. |
| **5. Hallazgo relacionado** | ZM-OPS-014; elementos no verificables; ZM-FIN-007. |
| **6. Módulos afectados** | POS, Backoffice, support, security, operations y business governance. |
| **7. Archivos/áreas a inspeccionar** | Docs operativas; runbooks; manuales por rol; matriz regulatoria; materiales de entrenamiento. |
| **8. Dependencias previas** | ZM-FIN-007, ZM-FIN-056–103 y decisiones aprobadas. |
| **9. Cambios a implementar** | Crear manuales por rol para apertura/cierre, venta/pedido/inventario/producción, STOP-B, pause/resume dual, contingencia stop-only y futura validación manual, privacidad/fiscalidad, BBVA, hardware, cutover, rollout, hotfix, reconciliación, soporte y escalación DEC-20. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Documentar un flujo distinto al sistema o convertir decisiones no aprobadas en política. |
| **13. Posibles regresiones** | Ninguna funcional; riesgo de operación incorrecta. |
| **14. Pruebas requeridas** | Usuario nuevo, terminal compartida, periférico caído, cierre con diferencia, restore, usuario dado de baja y solicitud de datos. |
| **15. Criterios de aceptación** | Cada proceso productivo y de piloto tiene SOP, autoridad, precondiciones, controles, evidencia y criterio de salida; capacitación usa checklist observado/firmado; soporte cubre cutover/horario operativo/incidentes; requisitos externos y stop-only inicial están cubiertos. |
| **16. Definition of Done específica** | Cada proceso productivo tiene SOP, responsable, precondiciones, controles, evidencia y contingencia; requisitos externos aprobados están cubiertos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Walkthrough/UAT de manuales, firmas de responsables y materiales versionados. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Production Ready y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-105 — Completar manuales operativos, privacidad, fiscalidad y capacitación**.

**Objetivo**
Preparar a panaderías y soporte para operar, recuperar y auditar el producto correctamente.

**Problema y contexto de ZeroMerma**
Hardware, instalación, backup, privacidad, fiscalidad y capacitación no estaban verificados; los flujos necesitan SOP. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-OPS-014; elementos no verificables; ZM-FIN-007.

**Dependencias que puedes asumir terminadas**
ZM-FIN-007, ZM-FIN-056–103 y decisiones aprobadas.

**Inspección inicial obligatoria**
Inspecciona flujos reales y requisitos aprobados; valida con usuarios de operación.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Crear manuales por rol; apertura/cierre; venta/pedido/inventario/producción; incidentes; privacidad; retención; ticket; hardware; soporte y escalación.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No incluir secretos/credenciales reales ni afirmaciones legales no aprobadas. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Turno de reemplazo, sucursal offline, incidente de seguridad, diferencia de caja y devolución compleja.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Usuario nuevo, terminal compartida, periférico caído, cierre con diferencia, restore, usuario dado de baja y solicitud de datos.

**Validación y comandos**
Ejecuta walkthroughs y simulacros en staging; valida enlaces/formatos. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada proceso productivo tiene SOP, responsable, precondiciones, controles, evidencia y contingencia; requisitos externos aprobados están cubiertos.
Definition of Done específica: Cada proceso productivo tiene SOP, responsable, precondiciones, controles, evidencia y contingencia; requisitos externos aprobados están cubiertos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Es la esencia de la tarea.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```


## Fase 9 — Plataforma de producción, despliegue y recuperación — Tareas ejecutables

### ZM-FIN-106 — Construir artefactos inmutables y manifiesto de release

**Épica:** Artefactos
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST, standby controlado, observabilidad amplia, alerting conservador, backup/restore y cloud complementario.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-106 |
| **2. Nombre de la tarea** | Construir artefactos inmutables y manifiesto de release |
| **3. Objetivo** | Empaquetar API, worker, POS y Backoffice desde el mismo commit/contrato con identidad verificable. |
| **4. Problema que resuelve** | El repositorio sólo demuestra desarrollo local y no hay imágenes/manifests productivos. |
| **5. Hallazgo relacionado** | ZM-OPS-014; ZM-REL-015. |
| **6. Módulos afectados** | API, worker, frontends, containers, SBOM y release metadata. |
| **7. Archivos/áreas a inspeccionar** | Dockerfiles/build configs; workspace; static hosting; version endpoints; CI artifacts. |
| **8. Dependencias previas** | ZM-FIN-014, ZM-FIN-103–104. |
| **9. Cambios a implementar** | Crear builds reproducibles/multi-stage; usuario no root; health hooks; version metadata; hashes/SBOM; un manifiesto commit→schema→OpenAPI→artefactos. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Imágenes mutables, secretos horneados, dependencias dev o versiones desalineadas. |
| **13. Posibles regresiones** | Diferencias de runtime frente a desarrollo y rutas de assets. |
| **14. Pruebas requeridas** | Build limpio, cache/no-cache, imagen mínima, usuario no root, assets, versión y vulnerabilidad de base. |
| **15. Criterios de aceptación** | Los cuatro componentes se reconstruyen con hashes esperados; no contienen secretos; reportan la misma versión y contrato. |
| **16. Definition of Done específica** | Los cuatro componentes se reconstruyen con hashes esperados; no contienen secretos; reportan la misma versión y contrato. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Digests, SBOM, manifiesto y smoke local. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-107–111 y Gate Staging Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-106 — Construir artefactos inmutables y manifiesto de release**.

**Objetivo**
Empaquetar API, worker, POS y Backoffice desde el mismo commit/contrato con identidad verificable.

**Problema y contexto de ZeroMerma**
El repositorio sólo demuestra desarrollo local y no hay imágenes/manifests productivos. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-OPS-014; ZM-REL-015.

**Dependencias que puedes asumir terminadas**
ZM-FIN-014, ZM-FIN-103–104.

**Inspección inicial obligatoria**
Inspecciona builds actuales, dependencias runtime, archivos estáticos y variables de configuración.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Crear builds reproducibles/multi-stage; usuario no root; health hooks; version metadata; hashes/SBOM; un manifiesto commit→schema→OpenAPI→artefactos.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No compilar configuración/secrets de entorno dentro de los artefactos. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Build sin red, cache contaminada, arquitectura CPU, timestamp reproducible y assets con base path.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Build limpio, cache/no-cache, imagen mínima, usuario no root, assets, versión y vulnerabilidad de base.

**Validación y comandos**
Build de todos los artefactos desde checkout limpio, escaneo y smoke en contenedores. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Los cuatro componentes se reconstruyen con hashes esperados; no contienen secretos; reportan la misma versión y contrato.
Definition of Done específica: Los cuatro componentes se reconstruyen con hashes esperados; no contienen secretos; reportan la misma versión y contrato. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Documentar manifiesto y procedimiento de build/reproducción.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-107 — Definir infraestructura como código, red, TLS y hosting

**Épica:** Infraestructura
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Infra reproducible LOCAL_FIRST: mini-PC primario, LAN/ingress local y segundo mini-PC standby controlado; cloud/off-site complementario, no autoridad del piloto.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-107 |
| **2. Nombre de la tarea** | Definir infraestructura como código, red, TLS y hosting |
| **3. Objetivo** | Crear la topología productiva LOCAL_FIRST reproducible y aislada para mini-PC primario, standby controlado, API, worker, frontends y PostgreSQL local autoritativo, con cloud/off-site complementario. |
| **4. Problema que resuelve** | Docker Compose sólo levanta PostgreSQL local; TLS/proxy/WAF externos no fueron verificables. |
| **5. Hallazgo relacionado** | ZM-OPS-014; elementos no verificables de infraestructura. |
| **6. Módulos afectados** | Network, compute, DB, object/static hosting, DNS, TLS, firewall y environments. |
| **7. Archivos/áreas a inspeccionar** | `infra`; manifests/terraform u opción aprobada; proxy; DNS; certificados; security groups. |
| **8. Dependencias previas** | ZM-FIN-002, ZM-FIN-026–027, ZM-FIN-106 y DEC-17 LOCAL_FIRST. |
| **9. Cambios a implementar** | Codificar staging/production local; primario y segundo mini-PC; segmentar LAN; ingress local y TLS/confianza controlada; egress tolerante a Internet para backup/Telegram; worker sin entrada pública; impedir promoción ciega/split-brain. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Infraestructura sobrepermisiva, drift manual o proveedor no aprobado. |
| **13. Posibles regresiones** | Conectividad, CORS/cookies y URLs frontend. |
| **14. Pruebas requeridas** | Fresh provision, cambio de configuración, certificado, acceso DB, pérdida de nodo, origen CORS y rollback de IaC. |
| **15. Criterios de aceptación** | Primario y standby nacen reproduciblemente; DB no es pública; LAN/TLS/orígenes/puertos coinciden con política; drift se detecta; cloud no es autoridad ni requisito primario del piloto. |
| **16. Definition of Done específica** | Un entorno vacío se aprovisiona reproduciblemente; DB no es pública; TLS/orígenes/puertos coinciden con política; drift se detecta. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Plan/apply de staging, diagrama y pruebas de red/TLS. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-108–116 y Gate Staging Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-107 — Definir infraestructura como código, red, TLS y hosting**.

**Objetivo**
Crear la topología productiva LOCAL_FIRST reproducible y aislada para mini-PC primario, standby controlado, API, worker, frontends y PostgreSQL local autoritativo, con cloud/off-site complementario.

**Problema y contexto de ZeroMerma**
Docker Compose sólo levanta PostgreSQL local; TLS/proxy/WAF externos no fueron verificables. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-OPS-014; elementos no verificables de infraestructura.

**Dependencias que puedes asumir terminadas**
ZM-FIN-002, ZM-FIN-026–027, ZM-FIN-106 y DEC-17 LOCAL_FIRST.

**Inspección inicial obligatoria**
Inspecciona infra existente fuera del repo si se proporciona evidencia; no asumas inexistencia.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Codificar staging/production local; primario y segundo mini-PC; segmentar LAN; ingress local y TLS/confianza controlada; egress tolerante a Internet para backup/Telegram; worker sin entrada pública; impedir promoción ciega/split-brain.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No usar túneles temporales como arquitectura productiva ni aplicar a producción en esta tarea. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
DNS cutover, renovación de certificado, ambiente destruido/recreado, egress de providers y acceso de soporte.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Fresh provision, cambio de configuración, certificado, acceso DB, pérdida de nodo, origen CORS y rollback de IaC.

**Validación y comandos**
Validate/plan/apply en cuenta de staging; tests de red/TLS y drift detection. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Un entorno vacío se aprovisiona reproduciblemente; DB no es pública; TLS/orígenes/puertos coinciden con política; drift se detecta.
Definition of Done específica: Un entorno vacío se aprovisiona reproduciblemente; DB no es pública; TLS/orígenes/puertos coinciden con política; drift se detecta. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
ADR/topología, inventario de recursos y procedimiento de acceso.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-108 — Configurar PostgreSQL, pooling y orquestación de migraciones

**Épica:** Base de datos productiva
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** PostgreSQL local autoritativo; replicación sostiene RPO local cero/casi cero sin promoción ciega/split-brain; audit/outbox atómico.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-108 |
| **2. Nombre de la tarea** | Configurar PostgreSQL, pooling y orquestación de migraciones |
| **3. Objetivo** | Operar la base con conexiones, locks, timeouts, migraciones y mantenimiento adecuados al producto. |
| **4. Problema que resuelve** | Sólo se verificó PostgreSQL local; no hay estrategia productiva de pooling/migración/compatibilidad demostrada. |
| **5. Hallazgo relacionado** | ZM-OPS-014; ZM-DATA-003/004; ZM-REL-015. |
| **6. Módulos afectados** | PostgreSQL, API, worker, Alembic y infrastructure. |
| **7. Archivos/áreas a inspeccionar** | Engine/session settings; pool; DB roles; Alembic job; indexes; maintenance/monitoring. |
| **8. Dependencias previas** | ZM-FIN-006, ZM-FIN-038, ZM-FIN-055, ZM-FIN-106–107. |
| **9. Cambios a implementar** | Definir PostgreSQL local autoritativo; roles mínimos; pool/timeouts; SSL; migration job y carga/opening state únicos e idempotentes; guardas por entorno e identidad de dataset; expand-contract; durabilidad/replicación al standby; fencing/promoción controlada; maintenance, schema drift y reconciliación posterior. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Migración bloqueante, pool storm o privilegios excesivos. |
| **13. Posibles regresiones** | Latencia y comportamiento de tests/local. |
| **14. Pruebas requeridas** | Deploy con versiones mixtas, migración larga/fallida, pool agotado, deadlock, worker+API y read-only maintenance. |
| **15. Criterios de aceptación** | Migración/opening load corre una vez antes de tráfico incompatible, registra dataset y schema revision, aborta contra target no autorizado y reconcilia; API/worker manejan conexiones; replicación/fencing evita split-brain y demuestra RPO local cero/casi cero; métricas existen. |
| **16. Definition of Done específica** | Migración corre una vez antes de tráfico incompatible; API/worker manejan conexiones; roles no pueden saltarse inmutabilidad; métricas existen. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Staging upgrade, planes de consulta, métricas de pool/locks y permisos DB. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-109–116 y Gate Production Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-108 — Configurar PostgreSQL, pooling y orquestación de migraciones**.

**Objetivo**
Operar la base con conexiones, locks, timeouts, migraciones y mantenimiento adecuados al producto.

**Problema y contexto de ZeroMerma**
Sólo se verificó PostgreSQL local; no hay estrategia productiva de pooling/migración/compatibilidad demostrada. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-OPS-014; ZM-DATA-003/004; ZM-REL-015.

**Dependencias que puedes asumir terminadas**
ZM-FIN-006, ZM-FIN-038, ZM-FIN-055, ZM-FIN-106–107.

**Inspección inicial obligatoria**
Inspecciona configuración engine/session, patrones de conexión, migraciones y queries críticas.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir PostgreSQL local autoritativo; roles mínimos; pool/timeouts; SSL; migration job único; expand-contract; durabilidad/replicación al standby; fencing/promoción controlada; maintenance y schema drift.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No aplicar tuning arbitrario sin perfiles ni conceder superuser a la aplicación. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Restart DB, failover, migration interrupted, pool exhausted, statement timeout y schema incompatible.

**Concurrencia y consistencia**
Probar API+worker bajo pool limitado, locks y migración singleton.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Deploy con versiones mixtas, migración larga/fallida, pool agotado, deadlock, worker+API y read-only maintenance.

**Validación y comandos**
Upgrade staging, smoke, pruebas de pool/failover y schema drift. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Migración corre una vez antes de tráfico incompatible; API/worker manejan conexiones; roles no pueden saltarse inmutabilidad; métricas existen.
Definition of Done específica: Migración corre una vez antes de tráfico incompatible; API/worker manejan conexiones; roles no pueden saltarse inmutabilidad; métricas existen. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Runbook DB, migraciones y parámetros aprobados.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-109 — Implementar logging, métricas, tracing, health y readiness productivos

**Épica:** Observabilidad
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Observar API, DB, primario, standby/replicación, backup/off-site, LAN, bridge, worker/outbox, alert dashboard y Telegram; sin Internet persistir local y dejar delivery pending.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-109 |
| **2. Nombre de la tarea** | Implementar logging, métricas, tracing, health y readiness productivos |
| **3. Objetivo** | Hacer observable cada operación y detectar degradación antes de afectar panaderías. |
| **4. Problema que resuelve** | Logging es básico; no hay request ID transversal, métricas/tracing/readiness y health ocultó outbox detenido. |
| **5. Hallazgo relacionado** | ZM-OBS-017; ZMA-ASYNC-001; ZMA-AUD-001. |
| **6. Módulos afectados** | API, worker, frontends, DB, infrastructure y alerting. |
| **7. Archivos/áreas a inspeccionar** | Logging config; middleware; OpenTelemetry/metrics stack aprobada; probes; dashboards. |
| **8. Dependencias previas** | ZM-FIN-040, ZM-FIN-082, ZM-FIN-087–093 y ZM-FIN-107–108. |
| **9. Cambios a implementar** | Logs/redacción; correlation/causation; instrumentación DEC-18; traces; liveness/readiness; API/DB/primario/standby/backup/LAN/bridge/worker/outbox; dashboard/Telegram; subconjunto KPI de piloto; alertas A/B/C separadas de defectos; evidencia stop/resume, reconciliación y estabilidad por Sucursal Matriz. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Cardinalidad/costo altos, datos sensibles o alertas ruidosas. |
| **13. Posibles regresiones** | Latencia y volumen de logs. |
| **14. Pruebas requeridas** | DB caída, worker backlog, provider error, alta latencia, venta fallida, frontend error y secreto en input. |
| **15. Criterios de aceptación** | Venta se rastrea UI→API→DB→outbox→worker→fact; readiness refleja dependencias locales; Internet/Telegram caído no afecta backend sano; KPI mínimos cubren dinero/inventario/outbox/DQ/backup/ACK; severidades no se mezclan y logs/evidencia no contienen secretos/PII innecesaria. |
| **16. Definition of Done específica** | Una venta se rastrea UI→API→DB→outbox→worker; readiness refleja dependencias; logs no contienen secretos/PII innecesaria. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Dashboards, traces de casos, simulación de alertas y escaneo de logs. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | Posible |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Staging Ready y Production Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-109 — Implementar logging, métricas, tracing, health y readiness productivos**.

**Objetivo**
Hacer observable cada operación y detectar degradación antes de afectar panaderías.

**Problema y contexto de ZeroMerma**
Logging es básico; no hay request ID transversal, métricas/tracing/readiness y health ocultó outbox detenido. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-OBS-017; ZMA-ASYNC-001; ZMA-AUD-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-040, ZM-FIN-082, ZM-FIN-087–093 y ZM-FIN-107–108.

**Inspección inicial obligatoria**
Inspecciona formatter actual API/worker, health endpoint y operation context.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Logs/redacción; correlation/causation; instrumentación DEC-18; traces; liveness/readiness; API/DB/primario/standby/backup/LAN/bridge/worker/outbox; dashboard local y Telegram con pending/retry.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No hacer que la operación dependa de la disponibilidad del proveedor de observabilidad. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Request anónimo, batch worker, replay, provider callback, sampling y caída del observability backend.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: Posible. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
DB caída, worker backlog, provider error, alta latencia, venta fallida, frontend error y secreto en input.

**Validación y comandos**
Pruebas de propagación/probes, carga moderada y simulación de fallos en staging. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Una venta se rastrea UI→API→DB→outbox→worker; readiness refleja dependencias; logs no contienen secretos/PII innecesaria.
Definition of Done específica: Una venta se rastrea UI→API→DB→outbox→worker; readiness refleja dependencias; logs no contienen secretos/PII innecesaria. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Catálogo de señales, dashboards y runbooks.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-110 — Implementar promoción CI/CD, aprobaciones y smoke de release

**Épica:** Entrega continua
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST, standby controlado, observabilidad amplia, alerting conservador, backup/restore y cloud complementario.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-110 |
| **2. Nombre de la tarea** | Implementar promoción CI/CD, aprobaciones y smoke de release |
| **3. Objetivo** | Promover exactamente los mismos artefactos de commit a staging y producción con controles auditable. |
| **4. Problema que resuelve** | No existe despliegue productivo, promoción, rollback ni evidencia de artefactos inmutables. |
| **5. Hallazgo relacionado** | ZM-OPS-014; ZM-REL-015. |
| **6. Módulos afectados** | CI/CD, artifacts, IaC, migrations, smoke y approvals. |
| **7. Archivos/áreas a inspeccionar** | Workflows; registries; manifests; deployment scripts; environment protections. |
| **8. Dependencias previas** | ZM-FIN-014, ZM-FIN-106–109 y política de release. |
| **9. Cambios a implementar** | Pipeline build-once/promote; firma/attestation si aprobada; migration gate; smoke; approvals; freeze/concurrency; release notes y evidence bundle. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Rebuild diferente por ambiente, bypass de approval o despliegues concurrentes. |
| **13. Posibles regresiones** | Entornos actuales y tiempos de release. |
| **14. Pruebas requeridas** | Re-run, cancel, deploy concurrente, migration fail, smoke fail, rollback y secret unavailable. |
| **15. Criterios de aceptación** | Producción sólo recibe digests probados en staging; un fallo detiene promoción; cada release es trazable a commit/schema/tests. |
| **16. Definition of Done específica** | Producción sólo recibe digests probados en staging; un fallo detiene promoción; cada release es trazable a commit/schema/tests. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Run de staging, intento fallido controlado, manifiesto y approvals. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-117–123 y Gate Production Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-110 — Implementar promoción CI/CD, aprobaciones y smoke de release**.

**Objetivo**
Promover exactamente los mismos artefactos de commit a staging y producción con controles auditable.

**Problema y contexto de ZeroMerma**
No existe despliegue productivo, promoción, rollback ni evidencia de artefactos inmutables. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-OPS-014; ZM-REL-015.

**Dependencias que puedes asumir terminadas**
ZM-FIN-014, ZM-FIN-106–109 y política de release.

**Inspección inicial obligatoria**
Inspecciona workflow foundation, permisos OIDC/secrets, registry y scripts.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Pipeline build-once/promote; firma/attestation si aprobada; migration gate; smoke; approvals; freeze/concurrency; release notes y evidence bundle.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No recompilar por ambiente ni permitir cambios manuales no registrados. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Hotfix, rollback, migration incompatible, artefacto expirado y rerun.

**Concurrencia y consistencia**
Serializar despliegues por ambiente y evitar dos jobs de migración.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Re-run, cancel, deploy concurrente, migration fail, smoke fail, rollback y secret unavailable.

**Validación y comandos**
Ejecuta pipeline completo en staging, smoke y fallo controlado; no desplegar a producción aún. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Producción sólo recibe digests probados en staging; un fallo detiene promoción; cada release es trazable a commit/schema/tests.
Definition of Done específica: Producción sólo recibe digests probados en staging; un fallo detiene promoción; cada release es trazable a commit/schema/tests. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Procedimiento de release, approvals y evidencia.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-111 — Integrar secretos y configuración externa en la plataforma

**Épica:** Configuración runtime
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST, standby controlado, observabilidad amplia, alerting conservador, backup/restore y cloud complementario.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-111 |
| **2. Nombre de la tarea** | Integrar secretos y configuración externa en la plataforma |
| **3. Objetivo** | Inyectar configuración validada por entorno sin editar artefactos y con rotación operable. |
| **4. Problema que resuelve** | La app debe fallar cerrada y los secretos no pueden residir en Git/imágenes; falta integración productiva demostrada. |
| **5. Hallazgo relacionado** | ZM-SEC-007; ZM-OPS-014. |
| **6. Módulos afectados** | Runtime platform, API, worker, frontends, DB y providers. |
| **7. Archivos/áreas a inspeccionar** | Secret manager/config maps; startup; frontend runtime config; rotation hooks. |
| **8. Dependencias previas** | ZM-FIN-026–027, ZM-FIN-085 y ZM-FIN-107–110. |
| **9. Cambios a implementar** | Gestionar secreto/config local y externo; versionar config; incluir Telegram, backup off-site y standby; inyectar URL LAN no secreta; validar startup; probar rotación/recuperación sin depender de Internet para operar. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Exponer secretos al frontend o bloquear todas las instancias al rotar. |
| **13. Posibles regresiones** | Startup y providers. |
| **14. Pruebas requeridas** | Secreto ausente/rotado, config inválida, versiones mixtas, rollback y frontend cacheado. |
| **15. Criterios de aceptación** | Artefacto idéntico funciona en staging/prod con config externa; valores inválidos detienen arranque; rotación probada. |
| **16. Definition of Done específica** | Artefacto idéntico funciona en staging/prod con config externa; valores inválidos detienen arranque; rotación probada. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Manifiesto de config no secreta y simulacro de rotación. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Production Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-111 — Integrar secretos y configuración externa en la plataforma**.

**Objetivo**
Inyectar configuración validada por entorno sin editar artefactos y con rotación operable.

**Problema y contexto de ZeroMerma**
La app debe fallar cerrada y los secretos no pueden residir en Git/imágenes; falta integración productiva demostrada. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-SEC-007; ZM-OPS-014.

**Dependencias que puedes asumir terminadas**
ZM-FIN-026–027, ZM-FIN-085 y ZM-FIN-107–110.

**Inspección inicial obligatoria**
Inspecciona todas las variables build-time/runtime y qué necesita cada componente.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Conectar gestor; separar secreto/config; versionar config; inyectar frontend URL no secreta; validar startup; rotación sin downtime según política.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No imprimir secretos ni usar `.env` manual como mecanismo productivo. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Secret version, rollback, cache frontend, provider optional y environment drift.

**Concurrencia y consistencia**
Rotación durante rollout gradual.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Secreto ausente/rotado, config inválida, versiones mixtas, rollback y frontend cacheado.

**Validación y comandos**
Deploy staging con config externa, casos de fallo y rotación. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Artefacto idéntico funciona en staging/prod con config externa; valores inválidos detienen arranque; rotación probada.
Definition of Done específica: Artefacto idéntico funciona en staging/prod con config externa; valores inválidos detienen arranque; rotación probada. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Inventario de config y runbook de rotación.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-112 — Implementar backups, PITR y simulacro de restauración

**Épica:** Continuidad
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Demostrar RPO nodo cero/casi cero, RPO sitio <=5m, RTO primario <=1h y RTO sitio <=8h; backup/restore separado del archivo analítico.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-112 |
| **2. Nombre de la tarea** | Implementar backups, PITR y simulacro de restauración |
| **3. Objetivo** | Demostrar recuperación LOCAL_FIRST: RPO nodo cero/casi cero, RPO pérdida de sitio <=5m, RTO servidor primario <=1h y RTO pérdida de sitio <=8h. |
| **4. Problema que resuelve** | Backup/PITR se menciona como necesidad, pero no hay automatización ni restore verificado. |
| **5. Hallazgo relacionado** | ZM-OPS-014; elementos no verificables de recuperación. |
| **6. Módulos afectados** | PostgreSQL, object storage/backup service, security y runbooks. |
| **7. Archivos/áreas a inspeccionar** | Infra DB; backup policies; encryption; restore scripts; validation queries. |
| **8. Dependencias previas** | ZM-FIN-007, ZM-FIN-047, ZM-FIN-055 y ZM-FIN-107–111; RPO/RTO aprobados. |
| **9. Cambios a implementar** | Configurar backup/PITR/replicación cifrados, copia off-site, retención/acceso; restore aislado/local/off-site; arrancar y reconciliar ledger/audit/outbox/fact; producir evidencia reusable para Sucursal Matriz sin restore destructivo en vivo; separar backup operacional de archivo HOT/WARM/COLD. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Backups no restaurables, acceso indebido o retención insuficiente/excesiva. |
| **13. Posibles regresiones** | Carga/IO sobre DB y costos. |
| **14. Pruebas requeridas** | Backup corrupto, punto en tiempo, secreto perdido, restore a versión distinta, backlog y PII. |
| **15. Criterios de aceptación** | Backup se restaura en entorno vacío y desde off-site; DB/app arrancan y reconciliaciones pasan; evidencia vigente/trazable corresponde al release del piloto; RPO/RTO se comparan con DEC-17; no se provoca restore destructivo en Sucursal Matriz ni se confunde backup con archivo. |
| **16. Definition of Done específica** | Un backup candidato se restaura en entorno vacío; DB arranca y reconciliaciones pasan; tiempos observados se comparan con objetivos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Checksums, logs de restore, revisión restaurada y reconciliación firmada. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Production Ready y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-112 — Implementar backups, PITR y simulacro de restauración**.

**Objetivo**
Demostrar que los datos pueden recuperarse dentro de objetivos aprobados.

**Problema y contexto de ZeroMerma**
Backup/PITR se menciona como necesidad, pero no hay automatización ni restore verificado. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-OPS-014; elementos no verificables de recuperación.

**Dependencias que puedes asumir terminadas**
ZM-FIN-007, ZM-FIN-047, ZM-FIN-055 y ZM-FIN-107–111; RPO/RTO aprobados.

**Inspección inicial obligatoria**
Inspecciona plataforma DB y políticas existentes antes de afirmar ausencia.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Configurar backup/PITR/replicación cifrados, copia off-site, retención/acceso; restore aislado/local/off-site; arrancar y reconciliar ledger/audit/outbox/fact layer; separar backup operacional de archivo HOT/WARM/COLD.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No considerar un backup válido sin restaurarlo. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Restore parcial, PITR antes/después de migración, claves de cifrado y backup durante alta carga.

**Concurrencia y consistencia**
Validar consistencia del backup con escrituras y WAL/PITR.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Backup corrupto, punto en tiempo, secreto perdido, restore a versión distinta, backlog y PII.

**Validación y comandos**
Ejecuta backup/restore drill sólo en staging/entorno aislado y reconciliaciones completas. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Un backup candidato se restaura en entorno vacío; DB arranca y reconciliaciones pasan; tiempos observados se comparan con objetivos.
Definition of Done específica: Un backup candidato se restaura en entorno vacío; DB arranca y reconciliaciones pasan; tiempos observados se comparan con objetivos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Runbook, retención, acceso y registro de simulacros.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-113 — Definir y ensayar roll-forward, rollback y disaster recovery

**Épica:** Recuperación
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Ensayar standby sin split-brain, pérdida de sitio, reconciliación ledger/outbox/alertas/proyecciones e Incident Commander con doble aprobación destructiva.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-113 |
| **2. Nombre de la tarea** | Definir y ensayar roll-forward, rollback y disaster recovery |
| **3. Objetivo** | Recuperar ante release/migración, pérdida de worker/nodo/sitio o corrupción lógica sin improvisar ni crear split-brain. |
| **4. Problema que resuelve** | No existe procedimiento comprobable de rollback/DR; downgrade de migraciones no fue validado. |
| **5. Hallazgo relacionado** | ZM-OPS-014; elementos no verificables. |
| **6. Módulos afectados** | Application release, DB, worker, frontends, DNS y incident response. |
| **7. Archivos/áreas a inspeccionar** | Deployment scripts; migration strategy; backups; feature flags; runbooks. |
| **8. Dependencias previas** | ZM-FIN-108, ZM-FIN-110–112. |
| **9. Cambios a implementar** | Definir roll-forward/rollback, stop-only inicial y aislamiento por sucursal; compatibilidad N/N-1; restore lógico; worker pause/replay; standby con fencing; pérdida de sitio/DR; reconciliar ledger/outbox/alertas/proyecciones; dual authority para resume crítico y comunicación DEC-20. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Rollback de app incompatible con schema o pérdida de eventos durante recuperación. |
| **13. Posibles regresiones** | Complejidad de deployment y flags. |
| **14. Pruebas requeridas** | App bad release, migration parcialmente aplicada, schema incompatible, worker corrupto, secret compromise y region/service outage. |
| **15. Criterios de aceptación** | Cada fallo tiene drill seguro y RPO/RTO observado; no hay split-brain ni downgrade supuesto; IC/supervisor pueden stop; reanudación crítica y restore destructivo exigen autoridad técnica/administrativa; rollback preserva DB/evidencia y no afecta otra sucursal sin alcance demostrado. |
| **16. Definition of Done específica** | Cada clase de fallo tiene procedimiento probado; no se usa downgrade destructivo sin evidencia; restore/roll-forward preserva integridad. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Simulacros, tiempos observados, decisiones y acciones correctivas. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Production Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-113 — Definir y ensayar roll-forward, rollback y disaster recovery**.

**Objetivo**
Recuperar servicio ante release/migración fallida, pérdida de worker o corrupción lógica sin improvisación.

**Problema y contexto de ZeroMerma**
No existe procedimiento comprobable de rollback/DR; downgrade de migraciones no fue validado. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-OPS-014; elementos no verificables.

**Dependencias que puedes asumir terminadas**
ZM-FIN-108, ZM-FIN-110–112.

**Inspección inicial obligatoria**
Inspecciona compatibilidad de migraciones, release topology y dependencias externas.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir roll-forward/rollback; compatibilidad N/N-1; restore lógico; worker pause/replay; promoción del standby con fencing; pérdida de sitio desde off-site/DR; reconciliar ledger/outbox/alertas/proyecciones; comunicación.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No prometer downgrade genérico de Alembic ni multi-región sin alcance. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Datos escritos por versión nueva, rollback frontend, outbox pendiente y secreto revocado.

**Concurrencia y consistencia**
Coordinar tráfico, migration job, worker y restore durante el ejercicio.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
App bad release, migration parcialmente aplicada, schema incompatible, worker corrupto, secret compromise y region/service outage.

**Validación y comandos**
Ejecuta game days en staging: bad deploy, worker outage y restore/roll-forward. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada clase de fallo tiene procedimiento probado; no se usa downgrade destructivo sin evidencia; restore/roll-forward preserva integridad.
Definition of Done específica: Cada clase de fallo tiene procedimiento probado; no se usa downgrade destructivo sin evidencia; restore/roll-forward preserva integridad. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Runbooks DR y matriz de decisión por tipo de cambio.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-114 — Implementar hosting, caché y actualización segura de POS/Backoffice

**Épica:** Entrega frontend
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Frontends por LAN operan sin Internet; no hay mutaciones offline del browser y hosting cloud no bloquea piloto.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-114 |
| **2. Nombre de la tarea** | Implementar hosting, caché y actualización segura de POS/Backoffice |
| **3. Objetivo** | Servir frontends versionados sin mezclar assets/API incompatibles y con actualización controlada. |
| **4. Problema que resuelve** | No existe despliegue productivo de frontends; la configuración Vite actual es de desarrollo. |
| **5. Hallazgo relacionado** | ZM-OPS-014; ZM-REL-018. |
| **6. Módulos afectados** | POS, Backoffice, static hosting/CDN/proxy y runtime config. |
| **7. Archivos/áreas a inspeccionar** | Vite builds; asset hashing; cache headers; base URLs; service worker; error pages. |
| **8. Dependencias previas** | ZM-FIN-106–111 y ZM-FIN-009. |
| **9. Cambios a implementar** | Servir POS/Backoffice por LAN; assets inmutables, HTML no stale, runtime config, CSP, compatibilidad/rollback; no implementar mutaciones browser-offline ni exigir hosting cloud. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Cache poisoning/stale assets o recarga durante venta. |
| **13. Posibles regresiones** | PWA/service worker, rutas SPA y base paths. |
| **14. Pruebas requeridas** | Deploy de nueva versión con pestaña abierta, rollback, cache corrupta, API N/N-1 y service worker. |
| **15. Criterios de aceptación** | Cliente carga versión coherente por LAN y opera sin Internet con backend local sano; no conserva HTML incompatible; actualización no duplica/pierde operación; LAN/backend caído bloquea la mutación. |
| **16. Definition of Done específica** | Cliente carga assets de una versión coherente; no conserva HTML incompatible; actualización no duplica ni pierde operación en curso. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Pruebas de cache/upgrade/rollback y headers. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-117–123 y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-114 — Implementar hosting, caché y actualización segura de POS/Backoffice**.

**Objetivo**
Servir frontends versionados sin mezclar assets/API incompatibles y con actualización controlada.

**Problema y contexto de ZeroMerma**
No existe despliegue productivo de frontends; la configuración Vite actual es de desarrollo. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-OPS-014; ZM-REL-018.

**Dependencias que puedes asumir terminadas**
ZM-FIN-106–111 y ZM-FIN-009.

**Inspección inicial obligatoria**
Inspecciona configuración Vite, routing, service worker y cómo se inyecta API URL.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Servir POS/Backoffice por LAN; assets inmutables, HTML no stale, runtime config, CSP, compatibilidad/rollback; no implementar mutaciones browser-offline ni exigir hosting cloud.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No editar bundles manualmente ni usar cache-busting sin versionado coherente. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Pestaña antigua, offline cache, rollback, nueva versión durante venta y CDN invalidation.

**Concurrencia y consistencia**
Versiones de frontend/API coexistentes durante rollout deben ser compatibles según contrato.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Deploy de nueva versión con pestaña abierta, rollback, cache corrupta, API N/N-1 y service worker.

**Validación y comandos**
Deploy staging, pruebas de cache/upgrade/rollback y E2E. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cliente carga assets de una versión coherente; no conserva HTML incompatible; actualización no duplica ni pierde operación en curso.
Definition of Done específica: Cliente carga assets de una versión coherente; no conserva HTML incompatible; actualización no duplica ni pierde operación en curso. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Procedimiento de publicación y actualización frontend.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-115 — Crear paquete de instalación, actualización y soporte por estación

**Épica:** Distribución POS
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: LOCAL_FIRST, standby controlado, observabilidad amplia, alerting conservador, backup/restore y cloud complementario.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-115 |
| **2. Nombre de la tarea** | Crear paquete de instalación, actualización y soporte por estación |
| **3. Objetivo** | Preparar cada terminal de panadería con navegador, URL, hardware y configuración reproducibles. |
| **4. Problema que resuelve** | Instalación/actualización y hardware real no están documentados ni validados productivamente. |
| **5. Hallazgo relacionado** | ZM-OPS-014; elementos no verificables de hardware/instalación. |
| **6. Módulos afectados** | POS workstation, browser/kiosk, printer/drawer/terminal, network y support. |
| **7. Archivos/áreas a inspeccionar** | Scripts/installer; workstation config; browser policies; hardware drivers/bridge; diagnostics. |
| **8. Dependencias previas** | ZM-FIN-064–067, ZM-FIN-107, ZM-FIN-111 y ZM-FIN-114. |
| **9. Cambios a implementar** | Definir imagen/checklist; inventariar hardware de Sucursal Matriz; registrar branch/workstation y binding de periféricos/BBVA; instalar drivers/bridge; auto-start/kiosk si aprobado; versión identificable, update/rollback, diagnóstico y soporte remoto seguro. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Configuración manual no reproducible, credenciales compartidas o soporte remoto inseguro. |
| **13. Posibles regresiones** | Terminales existentes y compatibilidad de drivers. |
| **14. Pruebas requeridas** | Terminal nueva, reinstall, hardware desconectado, cambio de sucursal/caja, browser update y pérdida de config. |
| **15. Criterios de aceptación** | Cada estación de Sucursal Matriz se prepara por runbook, obtiene sólo contexto autorizado y conserva inventario/config/release; principal/standby/LAN/periféricos pasan smoke; update/rollback no introduce drift ni cruza branches. |
| **16. Definition of Done específica** | Una estación nueva se prepara siguiendo el runbook; obtiene sólo su contexto autorizado; hardware y actualización pasan smoke. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Checklist firmado, smoke por estación y matriz de versiones. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-120–123 y Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-115 — Crear paquete de instalación, actualización y soporte por estación**.

**Objetivo**
Preparar cada terminal de panadería con navegador, URL, hardware y configuración reproducibles.

**Problema y contexto de ZeroMerma**
Instalación/actualización y hardware real no están documentados ni validados productivamente. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-OPS-014; elementos no verificables de hardware/instalación.

**Dependencias que puedes asumir terminadas**
ZM-FIN-064–067, ZM-FIN-107, ZM-FIN-111 y ZM-FIN-114.

**Inspección inicial obligatoria**
Inspecciona requisitos de workstation actuales, assignments y hardware objetivo.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir imagen/checklist; registrar workstation; instalar drivers/bridge; auto-start/kiosk si aprobado; update/rollback; diagnóstico y soporte remoto seguro.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No incrustar credenciales ni depender de pasos manuales no verificables. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Reemplazo de terminal, cambio de IP, pérdida de certificados, browser cache y usuario diferente.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Terminal nueva, reinstall, hardware desconectado, cambio de sucursal/caja, browser update y pérdida de config.

**Validación y comandos**
Instalación limpia en hardware de prueba, update/rollback y smoke completo. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Una estación nueva se prepara siguiendo el runbook; obtiene sólo su contexto autorizado; hardware y actualización pasan smoke.
Definition of Done específica: Una estación nueva se prepara siguiendo el runbook; obtiene sólo su contexto autorizado; hardware y actualización pasan smoke. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Guía de instalación, actualización y troubleshooting por estación.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-116 — Definir SLOs, alertas, incidentes y responsabilidad operativa

**Épica:** Operación SRE
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** CRITICAL-A/B/C, ACK 5/15/60m, owner/acción/escalamiento/resolución, dashboard local y Telegram crítico no bloqueante; sensibilidad conservadora.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-116 |
| **2. Nombre de la tarea** | Definir SLOs, alertas, incidentes y responsabilidad operativa |
| **3. Objetivo** | Establecer cómo se detecta, clasifica, responde y aprende de fallos productivos. |
| **4. Problema que resuelve** | No hay métricas/alertas/runbooks productivos ni objetivos de recuperación demostrados. |
| **5. Hallazgo relacionado** | ZM-OPS-014; ZM-OBS-017. |
| **6. Módulos afectados** | All services, observability, support, business operations y security. |
| **7. Archivos/áreas a inspeccionar** | Dashboards/alerts; runbooks; incident templates; ownership; escalation. |
| **8. Dependencias previas** | ZM-FIN-089, ZM-FIN-102, ZM-FIN-109–115 y objetivos aprobados. |
| **9. Cambios a implementar** | Definir SLI/SLO sin cifras arbitrarias; CRITICAL-A/B/C y defectos CRITICAL/HIGH/MEDIUM/LOW separados; ACK 5/15/60m; STOP-B, pausa protectora, dual resume/expansion; owner/acción/dedup/escalamiento/resolución; dashboard/Telegram; soporte durante cutover/operación e incidentes; runbooks/postmortem. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Alert fatigue, objetivos irreales o responsabilidades ambiguas. |
| **13. Posibles regresiones** | Carga operativa y costo de observabilidad. |
| **14. Pruebas requeridas** | API down, DB degraded, worker backlog, payment provider, printer, stock mismatch, cash discrepancy y security incident. |
| **15. Criterios de aceptación** | Cada alerta tiene condición/owner/acción/ACK/escalamiento/resolución; CRITICAL-A presume stop y defectos siguen su propia taxonomía; autoridad stop/resume/expansion está probada; Telegram no bloquea, soporte tiene capacidad y SLOs reflejan evidencia sin cifras arbitrarias. |
| **16. Definition of Done específica** | Cada alerta tiene dueño/acción; incidentes críticos pueden diagnosticarse con evidencia; SLOs reflejan operación aprobada, no cifras arbitrarias. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Catálogo SLO/alertas, simulacros y postmortem de prueba. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Gate Production Ready y General Production. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-116 — Definir SLOs, alertas, incidentes y responsabilidad operativa**.

**Objetivo**
Establecer cómo se detecta, clasifica, responde y aprende de fallos productivos.

**Problema y contexto de ZeroMerma**
No hay métricas/alertas/runbooks productivos ni objetivos de recuperación demostrados. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-OPS-014; ZM-OBS-017.

**Dependencias que puedes asumir terminadas**
ZM-FIN-089, ZM-FIN-102, ZM-FIN-109–115 y objetivos aprobados.

**Inspección inicial obligatoria**
Inspecciona flujos críticos y señales disponibles; obtén requisitos del propietario.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Definir SLI/SLO sin cifras arbitrarias; CRITICAL-A/B/C; ACK 5/15/60m; owner/acción/dedup/escalamiento/resolución; dashboard local; Telegram crítico no bloqueante; runbooks/postmortem/ventanas.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No fijar disponibilidad/latencia sin contexto de negocio ni alertar sin acción. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Fuera de horario, proveedor externo, sucursal aislada, incidente de datos y alerta duplicada.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
API down, DB degraded, worker backlog, payment provider, printer, stock mismatch, cash discrepancy y security incident.

**Validación y comandos**
Simular incidentes en staging y verificar alert routing/runbooks. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada alerta tiene dueño/acción; incidentes críticos pueden diagnosticarse con evidencia; SLOs reflejan operación aprobada, no cifras arbitrarias.
Definition of Done específica: Cada alerta tiene dueño/acción; incidentes críticos pueden diagnosticarse con evidencia; SLOs reflejan operación aprobada, no cifras arbitrarias. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
SLOs, runbooks, escalación y plantilla de postmortem.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```


## Fase 10 — Staging, piloto, estabilización y producción general — Tareas ejecutables

### ZM-FIN-117 — Desplegar la versión candidata en staging equivalente a producción

**Épica:** Staging
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: staging/piloto/gates generan evidencia LOCAL_FIRST y KPI/alertas válidos; lakehouse/IA/WhatsApp no bloquean v1.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-117 |
| **2. Nombre de la tarea** | Desplegar la versión candidata en staging equivalente a producción |
| **3. Objetivo** | Validar el release completo en staging reproducible equivalente a los controles LOCAL_FIRST antes del piloto, sin exigir proveedor cloud/lakehouse. |
| **4. Problema que resuelve** | No existe staging productivo, smoke autenticado ni evidencia de despliegue recuperable. |
| **5. Hallazgo relacionado** | ZM-OPS-014; elementos no verificables. |
| **6. Módulos afectados** | All artifacts, infrastructure, DB, worker, frontends y providers sandbox. |
| **7. Archivos/áreas a inspeccionar** | IaC; CI/CD; manifests; staging config; DNS/TLS; smoke scripts. |
| **8. Dependencias previas** | ZM-FIN-106–116 y Gates Development/Feature/Data/Security/QA aprobables. |
| **9. Cambios a implementar** | Provisionar/desplegar topología LOCAL_FIRST; cargar exclusivamente datos UAT clasificados; ensayar clean start/opening state idempotente y reconciliación; validar LAN/TLS/probes/standby; smoke API/POS/Backoffice/worker; simular Internet caído y delivery Telegram pendiente; ejecutar en staging/drill pérdida de nodo, split-brain, restore, failover, corrupción/provider outage y recuperación con la versión/semántica candidata. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Staging no equivalente, datos sensibles o pasos manuales ocultos. |
| **13. Posibles regresiones** | Ninguna productiva; detectar incompatibilidades de entorno. |
| **14. Pruebas requeridas** | Fresh deploy, rerun, migration fail, worker backlog, provider sandbox, cache frontend y rollback. |
| **15. Criterios de aceptación** | Staging nace desde cero con el manifiesto candidato y dataset UAT identificado; clean start/opening state y reconciliación pasan; ningún seed se presenta como historia productiva; fallos peligrosos tienen evidencia vigente/trazable reusable para go/no-go; smoke/probes pasan y no hay drift ni cambios manuales no registrados. |
| **16. Definition of Done específica** | Staging nace desde cero con el manifiesto candidato; smoke y probes pasan; no hay drift/manual changes no registrados. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Manifiesto desplegado, logs, digests, schema revision y smoke results. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | Sí |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-118–120 y Gate Staging Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-117 — Desplegar la versión candidata en staging equivalente a producción**.

**Objetivo**
Validar el release completo en staging reproducible equivalente a los controles LOCAL_FIRST antes del piloto, sin exigir proveedor cloud/lakehouse.

**Problema y contexto de ZeroMerma**
No existe staging productivo, smoke autenticado ni evidencia de despliegue recuperable. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZM-OPS-014; elementos no verificables.

**Dependencias que puedes asumir terminadas**
ZM-FIN-106–116 y Gates Development/Feature/Data/Security/QA aprobables.

**Inspección inicial obligatoria**
Inspecciona todo el release manifest y diferencias permitidas staging/prod.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Provisionar/desplegar topología LOCAL_FIRST; migrar/cargar datos; validar LAN/TLS/probes/standby; smoke API/POS/Backoffice/worker; simular Internet caído y delivery Telegram pendiente.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No usar datos productivos ni promover a producción. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Entorno vacío, redeploy, secret rotation, DNS, cache y provider sandbox.

**Concurrencia y consistencia**
Probar deployment lock y migration singleton.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: Sí. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Fresh deploy, rerun, migration fail, worker backlog, provider sandbox, cache frontend y rollback.

**Validación y comandos**
Ejecuta pipeline de promoción, smoke y drift detection. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Staging nace desde cero con el manifiesto candidato; smoke y probes pasan; no hay drift/manual changes no registrados.
Definition of Done específica: Staging nace desde cero con el manifiesto candidato; smoke y probes pasan; no hay drift/manual changes no registrados. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Registro del despliegue y diferencias de entorno.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-118 — Preparar dataset representativo y plan de aceptación de usuario

**Épica:** UAT
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: staging/piloto/gates generan evidencia LOCAL_FIRST y KPI/alertas válidos; lakehouse/IA/WhatsApp no bloquean v1.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-118 |
| **2. Nombre de la tarea** | Preparar dataset representativo y plan de aceptación de usuario |
| **3. Objetivo** | Cubrir procesos reales de panadería con datos seguros y escenarios aprobados. |
| **4. Problema que resuelve** | Las auditorías usaron datos `AUDIT-`, pero no existe un dataset UAT que cubra todo el negocio. |
| **5. Hallazgo relacionado** | Evidencia activa y elementos no verificables. |
| **6. Módulos afectados** | All business domains, staging DB, UAT scripts y privacy. |
| **7. Archivos/áreas a inspeccionar** | Seeds/fixtures; data factory; scenario catalog; cleanup/reset seguro. |
| **8. Dependencias previas** | ZM-FIN-003, ZM-FIN-007, ZM-FIN-099 y ZM-FIN-117. |
| **9. Cambios a implementar** | Crear datos sintéticos de sucursales, roles, estaciones, catálogo, precios, recetas, stock, proveedores, pedidos y excepciones; modelar Sucursal Matriz sin tratar `MAIN` como mapping productivo; mapear dos ciclos semanales, cadencias, stop/degraded/track, reconciliaciones, autoridades y evidencia. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Datos demasiado simples o copiar datos reales sin control. |
| **13. Posibles regresiones** | Seeds locales o tests si se mezclan entornos. |
| **14. Pruebas requeridas** | Estado vacío, múltiples sucursales, stock bajo, pagos mixtos, refunds, producción y cierre. |
| **15. Criterios de aceptación** | Dataset es reproducible, no contiene PII real, distingue Sucursal Matriz de seeds demo y permite ejecutar casos UAT de ciclos, stop, BBVA/fiscal gated y reconciliación sin ajustes manuales ocultos. |
| **16. Definition of Done específica** | Dataset es reproducible, no contiene PII real y permite ejecutar todos los casos UAT sin ajustes manuales ocultos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Seed versionado, catálogo de escenarios y hash/snapshot. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-119 y Gate Staging Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-118 — Preparar dataset representativo y plan de aceptación de usuario**.

**Objetivo**
Cubrir procesos reales de panadería con datos seguros y escenarios aprobados.

**Problema y contexto de ZeroMerma**
Las auditorías usaron datos `AUDIT-`, pero no existe un dataset UAT que cubra todo el negocio. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Evidencia activa y elementos no verificables.

**Dependencias que puedes asumir terminadas**
ZM-FIN-003, ZM-FIN-007, ZM-FIN-099 y ZM-FIN-117.

**Inspección inicial obligatoria**
Inspecciona seeds actuales y datos requeridos por cada flujo/gate.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Crear datos sintéticos: sucursales, roles, estaciones, catálogo, precios, recetas, stock, proveedores, pedidos y casos de excepción; mapear escenarios/roles/evidencia.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No anonimizar superficialmente datos reales; usar sintéticos salvo aprobación formal. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Colecciones vacías, roles limitados, dos branches y estados históricos.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Estado vacío, múltiples sucursales, stock bajo, pagos mixtos, refunds, producción y cierre.

**Validación y comandos**
Crear/resetear staging UAT mediante procedimiento seguro y ejecutar sanity checks. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Dataset es reproducible, no contiene PII real y permite ejecutar todos los casos UAT sin ajustes manuales ocultos.
Definition of Done específica: Dataset es reproducible, no contiene PII real y permite ejecutar todos los casos UAT sin ajustes manuales ocultos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Catálogo de datos y casos UAT.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-119 — Ejecutar el ensayo integral de operación en staging

**Épica:** UAT
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Ensayar atomic outbox, fact layer/rebuild, fórmulas KPI críticas, A/B/C, Telegram y pérdida de Internet sin detener operación local.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-119 |
| **2. Nombre de la tarea** | Ejecutar el ensayo integral de operación en staging |
| **3. Objetivo** | Probar con usuarios representativos todos los procesos diarios, semanales y administrativos incluidos. |
| **4. Problema que resuelve** | La auditoría activa cubrió 106 casos, pero dejó hardware, concurrencia, permisos finos y varios módulos sin verificar. |
| **5. Hallazgo relacionado** | Matriz completa de auditoría activa y pendientes. |
| **6. Módulos afectados** | POS, Backoffice, API, worker, hardware sandbox y operations. |
| **7. Archivos/áreas a inspeccionar** | UAT scripts; evidence capture; dashboards; runbooks. |
| **8. Dependencias previas** | ZM-FIN-117–118 y todos los módulos Feature Complete. |
| **9. Cambios a implementar** | Ejecutar ciclo completo y cadencias representativas; clean start/opening state; Superadministrador inicial y scopes; operaciones abiertas y rechazo de ambigüedad; mappings; atomic outbox; fact layer/rebuild; fórmulas KPI críticas; alertas A/B/C frente a severidad de defectos; stop/resume con dual authority; contingencia stop-only y drill manual; BBVA/fiscal gated; pérdida de Internet con LAN sana; fallos/recovery; reconciliaciones extraordinarias y firmas. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | UAT superficial o aprobación por apariencia sin persistencia/reconciliación. |
| **13. Posibles regresiones** | Descubrir defectos tardíos; es el propósito de la tarea. |
| **14. Pruebas requeridas** | Todos los casos auditados fallidos/bloqueados/no verificados, más escenarios profesionales añadidos. |
| **15. Criterios de aceptación** | Cada requisito DEC-20 tiene caso aprobado; opening state, operaciones abiertas, mappings, hechos/proyecciones/KPI reconcilian; stop/resume, autoridades, contingencia, BBVA/fiscal y evidencia live frente a drill son inequívocos; sólo el Superadministrador inicial tiene `GLOBAL`; discrepancias se convierten en tareas. |
| **16. Definition of Done específica** | Cada requisito de alcance tiene caso aprobado; discrepancias se convierten en tareas, no se aceptan silenciosamente. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Paquete UAT con resultado, IDs, capturas, logs, firmas y defectos. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-120 y Gate QA/Staging Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-119 — Ejecutar el ensayo integral de operación en staging**.

**Objetivo**
Probar con usuarios representativos todos los procesos diarios, semanales y administrativos incluidos.

**Problema y contexto de ZeroMerma**
La auditoría activa cubrió 106 casos, pero dejó hardware, concurrencia, permisos finos y varios módulos sin verificar. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Matriz completa de auditoría activa y pendientes.

**Dependencias que puedes asumir terminadas**
ZM-FIN-117–118 y todos los módulos Feature Complete.

**Inspección inicial obligatoria**
Usa la matriz de auditoría activa como mínimo y el alcance aprobado como máximo verificable.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Ejecutar ciclo completo; atomic outbox; fact layer/rebuild; fórmulas KPI críticas; roles/scopes; alertas A/B/C y Telegram; pérdida de Internet con operación LAN; fallos/recovery; firmas.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No marcar aprobado sólo porque la pantalla carga. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Todos los casos bloqueados/no verificados, recuperación y multi-sucursal.

**Concurrencia y consistencia**
Incluye pruebas coordinadas y carga representativa ya definida.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Todos los casos auditados fallidos/bloqueados/no verificados, más escenarios profesionales añadidos.

**Validación y comandos**
E2E automatizado más ejecución manual guiada; conservar evidencia. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada requisito de alcance tiene caso aprobado; discrepancias se convierten en tareas, no se aceptan silenciosamente.
Definition of Done específica: Cada requisito de alcance tiene caso aprobado; discrepancias se convierten en tareas, no se aceptan silenciosamente. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Actualizar resultados UAT y manuales si la operación difiere.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-120 — Ejecutar la revisión formal de readiness

**Épica:** Gates
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Aplicar Async/QA/Production/Pilot actualizados; ninguna DEC satisface gate y lakehouse/IA/WhatsApp no bloquean v1.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-120 |
| **2. Nombre de la tarea** | Ejecutar la revisión formal de readiness |
| **3. Objetivo** | Aprobar o rechazar con evidencia los gates Development Complete, Feature Complete, Data Integrity Ready, Security Ready, QA Ready, Staging Ready y Production Ready. |
| **4. Problema que resuelve** | El producto no puede llegar a piloto por acumulación informal de tareas; se requieren puertas objetivas. |
| **5. Hallazgo relacionado** | Conclusión de ambas auditorías: no apto para producción. |
| **6. Módulos afectados** | Producto, engineering, QA, security, data, SRE y business ownership. |
| **7. Archivos/áreas a inspeccionar** | Plan maestro; CI artifacts; audit evidence; risk register; decisions; release manifest. |
| **8. Dependencias previas** | ZM-FIN-001–119. |
| **9. Cambios a implementar** | Revisar criterios globales y evidencia actualizada por DEC-17–20; aprobar G1–G7 antes de G8; validar Sucursal Matriz, SITE-A, DUR-C, STOP-B, autoridades, stop-only, ROL-B, REL-C y gates BBVA/fiscales; clasificar excepciones y rechazar gate por crítico/alto, evidencia incompleta o contradicción; no exigir lakehouse/IA/WhatsApp. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Convertir gate en ceremonia o aceptar excepciones sin impacto/owner/fecha. |
| **13. Posibles regresiones** | Ninguna funcional; riesgo de retrasar release por evidencia insuficiente, que es correcto. |
| **14. Pruebas requeridas** | Evidencia faltante, test flaky, riesgo aceptado, módulo excluido visible, restore fallido y vulnerabilidad abierta. |
| **15. Criterios de aceptación** | Cada gate tiene decisión explícita y firmada; Production Ready sólo se aprueba tras todos los gates previos y Pilot Ready sólo después de Production Ready, sin usar el piloto como sustituto de QA ni marcar G8/G9 por aprobación documental. |
| **16. Definition of Done específica** | Cada gate tiene decisión explícita y firmada; Production Ready sólo se aprueba si todos los gates previos están aprobados sin contradicción. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Acta de gate con evidencia enlazada, excepciones, responsables y decisión go/no-go. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-121–126. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-120 — Ejecutar la revisión formal de readiness**.

**Objetivo**
Aprobar o rechazar con evidencia los gates Development Complete, Feature Complete, Data Integrity Ready, Security Ready, QA Ready, Staging Ready y Production Ready.

**Problema y contexto de ZeroMerma**
El producto no puede llegar a piloto por acumulación informal de tareas; se requieren puertas objetivas. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Conclusión de ambas auditorías: no apto para producción.

**Dependencias que puedes asumir terminadas**
ZM-FIN-001–119.

**Inspección inicial obligatoria**
Inspecciona resultados reales, no estados declarados; contrasta con auditorías y plan.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Revisar criterios globales y evidencia Async/QA/Production actualizada por DEC-17/18; clasificar excepciones; rechazar gate por hallazgo crítico/alto, decisión bloqueante pendiente o evidencia incompleta; no exigir lakehouse/IA/WhatsApp.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No aprobar condicionalmente un control crítico sin evidencia ni crear porcentajes de avance. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Función excluida, riesgo residual, proveedor pendiente, restore parcial y hardware no validado.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Evidencia faltante, test flaky, riesgo aceptado, módulo excluido visible, restore fallido y vulnerabilidad abierta.

**Validación y comandos**
No requiere nuevos cambios; ejecutar verificaciones reproducibles citadas y confirmar hashes. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada gate tiene decisión explícita y firmada; Production Ready sólo se aprueba si todos los gates previos están aprobados sin contradicción.
Definition of Done específica: Cada gate tiene decisión explícita y firmada; Production Ready sólo se aprueba si todos los gates previos están aprobados sin contradicción. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Acta única de readiness y actualización del plan/decisiones.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-121 — Preparar sitio piloto, hardware, red y migración de datos

**Épica:** Piloto
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Sitio con mini-PC primario, standby controlado, LAN y backup off-site; probar sin Internet, no browser offline.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-121 |
| **2. Nombre de la tarea** | Preparar sitio piloto, hardware, red y migración de datos |
| **3. Objetivo** | Preparar exclusivamente Sucursal Matriz como única branch piloto inicial, con reversa, soporte y evidencia, sin mapping implícito con seed `MAIN`. |
| **4. Problema que resuelve** | Hardware/red/migración real no fueron verificados y son necesarios para operación comercial. |
| **5. Hallazgo relacionado** | Elementos no verificables de ambas auditorías. |
| **6. Módulos afectados** | Pilot branch, workstations, network, hardware, users, catalog/inventory y production infrastructure. |
| **7. Archivos/áreas a inspeccionar** | Site survey; installation package; migration tools; branch config; backup/cutover plan. |
| **8. Dependencias previas** | Gate Production Ready aprobado y ZM-FIN-112–116. |
| **9. Cambios a implementar** | Crear/identificar productivamente Sucursal Matriz (`pilot_branch_count=1`) sin inferir `MAIN`; inventariar energía/red/equipos; instalar mini-PC primario y standby, LAN/estaciones/hardware; backup off-site; cargar master data aprobada; configurar usuarios/roles/scopes y Superadministrador; registrar conteo/opening state; reconciliar operaciones abiertas; probar Internet caído, RPO/RTO, stop-only, rollback y soporte. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Datos iniciales incorrectos, hardware no soportado o red sin contingencia. |
| **13. Posibles regresiones** | Operación actual de la sucursal durante transición. |
| **14. Pruebas requeridas** | Equipo incompatible, red caída, saldo inicial, usuario incorrecto, printer/terminal, rollback y datos legacy. |
| **15. Criterios de aceptación** | `pilot_site=Sucursal Matriz`, `pilot_branch_count=1` y `seed_MAIN_is_not_implicitly_Matriz=true`; sitio pasa checklist LOCAL_FIRST; historia inicia limpia; scopes, master data, opening state y operaciones abiertas tienen evidencia firmada; primario/standby/LAN/hardware/backup/soporte pasan smoke; outage autoritativo aplica stop-only y no existe browser offline. |
| **16. Definition of Done específica** | Sitio pasa checklist; datos iniciales reconcilian; hardware y connectivity smoke pasan; fallback probado. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Checklist firmado, inventario, reconciliación y plan de cutover. |
| **18. Requiere migración DB** | Sí |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-122–124 y Gate Pilot Ready. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-121 — Preparar sitio piloto, hardware, red y migración de datos**.

**Objetivo**
Convertir una panadería real en un entorno controlado de piloto con reversa y soporte.

**Problema y contexto de ZeroMerma**
Hardware/red/migración real no fueron verificados y son necesarios para operación comercial. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Elementos no verificables de ambas auditorías.

**Dependencias que puedes asumir terminadas**
Gate Production Ready aprobado y ZM-FIN-112–116.

**Inspección inicial obligatoria**
Realiza site survey y contrasta con matriz de hardware/red soportada.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Inventariar red/equipos; instalar mini-PC primario y standby controlado; LAN/estaciones; backup off-site; configurar/migrar/reconciliar; probar operación sin Internet, RPO/RTO, fallback y soporte.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No hacer cutover real en esta tarea. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Reemplazo de caja, impresora distinta, catálogo incompleto, stock inicial y rollback al proceso anterior.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: Sí. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Equipo incompatible, red caída, saldo inicial, usuario incorrecto, printer/terminal, rollback y datos legacy.

**Validación y comandos**
Dry run de migración, install/smoke y restore/fallback en entorno de ensayo. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Sitio pasa checklist; datos iniciales reconcilian; hardware y connectivity smoke pasan; fallback probado.
Definition of Done específica: Sitio pasa checklist; datos iniciales reconcilian; hardware y connectivity smoke pasan; fallback probado. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Plan de sitio, cutover y contactos.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-122 — Capacitar, ensayar y ejecutar el cutover del piloto

**Épica:** Piloto
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: staging/piloto/gates generan evidencia LOCAL_FIRST y KPI/alertas válidos; lakehouse/IA/WhatsApp no bloquean v1.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-122 |
| **2. Nombre de la tarea** | Capacitar, ensayar y ejecutar el cutover del piloto |
| **3. Objetivo** | Poner el sitio piloto en operación con usuarios capacitados, soporte activo y criterios de aborto. |
| **4. Problema que resuelve** | La capacitación y operación real no fueron cubiertas por auditoría. |
| **5. Hallazgo relacionado** | Brecha operativa profesional. |
| **6. Módulos afectados** | Pilot users, POS/Backoffice, support, SRE y business owner. |
| **7. Archivos/áreas a inspeccionar** | Training materials; SOPs; cutover checklist; support channels; release manifest. |
| **8. Dependencias previas** | ZM-FIN-105, ZM-FIN-121 y Gate Pilot Ready. |
| **9. Cambios a implementar** | Capacitar por rol con checklist observado/firmado; practicar stop, incidente y contingencia; respaldar y congelar; ejecutar cutover firmado con artefacto/opening state idempotentes; confirmar único `GLOBAL`; aplicar stop-only inicial; disponer rollback; exigir dual authority para resume crítico; habilitar BBVA sólo con gates completos; smoke y primera sesión supervisada. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Operar sin conocimiento, cambiar configuración durante cutover o no abortar ante discrepancia. |
| **13. Posibles regresiones** | Interrupción del negocio piloto. |
| **14. Pruebas requeridas** | Usuario ausente, credencial fallida, hardware failure, dato discrepante, payment provider y rollback. |
| **15. Criterios de aceptación** | Usuarios demuestran tareas críticas con evidencia firmada; cutover usa artefacto/dataset aprobados, stop-only inicial y rollback; resume crítico tiene aprobación técnica/administrativa; BBVA permanece deshabilitado hasta gates; opening state/excepciones reconcilian; soporte, runbooks, smoke y primera apertura pasan. |
| **16. Definition of Done específica** | Usuarios demuestran tareas críticas; cutover usa artefacto aprobado; smoke y primera apertura pasan; soporte y rollback están disponibles. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Firmas de capacitación, checklist de cutover, release IDs y resultado de smoke. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-123–124. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-122 — Capacitar, ensayar y ejecutar el cutover del piloto**.

**Objetivo**
Poner el sitio piloto en operación con usuarios capacitados, soporte activo y criterios de aborto.

**Problema y contexto de ZeroMerma**
La capacitación y operación real no fueron cubiertas por auditoría. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Brecha operativa profesional.

**Dependencias que puedes asumir terminadas**
ZM-FIN-105, ZM-FIN-121 y Gate Pilot Ready.

**Inspección inicial obligatoria**
Verifica que manuales, usuarios, hardware, backup y contactos estén vigentes.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Capacitar por rol; practicar escenarios; respaldar; congelar cambios; ejecutar migración final/deploy; smoke; abrir primera sesión bajo supervisión; definir abort/rollback.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No introducir cambios de código durante cutover salvo procedimiento de hotfix aprobado. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Cambio de turno, ausencia de internet, terminal caída, impresora y recuperación.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Usuario ausente, credencial fallida, hardware failure, dato discrepante, payment provider y rollback.

**Validación y comandos**
Ejecuta checklist, smoke, backup y validaciones; registrar cada paso. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Usuarios demuestran tareas críticas; cutover usa artefacto aprobado; smoke y primera apertura pasan; soporte y rollback están disponibles.
Definition of Done específica: Usuarios demuestran tareas críticas; cutover usa artefacto aprobado; smoke y primera apertura pasan; soporte y rollback están disponibles. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Registro de capacitación/cutover y cualquier desviación.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-123 — Operar reconciliación diaria y respuesta de incidentes del piloto

**Épica:** Piloto
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Reconciliar fact layer/proyecciones, validez KPI y backlog alertas/Telegram; no ocultar discrepancias en agregados.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-123 |
| **2. Nombre de la tarea** | Operar reconciliación diaria y respuesta de incidentes del piloto |
| **3. Objetivo** | Verificar cada ciclo operativo con datos, no sólo disponibilidad visual. |
| **4. Problema que resuelve** | Los defectos auditados afectaban caja, inventario y outbox de forma silenciosa; el piloto debe detectarlos inmediatamente. |
| **5. Hallazgo relacionado** | ZMA-FIN-001; ZMA-DATA-001; ZMA-ASYNC-001. |
| **6. Módulos afectados** | Pilot branch, ledgers, cash closes, inventory, worker, observability y support. |
| **7. Archivos/áreas a inspeccionar** | Reconciliation scripts; dashboards; incident process; audit logs. |
| **8. Dependencias previas** | ZM-FIN-122 y runbooks/SLOs. |
| **9. Cambios a implementar** | Reconciliar cada cierre y diariamente contra opening state, mappings, ventas/orders/payments/PaymentLeg/refunds/caja/inventario/producción/merma/outbox/proyecciones; reconciliar adicionalmente tras incidente, hotfix, restore, failover, contingencia o correctivo; revisar alertas/Telegram, clasificar incidentes y preservar evidencia. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Normalizar discrepancias como operación cotidiana o corregir DB manualmente. |
| **13. Posibles regresiones** | Carga operativa adicional durante piloto. |
| **14. Pruebas requeridas** | Diferencia de caja, stock negativo, backlog, refund pendiente, hardware y red. |
| **15. Criterios de aceptación** | Cada cierre, día y evento extraordinario tiene reconciliación aplicable; antes de expansión existe reconciliación integral firmada; ninguna discrepancia queda sin causa/owner; demo/test no se normaliza como real; stop/rollback, alertas, incidentes y acciones quedan auditados. |
| **16. Definition of Done específica** | No queda discrepancia sin causa/owner; incidentes críticos activan stop/rollback; datos se preservan y acciones quedan auditadas. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Reportes de reconciliación, incidentes, tiempos y decisiones diarias. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-124 y Gate General Production. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-123 — Operar reconciliación diaria y respuesta de incidentes del piloto**.

**Objetivo**
Verificar cada ciclo operativo con datos, no sólo disponibilidad visual.

**Problema y contexto de ZeroMerma**
Los defectos auditados afectaban caja, inventario y outbox de forma silenciosa; el piloto debe detectarlos inmediatamente. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
ZMA-FIN-001; ZMA-DATA-001; ZMA-ASYNC-001.

**Dependencias que puedes asumir terminadas**
ZM-FIN-122 y runbooks/SLOs.

**Inspección inicial obligatoria**
Usa queries/scripts canónicos y dashboards; no depender sólo de comentarios de usuarios.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Tras cada ciclo reconciliar dominio, outbox/audit, fact layer/proyecciones y KPI; revisar validez/DQ y backlog de alertas/Telegram; clasificar incidentes; aplicar sólo runbooks/compensaciones aprobados.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No editar filas directamente ni ocultar incidentes para mantener el piloto. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Diferencia pequeña, evento tardío, cierre reabierto no permitido, fallo de provider y ajuste necesario.

**Concurrencia y consistencia**
Investigar locks/deadlocks observados y mantener evidencia.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Diferencia de caja, stock negativo, backlog, refund pendiente, hardware y red.

**Validación y comandos**
Ejecutar reconciliaciones y smoke definidos; no consultas mutantes ad hoc. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
No queda discrepancia sin causa/owner; incidentes críticos activan stop/rollback; datos se preservan y acciones quedan auditadas.
Definition of Done específica: No queda discrepancia sin causa/owner; incidentes críticos activan stop/rollback; datos se preservan y acciones quedan auditadas. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Bitácora piloto e incidentes/postmortems.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-124 — Cerrar estabilización y aprobar expansión

**Épica:** Piloto
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Calibrar con 2–4 semanas reales; sensibilidad intermedia requiere evidencia y lakehouse no bloquea expansión.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-124 |
| **2. Nombre de la tarea** | Cerrar estabilización y aprobar expansión |
| **3. Objetivo** | Determinar con evidencia si el piloto cubrió los ciclos representativos y no dejó riesgos bloqueantes. |
| **4. Problema que resuelve** | Un piloto no puede considerarse exitoso por tiempo transcurrido o ausencia de quejas. |
| **5. Hallazgo relacionado** | Criterios de producción derivados de ambas auditorías. |
| **6. Módulos afectados** | Producto, QA, security, data, SRE, support y business owner. |
| **7. Archivos/áreas a inspeccionar** | Pilot logs; incidents; reconciliations; UAT; release history; user feedback. |
| **8. Dependencias previas** | ZM-FIN-123 y cadencias operativas aprobadas. |
| **9. Cambios a implementar** | Confirmar dos ciclos semanales operativos completos y cobertura live obligatoria; extender automáticamente por evidencia faltante; cerrar defectos; aplicar STOP-B y taxonomías separadas; repetir gates/evidencia invalidada por hotfix; evaluar KPI/alerting; actualizar capacidad/runbooks; obtener aprobación técnica y administrativa de expansión. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Expandir por presión comercial o considerar workaround como solución. |
| **13. Posibles regresiones** | Ninguna funcional; decisión de go/no-go. |
| **14. Pruebas requeridas** | Incidente reabierto, workaround manual, proceso no observado, discrepancia resuelta sin causa y release hotfix. |
| **15. Criterios de aceptación** | Dos ciclos semanales completos y cadencias obligatorias están cubiertos; no hay `CRITICAL`, blocker `HIGH` ni `CRITICAL-A` activa sin resolver; reconciliaciones/KPI son válidos; no hay workaround inseguro ni paso manual crítico oculto; expansión tiene dual approval y lakehouse no bloquea. |
| **16. Definition of Done específica** | No hay Sev crítico/alto abierto; reconciliaciones pasan; todos los procesos representativos fueron observados; soporte y usuarios aceptan operación. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Acta Pilot Ready→General Production con evidencia, riesgos residuales y alcance de expansión. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | No |
| **21. Requiere cambios Backoffice** | No |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-125–126. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-124 — Cerrar estabilización y aprobar expansión**.

**Objetivo**
Determinar con evidencia si el piloto cubrió los ciclos representativos y no dejó riesgos bloqueantes.

**Problema y contexto de ZeroMerma**
Un piloto no puede considerarse exitoso por tiempo transcurrido o ausencia de quejas. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Criterios de producción derivados de ambas auditorías.

**Dependencias que puedes asumir terminadas**
ZM-FIN-123 y cadencias operativas aprobadas.

**Inspección inicial obligatoria**
Revisa evidencia completa del piloto y repite verificaciones afectadas por hotfixes.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Confirmar procesos recurrentes; cerrar defectos; repetir gates; evaluar dashboard selectivo y alerting conservador; iniciar calibración con 2–4 semanas reales; actualizar capacidad/runbooks; go/no-go sin exigir lakehouse.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No usar porcentajes arbitrarios ni aprobar con defectos críticos/altos abiertos. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Proceso de baja frecuencia no observado, cambio de proveedor/hardware y riesgo aceptado.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: No. Cambios Backoffice: No. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Incidente reabierto, workaround manual, proceso no observado, discrepancia resuelta sin causa y release hotfix.

**Validación y comandos**
Reejecuta gates y reconciliaciones; verifica digests de la versión final. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
No hay Sev crítico/alto abierto; reconciliaciones pasan; todos los procesos representativos fueron observados; soporte y usuarios aceptan operación.
Definition of Done específica: No hay Sev crítico/alto abierto; reconciliaciones pasan; todos los procesos representativos fueron observados; soporte y usuarios aceptan operación. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Acta de estabilización y actualización de runbooks.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-125 — Desplegar ZeroMerma por oleadas controladas

**Épica:** Producción general
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Referencia DEC-17/DEC-18: staging/piloto/gates generan evidencia LOCAL_FIRST y KPI/alertas válidos; lakehouse/IA/WhatsApp no bloquean v1.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-125 |
| **2. Nombre de la tarea** | Desplegar ZeroMerma por oleadas controladas |
| **3. Objetivo** | Expandir a las sucursales aprobadas conservando reversa, observabilidad y aislamiento. |
| **4. Problema que resuelve** | La producción general requiere demostrar multi-sucursal, instalación y soporte más allá del piloto. |
| **5. Hallazgo relacionado** | Objetivo final; ZM-SEC-002; ZM-OPS-014. |
| **6. Módulos afectados** | All branches, deployment, data migration, support y operations. |
| **7. Archivos/áreas a inspeccionar** | Rollout plan; site checklists; release pipeline; branch configs; migration/reconciliation. |
| **8. Dependencias previas** | ZM-FIN-124 y Gate General Production aprobado. |
| **9. Cambios a implementar** | Aplicar `one_branch_per_wave=true`; repetir prepare/cutover/reconcile/stabilize/approve; mantener `controlled_release_line=true` con release piloto/hotfixes revalidados; pausar nuevas oleadas ante incidente material; demostrar aislamiento antes de continuar sitios operativos; conservar aprobación técnica/administrativa. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Blast radius, configuración cross-branch o soporte insuficiente. |
| **13. Posibles regresiones** | Carga de plataforma y procesos del piloto. |
| **14. Pruebas requeridas** | Sucursal con hardware distinto, datos legacy, zona horaria/red, incidente en una oleada y rollback selectivo. |
| **15. Criterios de aceptación** | Una sola sucursal entra por oleada; cada sitio pasa checklist, estabilización, reconciliación y aprobación antes de continuar; `wave_pause_on_material_incident=true`; no hay drift libre, big bang ni contaminación cross-branch; rollout es trazable. |
| **16. Definition of Done específica** | Cada sucursal pasa checklist y reconciliación antes de continuar; un fallo no compromete aislamiento de otras; rollout es trazable. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Registro por sucursal, release IDs, reconciliaciones y decisiones de continuar/pausar. |
| **18. Requiere migración DB** | Posible |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | ZM-FIN-126 y operación general. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-125 — Desplegar ZeroMerma por oleadas controladas**.

**Objetivo**
Expandir a las sucursales aprobadas conservando reversa, observabilidad y aislamiento.

**Problema y contexto de ZeroMerma**
La producción general requiere demostrar multi-sucursal, instalación y soporte más allá del piloto. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Objetivo final; ZM-SEC-002; ZM-OPS-014.

**Dependencias que puedes asumir terminadas**
ZM-FIN-124 y Gate General Production aprobado.

**Inspección inicial obligatoria**
Inspecciona diferencias de cada sitio y capacidad real antes de agrupar.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Agrupar sitios por riesgo/compatibilidad; repetir preparación/capacitación/cutover/reconciliación; pausar expansión ante criterio de stop; mantener mismo artefacto o release aprobado.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No desplegar a todas las sucursales simultáneamente sin evidencia de capacidad y reversa. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Rollout parcial, sucursal rollback, release hotfix, branch offline y configuración global.

**Concurrencia y consistencia**
Múltiples cutovers sólo si soporte/infra y aislamiento han sido demostrados; serializar migraciones sensibles.

**Migraciones y contratos**
Migración de base de datos: Posible. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Sucursal con hardware distinto, datos legacy, zona horaria/red, incidente en una oleada y rollback selectivo.

**Validación y comandos**
Pipeline de promoción, site smoke y reconciliación por sucursal. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Cada sucursal pasa checklist y reconciliación antes de continuar; un fallo no compromete aislamiento de otras; rollout es trazable.
Definition of Done específica: Cada sucursal pasa checklist y reconciliación antes de continuar; un fallo no compromete aislamiento de otras; rollout es trazable. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Plan/registro de rollout y soporte.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

### ZM-FIN-126 — Verificar post-producción y transferir operación

**Épica:** Cierre de producto
**Alineación canónica DEC-17/DEC-18 — criterio adicional obligatorio:** Handover asigna owners KPI/alertas/DQ/archive/backup/event contracts; lakehouse no es requisito v1.

| Campo | Especificación |
|---|---|
| **1. ID único** | ZM-FIN-126 |
| **2. Nombre de la tarea** | Verificar post-producción y transferir operación |
| **3. Objetivo** | Cerrar formalmente el programa de finalización y dejar el producto bajo operación/mantenimiento continuo. |
| **4. Problema que resuelve** | El estado terminado requiere evidencia sostenida, ownership y backlog residual, no sólo un despliegue exitoso. |
| **5. Hallazgo relacionado** | Resultado final solicitado por el propietario. |
| **6. Módulos afectados** | Product, engineering, QA, security, SRE, support y business operations. |
| **7. Archivos/áreas a inspeccionar** | Production dashboards; incident history; docs; ownership; backlog; release artifacts. |
| **8. Dependencias previas** | ZM-FIN-125 y periodo/cadencias representativas aprobadas. |
| **9. Cambios a implementar** | Verificar por sucursal SLO, reconciliaciones, versión/configuración, KPI/DQ, backups/restores, alertas, seguridad, runbooks y capacidad de soporte; cerrar/aceptar riesgos; archivar evidencia; transferir ownership de operación, hardware, KPI, alertas, backup y contratos de eventos. |
| **10. Restricciones arquitectónicas** | Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia. |
| **11. Decisiones a conservar** | Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno. |
| **12. Riesgos** | Declarar cierre mientras subsisten workarounds o conocimiento sólo en el equipo de implementación. |
| **13. Posibles regresiones** | Ninguna funcional; transición de ownership. |
| **14. Pruebas requeridas** | Incidente reciente, drift, backup no probado, alertas sin owner, dependencia vulnerable y proceso de baja frecuencia. |
| **15. Criterios de aceptación** | Se cumplen General Production y handover por sucursal; soporte acepta capacidad y escalamiento; reconciliación, versiones, runbooks, ownership y evidencia son trazables; no existen blockers críticos/altos abiertos ni pasos manuales críticos ocultos. |
| **16. Definition of Done específica** | Se cumplen criterios de ZeroMerma terminado y General Production; owners aceptan operación; no hay bloqueos críticos/altos abiertos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta. |
| **17. Evidencia de terminación** | Informe final, hashes de release, actas de gates, ownership y backlog residual priorizado. |
| **18. Requiere migración DB** | No |
| **19. Requiere OpenAPI/cliente TS** | No |
| **20. Requiere cambios POS** | Sí |
| **21. Requiere cambios Backoffice** | Sí |
| **22. Requiere cambios de infraestructura** | Sí |
| **23. Tareas posteriores que desbloquea** | Operación continua, analítica/IA y evolución del producto. |

#### Prompt de Codex

```text
Trabaja exclusivamente en la tarea **ZM-FIN-126 — Verificar post-producción y transferir operación**.

**Objetivo**
Cerrar formalmente el programa de finalización y dejar el producto bajo operación/mantenimiento continuo.

**Problema y contexto de ZeroMerma**
El estado terminado requiere evidencia sostenida, ownership y backlog residual, no sólo un despliegue exitoso. ZeroMerma debe conservar su monolito modular con FastAPI, SQLAlchemy y PostgreSQL; POS y Backoffice siguen separados; OpenAPI es la fuente contractual; dinero y cantidades mantienen precisión Decimal/Numeric; auditoría y outbox deben permanecer dentro de las transacciones de negocio.

**Hallazgos relacionados**
Resultado final solicitado por el propietario.

**Dependencias que puedes asumir terminadas**
ZM-FIN-125 y periodo/cadencias representativas aprobadas.

**Inspección inicial obligatoria**
Revisa producción real, no sólo staging/piloto; contrasta con Definition of Done global.
Localiza los símbolos y archivos reales antes de editar. Si las rutas probables del plan no coinciden con el repositorio, informa la discrepancia y usa la evidencia del código vigente como fuente superior.

**Alcance de implementación**
Verificar SLO, reconciliaciones, KPI/DQ, backups/restores, alertas, seguridad y soporte; cerrar/aceptar riesgos; archivar evidencia; transferir owners de KPI/alertas/archive/backup/event contracts.

**Comportamiento y decisiones que debes preservar**
Compatibilidad con la arquitectura vigente, la experiencia táctil del POS, el cliente generado y la trazabilidad por usuario, sucursal, caja, estación y turno.

**Restricciones arquitectónicas**
Conservar el monolito modular, FastAPI/SQLAlchemy/PostgreSQL, POS y Backoffice separados, OpenAPI como contrato fuente, tipos Decimal/Numeric, auditoría y outbox transaccionales. No introducir microservicios, repositorios paralelos, tipos de dominio manuales en frontend ni una reescritura amplia.

**No debes hacer**
No eliminar historial ni convertir el backlog residual en trabajo oculto. No realices refactors amplios, reescrituras ni cambios fuera del alcance salvo que sean estrictamente necesarios para cumplir el criterio. Si descubres otro defecto, documéntalo por separado con evidencia y propuesta de backlog; no lo mezcles silenciosamente.

**Edge cases**
Riesgo residual aceptado, proveedor pendiente, proceso estacional y cambio de owner.

**Concurrencia y consistencia**
No aplica salvo que las pruebas de la tarea indiquen lo contrario.

**Migraciones y contratos**
Migración de base de datos: No. Regenerar OpenAPI/cliente TypeScript: No. Cambios POS: Sí. Cambios Backoffice: Sí. Cambios de infraestructura: Sí. Si una migración es necesaria, debe ser compatible con la cadena vigente, probarse desde base vacía y desde las versiones soportadas, y contar con estrategia de roll-forward/restore.

**Pruebas obligatorias**
Incidente reciente, drift, backup no probado, alertas sin owner, dependencia vulnerable y proceso de baja frecuencia.

**Validación y comandos**
Ejecuta smoke, reconciliaciones, restore evidence check, security scan y verificación de observabilidad. Ejecuta sólo contra entornos seguros y aislados. Incluye lint, typecheck, unitarias, integración, contract/E2E y build únicamente cuando correspondan al alcance. Registra el comando exacto y su resultado; no digas “pasa” sin salida verificable.

**Criterios para considerar terminada la tarea**
Se cumplen criterios de ZeroMerma terminado y General Production; owners aceptan operación; no hay bloqueos críticos/altos abiertos.
Definition of Done específica: Se cumplen criterios de ZeroMerma terminado y General Production; owners aceptan operación; no hay bloqueos críticos/altos abiertos. Los cambios aplicables, pruebas y documentación quedan integrados; no existen cambios accidentales y la evidencia solicitada está adjunta.

**Documentación**
Informe final y actualización del único plan/decisiones a estado cerrado/operación.

**Reporte final obligatorio**
Al terminar, reporta: resumen técnico; archivos modificados; migraciones; cambios OpenAPI/cliente; pruebas y comandos con resultado exacto; evidencia por criterio de aceptación; riesgos pendientes; hallazgos fuera de alcance; y estado Git final.
```

## 10. Criterios finales de declaración

### 10.1 Cuándo puede afirmarse técnicamente que ZeroMerma está terminado
Sólo cuando G1 Development Complete y G2 Feature Complete estén aprobados, y el alcance aprobado no contenga placeholders, deuda funcional oculta ni decisiones de negocio pendientes. Esto significa producto completo en código y pruebas, pero todavía no autorización para operar.

### 10.2 Cuándo puede afirmarse que está listo para producción
Sólo cuando G3 Data Integrity Ready, G4 Security Ready, G5 QA Ready, G6 Staging Ready y G7 Production Ready estén aprobados. En particular, restore, rollback, observabilidad, hardware y seguridad deben tener evidencia; no basta con “funciona en desarrollo”.

### 10.3 Cuándo puede afirmarse que está listo para piloto
Sólo cuando G8 Pilot Ready esté aprobado: sitio, red, hardware, datos, capacitación, soporte y cutover fueron ensayados y el release es exactamente el aprobado en Production Ready.

### 10.4 Cuándo puede afirmarse que está en producción general
Sólo cuando G9 General Production esté aprobado después de un piloto que cubra todas las cadencias representativas del negocio, sin defectos críticos/altos abiertos, con reconciliación de caja, inventario y outbox, y con ownership operativo transferido.
## 11. Control de trazabilidad
- Número total de tareas: **126**.
- Cada tarea contiene los 23 campos obligatorios y un prompt autocontenido.
- Los hallazgos `ZM-*` y `ZMA-*` están asignados a tareas específicas; las brechas no auditadas se identifican como propuestas profesionales, no como defectos comprobados.
- Los resultados futuros de Codex deben actualizar estado/evidencia de la tarea correspondiente; no se declara cierre sin pruebas.
- Cualquier cambio fuera de alcance descubierto durante una tarea se registra por separado en el backlog y no se mezcla silenciosamente.
